"""
Production BAIS Backend
Integrates real BAIS protocol implementations with business management
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import asyncio
import uuid
from datetime import datetime, timedelta
import hashlib
import jwt
from pathlib import Path
import json

# Import our BAIS components
from bais_schema_validator import BAISBusinessSchema, BAISSchemaValidator
from mcp_server_generator import BAISMCPServerFactory, BAISMCPServer
from a2a_integration import BAISA2AFactory, BAISA2AServer

# API Models
class BusinessRegistrationRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=255)
    business_type: str = Field(..., regex="^(hospitality|food_service|retail|healthcare|finance)$")
    contact_info: Dict[str, str] = Field(...)
    location: Dict[str, Any] = Field(...)
    services_config: List[Dict[str, Any]] = Field(..., min_items=1)

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

# Production BAIS Application
class ProductionBAISApp:
    """Production BAIS application with full protocol support"""
    
    def __init__(self):
        self.app = FastAPI(
            title="BAIS Production Server",
            description="Business-Agent Integration Standard Production Implementation",
            version="1.0.0"
        )
        
        # Storage for businesses and their services
        self.businesses: Dict[str, BAISBusinessSchema] = {}
        self.mcp_servers: Dict[str, BAISMCPServer] = {}
        self.a2a_servers: Dict[str, BAISA2AServer] = {}
        self.api_keys: Dict[str, str] = {}  # api_key -> business_id mapping
        
        # Security
        self.security = HTTPBearer()
        self.jwt_secret = "your-jwt-secret-key"  # In production, use environment variable
        
        self._setup_middleware()
        self._setup_routes()
        
        # Initialize with sample businesses for demo
        self._initialize_sample_businesses()
    
    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            """API root endpoint"""
            return {
                "service": "BAIS Production Server",
                "version": "1.0.0",
                "protocol_support": {
                    "bais": "1.0",
                    "mcp": "2025-06-18",
                    "a2a": "1.0"
                },
                "endpoints": {
                    "business_registration": "/api/v1/businesses",
                    "schema_validation": "/api/v1/schemas/validate",
                    "agent_interaction": "/api/v1/agents/interact",
                    "mcp_servers": "/api/v1/mcp",
                    "a2a_discovery": "/api/v1/a2a/discover"
                }
            }
        
        @self.app.post("/api/v1/businesses", response_model=BusinessRegistrationResponse)
        async def register_business(
            request: BusinessRegistrationRequest,
            background_tasks: BackgroundTasks
        ):
            """Register a new business with BAIS"""
            try:
                # Generate business ID
                business_id = str(uuid.uuid4())
                
                # Create BAIS schema from request
                schema = self._create_business_schema(business_id, request)
                
                # Validate schema
                is_valid, issues = BAISSchemaValidator.validate_schema(schema.dict())
                if not is_valid:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid business schema: {'; '.join(issues)}"
                    )
                
                # Generate API keys
                api_key = self._generate_api_key(business_id)
                
                # Store business
                self.businesses[business_id] = schema
                self.api_keys[api_key] = business_id
                
                # Create and start MCP and A2A servers in background
                background_tasks.add_task(self._setup_business_servers, business_id, schema)
                
                return BusinessRegistrationResponse(
                    business_id=business_id,
                    status="registered",
                    mcp_endpoint=schema.integration.mcp_server.endpoint,
                    a2a_endpoint=schema.integration.a2a_endpoint.discovery_url,
                    api_keys={"primary": api_key},
                    setup_complete=False
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/businesses/{business_id}", response_model=BusinessStatusResponse)
        async def get_business_status(
            business_id: str,
            auth: HTTPAuthorizationCredentials = Depends(self.security)
        ):
            """Get business status and metrics"""
            await self._validate_business_access(auth, business_id)
            
            if business_id not in self.businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            business = self.businesses[business_id]
            
            return BusinessStatusResponse(
                business_id=business_id,
                name=business.business_info.name,
                status="active" if business_id in self.mcp_servers else "setting_up",
                services_enabled=len([s for s in business.services if s.enabled]),
                mcp_server_active=business_id in self.mcp_servers,
                a2a_server_active=business_id in self.a2a_servers,
                last_updated=business.updated_at,
                metrics=await self._get_business_metrics(business_id)
            )
        
        @self.app.post("/api/v1/schemas/validate", response_model=SchemaValidationResponse)
        async def validate_schema(request: SchemaValidationRequest):
            """Validate a BAIS business schema"""
            is_valid, issues = BAISSchemaValidator.validate_schema(request.schema_data)
            
            # Additional warnings for best practices
            warnings = []
            schema_data = request.schema_data
            
            if "services" in schema_data:
                for service in schema_data["services"]:
                    if len(service.get("parameters", {})) < 2:
                        warnings.append(f"Service {service.get('id')} has very few parameters")
            
            return SchemaValidationResponse(
                is_valid=is_valid,
                issues=issues,
                warnings=warnings
            )
        
        @self.app.post("/api/v1/agents/interact", response_model=AgentInteractionResponse)
        async def agent_interaction(
            request: AgentInteractionRequest,
            auth: HTTPAuthorizationCredentials = Depends(self.security)
        ):
            """Handle agent interaction with business services"""
            start_time = datetime.utcnow()
            
            # Validate business exists and is accessible
            if request.business_id not in self.businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            if request.business_id not in self.mcp_servers:
                raise HTTPException(status_code=503, detail="Business services not ready")
            
            try:
                # Route to appropriate handler based on interaction type
                if request.interaction_type == "search":
                    result = await self._handle_search_interaction(request)
                elif request.interaction_type == "book":
                    result = await self._handle_booking_interaction(request)
                elif request.interaction_type == "info":
                    result = await self._handle_info_interaction(request)
                else:
                    raise HTTPException(status_code=400, detail=f"Unsupported interaction type: {request.interaction_type}")
                
                processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                return AgentInteractionResponse(
                    interaction_id=str(uuid.uuid4()),
                    status="success",
                    response_data=result,
                    processing_time_ms=processing_time
                )
                
            except Exception as e:
                processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                return AgentInteractionResponse(
                    interaction_id=str(uuid.uuid4()),
                    status="error",
                    response_data={"error": str(e)},
                    processing_time_ms=processing_time
                )
        
        @self.app.get("/api/v1/businesses/{business_id}/schema")
        async def get_business_schema(
            business_id: str,
            auth: HTTPAuthorizationCredentials = Depends(self.security)
        ):
            """Get business BAIS schema"""
            await self._validate_business_access(auth, business_id)
            
            if business_id not in self.businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            return self.businesses[business_id].dict()
        
        @self.app.get("/api/v1/a2a/discover")
        async def discover_a2a_agents():
            """Discover available A2A agents"""
            agents = []
            
            for business_id, a2a_server in self.a2a_servers.items():
                business = self.businesses[business_id]
                agents.append({
                    "business_id": business_id,
                    "business_name": business.business_info.name,
                    "business_type": business.business_info.type.value,
                    "agent_card_url": business.integration.a2a_endpoint.discovery_url,
                    "capabilities": [cap.name for cap in a2a_server.agent_card.agent.capabilities],
                    "location": business.business_info.location.dict()
                })
            
            return {
                "agents": agents,
                "total_found": len(agents),
                "discovery_timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "businesses_registered": len(self.businesses),
                "mcp_servers_active": len(self.mcp_servers),
                "a2a_servers_active": len(self.a2a_servers)
            }
    
    def _create_business_schema(self, business_id: str, request: BusinessRegistrationRequest) -> BAISBusinessSchema:
        """Create BAIS schema from registration request"""
        from bais_schema_validator import (
            BusinessInfo, Location, ContactInfo, BusinessService, 
            WorkflowDefinition, WorkflowPattern, WorkflowStep,
            ServiceParameter, AvailabilityConfig, ServicePolicies,
            CancellationPolicyDetails, CancellationPolicy, PaymentConfig,
            PaymentMethod, IntegrationConfig, MCPIntegration, A2AIntegration,
            WebhookConfig, ServiceType
        )
        
        # Create location
        location = Location(**request.location)
        
        # Create contact info
        contact = ContactInfo(**request.contact_info)
        
        # Create business info
        business_info = BusinessInfo(
            id=business_id,
            name=request.business_name,
            type=ServiceType(request.business_type),
            location=location,
            contact=contact
        )
        
        # Create services from config
        services = []
        for service_config in request.services_config:
            # Create workflow
            workflow = WorkflowDefinition(
                pattern=WorkflowPattern(service_config.get("workflow_pattern", "booking_confirmation_payment")),
                steps=[
                    WorkflowStep(step=step["step"], description=step["description"])
                    for step in service_config.get("workflow_steps", [
                        {"step": "availability_check", "description": "Check availability"},
                        {"step": "booking", "description": "Create booking"},
                        {"step": "payment", "description": "Process payment"},
                        {"step": "confirmation", "description": "Send confirmation"}
                    ])
                ]
            )
            
            # Create parameters
            parameters = {}
            for param_name, param_config in service_config.get("parameters", {}).items():
                parameters[param_name] = ServiceParameter(**param_config)
            
            # Create policies
            policies = ServicePolicies(
                cancellation=CancellationPolicyDetails(
                    type=CancellationPolicy.FLEXIBLE,
                    free_until_hours=24,
                    penalty_percentage=0,
                    description="Free cancellation"
                ),
                payment=PaymentConfig(
                    methods=[PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD],
                    timing="at_booking"
                )
            )
            
            # Create service
            service = BusinessService(
                id=service_config["id"],
                name=service_config["name"],
                description=service_config.get("description", ""),
                category=service_config.get("category", "general"),
                workflow=workflow,
                parameters=parameters,
                availability=AvailabilityConfig(
                    endpoint=f"/api/v1/businesses/{business_id}/services/{service_config['id']}/availability"
                ),
                policies=policies
            )
            services.append(service)
        
        # Create integration config
        base_url = f"https://api.{request.business_name.lower().replace(' ', '-')}.com"
        integration = IntegrationConfig(
            mcp_server=MCPIntegration(
                endpoint=f"{base_url}/mcp"
            ),
            a2a_endpoint=A2AIntegration(
                discovery_url=f"{base_url}/.well-known/agent.json"
            ),
            webhooks=WebhookConfig(
                events=["booking_confirmed", "payment_processed"],
                endpoint=f"{base_url}/webhooks/bais"
            )
        )
        
        # Create complete schema
        return BAISBusinessSchema(
            business_info=business_info,
            services=services,
            integration=integration
        )
    
    async def _setup_business_servers(self, business_id: str, schema: BAISBusinessSchema):
        """Setup MCP and A2A servers for business"""
        try:
            # Create MCP server
            mcp_server = BAISMCPServerFactory.create_server(schema)
            self.mcp_servers[business_id] = mcp_server
            
            # Create A2A server
            a2a_server = BAISA2AFactory.create_server(schema, mcp_server)
            self.a2a_servers[business_id] = a2a_server
            
            print(f"Successfully set up servers for business {business_id}")
            
        except Exception as e:
            print(f"Failed to setup servers for business {business_id}: {e}")
    
    def _generate_api_key(self, business_id: str) -> str:
        """Generate API key for business"""
        data = f"{business_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    async def _validate_business_access(self, auth: HTTPAuthorizationCredentials, business_id: str):
        """Validate business access via API key"""
        api_key = auth.credentials
        
        if api_key not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        if self.api_keys[api_key] != business_id:
            raise HTTPException(status_code=403, detail="Access denied to this business")
    
    async def _get_business_metrics(self, business_id: str) -> Dict[str, Any]:
        """Get business metrics and analytics"""
        # This would integrate with actual analytics system
        return {
            "total_interactions": 156,
            "successful_bookings": 23,
            "revenue_today": 2847.50,
            "avg_response_time_ms": 145,
            "agent_satisfaction": 4.7
        }
    
    async def _handle_search_interaction(self, request: AgentInteractionRequest) -> Dict[str, Any]:
        """Handle search interaction"""
        mcp_server = self.mcp_servers[request.business_id]
        
        # Use the MCP server's business adapter
        service_id = request.parameters.get("service_id", "room_booking")
        search_params = {k: v for k, v in request.parameters.items() if k != "service_id"}
        
        result = await mcp_server.business_adapter.search_availability(service_id, search_params)
        
        return {
            "search_results": result,
            "business_id": request.business_id,
            "agent_id": request.agent_id,
            "search_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_booking_interaction(self, request: AgentInteractionRequest) -> Dict[str, Any]:
        """Handle booking interaction"""
        mcp_server = self.mcp_servers[request.business_id]
        
        # Use the MCP server's business adapter
        service_id = request.parameters.get("service_id", "room_booking")
        booking_params = {k: v for k, v in request.parameters.items() if k != "service_id"}
        
        result = await mcp_server.business_adapter.create_booking(service_id, booking_params)
        
        return {
            "booking_result": result,
            "business_id": request.business_id,
            "agent_id": request.agent_id,
            "booking_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_info_interaction(self, request: AgentInteractionRequest) -> Dict[str, Any]:
        """Handle info interaction"""
        business = self.businesses[request.business_id]
        
        return {
            "business_info": business.business_info.dict(),
            "services": [
                {
                    "id": service.id,
                    "name": service.name,
                    "description": service.description,
                    "enabled": service.enabled
                }
                for service in business.services
            ],
            "bais_version": business.bais_version,
            "last_updated": business.updated_at.isoformat()
        }
    
    def _initialize_sample_businesses(self):
        """Initialize sample businesses for demo"""
        try:
            # Create sample hotel
            hotel_schema = BAISSchemaValidator.create_hospitality_template()
            hotel_id = "demo-hotel-001"
            hotel_schema.business_info.id = hotel_id
            
            self.businesses[hotel_id] = hotel_schema
            api_key = self._generate_api_key(hotel_id)
            self.api_keys[api_key] = hotel_id
            
            # Setup servers for demo hotel
            asyncio.create_task(self._setup_business_servers(hotel_id, hotel_schema))
            
            print(f"Initialized demo hotel with ID: {hotel_id}, API Key: {api_key}")
            
        except Exception as e:
            print(f"Failed to initialize sample businesses: {e}")

# Application factory
def create_production_app() -> FastAPI:
    """Create production BAIS application"""
    bais_app = ProductionBAISApp()
    return bais_app.app

# For running with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    app = create_production_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)