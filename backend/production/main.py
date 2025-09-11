"""
BAIS Production Application Factory
Clean, focused application creation following single responsibility principle
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import api_router


class BAISApplicationFactory:
    """Factory for creating BAIS production applications"""
    
    @staticmethod
    def create_app() -> FastAPI:
        """Create and configure the BAIS production application"""
        app = BAISApplicationFactory._create_base_app()
        BAISApplicationFactory._configure_middleware(app)
        BAISApplicationFactory._configure_routes(app)
        return app
    
    @staticmethod
    def _create_base_app() -> FastAPI:
        """Create the base FastAPI application"""
        return FastAPI(
            title="BAIS Production Server",
            description="Business-Agent Integration Standard Production Implementation",
            version="1.0.0"
        )
    
    @staticmethod
    def _configure_middleware(app: FastAPI) -> None:
        """Configure application middleware"""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    @staticmethod
    def _configure_routes(app: FastAPI) -> None:
        """Configure application routes"""
        app.include_router(api_router, prefix="/api/v1")
        
        @app.get("/")
        def root():
            return {"message": "BAIS Production Server is running"}
        
        @app.get("/health")
        def health_check():
            return {"status": "healthy", "service": "BAIS Production Server"}


# Create application instance
app = BAISApplicationFactory.create_app()