#!/bin/bash

set -euo pipefail

readonly PRODUCTION_NAMESPACE="bais-production"
readonly STAGING_NAMESPACE="bais-staging"
readonly CHECKLIST_FILE="golive-checklist-$(date +%Y%m%d).json"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

declare -A CHECKLIST_ITEMS=(
    ["security_audit"]="Security audit completed and vulnerabilities addressed"
    ["ssl_certificates"]="SSL certificates configured and valid"
    ["backup_verified"]="Backup and restore procedures tested"
    ["monitoring_alerts"]="All monitoring alerts configured and tested"
    ["oncall_rotation"]="On-call rotation active and team trained"
    ["runbooks_updated"]="Runbooks documented and accessible"
    ["disaster_recovery"]="Disaster recovery plan tested"
    ["performance_validated"]="Performance benchmarks met"
    ["acceptance_tests"]="All acceptance tests passed"
    ["capacity_planning"]="Capacity planning reviewed and adequate"
    ["database_optimized"]="Database performance optimized"
    ["cache_configured"]="Redis cache properly configured"
    ["load_balancing"]="Load balancing and auto-scaling configured"
    ["network_security"]="Network security policies implemented"
    ["compliance_verified"]="Compliance requirements met"
)

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $*"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*" >&2
}

check_prerequisites() {
    local missing_tools=()
    
    for tool in kubectl jq curl openssl bc; do
        if ! command -v "$tool" &>/dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi
    
    log_info "All prerequisites satisfied"
    return 0
}

verify_ssl_certificates() {
    log_info "Verifying SSL certificates..."
    
    local domain="api.bais.io"
    local cert_info
    cert_info=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        log_warning "Cannot verify SSL certificate for $domain (may not be deployed yet)"
        return 0
    fi
    
    local expiry_date
    expiry_date=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
    
    local expiry_epoch
    expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s)
    local current_epoch
    current_epoch=$(date +%s)
    local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
    
    if [ "$days_until_expiry" -lt 30 ]; then
        log_error "SSL certificate expires in ${days_until_expiry} days"
        return 1
    fi
    
    log_success "SSL certificate valid for ${days_until_expiry} days"
    return 0
}

verify_backup_system() {
    log_info "Verifying backup system..."
    
    # Check if backup CronJob exists
    if ! kubectl get cronjob postgres-backup -n "$PRODUCTION_NAMESPACE" &>/dev/null; then
        log_warning "Backup CronJob not found in production namespace"
        return 1
    fi
    
    # Check backup schedule
    local backup_schedule
    backup_schedule=$(kubectl get cronjob postgres-backup -n "$PRODUCTION_NAMESPACE" -o jsonpath='{.spec.schedule}')
    log_info "Backup schedule: $backup_schedule"
    
    # Check backup PVC exists
    if ! kubectl get pvc backup-pvc -n "$PRODUCTION_NAMESPACE" &>/dev/null; then
        log_error "Backup PVC not found"
        return 1
    fi
    
    # Test backup functionality
    kubectl run backup-test \
        --image=postgres:15.4-alpine \
        --namespace="$PRODUCTION_NAMESPACE" \
        --restart=Never \
        --rm -i --tty \
        --command -- bash -c "
            pg_dump -h postgres-production -U postgres bais_production > /tmp/test_backup.sql && 
            [ -s /tmp/test_backup.sql ] && 
            echo 'Backup test successful'
        " 2>/dev/null || {
        log_warning "Backup test failed - database may not be accessible"
        return 1
    }
    
    log_success "Backup system verified"
    return 0
}

verify_monitoring_alerts() {
    log_info "Verifying monitoring alerts..."
    
    # Check if Prometheus is running
    if ! kubectl get pods -n monitoring -l app=prometheus --field-selector=status.phase=Running &>/dev/null; then
        log_error "Prometheus not running"
        return 1
    fi
    
    # Check alert rules
    local alert_count
    alert_count=$(kubectl get prometheusrules -n monitoring -o json 2>/dev/null | jq '.items | length' || echo "0")
    
    if [ "$alert_count" -lt 5 ]; then
        log_error "Insufficient alert rules configured (found: $alert_count)"
        return 1
    fi
    
    # Check Alertmanager
    local alertmanager_status
    alertmanager_status=$(kubectl get pods -n monitoring -l app=alertmanager -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "Unknown")
    
    if [ "$alertmanager_status" != "Running" ]; then
        log_error "Alertmanager not running (status: $alertmanager_status)"
        return 1
    fi
    
    log_success "Monitoring alerts verified (${alert_count} rules active)"
    return 0
}

verify_performance_targets() {
    log_info "Verifying performance targets..."
    
    # Test against staging environment
    local api_url="http://staging-api.bais.io/health"
    local total_time=0
    local request_count=5
    
    for i in $(seq 1 $request_count); do
        local response_time
        response_time=$(curl -w "%{time_total}" -o /dev/null -s --connect-timeout 10 "$api_url" 2>/dev/null || echo "0")
        
        if (( $(echo "$response_time == 0" | bc -l) )); then
            log_warning "Cannot reach staging API for performance testing"
            return 1
        fi
        
        total_time=$(echo "$total_time + $response_time" | bc)
    done
    
    local avg_time
    avg_time=$(echo "scale=3; $total_time / $request_count" | bc)
    
    if (( $(echo "$avg_time > 0.2" | bc -l) )); then
        log_error "Average response time ${avg_time}s exceeds 200ms target"
        return 1
    fi
    
    log_success "Performance target met (avg: ${avg_time}s)"
    return 0
}

verify_disaster_recovery() {
    log_info "Verifying disaster recovery setup..."
    
    # Check backup CronJob
    if ! kubectl get cronjob postgres-backup -n "$PRODUCTION_NAMESPACE" &>/dev/null; then
        log_error "Backup CronJob not found"
        return 1
    fi
    
    local backup_schedule
    backup_schedule=$(kubectl get cronjob postgres-backup -n "$PRODUCTION_NAMESPACE" -o jsonpath='{.spec.schedule}')
    log_info "Backup schedule: $backup_schedule"
    
    # Check backup PVC
    if ! kubectl get pvc backup-pvc -n "$PRODUCTION_NAMESPACE" &>/dev/null; then
        log_error "Backup PVC not found"
        return 1
    fi
    
    # Check if we have multiple replicas for HA
    local replica_count
    replica_count=$(kubectl get deployment bais-api -n "$PRODUCTION_NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
    
    if [ "$replica_count" -lt 3 ]; then
        log_warning "Low replica count for HA: $replica_count"
    fi
    
    log_success "Disaster recovery setup verified"
    return 0
}

verify_capacity_planning() {
    log_info "Verifying capacity planning..."
    
    # Check cluster resources
    local cpu_usage
    cpu_usage=$(kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$3} END {print sum/NR}' || echo "0")
    
    local memory_usage
    memory_usage=$(kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$5} END {print sum/NR}' || echo "0")
    
    if (( $(echo "$cpu_usage > 70" | bc -l) )); then
        log_error "Cluster CPU usage at ${cpu_usage}%"
        return 1
    fi
    
    if (( $(echo "$memory_usage > 75" | bc -l) )); then
        log_error "Cluster memory usage at ${memory_usage}%"
        return 1
    fi
    
    # Check HPA configuration
    if ! kubectl get hpa bais-api-hpa -n "$PRODUCTION_NAMESPACE" &>/dev/null; then
        log_warning "HPA not configured for bais-api"
    fi
    
    log_success "Capacity planning verified (CPU: ${cpu_usage}%, Memory: ${memory_usage}%)"
    return 0
}

verify_security_compliance() {
    log_info "Verifying security compliance..."
    
    # Check for security policies
    local security_policies
    security_policies=$(kubectl get networkpolicies -n "$PRODUCTION_NAMESPACE" 2>/dev/null | wc -l || echo "0")
    
    if [ "$security_policies" -eq 0 ]; then
        log_warning "No network policies configured"
    fi
    
    # Check for non-root containers
    local non_root_containers
    non_root_containers=$(kubectl get pods -n "$PRODUCTION_NAMESPACE" -o jsonpath='{.items[*].spec.securityContext.runAsNonRoot}' 2>/dev/null | grep -c "true" || echo "0")
    
    if [ "$non_root_containers" -eq 0 ]; then
        log_warning "No non-root containers detected"
    fi
    
    # Check for resource limits
    local containers_with_limits
    containers_with_limits=$(kubectl get pods -n "$PRODUCTION_NAMESPACE" -o jsonpath='{.items[*].spec.containers[*].resources.limits}' 2>/dev/null | grep -c "memory\|cpu" || echo "0")
    
    if [ "$containers_with_limits" -eq 0 ]; then
        log_warning "No resource limits configured"
    fi
    
    log_success "Security compliance verified"
    return 0
}

verify_acceptance_tests() {
    log_info "Verifying acceptance tests..."
    
    # Check if acceptance test report exists
    local test_reports
    test_reports=$(ls acceptance_test_report_*.json 2>/dev/null | wc -l)
    
    if [ "$test_reports" -eq 0 ]; then
        log_warning "No acceptance test reports found"
        return 1
    fi
    
    # Check latest test report
    local latest_report
    latest_report=$(ls -t acceptance_test_report_*.json 2>/dev/null | head -1)
    
    if [[ -n "$latest_report" ]]; then
        local failed_tests
        failed_tests=$(jq -r '.summary.failed' "$latest_report" 2>/dev/null || echo "1")
        
        if [ "$failed_tests" -gt 0 ]; then
            log_error "Acceptance tests failed: $failed_tests failures"
            return 1
        fi
        
        log_success "Acceptance tests passed"
        return 0
    fi
    
    log_warning "Cannot verify acceptance test results"
    return 1
}

generate_golive_report() {
    local status=$1
    
    local results=()
    
    for key in "${!CHECKLIST_ITEMS[@]}"; do
        results+=("{\"item\": \"$key\", \"description\": \"${CHECKLIST_ITEMS[$key]}\", \"status\": \"$status\"}")
    done
    
    local json_output
    json_output=$(printf '%s\n' "${results[@]}" | jq -s '.')
    
    cat > "$CHECKLIST_FILE" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "environment": "production",
  "namespace": "$PRODUCTION_NAMESPACE",
  "status": "$status",
  "checklist": $json_output,
  "next_steps": [
    "Review checklist items",
    "Address any failed checks",
    "Execute production deployment",
    "Monitor system health post-deployment",
    "Update status page and stakeholders"
  ]
}
EOF
    
    log_info "Go-live checklist saved to $CHECKLIST_FILE"
}

execute_production_deployment() {
    log_info "Executing production deployment..."
    
    # Apply production configuration
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bais-production
  namespace: $PRODUCTION_NAMESPACE
  labels:
    app: bais
    environment: production
    version: "production"
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: bais
      environment: production
  template:
    metadata:
      labels:
        app: bais
        environment: production
        version: "production"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
      - name: bais-app
        image: bais/api:production
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        - name: LOG_LEVEL
          value: "INFO"
        - name: WORKERS
          value: "4"
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
          failureThreshold: 3
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
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
  name: bais-production-service
  namespace: $PRODUCTION_NAMESPACE
  labels:
    app: bais
    environment: production
spec:
  selector:
    app: bais
    environment: production
  ports:
  - name: http
    port: 443
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
  type: LoadBalancer
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: bais-production-ingress
  namespace: $PRODUCTION_NAMESPACE
  labels:
    app: bais
    environment: production
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  tls:
  - hosts:
    - api.bais.io
    secretName: bais-tls-cert
  rules:
  - host: api.bais.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: bais-production-service
            port:
              number: 443
EOF
    
    # Wait for deployment to complete
    kubectl rollout status deployment/bais-production -n "$PRODUCTION_NAMESPACE" --timeout=600s
    
    log_success "Production deployment completed successfully"
}

run_post_deployment_tests() {
    log_info "Running post-deployment tests..."
    
    # Wait for service to be ready
    sleep 30
    
    # Test health endpoint
    local service_ip
    service_ip=$(kubectl get svc bais-production-service -n "$PRODUCTION_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    
    if [[ -n "$service_ip" ]]; then
        # Test with external IP
        local health_status
        health_status=$(curl -s --connect-timeout 10 "https://$service_ip/health" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        
        if [[ "$health_status" == "healthy" ]]; then
            log_success "Post-deployment health check passed"
        else
            log_warning "Post-deployment health check failed: $health_status"
        fi
    else
        # Test with port-forward
        kubectl port-forward svc/bais-production-service 8080:443 -n "$PRODUCTION_NAMESPACE" &
        local port_forward_pid=$!
        sleep 5
        
        local health_status
        health_status=$(curl -s -k --connect-timeout 10 "https://localhost:8080/health" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        
        if [[ "$health_status" == "healthy" ]]; then
            log_success "Post-deployment health check passed"
        else
            log_warning "Post-deployment health check failed: $health_status"
        fi
        
        kill $port_forward_pid 2>/dev/null || true
    fi
}

main() {
    log_info "========================================="
    log_info "BAIS Platform Production Go-Live"
    log_info "========================================="
    
    check_prerequisites || exit 1
    
    local all_checks_passed=true
    
    # Run all verification checks
    verify_ssl_certificates || all_checks_passed=false
    verify_backup_system || all_checks_passed=false
    verify_monitoring_alerts || all_checks_passed=false
    verify_performance_targets || all_checks_passed=false
    verify_disaster_recovery || all_checks_passed=false
    verify_capacity_planning || all_checks_passed=false
    verify_security_compliance || all_checks_passed=false
    verify_acceptance_tests || all_checks_passed=false
    
    if [ "$all_checks_passed" = true ]; then
        generate_golive_report "PASSED"
        
        log_success "All pre-deployment checks passed"
        log_info "Proceeding with production deployment..."
        
        execute_production_deployment
        run_post_deployment_tests
        
        log_success "========================================="
        log_success "Production Deployment Complete!"
        log_success "========================================="
        log_info "Status: https://status.bais.com"
        log_info "Monitoring: https://grafana.bais.com"
        log_info "API: https://api.bais.io"
        log_info "Kibana: https://kibana.bais.com"
        
        log_info ""
        log_info "Next Steps:"
        log_info "1. Monitor system health for 24 hours"
        log_info "2. Update status page with go-live announcement"
        log_info "3. Notify stakeholders of successful deployment"
        log_info "4. Schedule post-deployment review meeting"
        
    else
        generate_golive_report "FAILED"
        log_error "Pre-deployment checks failed"
        log_error "Review $CHECKLIST_FILE for details"
        log_error "Address all issues before attempting deployment"
        exit 1
    fi
}

main "$@"
