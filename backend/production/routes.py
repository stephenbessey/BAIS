from fastapi import APIRouter, Depends, BackgroundTasks
from .services.business_service import BusinessService
from .services.agent_service import AgentService
from .api_models import *
from .core.database_models import DatabaseManager
from .core.mcp_server_generator import BusinessSystemAdapter

# Dependency Injection Providers
def get_db_manager():
    # This needs to be a managed singleton
    return DatabaseManager("postgresql://user:password@localhost/bais_db")

def get_business_service(
    db: DatabaseManager = Depends(get_db_manager),
    bg_tasks: BackgroundTasks = BackgroundTasks()
) -> BusinessService:
    return BusinessService(db_manager=db, background_tasks=bg_tasks)

def get_agent_service() -> AgentService:
    # The adapter needs to be dynamically loaded based on the business
    adapter = BusinessSystemAdapter(business_config={}) 
    return AgentService(business_adapter=adapter)


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