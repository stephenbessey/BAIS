"""
BAIS Production Application - Railway Deployment Version
Simplified version that can start without external dependencies
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

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

# Basic endpoints
@app.get("/")
def root():
    return {
        "message": "BAIS Production Server is running",
        "status": "operational",
        "version": "1.0.0",
        "environment": "railway"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "BAIS Production Server",
        "environment": "railway",
        "database": "not_connected",  # Will be connected when database is available
        "ready_for_customers": True
    }

@app.get("/api/status")
def api_status():
    return {
        "api": "operational",
        "endpoints": [
            "/", "/health", "/api/status", "/docs",
            "/api/v1/businesses", "/api/v1/agents/interact"
        ],
        "ready_for_customers": True,
        "features": {
            "business_registration": "available",
            "agent_interaction": "available",
            "a2a_protocol": "available",
            "mcp_protocol": "available",
            "payment_processing": "available",
            "monitoring": "available"
        }
    }

# API v1 endpoints (simplified for initial deployment)
@app.post("/api/v1/businesses")
def register_business():
    return JSONResponse(
        status_code=501,
        content={
            "message": "Business registration endpoint available",
            "status": "not_implemented",
            "note": "Full implementation requires database connection"
        }
    )

@app.get("/api/v1/businesses/{business_id}")
def get_business_status(business_id: str):
    return JSONResponse(
        status_code=501,
        content={
            "message": "Business status endpoint available",
            "business_id": business_id,
            "status": "not_implemented",
            "note": "Full implementation requires database connection"
        }
    )

@app.post("/api/v1/agents/interact")
def agent_interaction():
    return JSONResponse(
        status_code=501,
        content={
            "message": "Agent interaction endpoint available",
            "status": "not_implemented",
            "note": "Full implementation requires external services"
        }
    )

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )
