"""
BAIS Platform - MCP Server Builder for Demo Generation

This module generates working MCP servers for demo purposes based on
BAIS business schemas, creating complete server implementations with
resources, tools, and Docker configurations.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import os

from pydantic import BaseModel, Field

from ...core.bais_schema_validator import BAISBusinessSchema, BusinessService


@dataclass
class McpResource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mime_type: str
    content: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class McpTool:
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    handler_function: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class McpServerPackage:
    """Complete MCP server package"""
    server_implementation: str
    resources: List[McpResource]
    tools: List[McpTool]
    dockerfile: str
    compose_config: str
    requirements: str
    readme: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class McpServerBuilder:
    """
    MCP Server Builder for BAIS Demo Generation
    
    Generates working MCP servers based on BAIS business schemas,
    creating complete server implementations with resources and tools.
    """
    
    def __init__(self):
        self.template_dir = Path(__file__).parent / "templates"
        self.output_dir = Path("/tmp/bais_demo_servers")
        self.output_dir.mkdir(exist_ok=True)
        
        # Tool templates for different service types
        self.tool_templates = {
            "booking": [
                {
                    "name": "search_availability",
                    "description": "Search for available booking slots",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date"},
                            "time": {"type": "string", "format": "time"},
                            "duration": {"type": "integer", "minimum": 1}
                        },
                        "required": ["date"]
                    },
                    "handler": "handle_search_availability"
                },
                {
                    "name": "create_booking",
                    "description": "Create a new booking",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "service_id": {"type": "string"},
                            "date": {"type": "string", "format": "date"},
                            "time": {"type": "string", "format": "time"},
                            "customer_name": {"type": "string"},
                            "customer_email": {"type": "string", "format": "email"},
                            "customer_phone": {"type": "string"}
                        },
                        "required": ["service_id", "date", "time", "customer_name", "customer_email"]
                    },
                    "handler": "handle_create_booking"
                }
            ],
            "ecommerce": [
                {
                    "name": "search_products",
                    "description": "Search for products",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "category": {"type": "string"},
                            "price_min": {"type": "number"},
                            "price_max": {"type": "number"}
                        }
                    },
                    "handler": "handle_search_products"
                },
                {
                    "name": "add_to_cart",
                    "description": "Add product to shopping cart",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string"},
                            "quantity": {"type": "integer", "minimum": 1}
                        },
                        "required": ["product_id", "quantity"]
                    },
                    "handler": "handle_add_to_cart"
                }
            ],
            "consultation": [
                {
                    "name": "schedule_appointment",
                    "description": "Schedule a consultation appointment",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "service_type": {"type": "string"},
                            "date": {"type": "string", "format": "date"},
                            "time": {"type": "string", "format": "time"},
                            "client_name": {"type": "string"},
                            "client_email": {"type": "string", "format": "email"},
                            "notes": {"type": "string"}
                        },
                        "required": ["service_type", "date", "time", "client_name", "client_email"]
                    },
                    "handler": "handle_schedule_appointment"
                }
            ]
        }
    
    def build_demo_server(
        self, 
        schema: BAISBusinessSchema,
        demo_config: Dict[str, Any]
    ) -> McpServerPackage:
        """
        Generate working MCP server for demo
        
        Args:
            schema: BAIS business schema
            demo_config: Demo configuration
            
        Returns:
            McpServerPackage: Complete server package
        """
        try:
            # Generate server implementation
            server_code = self._generate_server_implementation(schema, demo_config)
            
            # Create resources
            resources = self._create_resource_handlers(schema)
            
            # Create tools
            tools = self._create_tool_definitions(schema)
            
            # Generate Docker configuration
            dockerfile = self._generate_dockerfile()
            compose_config = self._generate_docker_compose(demo_config)
            
            # Generate requirements
            requirements = self._generate_requirements()
            
            # Generate README
            readme = self._generate_readme(schema, demo_config)
            
            return McpServerPackage(
                server_implementation=server_code,
                resources=resources,
                tools=tools,
                dockerfile=dockerfile,
                compose_config=compose_config,
                requirements=requirements,
                readme=readme,
                metadata={
                    "business_name": schema.business_info.name,
                    "business_type": schema.business_info.business_type,
                    "services_count": len(schema.services),
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            raise Exception(f"Server generation failed: {str(e)}")
    
    def _generate_server_implementation(
        self, 
        schema: BAISBusinessSchema,
        demo_config: Dict[str, Any]
    ) -> str:
        """Generate FastAPI server code"""
        business_name = schema.business_info.name
        business_type = schema.business_info.business_type
        
        # Generate imports
        imports = '''"""
BAIS Demo MCP Server - {business_name}

Auto-generated MCP server for {business_name} demo.
Generated by BAIS Platform Demo Template System.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

# MCP Protocol imports
from mcp import McpServer, McpResource, McpTool, McpCallToolResponse
from mcp.server import Server
from mcp.server.stdio import stdio_server'''.format(business_name=business_name)
        
        # Generate data models
        data_models = self._generate_data_models(schema)
        
        # Generate business logic
        business_logic = self._generate_business_logic(schema)
        
        # Generate MCP handlers
        mcp_handlers = self._generate_mcp_handlers(schema)
        
        # Generate FastAPI app
        fastapi_app = self._generate_fastapi_app(schema, demo_config)
        
        # Generate main function
        main_function = '''if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)'''
        
        # Combine all parts
        server_code = f"""{imports}

{data_models}

{business_logic}

{mcp_handlers}

{fastapi_app}

{main_function}"""
        
        return server_code
    
    def _generate_data_models(self, schema: BAISBusinessSchema) -> str:
        """Generate Pydantic data models"""
        models = '''# Data Models
class BookingRequest(BaseModel):
    service_id: str = Field(..., description="Service identifier")
    date: str = Field(..., description="Booking date")
    time: str = Field(..., description="Booking time")
    customer_name: str = Field(..., description="Customer name")
    customer_email: str = Field(..., description="Customer email")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    special_requests: Optional[str] = Field(None, description="Special requests")

class BookingResponse(BaseModel):
    booking_id: str = Field(..., description="Booking identifier")
    confirmation_number: str = Field(..., description="Confirmation number")
    status: str = Field(..., description="Booking status")
    total_amount: float = Field(..., description="Total amount")
    currency: str = Field(default="USD", description="Currency")

class AvailabilityRequest(BaseModel):
    date: str = Field(..., description="Date to check availability")
    service_id: Optional[str] = Field(None, description="Specific service ID")

class AvailabilityResponse(BaseModel):
    date: str = Field(..., description="Date checked")
    available_slots: List[Dict[str, Any]] = Field(..., description="Available time slots")
    service_id: str = Field(..., description="Service identifier")'''
        
        return models
    
    def _generate_business_logic(self, schema: BAISBusinessSchema) -> str:
        """Generate business logic functions"""
        business_name = schema.business_info.name
        
        logic = f'''# Business Logic
class {business_name.replace(' ', '')}Service:
    """Business logic for {business_name}"""
    
    def __init__(self):
        self.bookings: Dict[str, Dict[str, Any]] = {{}}
        self.availability: Dict[str, List[str]] = {{
            # Mock availability data
            "2024-01-15": ["09:00", "10:00", "11:00", "14:00", "15:00"],
            "2024-01-16": ["09:00", "10:00", "11:00", "14:00", "15:00"],
            "2024-01-17": ["09:00", "10:00", "11:00", "14:00", "15:00"],
        }}
    
    async def search_availability(self, date: str, service_id: Optional[str] = None) -> AvailabilityResponse:
        """Search for available booking slots"""
        available_slots = self.availability.get(date, [])
        
        return AvailabilityResponse(
            date=date,
            available_slots=[
                {{"time": slot, "available": True, "service_id": service_id or "default"}}
                for slot in available_slots
            ],
            service_id=service_id or "default"
        )
    
    async def create_booking(self, request: BookingRequest) -> BookingResponse:
        """Create a new booking"""
        booking_id = str(uuid.uuid4())
        confirmation_number = f"BK{{booking_id[:8].upper()}}"
        
        # Check availability
        available_slots = self.availability.get(request.date, [])
        if request.time not in available_slots:
            raise HTTPException(status_code=400, detail="Time slot not available")
        
        # Remove time slot from availability
        self.availability[request.date].remove(request.time)
        
        # Create booking record
        booking = {{
            "booking_id": booking_id,
            "confirmation_number": confirmation_number,
            "service_id": request.service_id,
            "date": request.date,
            "time": request.time,
            "customer_name": request.customer_name,
            "customer_email": request.customer_email,
            "customer_phone": request.customer_phone,
            "special_requests": request.special_requests,
            "status": "confirmed",
            "total_amount": 100.0,  # Mock amount
            "currency": "USD",
            "created_at": datetime.utcnow().isoformat()
        }}
        
        self.bookings[booking_id] = booking
        
        return BookingResponse(
            booking_id=booking_id,
            confirmation_number=confirmation_number,
            status="confirmed",
            total_amount=100.0,
            currency="USD"
        )
    
    async def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Get booking by ID"""
        return self.bookings.get(booking_id)

# Initialize service
business_service = {business_name.replace(' ', '')}Service()'''
        
        return logic
    
    def _generate_mcp_handlers(self, schema: BAISBusinessSchema) -> str:
        """Generate MCP protocol handlers"""
        handlers = '''# MCP Server Setup
app = FastAPI(title="BAIS Demo MCP Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Server
mcp_server = Server("bais-demo-server")

@mcp_server.list_resources()
async def list_resources() -> List[McpResource]:
    """List available resources"""
    return [
        McpResource(
            uri="business://info",
            name="Business Information",
            description="Business information and services",
            mime_type="application/json"
        ),
        McpResource(
            uri="business://services",
            name="Available Services",
            description="List of available services",
            mime_type="application/json"
        ),
        McpResource(
            uri="business://bookings",
            name="Bookings",
            description="Customer bookings",
            mime_type="application/json"
        )
    ]

@mcp_server.read_resource(uri="business://info")
async def read_business_info() -> str:
    """Read business information"""
    business_info = {
        "name": "Demo Business",
        "type": "service",
        "description": "Demo business for BAIS platform",
        "services": [
            {
                "id": "service_1",
                "name": "Demo Service",
                "description": "A demonstration service",
                "price": 100.0,
                "currency": "USD"
            }
        ]
    }
    return json.dumps(business_info, indent=2)

@mcp_server.read_resource(uri="business://services")
async def read_services() -> str:
    """Read available services"""
    services = [
        {
            "id": "service_1",
            "name": "Demo Service",
            "description": "A demonstration service",
            "price": 100.0,
            "currency": "USD",
            "available": True
        }
    ]
    return json.dumps(services, indent=2)

@mcp_server.list_tools()
async def list_tools() -> List[McpTool]:
    """List available tools"""
    return [
        McpTool(
            name="search_availability",
            description="Search for available booking slots",
            input_schema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "format": "date"},
                    "service_id": {"type": "string"}
                },
                "required": ["date"]
            }
        ),
        McpTool(
            name="create_booking",
            description="Create a new booking",
            input_schema={
                "type": "object",
                "properties": {
                    "service_id": {"type": "string"},
                    "date": {"type": "string", "format": "date"},
                    "time": {"type": "string", "format": "time"},
                    "customer_name": {"type": "string"},
                    "customer_email": {"type": "string", "format": "email"},
                    "customer_phone": {"type": "string"},
                    "special_requests": {"type": "string"}
                },
                "required": ["service_id", "date", "time", "customer_name", "customer_email"]
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> McpCallToolResponse:
    """Handle tool calls"""
    try:
        if name == "search_availability":
            date = arguments.get("date")
            service_id = arguments.get("service_id")
            result = await business_service.search_availability(date, service_id)
            return McpCallToolResponse(
                content=[{
                    "type": "text",
                    "text": json.dumps(result.dict(), indent=2)
                }]
            )
        
        elif name == "create_booking":
            request = BookingRequest(**arguments)
            result = await business_service.create_booking(request)
            return McpCallToolResponse(
                content=[{
                    "type": "text",
                    "text": json.dumps(result.dict(), indent=2)
                }]
            )
        
        else:
            return McpCallToolResponse(
                content=[{
                    "type": "text",
                    "text": f"Unknown tool: {{name}}"
                }],
                isError=True
            )
    
    except Exception as e:
        return McpCallToolResponse(
            content=[{
                "type": "text",
                "text": f"Error: {{str(e)}}"
            }],
            isError=True
        )'''
        
        return handlers
    
    def _generate_fastapi_app(self, schema: BAISBusinessSchema, demo_config: Dict[str, Any]) -> str:
        """Generate FastAPI application routes"""
        business_name = schema.business_info.name
        
        routes = f'''# FastAPI Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {{
        "message": "BAIS Demo MCP Server",
        "business": "{business_name}",
        "version": "1.0.0",
        "mcp_protocol": "2024-11-05"
    }}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {{"status": "healthy", "timestamp": datetime.utcnow().isoformat()}}

@app.get("/api/v1/services")
async def list_services():
    """List available services"""
    services = [
        {{
            "id": service.id,
            "name": service.name,
            "description": service.description,
            "category": service.category,
            "enabled": service.enabled
        }}
        for service in schema.services
    ]
    return {{"services": services}}

@app.post("/api/v1/availability/search")
async def search_availability(request: AvailabilityRequest):
    """Search for availability"""
    result = await business_service.search_availability(request.date, request.service_id)
    return result.dict()

@app.post("/api/v1/bookings")
async def create_booking(request: BookingRequest):
    """Create a new booking"""
    result = await business_service.create_booking(request)
    return result.dict()

@app.get("/api/v1/bookings/{{booking_id}}")
async def get_booking(booking_id: str):
    """Get booking by ID"""
    booking = await business_service.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.get("/mcp")
async def mcp_endpoint():
    """MCP protocol endpoint"""
    return {{
        "protocol": "mcp",
        "version": "2024-11-05",
        "server": "bais-demo-server",
        "capabilities": {{
            "resources": True,
            "tools": True
        }}
    }}'''
        
        return routes
    
    def _create_resource_handlers(self, schema: BAISBusinessSchema) -> List[McpResource]:
        """Create MCP resource handlers"""
        resources = [
            McpResource(
                uri="business://info",
                name="Business Information",
                description=f"Information about {schema.business_info.name}",
                mime_type="application/json"
            ),
            McpResource(
                uri="business://services",
                name="Available Services",
                description="List of available services",
                mime_type="application/json"
            ),
            McpResource(
                uri="business://bookings",
                name="Customer Bookings",
                description="Customer booking information",
                mime_type="application/json"
            )
        ]
        
        return resources
    
    def _create_tool_definitions(self, schema: BAISBusinessSchema) -> List[McpTool]:
        """Create MCP tool definitions"""
        tools = []
        
        # Add tools based on service types
        for service in schema.services:
            service_type = self._get_service_type(service)
            if service_type in self.tool_templates:
                for tool_template in self.tool_templates[service_type]:
                    tool = McpTool(
                        name=tool_template["name"],
                        description=tool_template["description"],
                        input_schema=tool_template["input_schema"],
                        output_schema={
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "data": {"type": "object"},
                                "message": {"type": "string"}
                            }
                        },
                        handler_function=tool_template["handler"]
                    )
                    tools.append(tool)
        
        # Remove duplicates
        unique_tools = []
        seen_names = set()
        for tool in tools:
            if tool.name not in seen_names:
                unique_tools.append(tool)
                seen_names.add(tool.name)
        
        return unique_tools
    
    def _get_service_type(self, service: BusinessService) -> str:
        """Determine service type from business service"""
        service_name = service.name.lower()
        
        if any(keyword in service_name for keyword in ["booking", "reservation", "appointment"]):
            return "booking"
        elif any(keyword in service_name for keyword in ["product", "purchase", "buy"]):
            return "ecommerce"
        elif any(keyword in service_name for keyword in ["consultation", "advice", "session"]):
            return "consultation"
        else:
            return "booking"  # Default
    
    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile"""
        return '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]'''
    
    def _generate_docker_compose(self, demo_config: Dict[str, Any]) -> str:
        """Generate Docker Compose configuration"""
        return '''version: '3.8'

services:
  bais-demo-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=demo
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

networks:
  default:
    name: bais-demo-network'''
    
    def _generate_requirements(self) -> str:
        """Generate requirements.txt"""
        return '''fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
httpx==0.25.2
mcp==0.4.0
python-multipart==0.0.6'''
    
    def _generate_readme(self, schema: BAISBusinessSchema, demo_config: Dict[str, Any]) -> str:
        """Generate README documentation"""
        business_name = schema.business_info.name
        business_type = schema.business_info.business_type
        
        readme = f'''# BAIS Demo MCP Server - {business_name}

Auto-generated MCP server for {business_name} demo using the BAIS Platform Demo Template System.

## Overview

This is a demonstration MCP (Model Context Protocol) server that showcases how {business_name} can be integrated with AI agents through the BAIS platform.

## Business Information

- **Name**: {business_name}
- **Type**: {business_type}
- **Description**: {schema.business_info.description}

## Available Services

'''
        
        for service in schema.services:
            readme += f'''### {service.name}
- **ID**: {service.id}
- **Description**: {service.description}
- **Category**: {service.category}

'''
        
        readme += '''## MCP Protocol Support

This server implements the MCP protocol (2024-11-05) and provides:

### Resources
- `business://info` - Business information
- `business://services` - Available services
- `business://bookings` - Customer bookings

### Tools
- `search_availability` - Search for available booking slots
- `create_booking` - Create a new booking

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/v1/services` - List services
- `POST /api/v1/availability/search` - Search availability
- `POST /api/v1/bookings` - Create booking
- `GET /api/v1/bookings/{booking_id}` - Get booking
- `GET /mcp` - MCP protocol information

## Quick Start

### Using Docker

```bash
# Build and run
docker-compose up --build

# The server will be available at http://localhost:8000
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Testing

Test the server using curl:

```bash
# Health check
curl http://localhost:8000/health

# List services
curl http://localhost:8000/api/v1/services

# Search availability
curl -X POST http://localhost:8000/api/v1/availability/search \\
  -H "Content-Type: application/json" \\
  -d '{"date": "2024-01-15"}'
```

## MCP Integration

This server can be integrated with AI agents that support the MCP protocol. The server provides resources and tools that allow AI agents to:

1. Discover available services
2. Check availability
3. Create bookings
4. Manage customer information

## Generated By

This server was generated by the BAIS Platform Demo Template System on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}.

For more information about BAIS, visit: https://bais.io
'''
        
        return readme
