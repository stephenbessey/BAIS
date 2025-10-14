"""
BAIS A2A Protocol Integration
Implements Google's Agent-to-Agent protocol for business service discovery and coordination
"""

from typing import Dict, List, Any, Optional, Union
import json
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import httpx
import uuid
import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

# A2A Protocol Models (based on Google's A2A spec)
class A2ACapability(BaseModel):
    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="Capability description")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for input")
    output_schema: Dict[str, Any] = Field(..., description="JSON Schema for output")
    timeout_seconds: int = Field(default=30, description="Maximum execution time")

class A2AAgent(BaseModel):
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description") 
    version: str = Field(..., description="Agent version")
    capabilities: List[A2ACapability] = Field(..., description="Agent capabilities")

class A2AServer(BaseModel):
    endpoint: str = Field(..., description="A2A server endpoint")
    transport: List[str] = Field(default=["http"], description="Supported transports")
    authentication: Dict[str, Any] = Field(..., description="Authentication config")

class A2AAgentCard(BaseModel):
    """A2A Agent Card - served at /.well-known/agent.json"""
    agent: A2AAgent
    server: A2AServer
    bais_integration: Optional[Dict[str, Any]] = Field(None, description="BAIS-specific metadata")

class A2ATaskRequest(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    capability: str = Field(..., description="Requested capability")
    input: Dict[str, Any] = Field(..., description="Task input data")
    timeout_seconds: int = Field(default=30)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    callback_url: Optional[str] = Field(None, description="Callback URL for async tasks")

class A2ATaskStatus(BaseModel):
    task_id: str
    status: str = Field(..., pattern="^(pending|running|completed|failed|cancelled)$")
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class A2ATaskResult(BaseModel):
    task_id: str
    status: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    completed_at: Optional[datetime] = None

class A2ADiscoveryRequest(BaseModel):
    requesting_agent: str
    capabilities_needed: List[str]
    location_preference: Optional[str] = None
    business_type_filter: Optional[List[str]] = None

class A2ADiscoveryResponse(BaseModel):
    agents: List[Dict[str, Any]]
    total_found: int
    search_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# BAIS A2A Integration
class BAISA2AServer:
    """A2A Server implementation for BAIS business services"""
    
    def __init__(self, business_schema: 'BAISBusinessSchema', mcp_server: 'BAISMCPServer'):
        self.business_schema = business_schema
        self.mcp_server = mcp_server
        self.app = FastAPI(title=f"BAIS A2A Server - {business_schema.business_info.name}")
        self.tasks: Dict[str, A2ATaskStatus] = {}
        self.task_results: Dict[str, A2ATaskResult] = {}
        self._setup_routes()
        
        # Generate agent card
        self.agent_card = self._generate_agent_card()
    
    def _setup_routes(self):
        """Setup A2A protocol routes"""
        
        @self.app.get("/.well-known/agent.json")
        async def get_agent_card() -> A2AAgentCard:
            """Serve agent discovery card"""
            return self.agent_card
        
        @self.app.post("/a2a/discover")
        async def discover_agents(request: A2ADiscoveryRequest) -> A2ADiscoveryResponse:
            """Discover compatible agents"""
            # For business services, we primarily expose our own capabilities
            # In a full implementation, this needs to be query a registry
            
            matching_agents = []
            
            # Check if we can handle the requested capabilities
            our_capabilities = [cap.name for cap in self.agent_card.agent.capabilities]
            
            for needed_cap in request.capabilities_needed:
                if any(needed_cap in cap or cap in needed_cap for cap in our_capabilities):
                    matching_agents.append({
                        "agent_name": self.agent_card.agent.name,
                        "endpoint": self.agent_card.server.endpoint,
                        "capabilities": our_capabilities,
                        "business_info": self.business_schema.business_info.dict(),
                        "confidence_score": 0.95
                    })
                    break
            
            return A2ADiscoveryResponse(
                agents=matching_agents,
                total_found=len(matching_agents)
            )
        
        @self.app.post("/a2a/task")
        async def submit_task(request: A2ATaskRequest, background_tasks: BackgroundTasks) -> A2ATaskStatus:
            """Submit a task for execution"""
            
            # Validate capability exists
            capability = next((cap for cap in self.agent_card.agent.capabilities 
                             if cap.name == request.capability), None)
            if not capability:
                raise HTTPException(status_code=404, detail=f"Capability {request.capability} not found")
            
            # Create task status
            task_status = A2ATaskStatus(
                task_id=request.task_id,
                status="pending",
                message=f"Task {request.capability} queued for execution"
            )
            self.tasks[request.task_id] = task_status
            
            # Execute task in background
            background_tasks.add_task(self._execute_task, request, capability)
            
            return task_status
        
        @self.app.get("/a2a/task/{task_id}/status")
        async def get_task_status(task_id: str) -> A2ATaskStatus:
            """Get task execution status"""
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            return self.tasks[task_id]
        
        @self.app.get("/a2a/task/{task_id}/result")
        async def get_task_result(task_id: str) -> A2ATaskResult:
            """Get task execution result"""
            if task_id not in self.task_results:
                raise HTTPException(status_code=404, detail="Task result not found")
            return self.task_results[task_id]
        
        @self.app.post("/a2a/task/{task_id}/cancel")
        async def cancel_task(task_id: str) -> A2ATaskStatus:
            """Cancel a running task"""
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            task_status = self.tasks[task_id]
            if task_status.status in ["completed", "failed", "cancelled"]:
                return task_status
            
            task_status.status = "cancelled"
            task_status.updated_at = datetime.utcnow()
            task_status.message = "Task cancelled by request"
            
            return task_status
    
    def _generate_agent_card(self) -> A2AAgentCard:
        """Generate A2A agent discovery card"""
        
        capabilities = []
        
        # Generate capabilities from business services
        for service in self.business_schema.services:
            if service.enabled:
                # Search capability
                capabilities.append(A2ACapability(
                    name=f"search_{service.id}",
                    description=f"Search for available {service.name} options",
                    input_schema={
                        "type": "object",
                        "properties": {
                            param_name: {
                                "type": param.type,
                                "description": param.description
                            }
                            for param_name, param in service.parameters.items()
                        },
                        "required": [name for name, param in service.parameters.items() if param.required]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "results": {"type": "array", "description": "Search results"},
                            "total_found": {"type": "integer", "description": "Total results found"},
                            "search_id": {"type": "string", "description": "Search identifier"}
                        }
                    }
                ))
                
                # Booking capability
                capabilities.append(A2ACapability(
                    name=f"book_{service.id}",
                    description=f"Create a booking for {service.name}",
                    input_schema={
                        "type": "object",
                        "properties": {
                            **{
                                param_name: {
                                    "type": param.type,
                                    "description": param.description
                                }
                                for param_name, param in service.parameters.items()
                            },
                            "customer_info": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string"},
                                    "phone": {"type": "string"}
                                },
                                "required": ["name", "email"]
                            }
                        },
                        "required": [name for name, param in service.parameters.items() if param.required] + ["customer_info"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "booking_id": {"type": "string"},
                            "status": {"type": "string"},
                            "confirmation_number": {"type": "string"},
                            "total_amount": {"type": "number"}
                        }
                    },
                    timeout_seconds=60
                ))
        
        # Business information capability
        capabilities.append(A2ACapability(
            name="get_business_info",
            description="Get business information and available services",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
            output_schema={
                "type": "object", 
                "properties": {
                    "business_info": {"type": "object"},
                    "services": {"type": "array"},
                    "capabilities": {"type": "array"}
                }
            }
        ))
        
        agent = A2AAgent(
            name=f"bais-{self.business_schema.business_info.type.value}-agent",
            description=f"BAIS agent for {self.business_schema.business_info.name}",
            version="1.0.0",
            capabilities=capabilities
        )
        
        server = A2AServer(
            endpoint=self.business_schema.integration.a2a_endpoint.discovery_url.replace("/.well-known/agent.json", "/a2a"),
            transport=["http", "grpc"],
            authentication={
                "method": "oauth2",
                "token_url": f"{self.business_schema.integration.mcp_server.endpoint}/oauth/token",
                "scopes": ["read", "write", "book"]
            }
        )
        
        bais_integration = {
            "schema_version": self.business_schema.bais_version,
            "business_type": self.business_schema.business_info.type.value,
            "services": [service.id for service in self.business_schema.services if service.enabled],
            "mcp_endpoint": self.business_schema.integration.mcp_server.endpoint,
            "real_time_availability": True,
            "supported_workflows": list(set(service.workflow.pattern.value for service in self.business_schema.services))
        }
        
        return A2AAgentCard(
            agent=agent,
            server=server,
            bais_integration=bais_integration
        )
    
    async def _execute_task(self, request: A2ATaskRequest, capability: A2ACapability):
        """Execute a task asynchronously"""
        task_id = request.task_id
        start_time = datetime.utcnow()
        
        try:
            # Update status to running
            self.tasks[task_id].status = "running"
            self.tasks[task_id].updated_at = datetime.utcnow()
            self.tasks[task_id].message = f"Executing {capability.name}"
            
            # Route to appropriate handler
            if capability.name.startswith("search_"):
                result = await self._handle_search_task(request, capability)
            elif capability.name.startswith("book_"):
                result = await self._handle_booking_task(request, capability)
            elif capability.name == "get_business_info":
                result = await self._handle_business_info_task(request)
            else:
                raise ValueError(f"Unknown capability: {capability.name}")
            
            # Store successful result
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            self.task_results[task_id] = A2ATaskResult(
                task_id=task_id,
                status="completed",
                output=result,
                execution_time_ms=execution_time,
                completed_at=datetime.utcnow()
            )
            
            # Update task status
            self.tasks[task_id].status = "completed"
            self.tasks[task_id].progress = 100.0
            self.tasks[task_id].updated_at = datetime.utcnow()
            self.tasks[task_id].message = "Task completed successfully"
            
        except Exception as e:
            # Store error result
            self.task_results[task_id] = A2ATaskResult(
                task_id=task_id,
                status="failed",
                error=str(e),
                completed_at=datetime.utcnow()
            )
            
            # Update task status
            self.tasks[task_id].status = "failed"
            self.tasks[task_id].updated_at = datetime.utcnow()
            self.tasks[task_id].message = f"Task failed: {str(e)}"
        
        # Send callback if provided
        if request.callback_url:
            await self._send_callback(request.callback_url, self.task_results[task_id])
    
    async def _handle_search_task(self, request: A2ATaskRequest, capability: A2ACapability) -> Dict[str, Any]:
        """Handle search capability task"""
        service_id = capability.name.replace("search_", "")
        
        # Use MCP server's business adapter
        result = await self.mcp_server.business_adapter.search_availability(service_id, request.input)
        
        return {
            "results": result.get("results", []),
            "total_found": result.get("total_results", 0),
            "search_id": result.get("search_id"),
            "service_id": service_id,
            "search_params": request.input
        }
    
    async def _handle_booking_task(self, request: A2ATaskRequest, capability: A2ACapability) -> Dict[str, Any]:
        """Handle booking capability task"""
        service_id = capability.name.replace("book_", "")
        
        # Use MCP server's business adapter
        result = await self.mcp_server.business_adapter.create_booking(service_id, request.input)
        
        return {
            "booking_id": result.get("booking_id"),
            "status": result.get("status"),
            "confirmation_number": result.get("confirmation_number"),
            "total_amount": result.get("total_amount"),
            "currency": result.get("currency", "USD"),
            "service_id": service_id
        }
    
    async def _handle_business_info_task(self, request: A2ATaskRequest) -> Dict[str, Any]:
        """Handle business info capability task"""
        return {
            "business_info": self.business_schema.business_info.dict(),
            "services": [
                {
                    "id": service.id,
                    "name": service.name,
                    "description": service.description,
                    "category": service.category,
                    "enabled": service.enabled
                }
                for service in self.business_schema.services
            ],
            "capabilities": [cap.name for cap in self.agent_card.agent.capabilities],
            "bais_version": self.business_schema.bais_version,
            "integration_endpoints": {
                "mcp": self.business_schema.integration.mcp_server.endpoint,
                "a2a": self.business_schema.integration.a2a_endpoint.discovery_url
            }
        }
    
    async def _send_callback(self, callback_url: str, result: A2ATaskResult):
        """Send callback notification"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(callback_url, json=result.dict(), timeout=10.0)
        except Exception as e:
            print(f"Failed to send callback to {callback_url}: {e}")

# A2A Client for connecting to other agents
class BAISA2AClient:
    """A2A Client for discovering and coordinating with other agents"""
    
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.discovered_agents: Dict[str, A2AAgentCard] = {}
    
    async def discover_agent(self, discovery_url: str) -> A2AAgentCard:
        """Discover an agent by its discovery URL"""
        try:
            response = await self.client.get(discovery_url)
            response.raise_for_status()
            
            agent_card = A2AAgentCard(**response.json())
            self.discovered_agents[agent_card.agent.name] = agent_card
            
            return agent_card
            
        except Exception as e:
            raise ValueError(f"Failed to discover agent at {discovery_url}: {e}")
    
    async def search_agents(self, agent_endpoints: List[str], capabilities_needed: List[str]) -> List[Dict[str, Any]]:
        """Search for agents with specific capabilities"""
        all_agents = []
        
        for endpoint in agent_endpoints:
            try:
                discovery_request = A2ADiscoveryRequest(
                    requesting_agent="bais-coordinator",
                    capabilities_needed=capabilities_needed
                )
                
                response = await self.client.post(f"{endpoint}/discover", json=discovery_request.dict())
                response.raise_for_status()
                
                discovery_response = A2ADiscoveryResponse(**response.json())
                all_agents.extend(discovery_response.agents)
                
            except Exception as e:
                print(f"Failed to search agents at {endpoint}: {e}")
        
        return all_agents
    
    async def execute_task(self, agent_endpoint: str, capability: str, task_input: Dict[str, Any]) -> A2ATaskResult:
        """Execute a task on a remote agent"""
        task_request = A2ATaskRequest(
            capability=capability,
            input=task_input
        )
        
        # Submit task
        response = await self.client.post(f"{agent_endpoint}/task", json=task_request.dict())
        response.raise_for_status()
        task_status = A2ATaskStatus(**response.json())
        
        # Poll for completion
        while task_status.status in ["pending", "running"]:
            await asyncio.sleep(1)
            response = await self.client.get(f"{agent_endpoint}/task/{task_status.task_id}/status")
            response.raise_for_status()
            task_status = A2ATaskStatus(**response.json())
        
        # Get result
        response = await self.client.get(f"{agent_endpoint}/task/{task_status.task_id}/result")
        response.raise_for_status()
        
        return A2ATaskResult(**response.json())

# Integration Factory
class BAISA2AFactory:
    """Factory for creating A2A servers and clients"""
    
    @staticmethod
    def create_server(business_schema: 'BAISBusinessSchema', mcp_server: 'BAISMCPServer') -> BAISA2AServer:
        """Create A2A server for business schema"""
        return BAISA2AServer(business_schema, mcp_server)
    
    @staticmethod
    def create_client() -> BAISA2AClient:
        """Create A2A client for agent coordination"""
        return BAISA2AClient()
    
    @staticmethod
    def deploy_server(server: BAISA2AServer, host: str = "0.0.0.0", port: int = 8002):
        """Deploy A2A server"""
        import uvicorn
        uvicorn.run(server.app, host=host, port=port)

# Example multi-agent coordination
async def coordinate_travel_booking():
    """Example of coordinating multiple BAIS agents for travel booking"""
    client = BAISA2AClient()
    
    # Discover hotel agent
    hotel_agent = await client.discover_agent("https://hotel.example.com/.well-known/agent.json")
    
    # Discover restaurant agent
    restaurant_agent = await client.discover_agent("https://restaurant.example.com/.well-known/agent.json")
    
    # Search for hotel rooms
    hotel_result = await client.execute_task(
        hotel_agent.server.endpoint,
        "search_room_booking",
        {
            "check_in": "2024-03-15",
            "check_out": "2024-03-17",
            "guests": 2
        }
    )
    
    # Search for restaurant reservations
    restaurant_result = await client.execute_task(
        restaurant_agent.server.endpoint,
        "search_table_reservation", 
        {
            "date": "2024-03-15",
            "time": "19:00",
            "party_size": 2
        }
    )
    
    return {
        "hotel_options": hotel_result.output,
        "restaurant_options": restaurant_result.output,
        "coordination_id": str(uuid.uuid4())
    }

if __name__ == "__main__":
    # Example usage
    from bais_schema_validator import BAISSchemaValidator
    from mcp_server_generator import BAISMCPServerFactory
    
    # Create hotel schema and MCP server
    hotel_schema = BAISSchemaValidator.create_hospitality_template()
    mcp_server = BAISMCPServerFactory.create_server(hotel_schema)
    
    # Create A2A server
    factory = BAISA2AFactory()
    a2a_server = factory.create_server(hotel_schema, mcp_server)
    
    # Deploy A2A server
    factory.deploy_server(a2a_server, port=8002)