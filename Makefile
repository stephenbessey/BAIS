.PHONY: help build start stop restart logs clean test migrate backup restore

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

start: ## Start all services
	docker-compose up -d

stop: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs
	docker-compose logs -f

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

test: ## Run tests
	docker-compose run --rm bais-api python -m pytest

migrate: ## Run database migrations
	docker-compose run --rm bais-api python -m alembic upgrade head

backup: ## Create database backup
	./scripts/backup.sh

restore: ## Restore database (usage: make restore BACKUP=filename.sql.gz)
	./scripts/restore.sh $(BACKUP)

deploy: ## Deploy to production
	./scripts/deploy.sh

status: ## Check service status
	docker-compose ps
	docker-compose exec bais-api curl -f http://localhost:8000/health
	docker-compose exec oauth-server curl -f http://localhost:8003/oauth/.well-known/authorization_server

monitor: ## Open monitoring dashboard
	open http://localhost:3001