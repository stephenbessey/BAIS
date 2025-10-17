"""
BAIS Production Application - Railway Fixed Version
Handles imports correctly for Railway deployment
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
    logger.info("Starting BAIS Railway fixed deployment initialization...")
    logger.info(f"System info: {system_info}")
    
    # Import FastAPI and create basic app structure
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    # Create the FastAPI app
    app = FastAPI(
        title="BAIS Production Server",
        description="Business-Agent Integration Standard Production Implementation - Railway Fixed",
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
    
    # Try to import and configure routes
    try:
        # Import routes with absolute imports
        from routes import api_router
        
        # Include API routes
        app.include_router(api_router, prefix="/api/v1")
        logger.info("Successfully imported and configured API routes")
        
    except ImportError as e:
        logger.warning(f"Could not import routes: {e}")
        import_errors.append(f"Routes import error: {str(e)}")
    
    # Try to import and configure A2A routes
    try:
        from api.v1.a2a.discovery import router as a2a_discovery_router
        from api.v1.a2a.tasks import router as a2a_tasks_router
        from api.v1.a2a.sse_router import router as a2a_sse_router
        
        app.include_router(a2a_discovery_router, tags=["A2A Discovery"])
        app.include_router(a2a_tasks_router, tags=["A2A Tasks"])
        app.include_router(a2a_sse_router, tags=["A2A SSE"])
        
        logger.info("Successfully imported and configured A2A routes")
        
    except ImportError as e:
        logger.warning(f"Could not import A2A routes: {e}")
        import_errors.append(f"A2A routes import error: {str(e)}")
    
    # Try to import and configure MCP routes
    try:
        from api.v1.mcp.sse_router import router as mcp_sse_router
        from api.v1.mcp.prompts_router import router as mcp_prompts_router
        from api.v1.mcp.subscription_router import router as mcp_subscription_router
        
        app.include_router(mcp_sse_router, tags=["MCP SSE"])
        app.include_router(mcp_prompts_router, tags=["MCP Prompts"])
        app.include_router(mcp_subscription_router, tags=["MCP Subscriptions"])
        
        logger.info("Successfully imported and configured MCP routes")
        
    except ImportError as e:
        logger.warning(f"Could not import MCP routes: {e}")
        import_errors.append(f"MCP routes import error: {str(e)}")
    
    # Try to import and configure error handling routes
    try:
        from api.v1.errors.unified_error_router import router as unified_error_router
        app.include_router(unified_error_router, tags=["Unified Error Handling"])
        logger.info("Successfully imported and configured error handling routes")
        
    except ImportError as e:
        logger.warning(f"Could not import error handling routes: {e}")
        import_errors.append(f"Error handling routes import error: {str(e)}")
    
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
        "features_available": len(import_errors) == 0
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy" if len(import_errors) == 0 else "degraded",
        "service": "BAIS Production Server",
        "environment": "railway",
        "import_errors": len(import_errors),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/status")
def api_status():
    return {
        "api": "operational",
        "endpoints": ["/", "/health", "/api/status", "/docs", "/diagnostics"],
        "ready_for_customers": len(import_errors) == 0,
        "features": {
            "business_registration": "available" if len(import_errors) == 0 else "degraded",
            "agent_interaction": "available" if len(import_errors) == 0 else "degraded",
            "a2a_protocol": "available" if len(import_errors) == 0 else "degraded",
            "mcp_protocol": "available" if len(import_errors) == 0 else "degraded",
            "payment_processing": "available" if len(import_errors) == 0 else "degraded",
            "monitoring": "available"
        }
    }

# Add diagnostic endpoints
@app.get("/diagnostics")
def get_diagnostics():
    """Comprehensive diagnostic endpoint"""
    return {
        "system_info": system_info,
        "import_errors": import_errors,
        "app_type": "full_bais_railway" if import_errors == [] else "diagnostic_railway",
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

logger.info(f"BAIS Railway fixed application initialized. Import errors: {len(import_errors)}")
if import_errors:
    logger.warning(f"Import errors detected: {import_errors}")
else:
    logger.info("BAIS Railway fixed application ready with full feature set")
