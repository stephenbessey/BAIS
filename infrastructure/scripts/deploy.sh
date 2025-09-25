#!/bin/bash
# ============================================================================
# BAIS Platform - Infrastructure Deployment Scripts
# Best practices: Single Responsibility, Clear Intent, Error Handling
# ============================================================================

set -euo pipefail
IFS=$'\n\t'

# ----------------------------------------------------------------------------
# Constants and Configuration
# ----------------------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly NAMESPACE="bais-production"
readonly MONITORING_NS="monitoring"
readonly LOGGING_NS="logging"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# ----------------------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------------------

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

check_prerequisites() {
    local missing_tools=()
    
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl")
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v helm >/dev/null 2>&1 || missing_tools+=("helm")
    command -v python3 >/dev/null 2>&1 || missing_tools+=("python3")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again."
        return 1
    fi
    
    log_info "All prerequisites satisfied"
    return 0
}

check_environment() {
    local required_vars=("DATABASE_URL" "REDIS_URL" "SECRET_KEY")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        log_error "Please set the required environment variables and try again."
        return 1
    fi
    
    log_info "Environment variables validated"
    return 0
}

create_namespace() {
    local namespace=$1
    
    if kubectl get namespace "${namespace}" >/dev/null 2>&1; then
        log_info "Namespace ${namespace} already exists"
    else
        kubectl create namespace "${namespace}"
        log_info "Created namespace ${namespace}"
    fi
}

wait_for_deployment() {
    local deployment=$1
    local namespace=$2
    local timeout=${3:-300}
    
    log_info "Waiting for deployment ${deployment} in ${namespace}..."
    
    if kubectl wait --for=condition=available \
        --timeout="${timeout}s" \
        "deployment/${deployment}" \
        -n "${namespace}" >/dev/null 2>&1; then
        log_info "Deployment ${deployment} is ready"
        return 0
    else
        log_error "Deployment ${deployment} failed to become ready"
        return 1
    fi
}

wait_for_statefulset() {
    local statefulset=$1
    local namespace=$2
    local timeout=${3:-300}
    
    log_info "Waiting for StatefulSet ${statefulset} in ${namespace}..."
    
    if kubectl wait --for=condition=ready pod \
        -l app="${statefulset}" \
        -n "${namespace}" \
        --timeout="${timeout}s" >/dev/null 2>&1; then
        log_info "StatefulSet ${statefulset} is ready"
        return 0
    else
        log_error "StatefulSet ${statefulset} failed to become ready"
        return 1
    fi
}

# ----------------------------------------------------------------------------
# Database Setup
# ----------------------------------------------------------------------------

setup_postgresql() {
    log_info "Setting up PostgreSQL database..."
    
    # Create secrets
    kubectl create secret generic postgres-secrets \
        --from-literal=POSTGRES_USER="${DB_USER:-bais_user}" \
        --from-literal=POSTGRES_PASSWORD="${DB_PASSWORD:-changeme}" \
        --namespace="${NAMESPACE}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply PostgreSQL configuration
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/database/postgresql.yaml"
    
    # Wait for PostgreSQL to be ready
    wait_for_statefulset "postgres-primary" "${NAMESPACE}" 300
    
    log_info "PostgreSQL setup complete"
}

initialize_database_schema() {
    log_info "Initializing database schema..."
    
    local pod_name
    pod_name=$(kubectl get pods -n "${NAMESPACE}" \
        -l app=postgres-primary \
        -o jsonpath='{.items[0].metadata.name}')
    
    # Run migrations
    kubectl exec -n "${NAMESPACE}" "${pod_name}" -- \
        psql -U "${DB_USER:-bais_user}" -d bais_production \
        -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
    
    # Apply schema migrations
    kubectl run migration-job \
        --image=bais/api:latest \
        --restart=Never \
        --namespace="${NAMESPACE}" \
        --command -- alembic upgrade head
    
    kubectl wait --for=condition=complete job/migration-job \
        -n "${NAMESPACE}" --timeout=300s
    
    kubectl delete job migration-job -n "${NAMESPACE}"
    
    log_info "Database schema initialized"
}

# ----------------------------------------------------------------------------
# Redis Setup
# ----------------------------------------------------------------------------

setup_redis_cluster() {
    log_info "Setting up Redis cluster..."
    
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/cache/redis-cluster.yaml"
    
    # Wait for all Redis pods
    wait_for_statefulset "redis-cluster" "${NAMESPACE}" 300
    
    # Create Redis cluster
    log_info "Creating Redis cluster..."
    
    local redis_pods
    redis_pods=$(kubectl get pods -n "${NAMESPACE}" \
        -l app=redis-cluster \
        -o jsonpath='{range.items[*]}{.status.podIP}:6379 ')
    
    kubectl exec -n "${NAMESPACE}" redis-cluster-0 -- \
        redis-cli --cluster create ${redis_pods} \
        --cluster-replicas 1 --cluster-yes
    
    log_info "Redis cluster setup complete"
}

# ----------------------------------------------------------------------------
# Application Deployment
# ----------------------------------------------------------------------------

build_and_push_image() {
    log_info "Building Docker image..."
    
    docker build -t "bais/api:${VERSION:-latest}" \
        -f "${PROJECT_ROOT}/infrastructure/docker/Dockerfile" \
        "${PROJECT_ROOT}"
    
    log_info "Pushing image to registry..."
    docker push "bais/api:${VERSION:-latest}"
    
    log_info "Image build and push complete"
}

deploy_application() {
    log_info "Deploying BAIS application..."
    
    # Create application secrets
    kubectl create secret generic bais-secrets \
        --from-literal=database-url="${DATABASE_URL}" \
        --from-literal=redis-url="${REDIS_URL}" \
        --from-literal=secret-key="${SECRET_KEY}" \
        --namespace="${NAMESPACE}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy application
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/k8s/deployment.yaml"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/k8s/service.yaml"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/k8s/ingress.yaml"
    
    # Wait for deployment
    wait_for_deployment "bais-api" "${NAMESPACE}"
    
    log_info "Application deployment complete"
}

setup_autoscaling() {
    log_info "Setting up auto-scaling..."
    
    # Install metrics server if not present
    if ! kubectl get deployment metrics-server -n kube-system >/dev/null 2>&1; then
        kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    fi
    
    # Apply HPA and VPA
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/k8s/hpa.yaml"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/k8s/vpa.yaml"
    
    log_info "Auto-scaling setup complete"
}

# ----------------------------------------------------------------------------
# Monitoring Setup
# ----------------------------------------------------------------------------

setup_prometheus() {
    log_info "Setting up Prometheus monitoring..."
    
    create_namespace "${MONITORING_NS}"
    
    # Install Prometheus using Helm
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace "${MONITORING_NS}" \
        --create-namespace \
        --values "${PROJECT_ROOT}/infrastructure/monitoring/prometheus-values.yaml" \
        --wait
    
    # Apply custom config
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/monitoring/prometheus-config.yaml"
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/monitoring/alerting-rules.yaml"
    
    log_info "Prometheus setup complete"
}

setup_grafana() {
    log_info "Setting up Grafana dashboards..."
    
    # Grafana is installed with Prometheus stack
    # Import custom dashboards
    local grafana_pod
    grafana_pod=$(kubectl get pods -n "${MONITORING_NS}" \
        -l app.kubernetes.io/name=grafana \
        -o jsonpath='{.items[0].metadata.name}')
    
    kubectl exec -n "${MONITORING_NS}" "${grafana_pod}" -- \
        grafana-cli admin reset-admin-password "${GRAFANA_PASSWORD:-admin123}"
    
    log_info "Grafana setup complete"
    log_info "Grafana URL: http://$(kubectl get svc -n ${MONITORING_NS} prometheus-grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
}

# ----------------------------------------------------------------------------
# Logging Setup
# ----------------------------------------------------------------------------

setup_elasticsearch() {
    log_info "Setting up Elasticsearch..."
    
    create_namespace "${LOGGING_NS}"
    
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/logging/elasticsearch.yaml"
    
    # Wait for Elasticsearch cluster
    wait_for_statefulset "elasticsearch" "${LOGGING_NS}" 600
    
    log_info "Elasticsearch setup complete"
}

setup_logstash() {
    log_info "Setting up Logstash..."
    
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/logging/logstash-config.yaml"
    
    # Deploy Logstash
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: logstash
  namespace: ${LOGGING_NS}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: logstash
  template:
    metadata:
      labels:
        app: logstash
    spec:
      containers:
      - name: logstash
        image: docker.elastic.co/logstash/logstash:8.10.0
        ports:
        - containerPort: 5044
        volumeMounts:
        - name: config
          mountPath: /usr/share/logstash/pipeline
      volumes:
      - name: config
        configMap:
          name: logstash-config
EOF
    
    wait_for_deployment "logstash" "${LOGGING_NS}"
    
    log_info "Logstash setup complete"
}

setup_kibana() {
    log_info "Setting up Kibana..."
    
    # Create Elasticsearch credentials secret
    kubectl create secret generic elastic-credentials \
        --from-literal=username="${ELASTIC_USER:-elastic}" \
        --from-literal=password="${ELASTIC_PASSWORD:-changeme}" \
        --namespace="${LOGGING_NS}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/logging/kibana.yaml"
    
    wait_for_deployment "kibana" "${LOGGING_NS}"
    
    log_info "Kibana setup complete"
}

setup_filebeat() {
    log_info "Setting up Filebeat..."
    
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/logging/filebeat-config.yaml"
    
    # Deploy Filebeat as DaemonSet
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: filebeat
  namespace: ${LOGGING_NS}
spec:
  selector:
    matchLabels:
      app: filebeat
  template:
    metadata:
      labels:
        app: filebeat
    spec:
      containers:
      - name: filebeat
        image: docker.elastic.co/beats/filebeat:8.10.0
        volumeMounts:
        - name: config
          mountPath: /usr/share/filebeat/filebeat.yml
          subPath: filebeat.yml
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: varlog
          mountPath: /var/log
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: filebeat-config
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
      - name: varlog
        hostPath:
          path: /var/log
EOF
    
    log_info "Filebeat setup complete"
}

# ----------------------------------------------------------------------------
# Validation and Testing
# ----------------------------------------------------------------------------

validate_deployment() {
    log_info "Validating deployment..."
    
    # Check all pods are running
    local failing_pods
    failing_pods=$(kubectl get pods -n "${NAMESPACE}" \
        --field-selector=status.phase!=Running \
        -o jsonpath='{.items[*].metadata.name}')
    
    if [ -n "${failing_pods}" ]; then
        log_error "Some pods are not running: ${failing_pods}"
        return 1
    fi
    
    # Check service endpoints
    if ! kubectl get endpoints bais-api-service -n "${NAMESPACE}" | grep -q "[0-9]"; then
        log_error "Service has no endpoints"
        return 1
    fi
    
    # Test health endpoint
    local api_url
    api_url=$(kubectl get ingress bais-ingress -n "${NAMESPACE}" \
        -o jsonpath='{.spec.rules[0].host}')
    
    if curl -f -s "https://${api_url}/health" >/dev/null; then
        log_info "Health check passed"
    else
        log_error "Health check failed"
        return 1
    fi
    
    log_info "Deployment validation complete"
}

run_smoke_tests() {
    log_info "Running smoke tests..."
    
    kubectl run smoke-test \
        --image=bais/api:latest \
        --restart=Never \
        --namespace="${NAMESPACE}" \
        --command -- pytest tests/smoke/ -v
    
    kubectl wait --for=condition=complete pod/smoke-test \
        -n "${NAMESPACE}" --timeout=300s
    
    local test_result
    test_result=$(kubectl logs smoke-test -n "${NAMESPACE}" | tail -1)
    
    kubectl delete pod smoke-test -n "${NAMESPACE}"
    
    log_info "Smoke tests complete: ${test_result}"
}

# ----------------------------------------------------------------------------
# Load Testing
# ----------------------------------------------------------------------------

run_load_test() {
    log_info "Running load test (1000+ concurrent connections)..."
    
    kubectl run load-test \
        --image=locustio/locust:latest \
        --restart=Never \
        --namespace="${NAMESPACE}" \
        --env="LOCUST_HOST=http://bais-api-service" \
        --env="LOCUST_USERS=1000" \
        --env="LOCUST_SPAWN_RATE=50" \
        --env="LOCUST_RUN_TIME=5m" \
        -- -f /mnt/locustfile.py --headless
    
    kubectl wait --for=condition=complete pod/load-test \
        -n "${NAMESPACE}" --timeout=600s
    
    kubectl logs load-test -n "${NAMESPACE}"
    kubectl delete pod load-test -n "${NAMESPACE}"
    
    log_info "Load test complete"
}

# ----------------------------------------------------------------------------
# Backup and Disaster Recovery
# ----------------------------------------------------------------------------

setup_backup() {
    log_info "Setting up backup..."
    
    # Create backup CronJob for PostgreSQL
    kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: ${NAMESPACE}
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15.4-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres-service -U \$POSTGRES_USER \$POSTGRES_DB | \
              gzip > /backup/bais-\$(date +%Y%m%d-%H%M%S).sql.gz
            env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: POSTGRES_PASSWORD
            - name: POSTGRES_DB
              value: bais_production
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
EOF
    
    log_info "Backup setup complete"
}

# ----------------------------------------------------------------------------
# Main Deployment Function
# ----------------------------------------------------------------------------

main() {
    log_info "Starting BAIS infrastructure deployment..."
    
    # Pre-flight checks
    check_prerequisites || exit 1
    check_environment || exit 1
    
    # Create namespaces
    create_namespace "${NAMESPACE}"
    
    # Phase 1: Database and Cache
    setup_postgresql
    initialize_database_schema
    setup_redis_cluster
    
    # Phase 2: Application
    build_and_push_image
    deploy_application
    setup_autoscaling
    
    # Phase 3: Monitoring
    setup_prometheus
    setup_grafana
    
    # Phase 4: Logging
    setup_elasticsearch
    setup_logstash
    setup_kibana
    setup_filebeat
    
    # Phase 5: Backup
    setup_backup
    
    # Phase 6: Validation
    validate_deployment
    run_smoke_tests
    
    # Phase 7: Load Testing
    if [ "${RUN_LOAD_TEST:-false}" = "true" ]; then
        run_load_test
    fi
    
    log_info "====================================="
    log_info "Infrastructure deployment complete!"
    log_info "====================================="
    log_info ""
    log_info "Access Points:"
    log_info "- API: https://$(kubectl get ingress bais-ingress -n ${NAMESPACE} -o jsonpath='{.spec.rules[0].host}')"
    log_info "- Grafana: http://$(kubectl get svc -n ${MONITORING_NS} prometheus-grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
    log_info "- Kibana: http://$(kubectl get svc -n ${LOGGING_NS} kibana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'):5601"
    log_info ""
    log_info "Next steps:"
    log_info "1. Review monitoring dashboards in Grafana"
    log_info "2. Configure alert rules in Alertmanager"
    log_info "3. Set up log queries in Kibana"
    log_info "4. Run comprehensive load tests"
}

# Run main function if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
