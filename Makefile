# ============================================================================
# BAIS Platform - Infrastructure Setup Makefile
# Best practices: Clear Targets, Self-Documenting, Reusable
# ============================================================================

.PHONY: help setup deploy test clean

# Default target: show help
.DEFAULT_GOAL := help

# ============================================================================
# Configuration Variables (Override with environment variables)
# ============================================================================

NAMESPACE ?= bais-production
MONITORING_NS ?= monitoring
LOGGING_NS ?= logging
VERSION ?= latest
DB_USER ?= bais_user
REDIS_CLUSTER_SIZE ?= 6
KUBE_CONTEXT ?= production
CLOUD_PROVIDER ?= aws
REGION ?= us-east-1

# ============================================================================
# Help Target (Self-Documenting)
# ============================================================================

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ============================================================================
# Prerequisites & Validation
# ============================================================================

check-tools: ## Check required tools are installed
	@echo "Checking prerequisites..."
	@command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required but not installed"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "docker is required but not installed"; exit 1; }
	@command -v helm >/dev/null 2>&1 || { echo "helm is required but not installed"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "python3 is required but not installed"; exit 1; }
	@echo "✓ All prerequisites satisfied"

check-env: ## Validate environment variables
	@echo "Checking environment configuration..."
	@test -n "$(DATABASE_URL)" || { echo "DATABASE_URL is required"; exit 1; }
	@test -n "$(REDIS_URL)" || { echo "REDIS_URL is required"; exit 1; }
	@test -n "$(SECRET_KEY)" || { echo "SECRET_KEY is required"; exit 1; }
	@echo "✓ Environment validated"

set-context: ## Set kubectl context to production
	@kubectl config use-context $(KUBE_CONTEXT)
	@echo "✓ Using context: $(KUBE_CONTEXT)"

# ============================================================================
# Infrastructure Setup - Phase 1: Foundation
# ============================================================================

create-namespaces: ## Create Kubernetes namespaces
	@echo "Creating namespaces..."
	@kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	@kubectl create namespace $(MONITORING_NS) --dry-run=client -o yaml | kubectl apply -f -
	@kubectl create namespace $(LOGGING_NS) --dry-run=client -o yaml | kubectl apply -f -
	@echo "✓ Namespaces created"

setup-secrets: check-env ## Create Kubernetes secrets
	@echo "Setting up secrets..."
	@kubectl create secret generic bais-secrets \
		--from-literal=database-url="$(DATABASE_URL)" \
		--from-literal=redis-url="$(REDIS_URL)" \
		--from-literal=secret-key="$(SECRET_KEY)" \
		--namespace=$(NAMESPACE) \
		--dry-run=client -o yaml | kubectl apply -f -
	@kubectl create secret generic postgres-secrets \
		--from-literal=POSTGRES_USER="$(DB_USER)" \
		--from-literal=POSTGRES_PASSWORD="$(DB_PASSWORD)" \
		--namespace=$(NAMESPACE) \
		--dry-run=client -o yaml | kubectl apply -f -
	@echo "✓ Secrets configured"

# ============================================================================
# Infrastructure Setup - Phase 2: Database
# ============================================================================

setup-postgres: ## Deploy PostgreSQL database
	@echo "Deploying PostgreSQL..."
	@kubectl apply -f infrastructure/database/postgresql.yaml
	@kubectl wait --for=condition=ready pod \
		-l app=postgres-primary \
		-n $(NAMESPACE) \
		--timeout=300s
	@echo "✓ PostgreSQL deployed"

init-database: ## Initialize database schema
	@echo "Initializing database..."
	@kubectl run migration-job \
		--image=bais/api:$(VERSION) \
		--restart=Never \
		--namespace=$(NAMESPACE) \
		--command -- alembic upgrade head
	@kubectl wait --for=condition=complete job/migration-job \
		-n $(NAMESPACE) --timeout=300s
	@kubectl delete job migration-job -n $(NAMESPACE)
	@echo "✓ Database initialized"

# ============================================================================
# Infrastructure Setup - Phase 3: Cache (Redis)
# ============================================================================

setup-redis: ## Deploy Redis cluster
	@echo "Deploying Redis cluster..."
	@kubectl apply -f infrastructure/cache/redis-cluster.yaml
	@kubectl wait --for=condition=ready pod \
		-l app=redis-cluster \
		-n $(NAMESPACE) \
		--timeout=300s
	@echo "✓ Redis cluster deployed"

# ============================================================================
# Infrastructure Setup - Phase 4: Application
# ============================================================================

build-image: ## Build Docker image
	@echo "Building application image..."
	@docker build -t bais/api:$(VERSION) \
		-f infrastructure/docker/Dockerfile .
	@echo "✓ Image built: bais/api:$(VERSION)"

deploy-app: ## Deploy application to Kubernetes
	@echo "Deploying application..."
	@kubectl apply -f infrastructure/k8s/deployment.yaml
	@kubectl apply -f infrastructure/k8s/service.yaml
	@kubectl apply -f infrastructure/k8s/ingress.yaml
	@kubectl wait --for=condition=available \
		deployment/bais-api \
		-n $(NAMESPACE) \
		--timeout=300s
	@echo "✓ Application deployed"

# ============================================================================
# Complete Setup Workflows
# ============================================================================

setup-foundation: check-tools set-context create-namespaces setup-secrets ## Setup foundation
	@echo "✓ Foundation setup complete"

setup-database-stack: setup-postgres init-database ## Setup complete database stack
	@echo "✓ Database stack ready"

setup-cache-stack: setup-redis ## Setup complete cache stack
	@echo "✓ Cache stack ready"

setup-app-stack: build-image deploy-app ## Setup complete application stack
	@echo "✓ Application stack ready"

# ============================================================================
# Main Setup Target (Complete Infrastructure)
# ============================================================================

setup: check-tools check-env ## Complete infrastructure setup (all phases)
	@echo "=========================================="
	@echo "Starting Complete Infrastructure Setup"
	@echo "=========================================="
	@$(MAKE) setup-foundation
	@$(MAKE) setup-database-stack
	@$(MAKE) setup-cache-stack
	@$(MAKE) setup-app-stack
	@echo ""
	@echo "=========================================="
	@echo "Infrastructure Setup Complete!"
	@echo "=========================================="

# ============================================================================
# Status & Information
# ============================================================================

status: ## Show infrastructure status
	@echo "=== Application Status ==="
	@kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "=== Services ==="
	@kubectl get svc -n $(NAMESPACE)

info: ## Display cluster information
	@echo "Kubernetes Context: $(shell kubectl config current-context)"
	@echo "Namespace: $(NAMESPACE)"
	@echo "Version: $(VERSION)"