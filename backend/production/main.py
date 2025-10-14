"""
BAIS Production Application Factory
Clean, focused application creation following single responsibility principle
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import api_router
from .api.v1.a2a.discovery import router as a2a_discovery_router
from .api.v1.a2a.tasks import router as a2a_tasks_router
from .api.v1.a2a.sse_router import router as a2a_sse_router
from .api.v1.mcp.sse_router import router as mcp_sse_router
from .api.v1.mcp.prompts_router import router as mcp_prompts_router
from .api.v1.mcp.subscription_router import router as mcp_subscription_router
from .api.v1.errors.unified_error_router import router as unified_error_router


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
		# Root and health endpoints
		@app.get("/")
		def root():
			return {"message": "BAIS Production Server is running"}
		
		@app.get("/health")
		def health_check():
			return {"status": "healthy", "service": "BAIS Production Server"}
		
		# API routes
		app.include_router(api_router, prefix="/api/v1")
		
		# A2A protocol routes
		app.include_router(a2a_discovery_router, tags=["A2A Discovery"])
		app.include_router(a2a_tasks_router, tags=["A2A Tasks"])
		app.include_router(a2a_sse_router, tags=["A2A SSE"])
		
		# MCP SSE transport routes
		app.include_router(mcp_sse_router, tags=["MCP SSE"])
		
		# MCP Prompts primitive routes
		app.include_router(mcp_prompts_router, tags=["MCP Prompts"])
		
		# MCP Subscription management routes
		app.include_router(mcp_subscription_router, tags=["MCP Subscriptions"])
		
		# Unified error handling routes
		app.include_router(unified_error_router, tags=["Unified Error Handling"])


# Create application instance
app = BAISApplicationFactory.create_app()