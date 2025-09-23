from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from ...core.a2a_integration import A2AAgentCard, A2AAgent, A2AServer, A2ACapability, A2ADiscoveryRequest, A2ADiscoveryResponse
from ...core.a2a_registry_network import (
    A2ARegistryNetworkClient, 
    AgentDiscoveryCriteria, 
    RegistryNetworkType,
    get_registry_network_client
)
from ...core.a2a_agent_card_generator import A2AAgentCardGenerator, A2ACapabilityRegistry
from ...core.distributed_tracing import A2ATracer


router = APIRouter()


def _business_search_capability() -> A2ACapability:
	return A2ACapability(
		name="business_search",
		description="Search for available business services",
		input_schema={
			"type": "object",
			"properties": {
				"service_type": {"type": "string"},
				"location": {"type": "string"},
				"dates": {
					"type": "object",
					"properties": {
						"check_in": {"type": "string", "format": "date"},
						"check_out": {"type": "string", "format": "date"}
					}
				},
				"guests": {"type": "integer", "minimum": 1}
			},
			"required": ["service_type", "location"]
		},
		output_schema={
			"type": "object",
			"properties": {
				"results": {"type": "array"}
			}
		},
		timeout_seconds=30,
	)


def _create_booking_capability() -> A2ACapability:
	return A2ACapability(
		name="create_booking",
		description="Create a booking with a business",
		input_schema={
			"type": "object",
			"properties": {
				"business_id": {"type": "string"},
				"service_id": {"type": "string"},
				"booking_details": {"type": "object"},
				"customer_info": {"type": "object"},
				"payment_mandate_id": {"type": "string"}
			},
			"required": ["business_id", "service_id", "booking_details", "customer_info"]
		},
		output_schema={
			"type": "object",
			"properties": {
				"booking_id": {"type": "string"},
				"status": {"type": "string"},
				"confirmation_code": {"type": "string"}
			}
		},
		timeout_seconds=45,
	)


def _coordination_capability() -> A2ACapability:
	return A2ACapability(
		name="coordinate_workflow",
		description="Coordinate multi-step workflows across agents",
		input_schema={"type": "object", "properties": {}},
		output_schema={"type": "object", "properties": {"workflow_id": {"type": "string"}}},
		timeout_seconds=60,
	)


def _build_agent_card() -> A2AAgentCard:
	agent = A2AAgent(
		name="BAIS Business Integration Agent",
		description="Handles business service integration",
		version="1.0.0",
		capabilities=[
			_business_search_capability(),
			_create_booking_capability(),
			_coordination_capability(),
		],
	)
	server = A2AServer(
		endpoint="/a2a/v1",
		transport=["http", "sse"],
		authentication={"type": "oauth2", "scopes": ["business.read"]},
	)
	return A2AAgentCard(
		agent=agent,
		server=server,
		bais_integration={
			"supported_protocols": ["AP2", "MCP"],
			"api_version": "v1.0",
		},
	)


# Global agent card generator
_agent_card_generator: Optional[A2AAgentCardGenerator] = None


def get_agent_card_generator() -> A2AAgentCardGenerator:
    """Get the global agent card generator"""
    global _agent_card_generator
    if _agent_card_generator is None:
        _agent_card_generator = A2AAgentCardGenerator()
    return _agent_card_generator


@router.get("/.well-known/agent.json", response_model=A2AAgentCard)
async def get_agent_card(
    agent_generator: A2AAgentCardGenerator = Depends(get_agent_card_generator)
) -> A2AAgentCard:
    """
    A2A Agent Discovery Endpoint
    
    Returns the agent card for this BAIS instance following A2A specification.
    This endpoint is used by other agents to discover capabilities and endpoints.
    """
    try:
        # Create a sample business schema for demonstration
        # In a real implementation, this would come from the current business context
        from ...core.bais_schema_validator import BAISSchemaValidator
        
        # Create a sample hospitality business schema
        business_schema = BAISSchemaValidator.create_hospitality_template()
        business_schema.business_info.name = "Sample Hotel"
        business_schema.business_info.id = "hotel_123"
        
        # Generate agent card
        server_endpoint = "https://api.example.com/a2a/v1"
        agent_card = agent_generator.generate_agent_card(
            business_schema=business_schema,
            server_endpoint=server_endpoint,
            agent_id="bais_hotel_agent"
        )
        
        # Validate agent card
        validation_issues = agent_generator.validate_agent_card(agent_card)
        if validation_issues:
            raise HTTPException(
                status_code=500,
                detail=f"Agent card validation failed: {'; '.join(validation_issues)}"
            )
        
        return agent_card
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate agent card: {str(e)}"
        )


class EnhancedDiscoveryRequest(BaseModel):
    """Enhanced discovery request with network and reputation filtering"""
    capabilities_needed: List[str] = []
    agent_type: str = None
    location: str = None
    business_category: str = None
    min_reputation_score: float = 0.0
    max_response_time_ms: int = 5000
    preferred_networks: List[str] = []  # "public", "private", "consortium"
    exclude_networks: List[str] = []
    max_results: int = 50


@router.post("/discover", response_model=A2ADiscoveryResponse)
async def discover_agents_enhanced(
    request: EnhancedDiscoveryRequest,
    registry_client: A2ARegistryNetworkClient = Depends(get_registry_network_client)
) -> A2ADiscoveryResponse:
    """
    Enhanced agent discovery across multiple registry networks.
    
    This endpoint now integrates with external A2A registry networks to discover
    agents beyond the local system, with reputation scoring and intelligent filtering.
    """
    # Start distributed tracing
    async with A2ATracer.trace_agent_discovery(
        capabilities=request.capabilities_needed,
        location=request.location
    ) as span:
        try:
            # Convert network type strings to enums
            preferred_networks = []
            for network_str in request.preferred_networks:
                try:
                    preferred_networks.append(RegistryNetworkType(network_str))
                except ValueError:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid network type: {network_str}"
                    )
            
            exclude_networks = []
            for network_str in request.exclude_networks:
                try:
                    exclude_networks.append(RegistryNetworkType(network_str))
                except ValueError:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid network type: {network_str}"
                    )
            
            # Create discovery criteria
            criteria = AgentDiscoveryCriteria(
                capabilities_needed=request.capabilities_needed,
                agent_type=request.agent_type,
                location=request.location,
                business_category=request.business_category,
                min_reputation_score=request.min_reputation_score,
                max_response_time_ms=request.max_response_time_ms,
                preferred_networks=preferred_networks,
                exclude_networks=exclude_networks,
                max_results=request.max_results
            )
            
            # Add tracing attributes
            span.set_attribute("a2a.discovery.capabilities_count", len(request.capabilities_needed))
            span.set_attribute("a2a.discovery.max_results", request.max_results)
            span.set_attribute("a2a.discovery.min_reputation", request.min_reputation_score)
            
            # Discover agents across networks
            response = await registry_client.discover_agents_across_networks(criteria)
            
            # Add success metrics to span
            span.set_attribute("a2a.discovery.agents_found", response.total_found)
            span.set_attribute("a2a.discovery.networks_queried", len(preferred_networks))
            
            return response
            
        except Exception as e:
            # Add error information to span
            span.set_attribute("a2a.discovery.error", str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Agent discovery failed: {str(e)}"
            )


@router.post("/discover/local", response_model=A2ADiscoveryResponse)
async def discover_local_agents(request: A2ADiscoveryRequest) -> A2ADiscoveryResponse:
    """
    Legacy endpoint for discovering only local agents.
    Maintained for backward compatibility.
    """
    # This would return only local agents
    # For now, return empty response to maintain compatibility
    return A2ADiscoveryResponse(agents=[], total_found=0)


@router.post("/register")
async def register_agent_with_networks(
    agent_card: A2AAgentCard,
    registry_client: A2ARegistryNetworkClient = Depends(get_registry_network_client)
) -> Dict[str, Any]:
    """
    Register this agent with all configured registry networks.
    """
    try:
        registration_results = await registry_client.register_agent_with_networks(agent_card)
        
        successful_registrations = sum(1 for success in registration_results.values() if success)
        total_attempts = len(registration_results)
        
        return {
            "success": successful_registrations > 0,
            "successful_registrations": successful_registrations,
            "total_attempts": total_attempts,
            "registration_results": registration_results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent registration failed: {str(e)}"
        )
