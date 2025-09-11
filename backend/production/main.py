from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import api_router

def create_production_app() -> FastAPI:
    """Create and configure the BAIS production application."""
    app = FastAPI(
        title="BAIS Production Server",
        description="Business-Agent Integration Standard Production Implementation",
        version="1.0.0"
    )

    # Configure middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], # Add production domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/")
    def root():
        return {"message": "BAIS Production Server is running"}

    return app

app = create_production_app()