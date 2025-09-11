"""
BAIS MCP Server Generator
Generates actual MCP-compliant servers from BAIS business schemas
"""

from typing import Dict, List, Any, Optional, Callable
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from pydantic import BaseModel
import uuid

# MCP Protocol Models (based on 2025-06-18 spec)
class MCPResource(BaseModel):
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = "application/json"

class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

class MCPPrompt(BaseModel):
    name: str
    description: str
    arguments: Optional[List[Dict[str, Any]]] = None

class MCPCapabilities(BaseModel):
    resources: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None

class MCPImplementation(BaseModel):
    name: str
    version: str

class MCPInitializeRequest(BaseModel):
    protocolVersion: str
    capabilities: MCPCapabilities
    clientInfo: MCPImplementation

class MCPInitializeResponse(BaseModel):
    protocolVersion: str = "2025-06-18"
    capabilities: MCPCapabilities
    serverInfo: MCPImplementation

class MCPListResourcesResponse(BaseModel):
    resources: List[MCPResource]

class MCPReadResourceRequest(BaseModel):
    uri: str

class MCPResourceContent(BaseModel):
    uri: str
    mimeType: str
    text: Optional[str] = None

class MCPReadResourceResponse(BaseModel):
    contents: List[MCPResourceContent]

class MCPCallToolRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

class MCPTextContent(BaseModel):
    type: str = "text"
    text: str

class MCPCallToolResponse(BaseModel):
    content: List[MCPTextContent]
    isError: bool = False

# BAIS-specific MCP Server Implementation
class BAISMCPServer:
    """MCP Server implementation for BAIS business services"""
    
    def __init__(self, business_schema: 'BAISBusinessSchema', business_system_adapter: 'BusinessSystemAdapter'):
        self.business_schema = business_schema
        self.business_adapter = business_system_adapter
        self.app = FastAPI(title=f"BAIS MCP Server - {business_schema.business_info.name}")
        self.security = HTTPBearer()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup MCP protocol routes"""
        
        @self.app.post("/mcp/initialize")
        async def initialize(request: MCPInitializeRequest) -> MCPInitializeResponse:
            """Initialize MCP connection"""
            
            # Validate protocol version
            if request.protocolVersion != "2025-06-18":
                raise HTTPException(status_code=400, detail="Unsupported protocol version")
            
            capabilities = MCPCapabilities(
                resources={"listChanged": True},
                tools={"listChanged": True},
                prompts={"listChanged": True}
            )
            
            server_info = MCPImplementation(
                name=f"bais-{self.business_schema.business_info.type.value}-server",
                version="1.0.0"
            )
            
            return MCPInitializeResponse(
                capabilities=capabilities,
                serverInfo=server_info
            )
        
        @self.app.get("/mcp/resources/list")
        async def list_resources(auth: HTTPAuthorizationCredentials = Depends(self.security)) -> MCPListResourcesResponse:
            """List available resources"""
            await self._validate_auth(auth)
            
            resources = []
            
            # Availability resources for each service
            for service in self.business_schema.services:
                if service.enabled:
                    resources.append(MCPResource(
                        uri=f"availability://{service.id}",
                        name=f"{service.name} Availability",
                        description=f"Real-time availability for {service.name}",
                        mimeType="application/json"
                    ))
                    
                    # Service information resource
                    resources.append(MCPResource(
                        uri=f"service://{service.id}",
                        name=f"{service.name} Information", 
                        description=f"Service details and pricing for {service.name}",
                        mimeType="application/json"
                    ))
            
            # Business information resource
            resources.append(MCPResource(
                uri="business://info",
                name="Business Information",
                description="General business information and contact details",
                mimeType="application/json"
            ))
            
            return MCPListResourcesResponse(resources=resources)
        
        @self.app.post("/mcp/resources/read")
        async def read_resource(
            request: MCPReadResourceRequest,
            auth: HTTPAuthorizationCredentials = Depends(self.security)
        ) -> MCPReadResourceResponse:
            """Read resource content"""
            await self._validate_auth(auth)
            
            uri_parts = request.uri.split("://")
            if len(uri_parts) != 2:
                raise HTTPException(status_code=400, detail="Invalid resource URI")
            
            scheme, path = uri_parts
            
            if scheme == "availability":
                content = await self._get_availability_resource(path)
            elif scheme == "service":
                content = await self._get_service_resource(path)
            elif scheme == "business":
                content = await self._get_business_resource(path)
            else:
                raise HTTPException(status_code=404, detail="Resource not found")
            
            return MCPReadResourceResponse(
                contents=[MCPResourceContent(
                    uri=request.uri,
                    mimeType="application/json",
                    text=json.dumps(content, indent=2)
                )]
            )
        
        @self.app.get("/mcp/tools/list")
        async def list_tools(auth: HTTPAuthorizationCredentials = Depends(self.security)) -> Dict[str, List[MCPTool]]:
            """List available tools"""
            await self._validate_auth(auth)
            
            tools = []
            
            for service in self.business_schema.services:
                if service.enabled:
                    # Search tool
                    tools.append(MCPTool(
                        name=f"search_{service.id}",
                        description=f"Search available {service.name} options",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                param_name: {
                                    "type": param.type,
                                    "description": param.description,
                                    **({"enum": param.enum} if param.enum else {}),
                                    **({"minimum": param.minimum} if param.minimum is not None else {}),
                                    **({"maximum": param.maximum} if param.maximum is not None else {})
                                }
                                for param_name, param in service.parameters.items()
                            },
                            "required": [name for name, param in service.parameters.items() if param.required]
                        }
                    ))
                    
                    # Book tool
                    tools.append(MCPTool(
                        name=f"book_{service.id}",
                        description=f"Create a booking for {service.name}",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                **{
                                    param_name: {
                                        "type": param.type,
                                        "description": param.description,
                                        **({"enum": param.enum} if param.enum else {}),
                                        **({"minimum": param.minimum} if param.minimum is not None else {}),
                                        **({"maximum": param.maximum} if param.maximum is not None else {})
                                    }
                                    for param_name, param in service.parameters.items()
                                },
                                "customer_info": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Customer full name"},
                                        "email": {"type": "string", "description": "Customer email"},
                                        "phone": {"type": "string", "description": "Customer phone number"}
                                    },
                                    "required": ["name", "email"]
                                }
                            },
                            "required": [name for name, param in service.parameters.items() if param.required] + ["customer_info"]
                        }
                    ))
            
            return {"tools": tools}
        
        @self.app.post("/mcp/tools/call")
        async def call_tool(
            request: MCPCallToolRequest,
            auth: HTTPAuthorizationCredentials = Depends(self.security)
        ) -> MCPCallToolResponse:
            """Call a tool"""
            await self._validate_auth(auth)
            
            try:
                # Parse tool name
                if "_" not in request.name:
                    raise ValueError("Invalid tool name format")
                
                action, service_id = request.name.split("_", 1)
                
                # Find service
                service = next((s for s in self.business_schema.services if s.id == service_id), None)
                if not service:
                    raise ValueError(f"Service {service_id} not found")
                
                # Execute tool action
                if action == "search":
                    result = await self.business_adapter.search_availability(service_id, request.arguments)
                elif action == "book":
                    result = await self.business_adapter.create_booking(service_id, request.arguments)
                else:
                    raise ValueError(f"Unknown action: {action}")
                
                return MCPCallToolResponse(
                    content=[MCPTextContent(text=json.dumps(result, indent=2))]
                )
                
            except Exception as e:
                return MCPCallToolResponse(
                    content=[MCPTextContent(text=f"Error: {str(e)}")],
                    isError=True
                )
    
    async def _validate_auth(self, auth: HTTPAuthorizationCredentials):
        """Validate authentication token"""
        # Implement OAuth 2.0 validation here
        # For now, just basic token validation
        if not auth.credentials:
            raise HTTPException(status_code=401, detail="Authentication required")
    
    async def _get_availability_resource(self, service_id: str) -> Dict[str, Any]:
        """Get availability resource content"""
        service = next((s for s in self.business_schema.services if s.id == service_id), None)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Get real-time availability from business system
        availability = await self.business_adapter.get_availability(service_id)
        
        return {
            "service_id": service_id,
            "service_name": service.name,
            "availability": availability,
            "last_updated": datetime.utcnow().isoformat(),
            "cache_timeout": service.availability.cache_timeout_seconds
        }
    
    async def _get_service_resource(self, service_id: str) -> Dict[str, Any]:
        """Get service resource content"""
        service = next((s for s in self.business_schema.services if s.id == service_id), None)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        return {
            "id": service.id,
            "name": service.name,
            "description": service.description,
            "category": service.category,
            "parameters": {name: param.dict() for name, param in service.parameters.items()},
            "policies": service.policies.dict(),
            "workflow": service.workflow.dict()
        }
    
    async def _get_business_resource(self, path: str) -> Dict[str, Any]:
        """Get business resource content"""
        if path == "info":
            return {
                "business_info": self.business_schema.business_info.dict(),
                "services_available": len([s for s in self.business_schema.services if s.enabled]),
                "bais_version": self.business_schema.bais_version,
                "capabilities": self.business_schema.integration.dict()
            }
        else:
            raise HTTPException(status_code=404, detail="Resource not found")

# Business System Adapter Interface
class BusinessSystemAdapter:
    """Interface for connecting to actual business systems"""
    
    def __init__(self, business_config: Dict[str, Any]):
        self.config = business_config
        self.client = httpx.AsyncClient()
    
    async def get_availability(self, service_id: str) -> Dict[str, Any]:
        """Get real-time availability from business system"""
        # This needs to integrate with actual PMS/POS systems
        # For demo purposes, return mock data
        return {
            "available_slots": [
                {
                    "date": "2024-03-15",
                    "available": True,
                    "price": 159.00,
                    "inventory": 5
                },
                {
                    "date": "2024-03-16", 
                    "available": True,
                    "price": 179.00,
                    "inventory": 3
                }
            ],
            "constraints": {
                "minimum_stay": 1,
                "maximum_advance_booking": 365
            }
        }
    
    async def search_availability(self, service_id: str, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for available options"""
        # Implement actual search logic here
        availability = await self.get_availability(service_id)
        
        return {
            "search_id": str(uuid.uuid4()),
            "results": availability["available_slots"],
            "search_params": search_params,
            "total_results": len(availability["available_slots"])
        }
    
    async def create_booking(self, service_id: str, booking_params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new booking"""
        # Implement actual booking logic here
        booking_id = str(uuid.uuid4())
        
        return {
            "booking_id": booking_id,
            "status": "confirmed",
            "service_id": service_id,
            "booking_params": booking_params,
            "confirmation_number": f"BAIS-{booking_id[:8].upper()}",
            "created_at": datetime.utcnow().isoformat(),
            "total_amount": 159.00,
            "currency": "USD"
        }

# MCP Server Factory
class BAISMCPServerFactory:
    """Factory for creating BAIS MCP servers"""
    
    @staticmethod
    def create_server(business_schema: 'BAISBusinessSchema', business_config: Dict[str, Any] = None) -> BAISMCPServer:
        """Create an MCP server for a business schema"""
        
        # Validate schema
        from bais_schema_validator import BAISSchemaValidator
        
        is_valid, issues = BAISSchemaValidator.validate_schema(business_schema.dict())
        if not is_valid:
            raise ValueError(f"Invalid business schema: {'; '.join(issues)}")
        
        # Create business adapter
        adapter = BusinessSystemAdapter(business_config or {})
        
        # Create MCP server
        return BAISMCPServer(business_schema, adapter)
    
    @staticmethod
    def deploy_server(server: BAISMCPServer, host: str = "0.0.0.0", port: int = 8000):
        """Deploy MCP server"""
        import uvicorn
        uvicorn.run(server.app, host=host, port=port)

# Example usage
if __name__ == "__main__":
    from bais_schema_validator import BAISSchemaValidator
    
    # Create a sample hotel schema
    hotel_schema = BAISSchemaValidator.create_hospitality_template()
    
    # Create MCP server
    factory = BAISMCPServerFactory()
    mcp_server = factory.create_server(hotel_schema)
    
    # Deploy server
    factory.deploy_server(mcp_server, port=8001)