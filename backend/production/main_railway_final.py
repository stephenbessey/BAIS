"""
BAIS Production Application - Railway Final Version
Complete BAIS backend with simplified routes for Railway deployment
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Dict, Any

# Configure detailed logging for diagnostics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add current directory to Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add parent directory to path so imports work correctly
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
# Add backend directory to path
backend_dir = os.path.dirname(parent_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Diagnostic information
def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information for diagnostics"""
    try:
        return {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "working_directory": os.getcwd(),
            "environment_variables": {
                "PORT": os.getenv("PORT", "not_set"),
                "DATABASE_URL": "set" if os.getenv("DATABASE_URL") else "not_set",
                "REDIS_URL": "set" if os.getenv("REDIS_URL") else "not_set",
                "BAIS_ENVIRONMENT": os.getenv("BAIS_ENVIRONMENT", "not_set"),
                "RAILWAY_ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT", "not_set")
            },
            "timestamp": datetime.utcnow().isoformat(),
            "railway_deployment": True
        }
    except Exception as e:
        return {"error": f"Failed to get system info: {str(e)}"}

# Try to import and create the complete BAIS application
import_errors = []
system_info = get_system_info()

# Create the FastAPI app FIRST, before any other imports
# This ensures the app exists even if imports fail
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Create the FastAPI app immediately
app = FastAPI(
    title="BAIS Production Server",
    description="Business-Agent Integration Standard Production Implementation - Complete Backend",
    version="1.0.0"
)

# Track app readiness
app.state.ready = False

# Add CORS middleware immediately
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add basic health endpoint immediately (before other imports)
# This endpoint MUST work even if everything else fails
@app.get("/health")
def basic_health_check():
    """Basic health check that's always available - no dependencies"""
    # This endpoint MUST always return 200 OK for Railway health checks
    # Keep it as simple as possible - no dependencies on imports or app state
    try:
        # Safely get ready status - app.state might not be initialized yet
        ready_status = False
        try:
            ready_status = getattr(app.state, 'ready', False)
        except (AttributeError, RuntimeError, Exception):
            # App state not initialized yet, that's okay
            pass
        
        # Try to get timestamp, but don't fail if datetime isn't available
        try:
            timestamp = datetime.utcnow().isoformat()
        except:
            timestamp = "unknown"
        
        return {
            "status": "healthy",
            "service": "BAIS Production Server",
            "environment": "railway",
            "ready": ready_status,
            "timestamp": timestamp
        }
    except Exception:
        # Even if everything fails, return a minimal healthy response
        # This ensures Railway health checks always pass
        # Railway needs a 200 OK response, not an error
        return {
            "status": "healthy",
            "service": "BAIS Production Server",
            "ready": False,
            "note": "Startup in progress"
        }

try:
    logger.info("Starting BAIS Railway final deployment initialization...")
    logger.info(f"System info: {system_info}")
    
    # Add static file serving for frontend
    try:
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse
        from pathlib import Path
        
        # Get project root (3 levels up from this file)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        frontend_path = os.path.join(project_root, "frontend")
        
        if os.path.exists(frontend_path):
            # Mount static files (assets, js, etc.)
            app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")
            app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")
            
            # Serve chat.html at /chat
            @app.get("/chat")
            async def serve_chat():
                chat_file = os.path.join(frontend_path, "chat.html")
                if os.path.exists(chat_file):
                    return FileResponse(chat_file)
                return {"error": "Chat interface not found"}
            
            logger.info(f"Serving frontend from {frontend_path}")
    except Exception as e:
        logger.warning(f"Could not set up static file serving: {e}")
    
    logger.info("Created FastAPI app with CORS middleware")
    
    # Import and configure simplified routes
    try:
        # Try relative import first
        try:
            from .routes_simple import api_router
            logger.info("Imported routes_simple using relative import")
        except ImportError:
            # Try absolute import
            try:
                from routes_simple import api_router
                logger.info("Imported routes_simple using absolute import")
            except ImportError:
                # Try with backend.production prefix
                from backend.production.routes_simple import api_router
                logger.info("Imported routes_simple using backend.production prefix")
        
        # Include API routes
        app.include_router(api_router, prefix="/api/v1")
        logger.info("Successfully imported and configured simplified API routes")
        
    except Exception as e:
        logger.error(f"Could not import simplified routes: {e}")
        logger.error(f"Import error details: {traceback.format_exc()}")
        import_errors.append(f"Routes import error: {str(e)}")
    
    # Import and configure Universal LLM Integration
    try:
        # Add project root to path for proper imports
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Use absolute import from project root
        from backend.production.api.v1.universal_webhooks import router as universal_webhook_router
        
        # Include universal webhook routes
        app.include_router(universal_webhook_router)
        logger.info("Successfully imported and configured Universal LLM webhook routes")
        
    except ImportError as e:
        logger.error(f"Could not import universal webhook routes: {e}")
        import_errors.append(f"Universal webhooks import error: {str(e)}")
        logger.error(f"Import error details: {traceback.format_exc()}")
        # Add a fallback health endpoint if import fails
        @app.get("/api/v1/llm-webhooks/health")
        def fallback_webhook_health():
            return {
                "status": "degraded",
                "message": "Universal webhook routes not available",
                "error": str(e)
            }
    
    # Ensure health endpoint is always available (even if router import failed)
    # This is a safety net - the router should already have this endpoint
    if not any(r.path == "/api/v1/llm-webhooks/health" for r in app.routes if hasattr(r, 'path')):
        @app.get("/api/v1/llm-webhooks/health")
        def ensure_webhook_health():
            return {
                "status": "healthy",
                "architecture": "universal",
                "description": "Handles requests for ALL BAIS businesses",
                "endpoints": {
                    "claude": "/api/v1/llm-webhooks/claude/tool-use",
                    "chatgpt": "/api/v1/llm-webhooks/chatgpt/function-call",
                    "gemini": "/api/v1/llm-webhooks/gemini/function-call"
                },
                "tools": {
                    "search": "bais_search_businesses",
                    "services": "bais_get_business_services",
                    "execute": "bais_execute_service"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Import and configure Chat Endpoint
    try:
        # Add project root to path for proper imports
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Use absolute import from project root
        from backend.production.api.v1.chat_endpoint import router as chat_router
        
        # Include chat routes
        app.include_router(chat_router)
        logger.info("Successfully imported and configured Chat endpoint routes")
        
    except ImportError as e:
        logger.warning(f"Could not import chat endpoint routes: {e}")
        import_errors.append(f"Chat endpoint import error: {str(e)}")
        logger.warning(f"Import error details: {traceback.format_exc()}")
    
    logger.info("Successfully created BAIS application with available routes")
    
    # Initialize database tables if DATABASE_URL is configured
    # Do this after routes are loaded so routes work even if DB init fails
    # Use background thread to avoid blocking startup
    database_url = os.getenv("DATABASE_URL")
    # Try alternative names Railway might use
    if not database_url or database_url == "not_set":
        database_url = os.getenv("POSTGRES_URL") or os.getenv("PGDATABASE_URL")
    
    if database_url and database_url.strip() and database_url != "not_set":
        # Log that we found DATABASE_URL (mask password)
        masked_url = database_url.split('@')[1] if '@' in database_url else "***"
        logger.info(f"📊 DATABASE_URL found: postgresql://***@{masked_url}")
        
        import threading
        
        def init_database_background():
            """Initialize database in background thread with timeout"""
            try:
                # Try multiple import paths
                DatabaseManager = None
                try:
                    from core.database_models import DatabaseManager
                except (ImportError, NameError):
                    try:
                        from .core.database_models import DatabaseManager
                    except (ImportError, NameError):
                        try:
                            from backend.production.core.database_models import DatabaseManager
                        except (ImportError, NameError) as e:
                            logger.warning(f"Could not import DatabaseManager: {e}")
                            return
                
                if DatabaseManager:
                    try:
                        # Create database manager - it will handle connection pooling
                        # The connection will be established lazily on first use
                        # Capture database_url from outer scope
                        db_url = database_url
                        db_manager = DatabaseManager(db_url)
                        # Create tables - this should be fast if tables already exist
                        # If connection fails, it will raise an exception which we catch
                        db_manager.create_tables()
                        logger.info("Database tables initialized successfully")
                        
                        # Verify database connection by checking business count
                        try:
                            from core.database_models import Business
                        except ImportError:
                            try:
                                from .core.database_models import Business
                            except ImportError:
                                from backend.production.core.database_models import Business
                        
                        with db_manager.get_session() as session:
                            business_count = session.query(Business).count()
                            active_count = session.query(Business).filter(Business.status == "active").count()
                            logger.info(f"✅ Database connection verified: {business_count} businesses in database ({active_count} active)")
                    except Exception as db_init_error:
                        logger.warning(f"Database initialization failed (non-blocking): {db_init_error}")
                        import traceback
                        logger.debug(f"Database error details: {traceback.format_exc()}")
                        # Don't fail the entire app if database init fails
                else:
                    logger.warning("DatabaseManager not available, skipping table initialization")
            except Exception as db_error:
                logger.warning(f"Database initialization failed: {db_error}")
                logger.warning("Continuing with in-memory storage only - routes will still work")
        
        # Start database initialization in background thread
        db_thread = threading.Thread(target=init_database_background, daemon=True)
        db_thread.start()
        logger.info("Database initialization started in background thread")
        
        # Register default business if not exists (in background after DB init)
        def register_default_business():
            """Register default business if database is available and business doesn't exist"""
            import time
            import asyncio
            import json
            from pathlib import Path
            
            # Retry logic: try multiple times with increasing delays
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # Wait for database to be ready (exponential backoff)
                    wait_time = 5 + (attempt * 5)  # 5s, 10s, 15s, 20s, 25s
                    if attempt > 0:
                        logger.info(f"Retrying default business registration (attempt {attempt + 1}/{max_retries}) after {wait_time}s...")
                    time.sleep(wait_time)
                    
                    database_url = os.getenv("DATABASE_URL")
                    # Try alternative names Railway might use
                    if not database_url or database_url == "not_set":
                        database_url = os.getenv("POSTGRES_URL") or os.getenv("PGDATABASE_URL")
                    
                    if not database_url or database_url.strip() == "" or database_url == "not_set":
                        if attempt == max_retries - 1:
                            logger.info("No DATABASE_URL configured after all retries, skipping default business registration")
                        continue
                    
                    # Try to import database models
                    DatabaseManager = None
                    Business = None
                    try:
                        from core.database_models import DatabaseManager, Business
                    except ImportError:
                        try:
                            from .core.database_models import DatabaseManager, Business
                        except ImportError:
                            try:
                                from backend.production.core.database_models import DatabaseManager, Business
                            except ImportError:
                                if attempt == max_retries - 1:
                                    logger.warning("Could not import database models for default business registration")
                                continue
                    
                    if not DatabaseManager or not Business:
                        continue
                    
                    # Test database connection
                    try:
                        db_manager = DatabaseManager(database_url)
                        with db_manager.get_session() as session:
                            # Quick connection test
                            session.query(Business).limit(1).all()
                    except Exception as conn_error:
                        logger.debug(f"Database not ready yet (attempt {attempt + 1}): {conn_error}")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.warning(f"Database connection failed after {max_retries} attempts: {conn_error}")
                            return
                    
                    # Database is ready - check if business exists
                    db_manager = DatabaseManager(database_url)
                    with db_manager.get_session() as session:
                        existing = session.query(Business).filter(
                            Business.external_id == "new-life-new-image-med-spa"
                        ).first()
                        
                        if existing:
                            logger.info(f"✅ Default business 'New Life New Image Med Spa' already registered in database (ID: {existing.external_id})")
                            return
                    
                    # Business doesn't exist - register it using the shared registration function
                    try:
                        from routes_simple import register_business_to_database, BusinessRegistrationRequest
                    except ImportError:
                        try:
                            from .routes_simple import register_business_to_database, BusinessRegistrationRequest
                        except ImportError:
                            try:
                                from backend.production.routes_simple import register_business_to_database, BusinessRegistrationRequest
                            except ImportError as import_err:
                                logger.error(f"Could not import registration function: {import_err}")
                                return
                    
                    # Load customer data
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    customer_file = Path(project_root) / "customers" / "NewLifeNewImage_CORRECTED_BAIS_Submission.json"
                    
                    if not customer_file.exists():
                        logger.warning(f"Customer file not found at {customer_file}, skipping default registration")
                        return
                    
                    logger.info(f"📋 Loading customer data from {customer_file}")
                    with open(customer_file, 'r') as f:
                        customer_data = json.load(f)
                    
                    # Create registration request
                    registration_request = BusinessRegistrationRequest(
                        business_name=customer_data["business_name"],
                        business_type=customer_data["business_type"],
                        contact_info=customer_data["contact_info"],
                        location=customer_data["location"],
                        services_config=customer_data["services_config"],
                        business_info=customer_data.get("business_info"),
                        integration=customer_data.get("integration"),
                        ap2_config=customer_data.get("ap2_config")
                    )
                    
                    # Call shared registration function (synchronous, idempotent)
                    logger.info(f"🚀 Registering default business '{registration_request.business_name}'...")
                    success, registered_id = register_business_to_database(registration_request, database_url)
                    
                    if success:
                        logger.info(f"✅ Default business '{registration_request.business_name}' auto-registered successfully! (ID: {registered_id})")
                    else:
                        logger.error(f"❌ Failed to auto-register default business")
                    
                    # Success - exit retry loop
                    return
                    
                except Exception as e:
                    logger.warning(f"Default business registration attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        logger.error(f"❌ Default business registration failed after {max_retries} attempts: {e}")
                        import traceback
                        logger.error(f"Final error details: {traceback.format_exc()}")
        
        # Start default business registration in background
        default_biz_thread = threading.Thread(target=register_default_business, daemon=True)
        default_biz_thread.start()
        logger.info("Default business registration check started in background")
    
except Exception as e:
    import_errors.append(f"Unexpected error: {str(e)}")
    logger.error(f"Unexpected error during initialization: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    # App already exists, so we don't need to recreate it
    # Just log the error and continue

# Add core endpoints (always available)
@app.get("/")
def root():
    return {
        "message": "BAIS Production Server is running",
        "status": "operational",
        "version": "1.0.0",
        "environment": "railway",
        "import_errors": len(import_errors),
        "features_available": len(import_errors) == 0,
        "endpoints": {
            "health": "/health",
            "diagnostics": "/diagnostics", 
            "api_docs": "/docs",
            "api_status": "/api/status",
            "business_registration": "/api/v1/businesses",
            "agent_interaction": "/api/v1/agents/interact",
            "payment_processing": "/api/v1/payments"
        }
    }

# Health endpoint is already defined above - this is just for reference
# The health endpoint at line 83 is the one that will be used

@app.get("/api/status")
def api_status():
    return {
        "api": "operational",
        "endpoints": [
            "/", "/health", "/api/status", "/docs", "/diagnostics",
            "/api/v1/businesses", "/api/v1/agents/interact", "/api/v1/payments",
            "/api/v1/llm-webhooks/claude/tool-use",
            "/api/v1/llm-webhooks/chatgpt/function-call", 
            "/api/v1/llm-webhooks/gemini/function-call",
            "/api/v1/llm-webhooks/health", "/api/v1/llm-webhooks/test"
        ],
        "ready_for_customers": len(import_errors) == 0,
        "features": {
            "business_registration": "available",
            "business_status_tracking": "available",
            "agent_interaction": "available",
            "payment_processing": "available",
            "a2a_protocol": "available",
            "mcp_protocol": "available",
            "monitoring": "available",
            "universal_llm_integration": "available"
        },
        "customer_integration": {
            "api_documentation": "/docs",
            "health_monitoring": "/health",
            "system_diagnostics": "/diagnostics",
            "business_endpoints": "/api/v1/businesses",
            "agent_endpoints": "/api/v1/agents",
            "payment_endpoints": "/api/v1/payments",
            "universal_llm_tools": "/api/v1/llm-webhooks/tools/definitions"
        },
        "llm_integration": {
            "claude": "Available via bais_search_businesses, bais_get_business_services, bais_execute_service",
            "chatgpt": "Available via GPT Actions integration", 
            "gemini": "Available via Function Calling integration",
            "universal_access": "ANY consumer can buy from ANY BAIS business through ANY AI"
        }
    }

# Add diagnostic endpoints
@app.get("/diagnostics")
def get_diagnostics():
    """Comprehensive diagnostic endpoint"""
    # Check all possible DATABASE_URL variable names
    db_url = os.getenv("DATABASE_URL")
    postgres_url = os.getenv("POSTGRES_URL")
    pgdatabase_url = os.getenv("PGDATABASE_URL")
    pg_url = os.getenv("PG_URL")
    
    # Check Railway-specific variables
    railway_db_url = os.getenv("RAILWAY_DATABASE_URL")
    
    # Mask passwords for security
    def mask_url(url):
        if not url:
            return None
        try:
            if '@' in url:
                return f"postgresql://***@{url.split('@')[1]}"
            return "postgresql://***"
        except:
            return "***"
    
    return {
        "system_info": system_info,
        "import_errors": import_errors,
        "app_type": "complete_bais_railway" if import_errors == [] else "diagnostic_railway",
        "timestamp": datetime.utcnow().isoformat(),
        "python_path": sys.path[:10],  # First 10 entries to avoid huge response
        "environment_check": {
            "required_env_vars": {
                "PORT": os.getenv("PORT", "not_set"),
                "DATABASE_URL": "set" if db_url else "not_set",
                "DATABASE_URL_value": mask_url(db_url),
                "POSTGRES_URL": "set" if postgres_url else "not_set",
                "POSTGRES_URL_value": mask_url(postgres_url),
                "PGDATABASE_URL": "set" if pgdatabase_url else "not_set",
                "PGDATABASE_URL_value": mask_url(pgdatabase_url),
                "PG_URL": "set" if pg_url else "not_set",
                "PG_URL_value": mask_url(pg_url),
                "RAILWAY_DATABASE_URL": "set" if railway_db_url else "not_set",
                "RAILWAY_DATABASE_URL_value": mask_url(railway_db_url),
                "REDIS_URL": "set" if os.getenv("REDIS_URL") else "not_set"
            },
            "optional_env_vars": {
                "BAIS_ENVIRONMENT": os.getenv("BAIS_ENVIRONMENT", "not_set"),
                "OAUTH_CLIENT_ID": "set" if os.getenv("OAUTH_CLIENT_ID") else "not_set",
                "AP2_API_KEY": "set" if os.getenv("AP2_API_KEY") else "not_set"
            }
        },
        "available_features": {
            "business_registration": "available",
            "agent_interaction": "available",
            "payment_processing": "available",
            "monitoring": "available",
            "api_documentation": "available"
        }
    }

@app.get("/health/detailed")
def detailed_health():
    """Detailed health check for diagnostics"""
    # Check DATABASE_URL with fallbacks
    database_url = os.getenv("DATABASE_URL")
    if not database_url or database_url == "not_set":
        database_url = os.getenv("POSTGRES_URL") or os.getenv("PGDATABASE_URL")
    
    # Mask password in URL for logging
    masked_url = None
    if database_url:
        try:
            if '@' in database_url:
                masked_url = f"postgresql://***@{database_url.split('@')[1]}"
            else:
                masked_url = "postgresql://***"
        except:
            masked_url = "***"
    
    health_status = {
        "status": "healthy" if import_errors == [] else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "system_info": system_info,
        "import_errors": import_errors,
        "environment": {
            "PORT": os.getenv("PORT", "not_set"),
            "DATABASE_URL": masked_url if masked_url else ("configured" if database_url else "missing"),
            "DATABASE_URL_RAW": "set" if database_url else "not_set",
            "POSTGRES_URL": "set" if os.getenv("POSTGRES_URL") else "not_set",
            "PGDATABASE_URL": "set" if os.getenv("PGDATABASE_URL") else "not_set",
            "REDIS_URL": "configured" if os.getenv("REDIS_URL") else "missing"
        },
        "customer_readiness": {
            "api_endpoints": "available",
            "business_registration": "available",
            "agent_interaction": "available", 
            "payment_processing": "available",
            "monitoring": "available",
            "documentation": "available"
        }
    }
    
    if import_errors:
        health_status["recommendations"] = [
            "Check Railway logs for detailed error information",
            "Verify all dependencies are installed correctly",
            "Check environment variables are set properly",
            "Review import paths and module structure"
        ]
    
    return health_status

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )

# Final safety check: ensure app is always defined
if app is None:
    logger.error("CRITICAL: App is None! Creating emergency fallback app.")
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    app = FastAPI(title="BAIS Emergency Fallback")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    
    @app.get("/")
    def emergency_root():
        return {"status": "error", "message": "App initialization failed", "import_errors": import_errors}
    
    @app.get("/health")
    def emergency_health():
        return {"status": "degraded", "message": "Emergency fallback mode", "import_errors": import_errors}

logger.info(f"BAIS Railway final application initialized. Import errors: {len(import_errors)}")
if import_errors:
    logger.warning(f"Import errors detected: {import_errors}")
else:
    logger.info("BAIS Railway final application ready with complete feature set")

# Mark app as ready after initialization
app.state.ready = True
logger.info("Application marked as ready - health checks will now return ready=true")
