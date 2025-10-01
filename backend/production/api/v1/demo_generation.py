"""
BAIS Platform - Demo Generation API

FastAPI endpoints for the demo template system, allowing users to generate
BAIS demonstrations from business websites through a REST API.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from ...core.database_models import DatabaseManager
from ...services.demo_templates import (
    DemoOrchestrator, DemoConfig, DemoType,
    WebsiteAnalyzer, BusinessIntelligence
)
import aiohttp


# Request/Response Models
class DemoGenerationRequest(BaseModel):
    """Request model for demo generation"""
    website_url: str = Field(..., description="Website URL to analyze", example="https://example.com")
    demo_type: str = Field(default="full_stack", description="Type of demo to generate")
    enable_acp: bool = Field(default=False, description="Enable ACP commerce integration")
    custom_domain: Optional[str] = Field(None, description="Custom domain for demo")
    output_format: str = Field(default="urls", description="Output format (urls, files, both)")
    
    @validator('demo_type')
    def validate_demo_type(cls, v):
        valid_types = ["full_stack", "backend_only", "frontend_only", "commerce_enabled"]
        if v not in valid_types:
            raise ValueError(f"demo_type must be one of: {valid_types}")
        return v
    
    @validator('website_url')
    def validate_website_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("website_url must start with http:// or https://")
        return v


class DemoGenerationResponse(BaseModel):
    """Response model for demo generation"""
    success: bool = Field(..., description="Generation success status")
    deployment_id: str = Field(..., description="Unique deployment identifier")
    demo_url: Optional[str] = Field(None, description="Demo application URL")
    admin_panel: Optional[str] = Field(None, description="Admin panel URL")
    api_endpoints: Optional[Dict[str, str]] = Field(None, description="API endpoints")
    documentation: Optional[str] = Field(None, description="Documentation URL")
    shutdown_command: Optional[str] = Field(None, description="Cleanup command")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WebsiteAnalysisRequest(BaseModel):
    """Request model for website analysis"""
    website_url: str = Field(..., description="Website URL to analyze", example="https://example.com")


class WebsiteAnalysisResponse(BaseModel):
    """Response model for website analysis"""
    success: bool = Field(..., description="Analysis success status")
    business_intelligence: Dict[str, Any] = Field(..., description="Extracted business intelligence")
    analysis_timestamp: datetime = Field(..., description="Analysis timestamp")


class DeploymentStatusResponse(BaseModel):
    """Response model for deployment status"""
    deployment_id: str = Field(..., description="Deployment identifier")
    demo_url: str = Field(..., description="Demo URL")
    status: str = Field(..., description="Deployment status")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: Dict[str, Any] = Field(..., description="Deployment metadata")


class DeploymentListResponse(BaseModel):
    """Response model for deployment listing"""
    deployments: List[DeploymentStatusResponse] = Field(..., description="List of deployments")
    total_count: int = Field(..., description="Total number of deployments")


# Router
router = APIRouter(prefix="/demo-generation", tags=["Demo Generation"])

# Global storage for demo deployments (in production, use database)
demo_deployments: Dict[str, Any] = {}


@router.post("/generate", response_model=DemoGenerationResponse)
async def generate_demo(
    request: DemoGenerationRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
) -> DemoGenerationResponse:
    """
    Generate a BAIS demo from a business website
    
    This endpoint analyzes a business website and generates a complete
    BAIS demonstration including MCP server, UI, and optionally ACP integration.
    """
    try:
        deployment_id = str(uuid.uuid4())
        
        # Configuration
        config = DemoConfig(
            environment="staging",
            include_mock_data=True,
            enable_analytics=True,
            enable_acp=request.enable_acp,
            custom_domain=request.custom_domain,
            infrastructure={
                "provider": "docker",
                "auto_cleanup": True,
                "resource_limits": {
                    "cpu": "1",
                    "memory": "2Gi"
                }
            }
        )
        
        # Generate demo in background
        background_tasks.add_task(
            _generate_demo_background,
            deployment_id,
            request.website_url,
            request.demo_type,
            config
        )
        
        # Store deployment info
        demo_deployments[deployment_id] = {
            "deployment_id": deployment_id,
            "website_url": request.website_url,
            "demo_type": request.demo_type,
            "status": "generating",
            "created_at": datetime.utcnow(),
            "config": config.dict()
        }
        
        return DemoGenerationResponse(
            success=True,
            deployment_id=deployment_id,
            created_at=datetime.utcnow(),
            metadata={
                "message": "Demo generation started",
                "estimated_completion": "2-5 minutes",
                "status_endpoint": f"/api/v1/demo-generation/status/{deployment_id}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demo generation failed: {str(e)}")


@router.post("/analyze", response_model=WebsiteAnalysisResponse)
async def analyze_website(request: WebsiteAnalysisRequest) -> WebsiteAnalysisResponse:
    """
    Analyze a business website and extract intelligence
    
    This endpoint performs website analysis to extract business information,
    services, and other relevant data for demo generation.
    """
    try:
        async with aiohttp.ClientSession() as session:
            analyzer = WebsiteAnalyzer(session)
            intelligence = await analyzer.analyze_business_website(request.website_url)
            
            # Convert to dict for JSON serialization
            intelligence_dict = {
                "business_name": intelligence.business_name,
                "business_type": intelligence.business_type.value,
                "description": intelligence.description,
                "services": [
                    {
                        "id": service.id,
                        "name": service.name,
                        "description": service.description,
                        "category": service.category,
                        "service_type": service.service_type.value,
                        "price": service.price,
                        "currency": service.currency
                    }
                    for service in intelligence.services
                ],
                "contact_info": {
                    "phone": intelligence.contact_info.phone,
                    "email": intelligence.contact_info.email,
                    "address": intelligence.contact_info.address,
                    "website": intelligence.contact_info.website,
                    "social_media": intelligence.contact_info.social_media
                },
                "operational_hours": intelligence.operational_hours.__dict__ if intelligence.operational_hours else None,
                "pricing_info": {
                    "currency": intelligence.pricing_info.currency,
                    "price_range": intelligence.pricing_info.price_range,
                    "min_price": intelligence.pricing_info.min_price,
                    "max_price": intelligence.pricing_info.max_price,
                    "pricing_model": intelligence.pricing_info.pricing_model
                },
                "metadata": intelligence.metadata
            }
            
            return WebsiteAnalysisResponse(
                success=True,
                business_intelligence=intelligence_dict,
                analysis_timestamp=datetime.utcnow()
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Website analysis failed: {str(e)}")


@router.get("/status/{deployment_id}", response_model=DeploymentStatusResponse)
async def get_deployment_status(deployment_id: str) -> DeploymentStatusResponse:
    """
    Get the status of a demo deployment
    
    Returns the current status and details of a demo deployment.
    """
    if deployment_id not in demo_deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    deployment = demo_deployments[deployment_id]
    
    return DeploymentStatusResponse(
        deployment_id=deployment_id,
        demo_url=deployment.get("demo_url", ""),
        status=deployment["status"],
        created_at=deployment["created_at"],
        metadata=deployment.get("metadata", {})
    )


@router.get("/deployments", response_model=DeploymentListResponse)
async def list_deployments() -> DeploymentListResponse:
    """
    List all demo deployments
    
    Returns a list of all active demo deployments.
    """
    deployments = []
    
    for deployment_id, deployment in demo_deployments.items():
        deployments.append(DeploymentStatusResponse(
            deployment_id=deployment_id,
            demo_url=deployment.get("demo_url", ""),
            status=deployment["status"],
            created_at=deployment["created_at"],
            metadata=deployment.get("metadata", {})
        ))
    
    return DeploymentListResponse(
        deployments=deployments,
        total_count=len(deployments)
    )


@router.delete("/deployments/{deployment_id}")
async def cleanup_deployment(deployment_id: str) -> JSONResponse:
    """
    Cleanup a demo deployment
    
    Removes a demo deployment and cleans up associated resources.
    """
    if deployment_id not in demo_deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    deployment = demo_deployments[deployment_id]
    
    try:
        # Execute cleanup command if available
        if "shutdown_command" in deployment:
            # In a real implementation, this would execute the actual cleanup
            print(f"Executing cleanup: {deployment['shutdown_command']}")
        
        # Remove from storage
        del demo_deployments[deployment_id]
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Deployment {deployment_id} cleaned up successfully"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/templates")
async def list_demo_templates() -> JSONResponse:
    """
    List available demo templates
    
    Returns information about available demo templates and their configurations.
    """
    templates = {
        "full_stack": {
            "name": "Full Stack Demo",
            "description": "Complete demo with frontend, backend, and all integrations",
            "components": ["mcp_server", "demo_ui", "acp_config"],
            "estimated_time": "3-5 minutes",
            "features": [
                "Interactive web interface",
                "MCP protocol server",
                "Agent chat interface",
                "Admin dashboard",
                "Analytics"
            ]
        },
        "backend_only": {
            "name": "Backend Only Demo",
            "description": "Backend API and MCP server without frontend",
            "components": ["mcp_server"],
            "estimated_time": "2-3 minutes",
            "features": [
                "MCP protocol server",
                "REST API endpoints",
                "Health checks",
                "Metrics"
            ]
        },
        "frontend_only": {
            "name": "Frontend Only Demo",
            "description": "Interactive web interface without backend",
            "components": ["demo_ui"],
            "estimated_time": "1-2 minutes",
            "features": [
                "Interactive web interface",
                "Mock data",
                "Demo scenarios",
                "Static deployment"
            ]
        },
        "commerce_enabled": {
            "name": "Commerce Enabled Demo",
            "description": "Full demo with ACP commerce integration",
            "components": ["mcp_server", "demo_ui", "acp_config"],
            "estimated_time": "4-6 minutes",
            "features": [
                "Interactive web interface",
                "MCP protocol server",
                "ACP commerce integration",
                "Payment processing",
                "Order management"
            ]
        }
    }
    
    return JSONResponse(content={"templates": templates})


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check for demo generation service
    
    Returns the health status of the demo generation service.
    """
    return JSONResponse(content={
        "status": "healthy",
        "service": "demo-generation",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "active_deployments": len(demo_deployments)
    })


# Background task function
async def _generate_demo_background(
    deployment_id: str,
    website_url: str,
    demo_type: str,
    config: DemoConfig
) -> None:
    """Background task for demo generation"""
    try:
        async with DemoOrchestrator(config) as orchestrator:
            demo_type_enum = DemoType(demo_type)
            deployment = await orchestrator.generate_full_demo(
                website_url=website_url,
                demo_type=demo_type_enum
            )
            
            # Update deployment info
            demo_deployments[deployment_id].update({
                "status": "completed",
                "demo_url": deployment.demo_url,
                "admin_panel": deployment.admin_panel,
                "api_endpoints": deployment.api_endpoints,
                "documentation": deployment.documentation,
                "shutdown_command": deployment.shutdown_command,
                "metadata": deployment.metadata
            })
            
    except Exception as e:
        # Update deployment with error status
        demo_deployments[deployment_id].update({
            "status": "failed",
            "error": str(e)
        })
