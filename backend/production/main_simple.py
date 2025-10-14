"""
BAIS Production Application - Simple Entry Point
Non-relative imports for Railway deployment
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
    return {"message": "BAIS Production Server is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "BAIS Production Server"}

# TODO: Add API routes once relative import issues are resolved
# For now, this provides a working deployment that Railway can start