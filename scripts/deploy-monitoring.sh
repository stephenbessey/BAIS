#!/bin/bash

# ============================================================================
# BAIS Platform - Monitoring Deployment Script
# Comprehensive monitoring setup with Prometheus, Grafana, and Alerting
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly MONITORING_NAMESPACE="monitoring"
readonly BAIS_NAMESPACE="bais-production"

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
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl")
    command -v helm >/dev/null 2>&1 || missing_tools+=("helm")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again."
        return 1
    fi
    
    # Check kubectl connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Cannot connect to Kubernetes cluster"
        log_error "Please ensure kubectl is configured correctly"
        return 1
    fi
    
    log_success "All prerequisites satisfied"
    return 0
}

create_namespaces() {
    log_info "Creating monitoring namespaces..."
    
    # Create monitoring namespace
    if kubectl get namespace "${MONITORING_NAMESPACE}" >/dev/null 2>&1; then
        log_info "Namespace ${MONITORING_NAMESPACE} already exists"
    else
        kubectl create namespace "${MONITORING_NAMESPACE}"
        kubectl label namespace "${MONITORING_NAMESPACE}" \
            monitoring=enabled \
            team=platform
        log_success "Created namespace ${MONITORING_NAMESPACE}"
    fi
    
    # Ensure BAIS namespace exists
    if kubectl get namespace "${BAIS_NAMESPACE}" >/dev/null 2>&1; then
        log_info "Namespace ${BAIS_NAMESPACE} already exists"
    else
        kubectl create namespace "${BAIS_NAMESPACE}"
        kubectl label namespace "${BAIS_NAMESPACE}" \
            environment=production \
            team=platform
        log_success "Created namespace ${BAIS_NAMESPACE}"
    fi
}

setup_helm_repositories() {
    log_info "Setting up Helm repositories..."
    
    # Add Prometheus community repository
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    
    # Update repositories
    helm repo update
    
    log_success "Helm repositories configured"
}

deploy_prometheus() {
    log_info "Deploying Prometheus..."
    
    # Create Prometheus values file
    cat > /tmp/prometheus-values.yaml <<EOF
server:
  persistentVolume:
    enabled: true
    size: 50Gi
  retention: 30d
  retentionSize: 50GB

alertmanager:
  enabled: true
  persistentVolume:
    enabled: true
    size: 10Gi
  config:
    global:
      resolve_timeout: 5m
    route:
      group_by: ['alertname']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'web.hook'
    receivers:
    - name: 'web.hook'
      webhook_configs:
      - url: 'http://webhook.example.com:5001/'

nodeExporter:
  enabled: true

kubeStateMetrics:
  enabled: true

pushgateway:
  enabled: true

extraScrapeConfigs: |
  - job_name: 'bais-application'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - ${BAIS_NAMESPACE}
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      action: keep
      regex: bais-api
    - source_labels: [__meta_kubernetes_pod_ip]
      target_label: __address__
      replacement: \$1:9090
    - source_labels: [__meta_kubernetes_pod_name]
      target_label: pod
    - source_labels: [__meta_kubernetes_namespace]
      target_label: namespace
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics

ruleFiles:
  - "/etc/config/alert-rules.yaml"
EOF

    # Deploy Prometheus
    helm upgrade --install prometheus prometheus-community/prometheus \
        --namespace "${MONITORING_NAMESPACE}" \
        --values /tmp/prometheus-values.yaml \
        --wait \
        --timeout=10m
    
    log_success "Prometheus deployed successfully"
}

deploy_grafana() {
    log_info "Deploying Grafana..."
    
    # Create Grafana values file
    cat > /tmp/grafana-values.yaml <<EOF
persistence:
  enabled: true
  size: 10Gi

adminPassword: "bais-admin-2024"

datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-server.${MONITORING_NAMESPACE}.svc.cluster.local
      access: proxy
      isDefault: true

dashboardProviders:
  dashboardproviders.yaml:
    apiVersion: 1
    providers:
    - name: 'default'
      orgId: 1
      folder: ''
      type: file
      disableDeletion: false
      editable: true
      options:
        path: /var/lib/grafana/dashboards/default

dashboards:
  default:
    bais-production:
      gnetId: 0
      revision: 1
      datasource: Prometheus

service:
  type: LoadBalancer
  port: 80

ingress:
  enabled: true
  hosts:
  - grafana.bais.io
  tls:
  - secretName: grafana-tls
    hosts:
    - grafana.bais.io

plugins:
  - grafana-clock-panel
  - grafana-piechart-panel
  - grafana-worldmap-panel
EOF

    # Deploy Grafana
    helm upgrade --install grafana grafana/grafana \
        --namespace "${MONITORING_NAMESPACE}" \
        --values /tmp/grafana-values.yaml \
        --wait \
        --timeout=10m
    
    log_success "Grafana deployed successfully"
}

deploy_alerting_rules() {
    log_info "Deploying alerting rules..."
    
    # Apply Prometheus alert rules
    kubectl apply -f "${SCRIPT_DIR}/prometheus-alerts.yaml" -n "${MONITORING_NAMESPACE}"
    
    # Apply Grafana dashboard
    kubectl create configmap grafana-dashboard-bais \
        --from-file="${SCRIPT_DIR}/grafana-dashboard-bais.json" \
        -n "${MONITORING_NAMESPACE}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Alerting rules and dashboard deployed"
}

setup_service_monitors() {
    log_info "Setting up service monitors..."
    
    # Create ServiceMonitor for BAIS application
    cat > /tmp/bais-servicemonitor.yaml <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: bais-application
  namespace: ${MONITORING_NAMESPACE}
  labels:
    app: bais-api
spec:
  selector:
    matchLabels:
      app: bais-api
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
  namespaceSelector:
    matchNames:
    - ${BAIS_NAMESPACE}
EOF

    kubectl apply -f /tmp/bais-servicemonitor.yaml
    
    # Create ServiceMonitor for PostgreSQL
    cat > /tmp/postgres-servicemonitor.yaml <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-exporter
  namespace: ${MONITORING_NAMESPACE}
  labels:
    app: postgres-exporter
spec:
  selector:
    matchLabels:
      app: postgres-exporter
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
  namespaceSelector:
    matchNames:
    - ${BAIS_NAMESPACE}
EOF

    kubectl apply -f /tmp/postgres-servicemonitor.yaml
    
    # Create ServiceMonitor for Redis
    cat > /tmp/redis-servicemonitor.yaml <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: redis-exporter
  namespace: ${MONITORING_NAMESPACE}
  labels:
    app: redis-exporter
spec:
  selector:
    matchLabels:
      app: redis-exporter
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
  namespaceSelector:
    matchNames:
    - ${BAIS_NAMESPACE}
EOF

    kubectl apply -f /tmp/redis-servicemonitor.yaml
    
    log_success "Service monitors configured"
}

configure_alertmanager() {
    log_info "Configuring Alertmanager..."
    
    # Wait for Alertmanager to be ready
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=alertmanager \
        -n "${MONITORING_NAMESPACE}" \
        --timeout=300s
    
    # Get Alertmanager service
    local alertmanager_service
    alertmanager_service=$(kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=alertmanager \
        -o jsonpath='{.items[0].metadata.name}')
    
    log_info "Alertmanager service: ${alertmanager_service}"
    log_success "Alertmanager configured"
}

validate_deployment() {
    log_info "Validating monitoring deployment..."
    
    # Check Prometheus
    if kubectl get pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=prometheus \
        --field-selector=status.phase=Running | grep -q prometheus; then
        log_success "Prometheus is running"
    else
        log_error "Prometheus is not running properly"
        return 1
    fi
    
    # Check Grafana
    if kubectl get pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=grafana \
        --field-selector=status.phase=Running | grep -q grafana; then
        log_success "Grafana is running"
    else
        log_error "Grafana is not running properly"
        return 1
    fi
    
    # Check Alertmanager
    if kubectl get pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=alertmanager \
        --field-selector=status.phase=Running | grep -q alertmanager; then
        log_success "Alertmanager is running"
    else
        log_error "Alertmanager is not running properly"
        return 1
    fi
    
    log_success "All monitoring components are running"
}

get_access_urls() {
    log_info "Getting access URLs..."
    
    # Get Grafana URL
    local grafana_service
    grafana_service=$(kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=grafana \
        -o jsonpath='{.items[0].metadata.name}')
    
    local grafana_port
    grafana_port=$(kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=grafana \
        -o jsonpath='{.items[0].spec.ports[0].port}')
    
    # Get Prometheus URL
    local prometheus_service
    prometheus_service=$(kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=prometheus \
        -o jsonpath='{.items[0].metadata.name}')
    
    local prometheus_port
    prometheus_port=$(kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=prometheus \
        -o jsonpath='{.items[0].spec.ports[0].port}')
    
    echo ""
    echo "========================================="
    echo "🎉 BAIS Platform Monitoring Deployed!"
    echo "========================================="
    echo ""
    echo "📊 Grafana Dashboard:"
    echo "   URL: http://${grafana_service}.${MONITORING_NAMESPACE}.svc.cluster.local:${grafana_port}"
    echo "   Username: admin"
    echo "   Password: bais-admin-2024"
    echo ""
    echo "📈 Prometheus Metrics:"
    echo "   URL: http://${prometheus_service}.${MONITORING_NAMESPACE}.svc.cluster.local:${prometheus_port}"
    echo ""
    echo "🔔 Alertmanager:"
    echo "   URL: http://alertmanager.${MONITORING_NAMESPACE}.svc.cluster.local:9093"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Access Grafana dashboard to view metrics"
    echo "   2. Configure alerting channels (Slack, PagerDuty)"
    echo "   3. Set up on-call rotation"
    echo "   4. Review and customize alert rules"
    echo ""
}

cleanup_temp_files() {
    log_info "Cleaning up temporary files..."
    rm -f /tmp/prometheus-values.yaml
    rm -f /tmp/grafana-values.yaml
    rm -f /tmp/bais-servicemonitor.yaml
    rm -f /tmp/postgres-servicemonitor.yaml
    rm -f /tmp/redis-servicemonitor.yaml
    log_success "Cleanup completed"
}

# ----------------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------------
main() {
    log_info "Starting BAIS Platform monitoring deployment..."
    log_info "Target namespace: ${MONITORING_NAMESPACE}"
    log_info "BAIS namespace: ${BAIS_NAMESPACE}"
    
    check_prerequisites
    create_namespaces
    setup_helm_repositories
    deploy_prometheus
    deploy_grafana
    deploy_alerting_rules
    setup_service_monitors
    configure_alertmanager
    validate_deployment
    get_access_urls
    cleanup_temp_files
    
    log_success "🎉 Monitoring deployment completed successfully!"
    log_info "All monitoring components are now running and ready for production use."
}

# Run main function
main "$@"
