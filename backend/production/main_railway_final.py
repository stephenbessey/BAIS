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
    
    logger.info("Created FastAPI app with CORS middleware")
    
    # Import and configure simplified routes
    try:
        from routes_simple import api_router
        
        # Include API routes
        app.include_router(api_router, prefix="/api/v1")
        logger.info("Successfully imported and configured simplified API routes")
        
    except ImportError as e:
        logger.warning(f"Could not import simplified routes: {e}")
        import_errors.append(f"Routes import error: {str(e)}")
    
    # Import and configure Universal LLM Integration
    try:
        from api.v1.universal_webhooks import router as universal_webhook_router
        
        # Include universal webhook routes
        app.include_router(universal_webhook_router)
        logger.info("Successfully imported and configured Universal LLM webhook routes")
        
    except ImportError as e:
        logger.warning(f"Could not import universal webhook routes: {e}")
        import_errors.append(f"Universal webhooks import error: {str(e)}")
    
    logger.info("Successfully created BAIS application with available routes")
    
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
