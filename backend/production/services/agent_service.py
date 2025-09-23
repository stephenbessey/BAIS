"""
Refactored AgentService following Clean Code principles
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Callable, Any
from fastapi import HTTPException

from ..api_models import AgentInteractionRequest, AgentInteractionResponse
from ..core.mcp_server_generator import BusinessSystemAdapter
from ..core.exceptions import ValidationError, IntegrationError


class InteractionType(Enum):
    """Clear enumeration of supported interaction types"""
    SEARCH = "search"
    BOOKING = "book"
    INFORMATION = "info"
    MODIFICATION = "modify"
    CANCELLATION = "cancel"


class InteractionResult:
    """Value object for interaction results"""
    def __init__(self, data: Dict[str, Any], status: str = "success"):
        self.data = data
        self.status = status


class AgentService:
    """Handles agent interactions with business systems"""
    
    def __init__(self, business_adapter: BusinessSystemAdapter):
        self.business_adapter = business_adapter
        self._interaction_handlers = self._create_interaction_handlers()
    
    def _create_interaction_handlers(self) -> Dict[InteractionType, Callable]:
        """Factory method for interaction handlers"""
        return {
            InteractionType.SEARCH: self._handle_availability_search,
            InteractionType.BOOKING: self._handle_booking_creation,
            InteractionType.INFORMATION: self._handle_information_request,
        }
    
    async def handle_interaction(self, request: AgentInteractionRequest) -> AgentInteractionResponse:
        """Main entry point for agent interactions"""
        start_time = datetime.utcnow()
        
        try:
            result = await self._process_interaction(request)
            return self._build_success_response(result, start_time)
        except ValidationError as e:
            return self._build_error_response(e, start_time)
        except IntegrationError as e:
            return self._build_error_response(e, start_time)
        except Exception as e:
            # Fallback for unexpected errors
            from ..core.exceptions import BAISException
            error = BAISException(f"Unexpected error in agent interaction: {str(e)}")
            return self._build_error_response(error, start_time)
    
    async def _process_interaction(self, request: AgentInteractionRequest) -> InteractionResult:
        """Process the interaction request"""
        interaction_type = self._parse_interaction_type(request.interaction_type)
        handler = self._get_interaction_handler(interaction_type)
        
        response_data = await handler(request)
        return InteractionResult(response_data)
    
    def _parse_interaction_type(self, interaction_type_str: str) -> InteractionType:
        """Parse and validate interaction type"""
        try:
            return InteractionType(interaction_type_str)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported interaction type: {interaction_type_str}"
            )
    
    def _get_interaction_handler(self, interaction_type: InteractionType) -> Callable:
        """Get the appropriate handler for the interaction type"""
        handler = self._interaction_handlers.get(interaction_type)
        if not handler:
            raise HTTPException(
                status_code=400,
                detail=f"No handler available for interaction type: {interaction_type.value}"
            )
        return handler
    
    async def _handle_availability_search(self, request: AgentInteractionRequest) -> Dict[str, Any]:
        """Handle availability search requests"""
        service_id = self._extract_service_id(request)
        search_parameters = self._extract_search_parameters(request)
        
        return await self.business_adapter.search_availability(service_id, search_parameters)
    
    async def _handle_booking_creation(self, request: AgentInteractionRequest) -> Dict[str, Any]:
        """Handle booking creation requests"""
        service_id = self._extract_service_id(request)
        booking_parameters = self._extract_booking_parameters(request)
        
        return await self.business_adapter.create_booking(service_id, booking_parameters)
    
    async def _handle_information_request(self, request: AgentInteractionRequest) -> Dict[str, Any]:
        """Handle information requests"""
        # Retrieve business information from schema
        return await self.business_adapter.get_business_info(request.parameters.get("business_id"))
    
    def _extract_service_id(self, request: AgentInteractionRequest) -> str:
        """Extract service ID from request parameters"""
        return request.parameters.get("service_id", "default_service")
    
    def _extract_search_parameters(self, request: AgentInteractionRequest) -> Dict[str, Any]:
        """Extract search-specific parameters"""
        return {k: v for k, v in request.parameters.items() if k != "service_id"}
    
    def _extract_booking_parameters(self, request: AgentInteractionRequest) -> Dict[str, Any]:
        """Extract booking-specific parameters"""
        return {k: v for k, v in request.parameters.items() if k != "service_id"}
    
    def _build_success_response(self, result: InteractionResult, start_time: datetime) -> AgentInteractionResponse:
        """Build successful response"""
        processing_time = self._calculate_processing_time(start_time)
        
        return AgentInteractionResponse(
            interaction_id=str(uuid.uuid4()),
            status=result.status,
            response_data=result.data,
            processing_time_ms=processing_time
        )
    
    def _build_error_response(self, error: Exception, start_time: datetime) -> AgentInteractionResponse:
        """Build error response"""
        processing_time = self._calculate_processing_time(start_time)
        
        return AgentInteractionResponse(
            interaction_id=str(uuid.uuid4()),
            status="error",
            response_data={"error": str(error)},
            processing_time_ms=processing_time
        )
    
    def _calculate_processing_time(self, start_time: datetime) -> int:
        """Calculate processing time in milliseconds"""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)