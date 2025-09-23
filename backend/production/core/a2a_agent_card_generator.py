"""
A2A Agent Card Generator - Clean Code Implementation
Generates compliant A2A agent cards with dynamic capability discovery
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .bais_schema_validator import BAISBusinessSchema


class CapabilityType(Enum):
    """A2A capability types"""
    TASK_EXECUTION = "task_execution"
    CONTEXT_SHARING = "context_sharing"
    DATA_ACCESS = "data_access"
    SERVICE_DISCOVERY = "service_discovery"
    PAYMENT_PROCESSING = "payment_processing"


@dataclass
class A2ACapability:
    """A2A capability definition"""
    name: str
    description: str
    version: str = "1.0"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    requires_authentication: bool = True
    rate_limit_per_minute: int = 100


@dataclass
class A2AAgent:
    """A2A agent definition"""
    id: str
    name: str
    description: str
    version: str = "1.0"
    capabilities: List[A2ACapability] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class A2AServer:
    """A2A server configuration"""
    endpoint: str
    transport: str = "http"
    version: str = "2025-06-18"
    supported_protocols: List[str] = field(default_factory=lambda: ["json-rpc-2.0"])
    authentication_required: bool = True


@dataclass
class A2AAgentCard:
    """Complete A2A agent card structure"""
    agent: A2AAgent
    server: A2AServer
    bais_integration: Dict[str, Any] = field(default_factory=dict)


class A2ACapabilityRegistry:
    """Registry for A2A capabilities - follows Single Responsibility Principle"""
    
    def __init__(self):
        self._capabilities: Dict[str, A2ACapability] = {}
        self._register_default_capabilities()
    
    def _register_default_capabilities(self):
        """Register default A2A capabilities"""
        # Task execution capability
        task_execution = A2ACapability(
            name="task_execution",
            description="Execute tasks on behalf of other agents",
            input_schema={
                "type": "object",
                "properties": {
                    "task_type": {"type": "string"},
                    "parameters": {"type": "object"},
                    "priority": {"type": "integer", "minimum": 1, "maximum": 10}
                },
                "required": ["task_type", "parameters"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string"},
                    "result": {"type": "object"}
                }
            },
            timeout_seconds=300
        )
        
        # Context sharing capability
        context_sharing = A2ACapability(
            name="context_sharing",
            description="Share context and state with other agents",
            input_schema={
                "type": "object",
                "properties": {
                    "context_type": {"type": "string"},
                    "data": {"type": "object"},
                    "expires_at": {"type": "string", "format": "date-time"}
                },
                "required": ["context_type", "data"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "context_id": {"type": "string"},
                    "shared_at": {"type": "string", "format": "date-time"}
                }
            }
        )
        
        # Data access capability
        data_access = A2ACapability(
            name="data_access",
            description="Provide controlled access to business data",
            input_schema={
                "type": "object",
                "properties": {
                    "data_type": {"type": "string"},
                    "filters": {"type": "object"},
                    "format": {"type": "string", "enum": ["json", "csv", "xml"]}
                },
                "required": ["data_type"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "array"},
                    "total_count": {"type": "integer"},
                    "access_granted_at": {"type": "string", "format": "date-time"}
                }
            },
            requires_authentication=True
        )
        
        self.register_capability(task_execution)
        self.register_capability(context_sharing)
        self.register_capability(data_access)
    
    def register_capability(self, capability: A2ACapability):
        """Register a new capability"""
        self._capabilities[capability.name] = capability
    
    def get_capability(self, name: str) -> Optional[A2ACapability]:
        """Get a capability by name"""
        return self._capabilities.get(name)
    
    def get_all_capabilities(self) -> List[A2ACapability]:
        """Get all registered capabilities"""
        return list(self._capabilities.values())
    
    def get_capabilities_by_type(self, capability_type: CapabilityType) -> List[A2ACapability]:
        """Get capabilities by type"""
        return [cap for cap in self._capabilities.values() 
                if capability_type.value in cap.name]


class BusinessCapabilityMapper:
    """Maps business schema to A2A capabilities - follows Single Responsibility Principle"""
    
    def __init__(self, capability_registry: A2ACapabilityRegistry):
        self._capability_registry = capability_registry
    
    def map_business_to_a2a_capabilities(self, business_schema: BAISBusinessSchema) -> List[A2ACapability]:
        """Map business services to A2A capabilities"""
        capabilities = []
        
        # Get business type and services
        business_type = business_schema.business_info.type
        services = business_schema.business_info.services if hasattr(business_schema.business_info, 'services') else []
        
        # Add default capabilities
        capabilities.extend(self._capability_registry.get_all_capabilities())
        
        # Add business-specific capabilities based on type
        if business_type == "hospitality":
            capabilities.extend(self._create_hospitality_capabilities())
        elif business_type == "restaurant":
            capabilities.extend(self._create_restaurant_capabilities())
        elif business_type == "retail":
            capabilities.extend(self._create_retail_capabilities())
        
        # Add service-specific capabilities
        for service in services:
            if service.get("type") == "booking":
                capabilities.append(self._create_booking_capability(service))
            elif service.get("type") == "payment":
                capabilities.append(self._create_payment_capability(service))
        
        return capabilities
    
    def _create_hospitality_capabilities(self) -> List[A2ACapability]:
        """Create hospitality-specific capabilities"""
        room_booking = A2ACapability(
            name="room_booking",
            description="Book hotel rooms and manage reservations",
            input_schema={
                "type": "object",
                "properties": {
                    "check_in": {"type": "string", "format": "date"},
                    "check_out": {"type": "string", "format": "date"},
                    "guests": {"type": "integer", "minimum": 1},
                    "room_type": {"type": "string"},
                    "special_requests": {"type": "string"}
                },
                "required": ["check_in", "check_out", "guests"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string"},
                    "room_number": {"type": "string"},
                    "total_amount": {"type": "number"},
                    "confirmation_code": {"type": "string"}
                }
            },
            timeout_seconds=60
        )
        
        room_search = A2ACapability(
            name="room_search",
            description="Search for available rooms",
            input_schema={
                "type": "object",
                "properties": {
                    "check_in": {"type": "string", "format": "date"},
                    "check_out": {"type": "string", "format": "date"},
                    "guests": {"type": "integer", "minimum": 1},
                    "max_price": {"type": "number"}
                },
                "required": ["check_in", "check_out", "guests"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "available_rooms": {"type": "array"},
                    "total_count": {"type": "integer"},
                    "search_id": {"type": "string"}
                }
            }
        )
        
        return [room_booking, room_search]
    
    def _create_restaurant_capabilities(self) -> List[A2ACapability]:
        """Create restaurant-specific capabilities"""
        table_reservation = A2ACapability(
            name="table_reservation",
            description="Make restaurant table reservations",
            input_schema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "format": "date"},
                    "time": {"type": "string", "format": "time"},
                    "party_size": {"type": "integer", "minimum": 1},
                    "special_requests": {"type": "string"}
                },
                "required": ["date", "time", "party_size"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                    "table_number": {"type": "string"},
                    "confirmation_code": {"type": "string"}
                }
            }
        )
        
        return [table_reservation]
    
    def _create_retail_capabilities(self) -> List[A2ACapability]:
        """Create retail-specific capabilities"""
        product_search = A2ACapability(
            name="product_search",
            description="Search for products in retail inventory",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string"},
                    "price_range": {"type": "object"},
                    "availability": {"type": "boolean"}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "products": {"type": "array"},
                    "total_count": {"type": "integer"},
                    "search_id": {"type": "string"}
                }
            }
        )
        
        return [product_search]
    
    def _create_booking_capability(self, service: Dict[str, Any]) -> A2ACapability:
        """Create booking capability from service definition"""
        return A2ACapability(
            name=f"booking_{service.get('id', 'service')}",
            description=f"Book {service.get('name', 'service')}",
            input_schema=service.get("input_schema", {}),
            output_schema=service.get("output_schema", {}),
            timeout_seconds=service.get("timeout_seconds", 60)
        )
    
    def _create_payment_capability(self, service: Dict[str, Any]) -> A2ACapability:
        """Create payment capability from service definition"""
        return A2ACapability(
            name="payment_processing",
            description="Process payments for services",
            input_schema={
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "payment_method": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["amount", "currency", "payment_method"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "string"},
                    "status": {"type": "string"},
                    "processed_at": {"type": "string", "format": "date-time"}
                }
            },
            requires_authentication=True
        )


class A2AAgentCardGenerator:
    """Generates A2A agent cards - follows Single Responsibility Principle"""
    
    def __init__(self, capability_registry: A2ACapabilityRegistry = None):
        self._capability_registry = capability_registry or A2ACapabilityRegistry()
        self._business_mapper = BusinessCapabilityMapper(self._capability_registry)
    
    def generate_agent_card(self, 
                          business_schema: BAISBusinessSchema,
                          server_endpoint: str,
                          agent_id: Optional[str] = None) -> A2AAgentCard:
        """Generate A2A agent card from business schema"""
        
        # Create agent ID if not provided
        if not agent_id:
            agent_id = f"agent_{business_schema.business_info.id}"
        
        # Map business to capabilities
        capabilities = self._business_mapper.map_business_to_a2a_capabilities(business_schema)
        
        # Create agent
        agent = A2AAgent(
            id=agent_id,
            name=business_schema.business_info.name,
            description=f"A2A agent for {business_schema.business_info.name}",
            version="1.0",
            capabilities=capabilities,
            metadata={
                "business_type": business_schema.business_info.type,
                "business_id": business_schema.business_info.id,
                "generated_at": datetime.utcnow().isoformat(),
                "capability_count": len(capabilities)
            }
        )
        
        # Create server configuration
        server = A2AServer(
            endpoint=server_endpoint,
            transport="http",
            version="2025-06-18",
            supported_protocols=["json-rpc-2.0"],
            authentication_required=True
        )
        
        # Create BAIS integration metadata
        bais_integration = {
            "supported_protocols": ["AP2", "MCP"],
            "api_version": "v1.0",
            "business_schema_version": business_schema.version,
            "integration_features": [
                "payment_processing",
                "booking_management",
                "data_access",
                "task_execution"
            ]
        }
        
        return A2AAgentCard(
            agent=agent,
            server=server,
            bais_integration=bais_integration
        )
    
    def validate_agent_card(self, agent_card: A2AAgentCard) -> List[str]:
        """Validate agent card compliance with A2A specification"""
        issues = []
        
        # Validate agent
        if not agent_card.agent.id:
            issues.append("Agent ID is required")
        
        if not agent_card.agent.name:
            issues.append("Agent name is required")
        
        if not agent_card.agent.description:
            issues.append("Agent description is required")
        
        if not agent_card.agent.capabilities:
            issues.append("Agent must have at least one capability")
        
        # Validate server
        if not agent_card.server.endpoint:
            issues.append("Server endpoint is required")
        
        if not agent_card.server.endpoint.startswith(('http://', 'https://')):
            issues.append("Server endpoint must be a valid URL")
        
        # Validate capabilities
        for capability in agent_card.agent.capabilities:
            if not capability.name:
                issues.append("Capability name is required")
            
            if not capability.description:
                issues.append("Capability description is required")
            
            if capability.timeout_seconds <= 0:
                issues.append("Capability timeout must be positive")
        
        return issues
