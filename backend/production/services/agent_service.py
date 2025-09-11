import uuid
from datetime import datetime
from fastapi import HTTPException
from ..api_models import AgentInteractionRequest, AgentInteractionResponse
# Need to create the adapter to be a separate, sophisticated component
from ..core.mcp_server_generator import BusinessSystemAdapter

class AgentService:
    def __init__(self, business_adapter: BusinessSystemAdapter):
        # The adapter needs to be configured per-business
        self.adapter = business_adapter

    async def handle_interaction(self, request: AgentInteractionRequest) -> AgentInteractionResponse:
        """Routes and handles an agent's interaction request."""
        start_time = datetime.utcnow()
        
        interaction_map = {
            "search": self._handle_search,
            "book": self._handle_booking,
            "info": self._handle_info,
        }
        
        handler = interaction_map.get(request.interaction_type)
        
        if not handler:
            raise HTTPException(status_code=400, detail=f"Unsupported interaction type: {request.interaction_type}")

        try:
            response_data = await handler(request)
            status = "success"
        except Exception as e:
            response_data = {"error": str(e)}
            status = "error"
            
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return AgentInteractionResponse(
            interaction_id=str(uuid.uuid4()),
            status=status,
            response_data=response_data,
            processing_time_ms=processing_time_ms
        )

    async def _handle_search(self, request: AgentInteractionRequest) -> dict:
        """Handles a 'search' interaction."""
        service_id = request.parameters.get("service_id", "default_service")
        search_params = {k: v for k, v in request.parameters.items() if k != "service_id"}
        return await self.adapter.search_availability(service_id, search_params)

    async def _handle_booking(self, request: AgentInteractionRequest) -> dict:
        """Handles a 'book' interaction."""
        service_id = request.parameters.get("service_id", "default_service")
        booking_params = {k: v for k, v in request.parameters.items() if k != "service_id"}
        return await self.adapter.create_booking(service_id, booking_params)

    async def _handle_info(self, request: AgentInteractionRequest) -> dict:
        """Handles an 'info' interaction."""
        # This needs to fetch formatted data from the business's schema
        return {"info": "Business information placeholder"}