"""
BAIS Production Application - Full Deployment
Complete implementation with all business logic and features
Enhanced with comprehensive diagnostic capabilities
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
    logger.info("Starting BAIS full deployment initialization...")
    logger.info(f"System info: {system_info}")
    
    # Import the complete BAIS application with absolute imports
    # Add the current directory to Python path for absolute imports
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # Import using absolute imports
    from main import app
    logger.info("Successfully imported complete BAIS application")
    
except ImportError as e:
    import_errors.append(f"Import error: {str(e)}")
    logger.error(f"Import error: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Create a diagnostic FastAPI app if imports fail
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    app = FastAPI(
        title="BAIS Diagnostic Server",
        description="BAIS application with import diagnostics",
        version="1.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    def diagnostic_root():
        return {
            "message": "BAIS Diagnostic Server",
            "status": "import_errors_detected",
            "system_info": system_info,
            "import_errors": import_errors,
            "note": "Check logs for detailed error information"
        }
    
    @app.get("/health")
    def diagnostic_health():
        return {
            "status": "unhealthy",
            "reason": "import_errors",
            "import_errors": import_errors,
            "system_info": system_info
        }
    
    @app.get("/diagnostics")
    def get_diagnostics():
        return {
            "system_info": system_info,
            "import_errors": import_errors,
            "python_path": sys.path,
            "available_modules": [m for m in sys.modules.keys() if "bais" in m.lower() or "backend" in m.lower()],
            "timestamp": datetime.utcnow().isoformat()
        }

except Exception as e:
    import_errors.append(f"Unexpected error: {str(e)}")
    logger.error(f"Unexpected error during initialization: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Create minimal diagnostic app
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(title="BAIS Error Diagnostic Server")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    
    @app.get("/")
    def error_root():
        return {"status": "error", "message": "Failed to initialize BAIS application", "errors": import_errors}
    
    @app.get("/health")
    def error_health():
        return {"status": "unhealthy", "errors": import_errors}
    
    @app.get("/diagnostics")
    def error_diagnostics():
        return {"errors": import_errors, "system_info": system_info, "traceback": traceback.format_exc()}

# Add diagnostic endpoints to the app (whether it's the full app or diagnostic app)
@app.get("/diagnostics")
def get_diagnostics():
    """Comprehensive diagnostic endpoint"""
    return {
        "system_info": system_info,
        "import_errors": import_errors,
        "app_type": "full_bais" if import_errors == [] else "diagnostic",
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
        "status": "healthy" if import_errors == [] else "unhealthy",
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

logger.info(f"BAIS application initialized. Import errors: {len(import_errors)}")
if import_errors:
    logger.warning(f"Import errors detected: {import_errors}")
else:
    logger.info("BAIS application ready with full feature set")
