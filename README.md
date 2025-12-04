# BAIS - Business-Agent Integration Standard

BAIS is a universal platform that makes businesses discoverable and bookable through AI agents. Once a business registers with BAIS, it becomes instantly accessible to users through any AI assistant (Claude, ChatGPT, Gemini, or local LLMs like Ollama) without requiring per-business integrations.

## What is BAIS?

BAIS solves a critical problem: **fragmentation in AI-powered business discovery and booking**. Instead of each business needing custom AI integrations, BAIS provides a single, universal standard that works across all AI platforms.

### Key Benefits

- **For Businesses**: Submit your business information once, become discoverable by all AI platforms automatically
- **For AI Platforms**: Register BAIS once, gain access to all registered businesses
- **For Consumers**: Use any AI assistant to find and book with any BAIS business

## Architecture

BAIS uses a **universal tools architecture**:

1. **Three Universal Tools**: All businesses are accessible through three standardized tools:
   - `bais_search_businesses` - Search for businesses by query, category, or location
   - `bais_get_business_services` - Get available services for a specific business
   - `bais_execute_service` - Execute a service (book appointment, make reservation, etc.)

2. **Single Integration**: BAIS registers these three tools once with each LLM provider (Claude, ChatGPT, Gemini). All businesses become accessible through this single integration.

3. **Database Persistence**: Businesses are stored in PostgreSQL (with SQLite fallback) for reliable persistence across server restarts.

## Features

### Chat Interface
- Modern, responsive chat UI that adapts to light/dark mode
- Direct integration with Ollama (local LLM support)
- Real-time business discovery and booking
- Tool call visualization
- Settings panel for Ollama configuration

### Business Registration
- Simple JSON-based registration
- Automatic service discovery
- Database persistence
- Instant discoverability after registration

### LLM Integration
- Universal webhook endpoints for Claude, ChatGPT, and Gemini
- Tool definitions automatically provided
- Works with local LLMs (Ollama) via Tailscale
- No per-business setup required

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (optional, SQLite fallback available)
- Ollama server (for local LLM support)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd BAIS
   ```

2. **Install dependencies**
   ```bash
   pip install -r backend/production/requirements.txt
   ```

3. **Start the server**
   ```bash
   ./start_bais.sh
   ```

   Or manually:
   ```bash
   python3 -m uvicorn backend.production.main_railway_final:app --host 0.0.0.0 --port 8000
   ```

4. **Access the chat interface**
   - Open http://localhost:8000/chat in your browser

### Configuration

#### Demo Businesses (for development)

BAIS uses a configuration file to load demo businesses, not hard-coded data. This ensures BAIS remains business-agnostic.

Edit `backend/production/config/demo_businesses.json`:
```json
{
  "demo_businesses": [
    {
      "enabled": true,
      "customer_file": "YourBusiness_BAIS_Submission.json",
      "description": "Your Business - Demo for [industry]"
    }
  ],
  "auto_load_on_startup": true,
  "auto_load_when_database_empty": true
}
```

**Important**: Never hard-code business-specific data. Always use:
- Configuration files for demos
- Database for production businesses
- Customer submission files for business data

#### Ollama Setup (for local LLM)

1. Click the settings icon (⚙️) in the chat interface header
2. Enter your Ollama host address (e.g., `http://100.x.x.x:11434` for Tailscale)
3. Enter your model name (e.g., `gpt-oss:120b` or `llama3`)
4. Click Save

#### Database Setup (optional)

Set the `DATABASE_URL` environment variable:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/bais"
```

If not set, BAIS will use in-memory storage (data lost on restart).

## Usage

### Chat Interface

1. Open http://localhost:8000/chat
2. Configure Ollama settings if needed (click ⚙️ icon)
3. Start chatting! Try queries like:
   - "Find a med spa in Las Vegas"
   - "What services does New Life New Image Med Spa offer?"
   - "Book me a Botox appointment"

### Register a Business

Use the registration script:
```bash
python3 scripts/submit_customer.py customers/your-business.json https://bais-production.up.railway.app
```

Or use the API directly:
```bash
curl -X POST http://localhost:8000/api/v1/businesses \
  -H "Content-Type: application/json" \
  -d @customers/your-business.json
```

### Example Business JSON

```json
{
  "name": "Your Business Name",
  "business_type": "healthcare",
  "description": "Business description",
  "address": "123 Main St",
  "city": "Las Vegas",
  "state": "NV",
  "postal_code": "89101",
  "services": [
    {
      "id": "service-1",
      "name": "Service Name",
      "description": "Service description",
      "price": 100.00
    }
  ]
}
```

## API Endpoints

### Core Endpoints

- `GET /` - Server status
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation (Swagger UI)

### Business Management

- `POST /api/v1/businesses` - Register a new business
- `GET /api/v1/businesses/{business_id}` - Get business details
- `GET /api/v1/businesses/{business_id}/services` - Get business services

### LLM Integration

- `GET /api/v1/llm-webhooks/tools/definitions` - Get tool definitions for LLM providers
- `POST /api/v1/llm-webhooks/claude/tool-use` - Claude webhook endpoint
- `POST /api/v1/llm-webhooks/chatgpt/function-call` - ChatGPT webhook endpoint
- `POST /api/v1/llm-webhooks/gemini/function-call` - Gemini webhook endpoint
- `GET /api/v1/llm-webhooks/health` - LLM webhooks health check

### Chat Interface

- `POST /api/v1/chat/message` - Send chat message
- `GET /api/v1/chat/models` - Get available models
- `GET /chat` - Chat interface (HTML)

## Repository Structure Guide

This section provides a comprehensive guide to every file and directory in the BAIS repository, organized by purpose and location.

### Root Level Files

#### Application Entry Points
- **`app.py`** - Simple FastAPI application entry point (alternative root entry for testing)
- **`registration_server.py`** - Standalone business registration server with comprehensive registration API and LLM platform management
- **`staging_app.py`** - Full-featured staging application for acceptance testing with metrics, Redis, and PostgreSQL integration
- **`backend/production/main_railway_final.py`** - **Primary production entry point** for Railway deployment; includes database initialization, demo business loading, and all route registration

#### Configuration Files
- **`Procfile`** - Railway deployment configuration specifying the web server command
- **`railway.json`** - Railway platform configuration (build settings, deploy commands, health checks)
- **`railway-full.json`** - Extended Railway configuration with additional settings
- **`requirements.txt`** - Root-level Python dependencies (minimal)
- **`requirements.staging.txt`** - Staging environment dependencies
- **`runtime.txt`** - Python runtime version specification
- **`pytest.ini`** - Pytest configuration for test discovery and execution

#### Deployment & Infrastructure
- **`Makefile`** - Infrastructure automation (Kubernetes deployment, database setup, monitoring)
- **`docker-compose.yml`** - Docker Compose configuration for local development
- **`docker-compose.staging.yml`** - Docker Compose for staging environment
- **`docker-compose.monitoring.yml`** - Docker Compose for monitoring stack (Prometheus, Grafana, etc.)
- **`Dockerfile.staging`** - Docker image definition for staging environment

#### Startup Scripts
- **`start_bais.sh`** - Main startup script that checks prerequisites, stops running services, and starts the BAIS server
- **`start_backend.sh`** - Alternative backend-only startup script

#### Test Files
- **`test_db_connection.py`** - Database connection testing utility
- **`test_contact_endpoints.py`** - Contact form endpoint testing
- **`test_dashboard_integration.py`** - Dashboard integration testing
- **`test_universal_llm.py`** - Universal LLM tool integration testing
- **`diagnostic_check.py`** - System diagnostic and health checking utility

#### Documentation
- **`README.md`** - This file - main project documentation
- **`DATABASE_SETUP.md`** - Database setup guide (PostgreSQL, SQLite, Railway)
- **`RAILWAY_DATABASE_SETUP.md`** - Railway-specific database configuration guide
- **`REFACTORING_SUMMARY.md`** - Documentation of refactoring to remove hard-coded business data

---

### Backend Structure (`backend/production/`)

#### Main Application Files
- **`main.py`** - Application factory using relative imports (alternative entry point)
- **`main_simple.py`** - Simplified entry point with non-relative imports for Railway
- **`main_railway.py`** - Initial Railway deployment entry point (superseded by `main_railway_final.py`)
- **`main_railway_fixed.py`** - Fixed version of Railway entry point (intermediate version)
- **`main_full.py`** - Full-featured application with all BAIS features enabled
- **`main_phase2.py`** - Phase 2 implementation entry point

#### Core Routes
- **`routes_simple.py`** - Simplified business registration and management routes (currently used)
- **`routes.py`** - Comprehensive route definitions (alternative/legacy)

#### Core Business Logic (`core/`)

**Universal Tools & Business Logic:**
- **`universal_tools.py`** - **Core BAIS universal tools implementation** (bais_search_businesses, bais_get_business_services, bais_execute_service)
- **`database_models.py`** - SQLAlchemy database models (Business, BusinessService, etc.)
- **`business_loader.py`** - Business loading from configuration files (demo businesses)
- **`shared_storage.py`** - In-memory business store fallback when database unavailable

**Protocol Implementations:**
- **`a2a_*.py`** (11 files) - Agent-to-Agent (A2A) protocol implementation:
  - `a2a_agent_card_generator.py` - Agent card generation
  - `a2a_agent_registry.py` - Agent registration and discovery
  - `a2a_authentication.py` - A2A authentication
  - `a2a_dependency_injection.py` - Dependency injection for A2A
  - `a2a_exceptions.py` - A2A-specific exceptions
  - `a2a_integration.py` - A2A integration service
  - `a2a_processor_manager.py` - Task processor management
  - `a2a_registry_network.py` - Network registry operations
  - `a2a_streaming_tasks.py` - Streaming task support
  - `a2a_task_processor.py` - Task processing logic
  - `ap2_exceptions.py` - AP2 payment protocol exceptions

**MCP (Model Context Protocol) Implementation:**
- **`mcp_*.py`** (12 files) - MCP protocol support:
  - `mcp_audit_logger.py` - Audit logging for MCP
  - `mcp_authentication_service.py` - MCP authentication
  - `mcp_error_handler.py` - MCP error handling
  - `mcp_graceful_shutdown.py` - Graceful shutdown for MCP
  - `mcp_input_validation.py` - Input validation
  - `mcp_monitoring.py` - MCP monitoring
  - `mcp_prompts.py` - Prompt management
  - `mcp_route_handlers.py` - Route handlers
  - `mcp_server_generator.py` - MCP server generation
  - `mcp_sse_transport.py` - Server-Sent Events transport
  - `mcp_subscription_manager.py` - Subscription management

**Payment System (`core/payments/`):**
- **`ap2_client.py`** - AP2 payment protocol client
- **`ap2_mandate_validator.py`** - Mandate validation
- **`ap2_payment_workflow.py`** - Payment workflow orchestration
- **`business_validator.py`** - Business validation for payments
- **`cryptographic_mandate_validator.py`** - Cryptographic mandate validation
- **`currency_manager.py`** - Currency management
- **`mandate_manager.py`** - Payment mandate management
- **`models.py`** - Payment data models
- **`payment_coordinator.py`** - Payment coordination
- **`payment_event_publisher.py`** - Event publishing
- **`verifiable_credential.py`** - Verifiable credential support

**Infrastructure & Utilities:**
- **`bais_schema_validator.py`** - BAIS schema validation
- **`business_command_repository.py`** - Command pattern repository
- **`business_query_repository.py`** - Query pattern repository
- **`cache_manager.py`** - Caching layer
- **`circuit_breaker.py`** - Circuit breaker pattern for resilience
- **`connection_pool_manager.py`** - Database connection pooling
- **`constants.py`** - Application constants
- **`comprehensive_error_handler.py`** - Error handling
- **`distributed_tracing.py`** - Distributed tracing support
- **`exceptions.py`** - Custom exceptions
- **`oauth2_*.py`** (4 files) - OAuth2 authentication and authorization
- **`parameter_objects.py`** - Parameter object pattern
- **`protocol_configurations.py`** - Protocol configuration
- **`protocol_error_handler.py`** - Protocol error handling
- **`secrets_manager.py`** - Secrets management
- **`secure_logging.py`** - Secure logging utilities
- **`security_audit_logger.py`** - Security audit logging
- **`unified_error_handler.py`** - Unified error handling
- **`workflow_event_bus.py`** - Event bus for workflows
- **`workflow_state_manager.py`** - Workflow state management
- **`schema_factory.py`** - Schema factory pattern

#### API Endpoints (`api/v1/`)

**Core LLM Integration:**
- **`universal_webhooks.py`** - **Universal webhook endpoints** for Claude, ChatGPT, and Gemini (tool definitions, health checks)
- **`chat_endpoint.py`** - **Chat interface backend** for Ollama integration with BAIS tools

**Protocol-Specific Endpoints:**
- **`a2a/`** - Agent-to-Agent endpoints:
  - `discovery.py` - Agent discovery endpoints
  - `sse_router.py` - Server-Sent Events router
  - `tasks.py` - Task submission and management
- **`mcp/`** - Model Context Protocol endpoints:
  - `prompts_router.py` - Prompt management endpoints
  - `sse_router.py` - MCP SSE transport
  - `subscription_router.py` - Subscription management

**Business & Commerce:**
- **`acp_commerce.py`** - ACP (Agent Commerce Protocol) commerce endpoints
- **`acp_manifest.py`** - ACP manifest generation
- **`contact_router.py`** - Contact form submission
- **`dashboard_router.py`** - Dashboard API endpoints
- **`demo_generation.py`** - Demo business generation endpoints

**Monitoring & Health:**
- **`health_router.py`** - Health check endpoints
- **`monitoring/`** - Monitoring endpoints:
  - `circuit_breaker_router.py` - Circuit breaker status
  - `dashboard_router.py` - Monitoring dashboard
  - `performance_router.py` - Performance metrics

**Payments:**
- **`payments/`** - Payment endpoints:
  - `mandate_router.py` - Payment mandate management
  - `transaction_router.py` - Transaction processing
  - `webhook_router.py` - Payment webhooks

**Error Handling:**
- **`errors/unified_error_router.py`** - Unified error reporting

#### Services (`services/`)

**Business Services:**
- **`business_service.py`** - Core business service logic
- **`business_repository.py`** - Business data repository
- **`business_registration_service.py`** - Business registration logic
- **`business_registration_orchestrator.py`** - Registration orchestration
- **`business_server_factory.py`** - Business server factory
- **`business_validator.py`** - Business data validation
- **`agent_service.py`** - Agent management service

**AI Model Integration:**
- **`ai_models/`** - AI model service wrappers:
  - `universal_ai_router.py` - Universal AI routing
  - `claude_service.py` - Claude API integration
  - `openai_service.py` - OpenAI/ChatGPT integration
  - `gemini_service.py` - Google Gemini integration

**Commerce & Demo Generation:**
- **`commerce/`** - Commerce protocol integration:
  - `acp_integration_service.py` - ACP integration
  - `acp_official_compliance.py` - ACP compliance checking
- **`demo_templates/`** - Demo generation system:
  - `generator/` - Demo generators (schema, MCP server, UI, ACP config)
  - `orchestrator/` - Demo workflow orchestration
  - `scraper/` - Website analysis and scraping
- **`business-registry.json`** - Business registry configuration

#### Configuration (`config/`)

- **`demo_businesses.json`** - **Configuration for demo businesses** - controls which businesses load automatically
- **`README.md`** - Configuration documentation

#### Monitoring (`monitoring/`)

- **`health_checks.py`** - Health check implementations
- **`health.py`** - Health monitoring utilities
- **`metrics.py`** - Prometheus metrics definitions
- **`performance_monitor.py`** - Performance monitoring

#### Middleware (`middleware/`)

- **`security_middleware.py`** - Security middleware (CORS, authentication, etc.)

#### Utilities (`utils/`)

- **`schema_factory.py`** - Schema factory utilities

#### Tests (`tests/`)

- **`conftest.py`** - Pytest configuration and fixtures
- **`test_*.py`** (15 files) - Comprehensive test suite:
  - Protocol compliance tests (ACP, AP2, A2A, MCP)
  - Integration tests
  - Business service tests
  - Security tests
  - Clean code verification tests

#### Dependencies

- **`requirements.txt`** - Production dependencies
- **`requirements_minimal.txt`** - Minimal dependencies for testing
- **`api_models.py`** - Pydantic API models

---

### Frontend (`frontend/`)

#### HTML Files
- **`chat.html`** - **Main chat interface** - responsive UI with dark mode
- **`index.html`** - Landing/home page

#### Styles (`assets/`)
- **`chat-styles.css`** - Chat interface styles with dark mode support
- **`styles.css`** - General application styles

#### JavaScript (`js/`)

**Core Application:**
- **`chat.js`** - **Main chat interface logic** - handles Ollama integration, tool calls, conversation management
- **`app.js`** - Application initialization

**Managers (`managers/`):**
- **`business-details-manager.js`** - Business details UI management
- **`form-validator.js`** - Form validation utilities
- **`ui-state-manager.js`** - UI state management

**Services (`services/`):**
- **`api-client.js`** - Generic API client
- **`production-api-client.js`** - Production API client with error handling
- **`prompt-builder.js`** - Prompt construction utilities

**Utilities (`utils/`):**
- **`dom-elements.js`** - DOM element utilities

**Configuration (`config/`):**
- **`constants.js`** - Frontend constants

**Data (`data/`):**
- **`business-registry.js`** - Business registry data

---

### Scripts (`scripts/`)

#### Business Registration & Testing
- **`submit_customer.py`** - **Main business registration script** - submits business JSON to BAIS API
- **`submit_customer_direct.py`** - Direct business registration (alternative method)
- **`register_business_railway.sh`** - Railway-specific registration script

#### LLM Integration Examples
- **`claude_with_bais.py`** - Claude integration example with BAIS tools
- **`ollama_with_bais.py`** - Ollama integration example
- **`quick_test_claude.py`** - Quick Claude API testing script

#### Testing Scripts
- **`test_business_search.py`** - Business search functionality testing
- **`test_claude_bais.sh`** - Claude integration testing
- **`test_claude_booking_flow.sh`** - End-to-end booking flow testing
- **`test_ollama_bais.sh`** - Ollama integration testing
- **`acceptance_test_suite.py`** - Comprehensive acceptance test suite

#### Demo & Generation
- **`generate_demo.py`** - Demo business generation script
- **`example_demo_generation.py`** - Demo generation example
- **`seed_data.py`** - Database seeding script

#### Security & Auditing
- **`day1-vulnerability-scan.sh`** - Day 1 security vulnerability scanning
- **`day2-secrets-audit.sh`** - Secrets management audit
- **`day3-auth-security.sh`** - Authentication security audit
- **`day4-ap2-crypto.sh`** - AP2 cryptographic security audit
- **`day5-https-tls.sh`** - HTTPS/TLS configuration audit
- **`day6-audit-logging.sh`** - Audit logging verification
- **`day7-final-review.sh`** - Final security review
- **`week1-security-audit.sh`** - Week 1 comprehensive security audit
- **`verify-clean-code-principles.sh`** - Clean code principles verification
- **`verify-infrastructure-best-practices.sh`** - Infrastructure best practices check

#### Performance & Monitoring
- **`week2-performance-testing.sh`** - Performance testing suite
- **`demo-week2-performance.sh`** - Performance demo script
- **`monitoring-health-check.sh`** - Monitoring system health check
- **`deploy-monitoring.sh`** - Monitoring stack deployment
- **`setup-monitoring-preview.sh`** - Monitoring preview setup
- **`prometheus-alerts.yaml`** - Prometheus alert rules

#### Deployment & Operations
- **`staging-deployment.sh`** - Staging environment deployment
- **`production-golive-checklist.sh`** - Production go-live checklist
- **`quick-start.sh`** - Quick start script for new developers
- **`deploy_dashboard_endpoints.sh`** - Dashboard endpoints deployment

#### Utility Scripts
- **`oncall-rotation-setup.py`** - On-call rotation setup
- **`remove-clean-code-references.sh`** - Cleanup script for code references
- **`remove-infrastructure-clean-code-references.sh`** - Infrastructure cleanup script

#### Configuration Files
- **`grafana-dashboard-bais.json`** - Grafana dashboard configuration
- **`simple-dashboard.json`** - Simple dashboard configuration
- **`init-db.sql`** - Database initialization SQL
- **`OLLAMA_BAIS_DEMO.md`** - Ollama BAIS demo documentation

---

### Customers (`customers/`)

- **`NewLifeNewImage_CORRECTED_BAIS_Submission.json`** - Example business submission (med spa)
- **`NewLifeNewImage_REGISTRATION_INFO.md`** - Registration information for demo business

---

### Infrastructure (`infrastructure/`)

#### Kubernetes (`k8s/`)
- **`deployment.yaml`** - Kubernetes deployment configuration
- **`service.yaml`** - Kubernetes service configuration
- **`hpa.yaml`** - Horizontal Pod Autoscaler configuration
- **`vpa.yaml`** - Vertical Pod Autoscaler configuration

#### Database (`database/`)
- **`postgresql.yaml`** - PostgreSQL Kubernetes deployment

#### Cache (`cache/`)
- **`redis-cluster.yaml`** - Redis cluster Kubernetes deployment

#### Docker (`docker/`)
- **`Dockerfile`** - Production Docker image definition
- **`docker-compose.yml`** - Docker Compose for infrastructure

#### Logging (`logging/`)
- **`elasticsearch.yaml`** - Elasticsearch deployment
- **`kibana.yaml`** - Kibana deployment
- **`logstash-config.yaml`** - Logstash configuration
- **`filebeat-config.yaml`** - Filebeat configuration

#### Monitoring (`monitoring/`)
- **`prometheus-config.yaml`** - Prometheus configuration

#### Scripts (`scripts/`)
- **`deploy.sh`** - Infrastructure deployment script

#### Utilities (`utils/`)
- **`infrastructure_manager.py`** - Infrastructure management utilities

---

### Monitoring (`monitoring/`)

#### Prometheus & Alerting
- **`prometheus.yml`** - Main Prometheus configuration
- **`prometheus-simple.yml`** - Simplified Prometheus config
- **`alertmanager.yml`** - Alertmanager configuration
- **`alert_rules.yml`** - Prometheus alert rules

#### Grafana
- **`grafana-datasources.yml`** - Grafana data source configuration
- **`grafana-dashboard-config.yml`** - Dashboard configuration
- **`grafana/dashboards/bais-ap2-dashboard.json`** - AP2 monitoring dashboard

#### Loki
- **`loki-config.yml`** - Loki log aggregation configuration

---

### Backend Root (`backend/`)

- **`__init__.py`** - Python package initialization
- **`Dockerfile`** - Alternative Docker configuration
- **`env.example`** - Environment variable template
- **`package.json`** - Node.js dependencies (if any)
- **`requirements.txt`** - Backend dependencies
- **`server.js`** - Node.js server (alternative/legacy)
- **`scripts/`** - Backend-specific scripts:
  - `backup.sh` - Database backup script
  - `restore.sh` - Database restore script
  - `deploy.sh` - Backend deployment script
- **`src/`** - Node.js source (alternative implementation):
  - `app.js` - Express application
  - `controllers/`, `middleware/`, `routes/`, `services/`, `utils/` - Node.js application structure

---

### Nginx (`nginx/`)

- **`nginx.conf`** - Nginx web server configuration
- **`conf.d/`** - Additional Nginx configuration files

---

## Key Files Quick Reference

### Must-Know Files
1. **`backend/production/main_railway_final.py`** - Production entry point
2. **`backend/production/core/universal_tools.py`** - Core BAIS tools implementation
3. **`backend/production/api/v1/universal_webhooks.py`** - LLM webhook endpoints
4. **`backend/production/api/v1/chat_endpoint.py`** - Chat interface backend
5. **`frontend/chat.html`** - Chat UI
6. **`frontend/js/chat.js`** - Chat interface logic
7. **`scripts/submit_customer.py`** - Business registration
8. **`start_bais.sh`** - Startup script
9. **`backend/production/config/demo_businesses.json`** - Demo business configuration

### Configuration Files
- **`railway.json`** - Railway deployment config
- **`backend/production/config/demo_businesses.json`** - Demo businesses
- **`docker-compose.yml`** - Local development setup
- **`requirements.txt`** - Python dependencies
- **`.env`** (not in repo) - Environment variables (see `backend/env.example`)

### Documentation Files
- **`README.md`** - This file
- **`DATABASE_SETUP.md`** - Database setup guide
- **`RAILWAY_DATABASE_SETUP.md`** - Railway-specific database guide
- **`REFACTORING_SUMMARY.md`** - Refactoring documentation

## Deployment

### Railway Deployment

BAIS is configured for Railway deployment:

1. Connect your repository to Railway
2. Set environment variables:
   - `DATABASE_URL` - PostgreSQL connection string (Railway auto-provides)
   - `PORT` - Server port (Railway auto-provides)
3. Railway will automatically deploy using `backend/production/main_railway_final.py`

### Local Deployment

```bash
./start_bais.sh
```

The script will:
- Check prerequisites
- Install dependencies if needed
- Start the FastAPI server
- Serve the frontend at http://localhost:8000/chat

## How It Works

### Universal Discovery

1. **Business Registration**: A business submits their information via JSON
2. **Database Storage**: Business is stored in PostgreSQL with all services
3. **Instant Discovery**: Business becomes immediately searchable through BAIS tools
4. **AI Access**: Any AI agent using BAIS tools can discover and interact with the business

### Example Flow

1. User asks AI: "Find a med spa in Las Vegas"
2. AI calls `bais_search_businesses` with query="med spa", location="Las Vegas"
3. BAIS searches database and returns matching businesses
4. AI presents results to user
5. User asks: "Book a Botox appointment"
6. AI calls `bais_get_business_services` to get available services
7. AI calls `bais_execute_service` to create the booking
8. Booking is processed and confirmed

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string (optional, uses SQLite fallback)
- `PORT` - Server port (default: 8000)
- `ANTHROPIC_API_KEY` - For Claude integration (if using Claude directly)
- `OLLAMA_HOST` - Ollama server address (default: http://localhost:11434)
- `OLLAMA_MODEL` - Ollama model name (default: llama3)

## Troubleshooting

### Chat Interface Not Loading

- Verify backend is running: `curl http://localhost:8000/health`
- Check browser console for errors
- Ensure frontend files exist in `frontend/` directory

### Ollama Connection Errors

- Verify Ollama server is running and accessible
- Check Tailscale connection if using remote server
- Test connection: `curl http://your-ollama-host:11434/api/tags`
- Verify host address in settings (include `http://` prefix)

### Business Not Found

- Verify business is registered: Check database or re-register
- Test search endpoint directly using API documentation at `/docs`
- Check business data includes proper location and service information

## License

Proprietary software. All rights reserved.
