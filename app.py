"""
BAIS Production Server - Root Entry Point
Simple FastAPI application for Railway deployment
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "BAIS Production Server",
        "timestamp": "2025-01-27T00:00:00Z"
    }

@app.get("/api/status")
def api_status():
    return {
        "api": "operational",
        "endpoints": ["/", "/health", "/api/status", "/docs"],
        "ready_for_customers": True
    }
