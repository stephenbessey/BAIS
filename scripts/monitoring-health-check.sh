#!/bin/bash

# ============================================================================
# BAIS Platform - Monitoring Health Check Script
# Comprehensive health validation for monitoring infrastructure
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
readonly MONITORING_NAMESPACE="monitoring"
readonly BAIS_NAMESPACE="bais-production"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Health check results
declare -a HEALTH_CHECKS=()
declare -a FAILED_CHECKS=()
declare -a WARNING_CHECKS=()

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

add_health_check() {
    local check_name="$1"
    local status="$2"
    local message="$3"
    
    HEALTH_CHECKS+=("${status}:${check_name}:${message}")
    
    case "${status}" in
        "PASS")
            log_success "✓ ${check_name}: ${message}"
            ;;
        "FAIL")
            log_error "✗ ${check_name}: ${message}"
            FAILED_CHECKS+=("${check_name}")
            ;;
        "WARN")
            log_warn "⚠ ${check_name}: ${message}"
            WARNING_CHECKS+=("${check_name}")
            ;;
    esac
}

check_namespace_exists() {
    log_info "Checking namespaces..."
    
    if kubectl get namespace "${MONITORING_NAMESPACE}" >/dev/null 2>&1; then
        add_health_check "Monitoring Namespace" "PASS" "Namespace ${MONITORING_NAMESPACE} exists"
    else
        add_health_check "Monitoring Namespace" "FAIL" "Namespace ${MONITORING_NAMESPACE} not found"
        return 1
    fi
    
    if kubectl get namespace "${BAIS_NAMESPACE}" >/dev/null 2>&1; then
        add_health_check "BAIS Namespace" "PASS" "Namespace ${BAIS_NAMESPACE} exists"
    else
        add_health_check "BAIS Namespace" "WARN" "Namespace ${BAIS_NAMESPACE} not found (expected for production)"
    fi
}

check_prometheus_deployment() {
    log_info "Checking Prometheus deployment..."
    
    # Check if Prometheus pods are running
    local prometheus_pods
    prometheus_pods=$(kubectl get pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=prometheus \
        --field-selector=status.phase=Running \
        --no-headers 2>/dev/null | wc -l)
    
    if [ "${prometheus_pods}" -gt 0 ]; then
        add_health_check "Prometheus Pods" "PASS" "${prometheus_pods} Prometheus pod(s) running"
    else
        add_health_check "Prometheus Pods" "FAIL" "No Prometheus pods running"
        return 1
    fi
    
    # Check Prometheus service
    if kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=prometheus >/dev/null 2>&1; then
        add_health_check "Prometheus Service" "PASS" "Prometheus service configured"
    else
        add_health_check "Prometheus Service" "FAIL" "Prometheus service not found"
    fi
    
    # Check Prometheus readiness
    if kubectl get pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=prometheus \
        -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null | grep -q "True"; then
        add_health_check "Prometheus Readiness" "PASS" "Prometheus is ready"
    else
        add_health_check "Prometheus Readiness" "WARN" "Prometheus readiness status unknown"
    fi
}

check_grafana_deployment() {
    log_info "Checking Grafana deployment..."
    
    # Check if Grafana pods are running
    local grafana_pods
    grafana_pods=$(kubectl get pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=grafana \
        --field-selector=status.phase=Running \
        --no-headers 2>/dev/null | wc -l)
    
    if [ "${grafana_pods}" -gt 0 ]; then
        add_health_check "Grafana Pods" "PASS" "${grafana_pods} Grafana pod(s) running"
    else
        add_health_check "Grafana Pods" "FAIL" "No Grafana pods running"
        return 1
    fi
    
    # Check Grafana service
    if kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=grafana >/dev/null 2>&1; then
        add_health_check "Grafana Service" "PASS" "Grafana service configured"
    else
        add_health_check "Grafana Service" "FAIL" "Grafana service not found"
    fi
    
    # Check Grafana readiness
    if kubectl get pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=grafana \
        -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null | grep -q "True"; then
        add_health_check "Grafana Readiness" "PASS" "Grafana is ready"
    else
        add_health_check "Grafana Readiness" "WARN" "Grafana readiness status unknown"
    fi
}

check_alertmanager_deployment() {
    log_info "Checking Alertmanager deployment..."
    
    # Check if Alertmanager pods are running
    local alertmanager_pods
    alertmanager_pods=$(kubectl get pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=alertmanager \
        --field-selector=status.phase=Running \
        --no-headers 2>/dev/null | wc -l)
    
    if [ "${alertmanager_pods}" -gt 0 ]; then
        add_health_check "Alertmanager Pods" "PASS" "${alertmanager_pods} Alertmanager pod(s) running"
    else
        add_health_check "Alertmanager Pods" "FAIL" "No Alertmanager pods running"
        return 1
    fi
    
    # Check Alertmanager service
    if kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=alertmanager >/dev/null 2>&1; then
        add_health_check "Alertmanager Service" "PASS" "Alertmanager service configured"
    else
        add_health_check "Alertmanager Service" "FAIL" "Alertmanager service not found"
    fi
}

check_alerting_rules() {
    log_info "Checking alerting rules..."
    
    # Check if alert rules ConfigMap exists
    if kubectl get configmap prometheus-alert-rules -n "${MONITORING_NAMESPACE}" >/dev/null 2>&1; then
        add_health_check "Alert Rules ConfigMap" "PASS" "Alert rules ConfigMap exists"
    else
        add_health_check "Alert Rules ConfigMap" "FAIL" "Alert rules ConfigMap not found"
        return 1
    fi
    
    # Check if Grafana dashboard ConfigMap exists
    if kubectl get configmap grafana-dashboard-bais -n "${MONITORING_NAMESPACE}" >/dev/null 2>&1; then
        add_health_check "Grafana Dashboard ConfigMap" "PASS" "BAIS dashboard ConfigMap exists"
    else
        add_health_check "Grafana Dashboard ConfigMap" "WARN" "BAIS dashboard ConfigMap not found"
    fi
}

check_service_monitors() {
    log_info "Checking service monitors..."
    
    # Check if ServiceMonitor CRD exists
    if kubectl get crd servicemonitors.monitoring.coreos.com >/dev/null 2>&1; then
        add_health_check "ServiceMonitor CRD" "PASS" "ServiceMonitor CRD available"
    else
        add_health_check "ServiceMonitor CRD" "WARN" "ServiceMonitor CRD not found (Prometheus Operator not installed)"
        return 0
    fi
    
    # Check BAIS application ServiceMonitor
    if kubectl get servicemonitor bais-application -n "${MONITORING_NAMESPACE}" >/dev/null 2>&1; then
        add_health_check "BAIS ServiceMonitor" "PASS" "BAIS application ServiceMonitor configured"
    else
        add_health_check "BAIS ServiceMonitor" "WARN" "BAIS application ServiceMonitor not found"
    fi
    
    # Check PostgreSQL ServiceMonitor
    if kubectl get servicemonitor postgres-exporter -n "${MONITORING_NAMESPACE}" >/dev/null 2>&1; then
        add_health_check "PostgreSQL ServiceMonitor" "PASS" "PostgreSQL ServiceMonitor configured"
    else
        add_health_check "PostgreSQL ServiceMonitor" "WARN" "PostgreSQL ServiceMonitor not found"
    fi
    
    # Check Redis ServiceMonitor
    if kubectl get servicemonitor redis-exporter -n "${MONITORING_NAMESPACE}" >/dev/null 2>&1; then
        add_health_check "Redis ServiceMonitor" "PASS" "Redis ServiceMonitor configured"
    else
        add_health_check "Redis ServiceMonitor" "WARN" "Redis ServiceMonitor not found"
    fi
}

check_persistent_volumes() {
    log_info "Checking persistent volumes..."
    
    # Check Prometheus PVC
    local prometheus_pvc
    prometheus_pvc=$(kubectl get pvc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=prometheus \
        --no-headers 2>/dev/null | wc -l)
    
    if [ "${prometheus_pvc}" -gt 0 ]; then
        add_health_check "Prometheus PVC" "PASS" "${prometheus_pvc} Prometheus PVC(s) configured"
    else
        add_health_check "Prometheus PVC" "WARN" "No Prometheus PVC found"
    fi
    
    # Check Grafana PVC
    local grafana_pvc
    grafana_pvc=$(kubectl get pvc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=grafana \
        --no-headers 2>/dev/null | wc -l)
    
    if [ "${grafana_pvc}" -gt 0 ]; then
        add_health_check "Grafana PVC" "PASS" "${grafana_pvc} Grafana PVC(s) configured"
    else
        add_health_check "Grafana PVC" "WARN" "No Grafana PVC found"
    fi
    
    # Check Alertmanager PVC
    local alertmanager_pvc
    alertmanager_pvc=$(kubectl get pvc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=alertmanager \
        --no-headers 2>/dev/null | wc -l)
    
    if [ "${alertmanager_pvc}" -gt 0 ]; then
        add_health_check "Alertmanager PVC" "PASS" "${alertmanager_pvc} Alertmanager PVC(s) configured"
    else
        add_health_check "Alertmanager PVC" "WARN" "No Alertmanager PVC found"
    fi
}

check_network_connectivity() {
    log_info "Checking network connectivity..."
    
    # Check if we can reach Prometheus service
    local prometheus_service
    prometheus_service=$(kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=prometheus \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [ -n "${prometheus_service}" ]; then
        if kubectl run test-prometheus-connectivity \
            --image=curlimages/curl:latest \
            --rm -i --restart=Never \
            -- curl -s "http://${prometheus_service}.${MONITORING_NAMESPACE}.svc.cluster.local:9090/api/v1/query?query=up" \
            >/dev/null 2>&1; then
            add_health_check "Prometheus Connectivity" "PASS" "Prometheus API accessible"
        else
            add_health_check "Prometheus Connectivity" "WARN" "Prometheus API not accessible"
        fi
    else
        add_health_check "Prometheus Connectivity" "FAIL" "Prometheus service not found"
    fi
    
    # Check if we can reach Grafana service
    local grafana_service
    grafana_service=$(kubectl get svc -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=grafana \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [ -n "${grafana_service}" ]; then
        if kubectl run test-grafana-connectivity \
            --image=curlimages/curl:latest \
            --rm -i --restart=Never \
            -- curl -s "http://${grafana_service}.${MONITORING_NAMESPACE}.svc.cluster.local:80/api/health" \
            >/dev/null 2>&1; then
            add_health_check "Grafana Connectivity" "PASS" "Grafana API accessible"
        else
            add_health_check "Grafana Connectivity" "WARN" "Grafana API not accessible"
        fi
    else
        add_health_check "Grafana Connectivity" "FAIL" "Grafana service not found"
    fi
}

check_resource_usage() {
    log_info "Checking resource usage..."
    
    # Check Prometheus resource usage
    local prometheus_cpu
    prometheus_cpu=$(kubectl top pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=prometheus \
        --no-headers 2>/dev/null | awk '{print $2}' | head -1 || echo "unknown")
    
    if [ "${prometheus_cpu}" != "unknown" ] && [ "${prometheus_cpu}" != "0" ]; then
        add_health_check "Prometheus Resource Usage" "PASS" "Prometheus CPU usage: ${prometheus_cpu}"
    else
        add_health_check "Prometheus Resource Usage" "WARN" "Prometheus resource usage unknown"
    fi
    
    # Check Grafana resource usage
    local grafana_cpu
    grafana_cpu=$(kubectl top pods -n "${MONITORING_NAMESPACE}" \
        -l app.kubernetes.io/name=grafana \
        --no-headers 2>/dev/null | awk '{print $2}' | head -1 || echo "unknown")
    
    if [ "${grafana_cpu}" != "unknown" ] && [ "${grafana_cpu}" != "0" ]; then
        add_health_check "Grafana Resource Usage" "PASS" "Grafana CPU usage: ${grafana_cpu}"
    else
        add_health_check "Grafana Resource Usage" "WARN" "Grafana resource usage unknown"
    fi
}

generate_health_report() {
    log_info "Generating health check report..."
    
    local total_checks=${#HEALTH_CHECKS[@]}
    local passed_checks=0
    local failed_checks=${#FAILED_CHECKS[@]}
    local warning_checks=${#WARNING_CHECKS[@]}
    
    # Count passed checks
    for check in "${HEALTH_CHECKS[@]}"; do
        if [[ "${check}" == "PASS:"* ]]; then
            ((passed_checks++))
        fi
    done
    
    echo ""
    echo "========================================="
    echo "🏥 BAIS Platform Monitoring Health Check"
    echo "========================================="
    echo ""
    echo "📊 Summary:"
    echo "   Total Checks: ${total_checks}"
    echo "   ✅ Passed: ${passed_checks}"
    echo "   ⚠️  Warnings: ${warning_checks}"
    echo "   ❌ Failed: ${failed_checks}"
    echo ""
    
    if [ "${failed_checks}" -eq 0 ]; then
        echo "🎉 Overall Status: HEALTHY"
        if [ "${warning_checks}" -gt 0 ]; then
            echo "⚠️  ${warning_checks} warning(s) found - review recommended"
        fi
    else
        echo "🚨 Overall Status: UNHEALTHY"
        echo "❌ ${failed_checks} critical issue(s) found - immediate attention required"
    fi
    
    echo ""
    echo "📋 Detailed Results:"
    for check in "${HEALTH_CHECKS[@]}"; do
        IFS=':' read -r status name message <<< "${check}"
        case "${status}" in
            "PASS")
                echo "   ✅ ${name}: ${message}"
                ;;
            "WARN")
                echo "   ⚠️  ${name}: ${message}"
                ;;
            "FAIL")
                echo "   ❌ ${name}: ${message}"
                ;;
        esac
    done
    
    echo ""
    echo "🔧 Next Steps:"
    if [ "${failed_checks}" -gt 0 ]; then
        echo "   1. Fix critical issues listed above"
        echo "   2. Re-run health check to verify fixes"
        echo "   3. Deploy monitoring components if missing"
    else
        echo "   1. Configure alerting channels (Slack, PagerDuty)"
        echo "   2. Set up on-call rotation"
        echo "   3. Customize alert rules as needed"
        echo "   4. Set up log aggregation (ELK stack)"
    fi
    
    echo ""
    
    # Return appropriate exit code
    if [ "${failed_checks}" -gt 0 ]; then
        return 1
    else
        return 0
    fi
}

# ----------------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------------
main() {
    log_info "Starting BAIS Platform monitoring health check..."
    log_info "Monitoring namespace: ${MONITORING_NAMESPACE}"
    log_info "BAIS namespace: ${BAIS_NAMESPACE}"
    
    check_namespace_exists
    check_prometheus_deployment
    check_grafana_deployment
    check_alertmanager_deployment
    check_alerting_rules
    check_service_monitors
    check_persistent_volumes
    check_network_connectivity
    check_resource_usage
    generate_health_report
}

# Run main function
main "$@"
