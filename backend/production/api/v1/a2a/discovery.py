from fastapi import APIRouter
from typing import Any, Dict

from ...core.a2a_integration import A2AAgentCard, A2AAgent, A2AServer, A2ACapability


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


@router.get("/.well-known/agent.json", response_model=A2AAgentCard)
async def get_agent_card() -> A2AAgentCard:
	return _build_agent_card()
