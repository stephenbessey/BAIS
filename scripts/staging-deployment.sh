#!/bin/bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly STAGING_NAMESPACE="bais-staging"
readonly PRODUCTION_NAMESPACE="bais-production"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error_exit() {
    log "ERROR: $1" >&2
    exit 1
}

verify_prerequisites() {
    command -v kubectl >/dev/null 2>&1 || error_exit "kubectl is required"
    command -v docker >/dev/null 2>&1 || error_exit "docker is required"
    command -v jq >/dev/null 2>&1 || error_exit "jq is required"
    
    kubectl cluster-info >/dev/null 2>&1 || error_exit "Cannot connect to Kubernetes cluster"
}

create_staging_namespace() {
    log "Creating staging namespace..."
    
    kubectl create namespace "${STAGING_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
    
    kubectl label namespace "${STAGING_NAMESPACE}" \
        environment=staging \
        team=platform \
        monitoring=enabled
}

deploy_database_staging() {
    log "Deploying staging database..."
    
    kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-staging-config
  namespace: ${STAGING_NAMESPACE}
data:
  POSTGRES_DB: "bais_staging"
  POSTGRES_MAX_CONNECTIONS: "200"
  POSTGRES_SHARED_BUFFERS: "1GB"
  POSTGRES_EFFECTIVE_CACHE_SIZE: "3GB"
  POSTGRES_WORK_MEM: "4MB"
---
apiVersion: v1
kind: Secret
metadata:
  name: postgres-staging-credentials
  namespace: ${STAGING_NAMESPACE}
type: Opaque
data:
  POSTGRES_PASSWORD: $(echo -n "staging_password_$(openssl rand -hex 16)" | base64)
  POSTGRES_USER: $(echo -n "bais_staging_user" | base64)
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres-staging
  namespace: ${STAGING_NAMESPACE}
  labels:
    app: postgres-staging
    environment: staging
spec:
  serviceName: postgres-staging
  replicas: 1
  selector:
    matchLabels:
      app: postgres-staging
  template:
    metadata:
      labels:
        app: postgres-staging
        environment: staging
    spec:
      securityContext:
        runAsUser: 999
        runAsGroup: 999
        fsGroup: 999
      containers:
      - name: postgres
        image: postgres:15.4-alpine
        ports:
        - containerPort: 5432
          name: postgres
        envFrom:
        - configMapRef:
            name: postgres-staging-config
        - secretRef:
            name: postgres-staging-credentials
        volumeMounts:
        - name: postgres-staging-data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - bais_staging_user
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - bais_staging_user
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          runAsNonRoot: true
          runAsUser: 999
          runAsGroup: 999
          capabilities:
            drop:
            - ALL
  volumeClaimTemplates:
  - metadata:
      name: postgres-staging-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: standard
      resources:
        requests:
          storage: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-staging
  namespace: ${STAGING_NAMESPACE}
  labels:
    app: postgres-staging
spec:
  selector:
    app: postgres-staging
  ports:
  - name: postgres
    port: 5432
    targetPort: 5432
  type: ClusterIP
EOF
}

deploy_redis_staging() {
    log "Deploying staging Redis..."
    
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-staging
  namespace: ${STAGING_NAMESPACE}
  labels:
    app: redis-staging
    environment: staging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-staging
  template:
    metadata:
      labels:
        app: redis-staging
        environment: staging
    spec:
      securityContext:
        runAsUser: 999
        runAsGroup: 999
        fsGroup: 999
      containers:
      - name: redis
        image: redis:7.2-alpine
        ports:
        - containerPort: 6379
          name: redis
        command:
        - redis-server
        - --appendonly
        - "yes"
        - --maxmemory
        - "1gb"
        - --maxmemory-policy
        - "allkeys-lru"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          runAsNonRoot: true
          runAsUser: 999
          runAsGroup: 999
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: redis-staging-data
          mountPath: /data
      volumes:
      - name: redis-staging-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: redis-staging
  namespace: ${STAGING_NAMESPACE}
  labels:
    app: redis-staging
spec:
  selector:
    app: redis-staging
  ports:
  - name: redis
    port: 6379
    targetPort: 6379
  type: ClusterIP
EOF
}

deploy_application_staging() {
    log "Deploying BAIS application to staging..."
    
    local IMAGE_TAG="${1:-latest}"
    
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bais-staging
  namespace: ${STAGING_NAMESPACE}
  labels:
    app: bais
    environment: staging
    version: "${IMAGE_TAG}"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bais
      environment: staging
  template:
    metadata:
      labels:
        app: bais
        environment: staging
        version: "${IMAGE_TAG}"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
      - name: bais-app
        image: bais/api:${IMAGE_TAG}
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: ENVIRONMENT
          value: "staging"
        - name: DATABASE_URL
          value: "postgresql://bais_staging_user:staging_password_123@postgres-staging:5432/bais_staging"
        - name: REDIS_URL
          value: "redis://redis-staging:6379"
        - name: LOG_LEVEL
          value: "INFO"
        - name: WORKERS
          value: "2"
        - name: TIMEOUT
          value: "60"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
            scheme: HTTP
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
            scheme: HTTP
          initialDelaySeconds: 15
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 1000
          capabilities:
            drop:
            - ALL
---
apiVersion: v1
kind: Service
metadata:
  name: bais-staging-service
  namespace: ${STAGING_NAMESPACE}
  labels:
    app: bais
    environment: staging
spec:
  selector:
    app: bais
    environment: staging
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
  type: LoadBalancer
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: bais-staging-ingress
  namespace: ${STAGING_NAMESPACE}
  labels:
    app: bais
    environment: staging
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  rules:
  - host: staging-api.bais.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: bais-staging-service
            port:
              number: 80
EOF
}

wait_for_deployment() {
    local deployment_name=$1
    local timeout=${2:-300}
    
    log "Waiting for ${deployment_name} to be ready..."
    
    kubectl rollout status deployment/"${deployment_name}" \
        -n "${STAGING_NAMESPACE}" \
        --timeout="${timeout}s" || error_exit "Deployment ${deployment_name} failed"
}

wait_for_statefulset() {
    local statefulset_name=$1
    local timeout=${2:-300}
    
    log "Waiting for ${statefulset_name} to be ready..."
    
    kubectl wait --for=condition=ready pod \
        -l app="${statefulset_name}" \
        -n "${STAGING_NAMESPACE}" \
        --timeout="${timeout}s" || error_exit "StatefulSet ${statefulset_name} failed"
}

run_database_migrations() {
    log "Running database migrations..."
    
    kubectl run migration-job \
        --image=bais/api:latest \
        --restart=Never \
        --namespace="${STAGING_NAMESPACE}" \
        --env="DATABASE_URL=postgresql://bais_staging_user:staging_password_123@postgres-staging:5432/bais_staging" \
        --command -- alembic upgrade head
    
    kubectl wait --for=condition=complete \
        --timeout=300s \
        job/migration-job \
        -n "${STAGING_NAMESPACE}" || error_exit "Migration failed"
    
    kubectl delete job migration-job -n "${STAGING_NAMESPACE}"
}

validate_staging_deployment() {
    log "Validating staging deployment..."
    
    local service_url
    service_url=$(kubectl get svc bais-staging-service \
        -n "${STAGING_NAMESPACE}" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    if [[ -z "${service_url}" ]]; then
        log "LoadBalancer IP not ready, using port-forward for validation..."
        kubectl port-forward svc/bais-staging-service 8080:80 -n "${STAGING_NAMESPACE}" &
        local port_forward_pid=$!
        sleep 5
        
        service_url="localhost:8080"
    fi
    
    local health_status
    health_status=$(curl -s "http://${service_url}/health" | jq -r '.status // "unknown"')
    
    if [[ "${health_status}" != "healthy" ]]; then
        error_exit "Health check failed: ${health_status}"
    fi
    
    log "Staging deployment validated successfully"
    echo "${service_url}"
    
    if [[ -n "${port_forward_pid:-}" ]]; then
        kill $port_forward_pid 2>/dev/null || true
    fi
}

run_smoke_tests() {
    log "Running smoke tests..."
    
    kubectl run smoke-test \
        --image=bais/api:latest \
        --restart=Never \
        --namespace="${STAGING_NAMESPACE}" \
        --env="API_URL=http://bais-staging-service" \
        --command -- pytest tests/smoke/ -v
    
    kubectl wait --for=condition=complete \
        --timeout=300s \
        job/smoke-test \
        -n "${STAGING_NAMESPACE}" || error_exit "Smoke tests failed"
    
    kubectl logs job/smoke-test -n "${STAGING_NAMESPACE}"
    kubectl delete job smoke-test -n "${STAGING_NAMESPACE}"
}

generate_staging_report() {
    local staging_url=$1
    local image_tag=$2
    
    cat > "staging-deployment-report-$(date +%Y%m%d-%H%M%S).json" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "environment": "staging",
  "namespace": "${STAGING_NAMESPACE}",
  "image_tag": "${image_tag}",
  "staging_url": "http://${staging_url}",
  "status": "success",
  "components": {
    "database": "postgres-staging",
    "cache": "redis-staging",
    "application": "bais-staging",
    "ingress": "bais-staging-ingress"
  },
  "next_steps": [
    "Run acceptance tests",
    "Configure monitoring alerts",
    "Set up on-call rotation",
    "Prepare for production go-live"
  ]
}
EOF
}

main() {
    log "========================================="
    log "Starting BAIS Platform Staging Deployment"
    log "========================================="
    
    local IMAGE_TAG="${1:-latest}"
    log "Using image tag: ${IMAGE_TAG}"
    
    verify_prerequisites
    create_staging_namespace
    deploy_database_staging
    deploy_redis_staging
    deploy_application_staging "${IMAGE_TAG}"
    
    wait_for_statefulset "postgres-staging" 300
    wait_for_deployment "redis-staging" 180
    wait_for_deployment "bais-staging" 300
    
    run_database_migrations
    run_smoke_tests
    
    local staging_url
    staging_url=$(validate_staging_deployment)
    
    generate_staging_report "${staging_url}" "${IMAGE_TAG}"
    
    log "========================================="
    log "Staging Deployment Complete!"
    log "========================================="
    log "Staging URL: http://${staging_url}"
    log "Namespace: ${STAGING_NAMESPACE}"
    log "Image Tag: ${IMAGE_TAG}"
    log ""
    log "Next Steps:"
    log "1. Run acceptance tests: python scripts/acceptance_test_suite.py"
    log "2. Configure monitoring alerts: kubectl apply -f scripts/prometheus-alerts.yaml"
    log "3. Set up on-call rotation: python scripts/oncall-rotation-setup.py"
    log "4. Prepare for production go-live: bash scripts/production-golive-checklist.sh"
}

main "$@"
