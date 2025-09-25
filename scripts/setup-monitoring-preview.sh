#!/bin/bash

# ============================================================================
# BAIS Platform - Monitoring Preview Setup Script
# Set up local monitoring environment for verification
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

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
    
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v docker-compose >/dev/null 2>&1 || missing_tools+=("docker-compose")
    command -v curl >/dev/null 2>&1 || missing_tools+=("curl")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again."
        return 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        log_error "Please start Docker and try again."
        return 1
    fi
    
    log_success "All prerequisites satisfied"
    return 0
}

ensure_staging_environment() {
    log_info "Ensuring staging environment is running..."
    
    # Check if staging environment is running
    if docker-compose -f docker-compose.staging.yml ps | grep -q "Up"; then
        log_success "Staging environment is running"
    else
        log_warn "Staging environment not running, starting it..."
        docker-compose -f docker-compose.staging.yml up -d
        
        # Wait for staging to be ready
        log_info "Waiting for staging environment to be ready..."
        sleep 10
        
        # Test staging health
        if curl -s http://localhost:8001/health >/dev/null 2>&1; then
            log_success "Staging environment is ready"
        else
            log_error "Staging environment failed to start"
            return 1
        fi
    fi
}

deploy_monitoring_stack() {
    log_info "Deploying monitoring stack..."
    
    # Build monitoring stack
    docker-compose -f docker-compose.monitoring.yml up -d --build
    
    # Wait for services to be ready
    log_info "Waiting for monitoring services to be ready..."
    sleep 15
    
    # Check Prometheus
    local prometheus_ready=false
    for i in {1..30}; do
        if curl -s http://localhost:9090/-/ready >/dev/null 2>&1; then
            prometheus_ready=true
            break
        fi
        log_info "Waiting for Prometheus... (${i}/30)"
        sleep 2
    done
    
    if [ "${prometheus_ready}" = true ]; then
        log_success "Prometheus is ready"
    else
        log_error "Prometheus failed to start"
        return 1
    fi
    
    # Check Grafana
    local grafana_ready=false
    for i in {1..30}; do
        if curl -s http://localhost:3000/api/health >/dev/null 2>&1; then
            grafana_ready=true
            break
        fi
        log_info "Waiting for Grafana... (${i}/30)"
        sleep 2
    done
    
    if [ "${grafana_ready}" = true ]; then
        log_success "Grafana is ready"
    else
        log_error "Grafana failed to start"
        return 1
    fi
    
    # Check Alertmanager
    local alertmanager_ready=false
    for i in {1..30}; do
        if curl -s http://localhost:9093/-/ready >/dev/null 2>&1; then
            alertmanager_ready=true
            break
        fi
        log_info "Waiting for Alertmanager... (${i}/30)"
        sleep 2
    done
    
    if [ "${alertmanager_ready}" = true ]; then
        log_success "Alertmanager is ready"
    else
        log_error "Alertmanager failed to start"
        return 1
    fi
}

generate_sample_metrics() {
    log_info "Generating sample metrics for preview..."
    
    # Generate some sample API requests to create metrics
    for i in {1..50}; do
        curl -s http://localhost:8002/health >/dev/null 2>&1 || true
        curl -s http://localhost:8002/api/v1/system/status >/dev/null 2>&1 || true
        
        if [ $((i % 10)) -eq 0 ]; then
            log_info "Generated ${i} sample requests..."
        fi
        
        sleep 0.1
    done
    
    log_success "Sample metrics generated"
}

validate_monitoring_setup() {
    log_info "Validating monitoring setup..."
    
    # Test Prometheus targets
    local targets_response
    targets_response=$(curl -s http://localhost:9090/api/v1/targets)
    
    if echo "${targets_response}" | jq -e '.data.activeTargets[]' >/dev/null 2>&1; then
        log_success "Prometheus targets are configured"
    else
        log_warn "Prometheus targets not yet configured"
    fi
    
    # Test Grafana datasource
    local datasources_response
    datasources_response=$(curl -s -u admin:bais-admin-2024 http://localhost:3000/api/datasources)
    
    if echo "${datasources_response}" | jq -e '.[] | select(.name=="Prometheus")' >/dev/null 2>&1; then
        log_success "Grafana datasource is configured"
    else
        log_warn "Grafana datasource not yet configured"
    fi
    
    # Test Alertmanager configuration
    local alertmanager_config
    alertmanager_config=$(curl -s http://localhost:9093/api/v1/status)
    
    if echo "${alertmanager_config}" | jq -e '.data.config' >/dev/null 2>&1; then
        log_success "Alertmanager is configured"
    else
        log_warn "Alertmanager configuration not yet loaded"
    fi
}

display_access_information() {
    log_info "Displaying access information..."
    
    echo ""
    echo "========================================="
    echo "🎉 BAIS Platform Monitoring Preview Ready!"
    echo "========================================="
    echo ""
    echo "📊 Monitoring Services:"
    echo ""
    echo "🔍 Prometheus (Metrics Collection):"
    echo "   URL: http://localhost:9090"
    echo "   Targets: http://localhost:9090/targets"
    echo "   Alerts: http://localhost:9090/alerts"
    echo ""
    echo "📈 Grafana (Dashboards & Visualization):"
    echo "   URL: http://localhost:3000"
    echo "   Username: admin"
    echo "   Password: bais-admin-2024"
    echo ""
    echo "🔔 Alertmanager (Alert Management):"
    echo "   URL: http://localhost:9093"
    echo "   Alerts: http://localhost:9093/#/alerts"
    echo ""
    echo "🏥 BAIS Application (with Metrics):"
    echo "   URL: http://localhost:8002"
    echo "   Metrics: http://localhost:8002/metrics"
    echo "   Health: http://localhost:8002/health"
    echo ""
    echo "📋 Preview Instructions:"
    echo "   1. Open Grafana: http://localhost:3000"
    echo "   2. Login with admin/bais-admin-2024"
    echo "   3. Navigate to 'Dashboards' → 'BAIS Platform'"
    echo "   4. Review the comprehensive dashboard"
    echo "   5. Check Prometheus for metrics: http://localhost:9090"
    echo "   6. Review Alertmanager for alert rules: http://localhost:9093"
    echo ""
    echo "🔧 To generate more sample data:"
    echo "   curl http://localhost:8002/health"
    echo "   curl http://localhost:8002/api/v1/system/status"
    echo ""
    echo "🛑 To stop monitoring:"
    echo "   docker-compose -f docker-compose.monitoring.yml down"
    echo ""
}

cleanup_on_error() {
    log_error "Setup failed, cleaning up..."
    docker-compose -f docker-compose.monitoring.yml down 2>/dev/null || true
}

# ----------------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------------
main() {
    log_info "Setting up BAIS Platform monitoring preview..."
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    check_prerequisites
    ensure_staging_environment
    deploy_monitoring_stack
    generate_sample_metrics
    validate_monitoring_setup
    display_access_information
    
    log_success "🎉 Monitoring preview setup completed successfully!"
    log_info "You can now preview the monitoring infrastructure and verify it meets your expectations."
}

# Run main function
main "$@"
