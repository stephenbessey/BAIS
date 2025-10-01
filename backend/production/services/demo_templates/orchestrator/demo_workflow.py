"""
BAIS Platform - Demo Orchestrator

This module orchestrates the complete demo generation pipeline, from website
analysis to deployment, creating full-stack demonstrations for potential clients.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import aiohttp
import httpx

from pydantic import BaseModel, Field

from ...core.bais_schema_validator import BAISBusinessSchema
from ..scraper.website_analyzer import WebsiteAnalyzer, BusinessIntelligence
from ..generator.schema_generator import SchemaGenerator
from ..generator.mcp_server_builder import McpServerBuilder, McpServerPackage
from ..generator.demo_ui_creator import DemoUiCreator, DemoApplication
from ..generator.acp_config_builder import AcpConfigBuilder, AcpConfiguration


class DemoType(str, Enum):
    """Demo generation types"""
    FULL_STACK = "full_stack"
    BACKEND_ONLY = "backend_only"
    FRONTEND_ONLY = "frontend_only"
    COMMERCE_ENABLED = "commerce_enabled"


class DemoConfig(BaseModel):
    """Demo configuration"""
    environment: str = Field(default="staging", description="Deployment environment")
    include_mock_data: bool = Field(default=True, description="Include mock data")
    enable_analytics: bool = Field(default=True, description="Enable analytics")
    enable_acp: bool = Field(default=False, description="Enable ACP commerce")
    infrastructure: Dict[str, Any] = Field(default_factory=dict, description="Infrastructure config")
    custom_domain: Optional[str] = Field(None, description="Custom domain for demo")


@dataclass
class DemoDeployment:
    """Demo deployment information"""
    demo_url: str
    admin_panel: str
    api_endpoints: Dict[str, str]
    documentation: str
    shutdown_command: str
    deployment_id: str
    created_at: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DemoOrchestrator:
    """
    Demo Orchestrator for BAIS Platform
    
    Orchestrates the complete demo generation pipeline from website analysis
    to deployment, creating full-stack demonstrations for potential clients.
    """
    
    def __init__(self, config: DemoConfig):
        self.config = config
        self.session = None
        self.http_client = None
        
        # Initialize components
        self.analyzer = None
        self.schema_generator = SchemaGenerator("templates/")
        self.mcp_builder = McpServerBuilder()
        self.ui_creator = DemoUiCreator()
        self.acp_builder = AcpConfigBuilder()
        
        # Deployment tracking
        self.active_deployments: Dict[str, DemoDeployment] = {}
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        self.http_client = httpx.AsyncClient()
        self.analyzer = WebsiteAnalyzer(self.session)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        if self.http_client:
            await self.http_client.aclose()
    
    async def generate_full_demo(
        self, 
        website_url: str,
        demo_type: DemoType = DemoType.FULL_STACK
    ) -> DemoDeployment:
        """
        End-to-end demo generation pipeline
        
        Args:
            website_url: Website URL to analyze
            demo_type: Type of demo to generate
            
        Returns:
            DemoDeployment: Complete demo deployment
        """
        try:
            deployment_id = str(uuid.uuid4())
            
            print(f"🚀 Starting demo generation for {website_url}")
            print(f"📋 Demo type: {demo_type.value}")
            print(f"🆔 Deployment ID: {deployment_id}")
            
            # Step 1: Extract intelligence from website
            print("🔍 Step 1: Analyzing website...")
            intelligence = await self.analyzer.analyze_business_website(website_url)
            print(f"✅ Extracted intelligence for {intelligence.business_name}")
            
            # Step 2: Generate BAIS schema
            print("📝 Step 2: Generating BAIS schema...")
            schema = self.schema_generator.generate_bais_schema(intelligence)
            print(f"✅ Generated schema with {len(schema.services)} services")
            
            # Step 3: Build components based on demo type
            print("🔧 Step 3: Building demo components...")
            components = await self._build_demo_components(schema, intelligence, demo_type)
            print(f"✅ Built {len(components)} components")
            
            # Step 4: Deploy and configure
            print("🚀 Step 4: Deploying demo...")
            deployment = await self._deploy_demo(
                components, 
                schema, 
                intelligence, 
                deployment_id
            )
            print(f"✅ Demo deployed at {deployment.demo_url}")
            
            # Step 5: Generate documentation
            print("📚 Step 5: Generating documentation...")
            documentation = self._generate_documentation(schema, deployment)
            deployment.documentation = documentation
            print("✅ Documentation generated")
            
            # Store deployment
            self.active_deployments[deployment_id] = deployment
            
            print(f"🎉 Demo generation complete!")
            print(f"🌐 Demo URL: {deployment.demo_url}")
            print(f"⚙️  Admin Panel: {deployment.admin_panel}")
            
            return deployment
            
        except Exception as e:
            print(f"❌ Demo generation failed: {str(e)}")
            raise Exception(f"Demo generation failed: {str(e)}")
    
    async def _build_demo_components(
        self, 
        schema: BAISBusinessSchema, 
        intelligence: BusinessIntelligence,
        demo_type: DemoType
    ) -> List[Any]:
        """Build demo components based on demo type"""
        components = []
        
        if demo_type in [DemoType.FULL_STACK, DemoType.BACKEND_ONLY]:
            print("  🔧 Building MCP server...")
            mcp_server = self.mcp_builder.build_demo_server(schema, self.config.dict())
            components.append(("mcp_server", mcp_server))
            print("  ✅ MCP server built")
        
        if demo_type in [DemoType.FULL_STACK, DemoType.COMMERCE_ENABLED]:
            print("  💳 Building ACP configuration...")
            acp_config = self.acp_builder.build_acp_integration(schema, intelligence.services)
            components.append(("acp_config", acp_config))
            print("  ✅ ACP configuration built")
        
        if demo_type in [DemoType.FULL_STACK, DemoType.FRONTEND_ONLY]:
            print("  🎨 Building demo UI...")
            ui_demo = self.ui_creator.create_interactive_demo(schema, intelligence)
            components.append(("ui_demo", ui_demo))
            print("  ✅ Demo UI built")
        
        return components
    
    async def _deploy_demo(
        self, 
        components: List[Tuple[str, Any]], 
        schema: BAISBusinessSchema,
        intelligence: BusinessIntelligence,
        deployment_id: str
    ) -> DemoDeployment:
        """Deploy demo components"""
        try:
            # Generate deployment URLs
            safe_name = schema.business_info.name.lower().replace(' ', '-').strip()
            demo_url = f"https://demo-{deployment_id[:8]}.bais.io"
            admin_panel = f"{demo_url}/admin"
            
            # Simulate deployment process
            # In a real implementation, this would:
            # 1. Create Kubernetes resources
            # 2. Deploy Docker containers
            # 3. Configure load balancers
            # 4. Set up monitoring
            
            # For demo purposes, we'll create mock deployment
            deployment = DemoDeployment(
                demo_url=demo_url,
                admin_panel=admin_panel,
                api_endpoints={
                    "mcp": f"{demo_url}/mcp",
                    "api": f"{demo_url}/api/v1",
                    "health": f"{demo_url}/health",
                    "metrics": f"{demo_url}/metrics"
                },
                documentation=f"{demo_url}/docs",
                shutdown_command=f"kubectl delete deployment demo-{deployment_id[:8]}",
                deployment_id=deployment_id,
                created_at=datetime.utcnow(),
                metadata={
                    "business_name": schema.business_info.name,
                    "business_type": schema.business_info.business_type,
                    "components": [comp[0] for comp in components],
                    "services_count": len(schema.services),
                    "website_url": intelligence.metadata.get('url', 'unknown')
                }
            )
            
            # Simulate deployment delay
            await asyncio.sleep(2)
            
            return deployment
            
        except Exception as e:
            raise Exception(f"Demo deployment failed: {str(e)}")
    
    def _generate_documentation(
        self, 
        schema: BAISBusinessSchema, 
        deployment: DemoDeployment
    ) -> str:
        """Generate comprehensive documentation"""
        business_name = schema.business_info.name
        
        doc = f'''# BAIS Demo - {business_name}

## Overview

This is a live demonstration of how {business_name} can be integrated with AI agents through the BAIS platform. The demo showcases real-time agent interactions with business services.

## Demo Information

- **Business**: {business_name}
- **Type**: {schema.business_info.business_type}
- **Demo URL**: {deployment.demo_url}
- **Admin Panel**: {deployment.admin_panel}
- **Generated**: {deployment.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")}

## Available Services

'''
        
        for service in schema.services:
            doc += f'''### {service.name}
- **ID**: {service.id}
- **Description**: {service.description}
- **Category**: {service.category}
- **Workflow**: {service.workflow.pattern}

'''
        
        doc += f'''## API Endpoints

- **MCP Protocol**: {deployment.api_endpoints["mcp"]}
- **REST API**: {deployment.api_endpoints["api"]}
- **Health Check**: {deployment.api_endpoints["health"]}
- **Metrics**: {deployment.api_endpoints["metrics"]}

## How to Use This Demo

### 1. Agent Integration
Connect an AI agent that supports the MCP protocol to the demo server:
```bash
# MCP endpoint
{deployment.api_endpoints["mcp"]}
```

### 2. REST API
Use the REST API for direct integration:
```bash
# List services
curl {deployment.api_endpoints["api"]}/services

# Search availability
curl -X POST {deployment.api_endpoints["api"]}/availability/search \\
  -H "Content-Type: application/json" \\
  -d '{{"date": "2024-01-15"}}'
```

### 3. Web Interface
Visit the admin panel to explore the demo:
- **URL**: {deployment.admin_panel}
- **Features**: Service management, booking monitoring, analytics

## Demo Scenarios

### Scenario 1: Service Discovery
1. Agent queries available services
2. Agent receives service catalog
3. Agent presents options to user

### Scenario 2: Booking Process
1. Agent searches availability
2. Agent collects user preferences
3. Agent creates booking
4. Agent confirms reservation

### Scenario 3: Customer Support
1. Agent accesses booking history
2. Agent provides status updates
3. Agent handles modifications

## Technical Details

### MCP Protocol Support
- **Version**: 2024-11-05
- **Resources**: Business info, services, bookings
- **Tools**: Search, book, modify, cancel

### Authentication
- **Type**: API Key
- **Header**: `X-API-Key: demo-key-{deployment_id[:8]}`

### Rate Limiting
- **Limit**: 100 requests/minute
- **Burst**: 200 requests/minute

## Cleanup

To remove this demo deployment:
```bash
{deployment.shutdown_command}
```

## Support

For questions about this demo or BAIS integration:
- **Documentation**: https://docs.bais.io
- **Support**: support@bais.io
- **Demo ID**: {deployment_id}

---
*Generated by BAIS Platform Demo Template System*
'''
        
        return doc
    
    async def cleanup_deployment(self, deployment_id: str) -> bool:
        """Cleanup demo deployment"""
        try:
            if deployment_id not in self.active_deployments:
                return False
            
            deployment = self.active_deployments[deployment_id]
            
            # Execute cleanup command
            print(f"🧹 Cleaning up deployment {deployment_id}...")
            # In real implementation, this would execute the shutdown command
            
            # Remove from active deployments
            del self.active_deployments[deployment_id]
            
            print(f"✅ Deployment {deployment_id} cleaned up")
            return True
            
        except Exception as e:
            print(f"❌ Cleanup failed: {str(e)}")
            return False
    
    async def list_active_deployments(self) -> List[DemoDeployment]:
        """List all active deployments"""
        return list(self.active_deployments.values())
    
    async def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status"""
        if deployment_id not in self.active_deployments:
            return None
        
        deployment = self.active_deployments[deployment_id]
        
        # Simulate health check
        try:
            async with self.http_client.get(f"{deployment.demo_url}/health") as response:
                status = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            status = "unreachable"
        
        return {
            "deployment_id": deployment_id,
            "demo_url": deployment.demo_url,
            "status": status,
            "created_at": deployment.created_at,
            "metadata": deployment.metadata
        }


# Example usage and CLI interface
async def main():
    """Example usage of Demo Orchestrator"""
    
    # Configuration
    config = DemoConfig(
        environment="staging",
        include_mock_data=True,
        enable_analytics=True,
        enable_acp=True
    )
    
    # Initialize orchestrator
    async with DemoOrchestrator(config) as orchestrator:
        
        # Generate demo for a hotel
        demo = await orchestrator.generate_full_demo(
            website_url="https://grandhotelstgeorge.com",
            demo_type=DemoType.FULL_STACK
        )
        
        print(f"Demo available at: {demo.demo_url}")
        print(f"Admin dashboard: {demo.admin_panel}")
        print(f"API docs: {demo.api_endpoints['api']}")
        
        # List active deployments
        deployments = await orchestrator.list_active_deployments()
        print(f"Active deployments: {len(deployments)}")
        
        # Get deployment status
        status = await orchestrator.get_deployment_status(demo.deployment_id)
        print(f"Deployment status: {status}")


if __name__ == "__main__":
    asyncio.run(main())
