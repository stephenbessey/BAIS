from fastapi import APIRouter, Depends, BackgroundTasks
from functools import lru_cache
from typing import Dict, Any, Optional
from .services.business_service import BusinessService
from .services.agent_service import AgentService
from .api_models import *
from .core.database_models import DatabaseManager
from .core.mcp_server_generator import BusinessSystemAdapter
from .config.settings import get_settings, get_database_url
from .core.exceptions import ConfigurationError


class DependencyContainer:
    """Dependency injection container for BAIS services"""
    
    def __init__(self):
        self._db_manager: Optional[DatabaseManager] = None
        self._settings = None
    
    @property
    def settings(self):
        """Get application settings"""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings
    
    @property
    def db_manager(self) -> DatabaseManager:
        """Get database manager instance"""
        if self._db_manager is None:
            database_url = get_database_url()
            self._db_manager = DatabaseManager(database_url)
        return self._db_manager


# Global dependency container
_container = DependencyContainer()


def get_db_manager() -> DatabaseManager:
    """Get database manager dependency"""
    return _container.db_manager


def get_business_service(
    db: DatabaseManager = Depends(get_db_manager),
    bg_tasks: BackgroundTasks = BackgroundTasks()
) -> BusinessService:
    """Get business service dependency"""
    return BusinessService(db_manager=db, background_tasks=bg_tasks)


def get_business_config() -> Dict[str, Any]:
    """Get business configuration for adapters"""
    settings = _container.settings
    return {
        "oauth_client_id": settings.oauth.client_id,
        "oauth_client_secret": settings.oauth.client_secret,
        "api_timeout": settings.api.timeout_seconds,
        "max_retries": settings.api.max_retries,
        "environment": settings.bais.environment
    }


def get_agent_service(
    business_config: Dict[str, Any] = Depends(get_business_config)
) -> AgentService:
    """Get agent service dependency with proper configuration"""
    try:
        adapter = BusinessSystemAdapter(business_config=business_config)
        return AgentService(business_adapter=adapter)
    except Exception as e:
        raise ConfigurationError(
            f"Failed to create agent service: {str(e)}",
            config_key="business_config"
        )


# Router Setup
api_router = APIRouter()

@api_router.post("/businesses", response_model=BusinessRegistrationResponse, tags=["Business Management"])
async def register_business(
    request: BusinessRegistrationRequest,
    service: BusinessService = Depends(get_business_service)
):
    return await service.register_business(request)

@api_router.get("/businesses/{business_id}", response_model=BusinessStatusResponse, tags=["Business Management"])
async def get_business_status(
    business_id: str,
    service: BusinessService = Depends(get_business_service)
):
    return await service.get_business_status(business_id)


@api_router.post("/agents/interact", response_model=AgentInteractionResponse, tags=["Agent Interaction"])
async def agent_interaction(
    request: AgentInteractionRequest,
    service: AgentService = Depends(get_agent_service)
):
    return await service.handle_interaction(request)