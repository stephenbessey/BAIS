from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime

class BusinessRegistrationRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=255, description="The official name of the business.")
    business_type: str = Field(..., regex="^(hospitality|food_service|retail|healthcare|finance)$", description="The category of the business.")
    contact_info: Dict[str, str] = Field(..., description="Contact details like website, phone, and email.")
    location: Dict[str, Any] = Field(..., description="Physical location information of the business.")
    services_config: List[Dict[str, Any]] = Field(..., min_items=1, description="A list of services offered by the business.")

class BusinessRegistrationResponse(BaseModel):
    business_id: str
    status: str
    mcp_endpoint: str
    a2a_endpoint: str
    api_keys: Dict[str, str]
    setup_complete: bool

class SchemaValidationRequest(BaseModel):
    schema_data: Dict[str, Any]

class SchemaValidationResponse(BaseModel):
    is_valid: bool
    issues: List[str]
    warnings: List[str] = []

class BusinessStatusResponse(BaseModel):
    business_id: str
    name: str
    status: str
    services_enabled: int
    mcp_server_active: bool
    a2a_server_active: bool
    last_updated: datetime
    metrics: Dict[str, Any]

class AgentInteractionRequest(BaseModel):
    business_id: str
    agent_id: str
    interaction_type: str = Field(..., regex="^(search|book|modify|cancel|info)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)

class AgentInteractionResponse(BaseModel):
    interaction_id: str
    status: str
    response_data: Dict[str, Any]
    processing_time_ms: int