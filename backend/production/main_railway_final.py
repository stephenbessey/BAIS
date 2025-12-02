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
app = None
import_errors = []
system_info = get_system_info()

try:
    logger.info("Starting BAIS Railway final deployment initialization...")
    logger.info(f"System info: {system_info}")
    
    # Import FastAPI and create basic app structure
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    # Create the FastAPI app
    app = FastAPI(
        title="BAIS Production Server",
        description="Business-Agent Integration Standard Production Implementation - Complete Backend",
        version="1.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
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
        logger.warning(f"Could not import universal webhook routes: {e}")
        import_errors.append(f"Universal webhooks import error: {str(e)}")
        logger.warning(f"Import error details: {traceback.format_exc()}")
    
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
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url != "not_set":
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
            
            if DatabaseManager:
                db_manager = DatabaseManager(database_url)
                db_manager.create_tables()
                logger.info("Database tables initialized successfully")
            else:
                logger.warning("DatabaseManager not available, skipping table initialization")
        except Exception as db_error:
            logger.warning(f"Database initialization failed: {db_error}")
            logger.warning("Continuing with in-memory storage only - routes will still work")
            import traceback
            logger.debug(f"Database init error details: {traceback.format_exc()}")
    
except Exception as e:
    import_errors.append(f"Unexpected error: {str(e)}")
    logger.error(f"Unexpected error during initialization: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Create minimal diagnostic app as fallback
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(title="BAIS Error Diagnostic Server")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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

@app.get("/health")
def health_check():
    return {
        "status": "healthy" if len(import_errors) == 0 else "degraded",
        "service": "BAIS Production Server",
        "environment": "railway",
        "import_errors": len(import_errors),
        "timestamp": datetime.utcnow().isoformat(),
        "ready_for_customers": len(import_errors) == 0
    }

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
    return {
        "system_info": system_info,
        "import_errors": import_errors,
        "app_type": "complete_bais_railway" if import_errors == [] else "diagnostic_railway",
        "timestamp": datetime.utcnow().isoformat(),
        "python_path": sys.path[:10],  # First 10 entries to avoid huge response
        "environment_check": {
            "required_env_vars": {
                "PORT": os.getenv("PORT", "not_set"),
                "DATABASE_URL": "set" if os.getenv("DATABASE_URL") else "not_set",
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
    health_status = {
        "status": "healthy" if import_errors == [] else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "system_info": system_info,
        "import_errors": import_errors,
        "environment": {
            "PORT": os.getenv("PORT", "not_set"),
            "DATABASE_URL": "configured" if os.getenv("DATABASE_URL") else "missing",
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

logger.info(f"BAIS Railway final application initialized. Import errors: {len(import_errors)}")
if import_errors:
    logger.warning(f"Import errors detected: {import_errors}")
else:
    logger.info("BAIS Railway final application ready with complete feature set")
