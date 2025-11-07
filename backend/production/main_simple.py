"""
BAIS Production Application - Simple Entry Point
Non-relative imports for Railway deployment
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(
    title="BAIS Production Server",
    description="Business-Agent Integration Standard Production Implementation",
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

# Import and include routes
try:
    from routes_simple import api_router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("Successfully included routes_simple")
except Exception as e:
    logger.error(f"Failed to import routes_simple: {e}")

# Import and include universal webhooks
try:
    from api.v1.universal_webhooks import router as universal_webhook_router
    app.include_router(universal_webhook_router)
    logger.info("Successfully included universal_webhooks")
except Exception as e:
    logger.warning(f"Failed to import universal_webhooks: {e}")

# Basic endpoints
@app.get("/")
def root():
    return {"message": "BAIS Production Server is running"}

@app.get("/health")
def health_check():
    try:
        from shared_storage import count_businesses
        business_count = count_businesses()
    except:
        business_count = "unknown"
    return {
        "status": "healthy", 
        "service": "BAIS Production Server",
        "businesses_registered": business_count
    }

# Diagnostic endpoint to check registered businesses
@app.get("/api/v1/debug/businesses")
def debug_businesses():
    """Debug endpoint to check registered businesses"""
    try:
        from shared_storage import BUSINESS_STORE, list_businesses
        businesses = list_businesses()
        return {
            "count": len(businesses),
            "businesses": {k: {
                "name": v.get("business_name"),
                "type": v.get("business_type"),
                "city": v.get("location", {}).get("city"),
                "state": v.get("location", {}).get("state")
            } for k, v in businesses.items()}
        }
    except Exception as e:
        return {"error": str(e), "count": 0}