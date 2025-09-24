"""
MCP Prompts Router - Clean Code Implementation
FastAPI router for MCP Prompts primitive endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ...core.mcp_prompts import (
    MCPPromptManager, 
    MCPPromptExecutor, 
    PromptTemplate, 
    PromptType, 
    PromptCategory,
    get_prompt_manager,
    get_prompt_executor
)
from ...core.mcp_authentication_service import AuthenticationService, AuthContext
from ...core.mcp_error_handler import MCPErrorHandler, ValidationError
from ...core.mcp_input_validation import MCPInputValidator

router = APIRouter(prefix="/mcp/prompts", tags=["MCP Prompts"])


class MCPPromptRequest(BaseModel):
    """Request model for MCP prompt execution"""
    name: str = Field(..., description="Name of the prompt template")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the prompt")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for execution")


class MCPPromptResponse(BaseModel):
    """Response model for MCP prompt execution"""
    success: bool = Field(..., description="Whether the prompt execution was successful")
    execution_id: Optional[str] = Field(None, description="Unique execution identifier")
    result: Optional[Dict[str, Any]] = Field(None, description="Prompt execution result")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")


class MCPPromptTemplate(BaseModel):
    """MCP prompt template model for API responses"""
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    prompt_type: str = Field(..., description="Type of prompt")
    category: str = Field(..., description="Category of prompt")
    variables: List[Dict[str, Any]] = Field(default_factory=list, description="Template variables")
    output_format: Dict[str, Any] = Field(default_factory=dict, description="Expected output format")
    version: str = Field(..., description="Template version")


class MCPPromptListResponse(BaseModel):
    """Response model for listing MCP prompts"""
    prompts: List[MCPPromptTemplate] = Field(..., description="List of available prompts")
    total_count: int = Field(..., description="Total number of prompts")


@router.get("/list", response_model=MCPPromptListResponse)
async def list_prompts(
    category: Optional[str] = Query(None, description="Filter by prompt category"),
    prompt_manager: MCPPromptManager = Depends(get_prompt_manager)
):
    """
    List available MCP prompt templates
    
    Returns a list of all available prompt templates, optionally filtered by category.
    This endpoint supports the MCP Prompts primitive for template discovery.
    """
    try:
        # Convert category string to enum if provided
        category_enum = None
        if category:
            try:
                category_enum = PromptCategory(category)
            except ValueError:
                raise ValidationError(
                    f"Invalid prompt category: {category}",
                    field="category",
                    details={"valid_categories": [c.value for c in PromptCategory]}
                )
        
        # Get templates
        templates = prompt_manager.list_templates(category_enum)
        
        # Convert to API response format
        prompt_templates = []
        for template in templates:
            prompt_templates.append(MCPPromptTemplate(
                name=template.name,
                description=template.description,
                prompt_type=template.prompt_type.value,
                category=template.category.value,
                variables=[
                    {
                        "name": var.name,
                        "description": var.description,
                        "type": var.type,
                        "required": var.required,
                        "default_value": var.default_value,
                        "examples": var.examples
                    }
                    for var in template.variables
                ],
                output_format=template.output_format,
                version=template.version
            ))
        
        return MCPPromptListResponse(
            prompts=prompt_templates,
            total_count=len(prompt_templates)
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list prompts: {str(e)}")


@router.get("/get/{prompt_name}", response_model=MCPPromptTemplate)
async def get_prompt(
    prompt_name: str,
    prompt_manager: MCPPromptManager = Depends(get_prompt_manager)
):
    """
    Get a specific MCP prompt template
    
    Returns detailed information about a specific prompt template including
    its variables, output format, and metadata.
    """
    try:
        template = prompt_manager.get_template(prompt_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"Prompt template not found: {prompt_name}")
        
        return MCPPromptTemplate(
            name=template.name,
            description=template.description,
            prompt_type=template.prompt_type.value,
            category=template.category.value,
            variables=[
                {
                    "name": var.name,
                    "description": var.description,
                    "type": var.type,
                    "required": var.required,
                    "default_value": var.default_value,
                    "examples": var.examples
                }
                for var in template.variables
            ],
            output_format=template.output_format,
            version=template.version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prompt template: {str(e)}")


@router.post("/execute", response_model=MCPPromptResponse)
async def execute_prompt(
    request: MCPPromptRequest,
    prompt_executor: MCPPromptExecutor = Depends(get_prompt_executor)
):
    """
    Execute an MCP prompt template
    
    Executes a prompt template with the provided arguments and returns the result.
    This endpoint supports the MCP Prompts primitive for prompt execution.
    """
    try:
        # Validate prompt name
        if not request.name or not request.name.strip():
            raise ValidationError("Prompt name cannot be empty", field="name")
        
        # Execute the prompt
        result = await prompt_executor.execute_prompt(
            prompt_name=request.name,
            variables=request.arguments,
            context=request.context or {}
        )
        
        return MCPPromptResponse(
            success=result["success"],
            execution_id=result.get("execution_id"),
            result=result.get("result"),
            error=result.get("error"),
            timestamp=datetime.now()
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute prompt: {str(e)}")


@router.get("/categories")
async def list_prompt_categories():
    """
    List available prompt categories
    
    Returns a list of all available prompt categories for filtering and organization.
    """
    try:
        categories = [
            {
                "name": category.value,
                "description": _get_category_description(category)
            }
            for category in PromptCategory
        ]
        
        return {
            "categories": categories,
            "total_count": len(categories)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list categories: {str(e)}")


@router.get("/types")
async def list_prompt_types():
    """
    List available prompt types
    
    Returns a list of all available prompt types for understanding prompt capabilities.
    """
    try:
        types = [
            {
                "name": prompt_type.value,
                "description": _get_prompt_type_description(prompt_type)
            }
            for prompt_type in PromptType
        ]
        
        return {
            "types": types,
            "total_count": len(types)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list types: {str(e)}")


@router.get("/execution-history")
async def get_execution_history(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of executions to return"),
    prompt_executor: MCPPromptExecutor = Depends(get_prompt_executor)
):
    """
    Get prompt execution history
    
    Returns the history of prompt executions for monitoring and debugging purposes.
    """
    try:
        history = prompt_executor.get_execution_history(limit)
        
        return {
            "executions": history,
            "total_count": len(history),
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get execution history: {str(e)}")


@router.get("/health")
async def prompts_health_check():
    """
    Health check endpoint for MCP prompts service
    
    Returns the health status of the prompts service and available templates.
    """
    try:
        prompt_manager = get_prompt_manager()
        templates = prompt_manager.list_templates()
        
        return {
            "status": "healthy",
            "service": "mcp-prompts",
            "available_templates": len(templates),
            "supported_categories": len(PromptCategory),
            "supported_types": len(PromptType),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "mcp-prompts",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _get_category_description(category: PromptCategory) -> str:
    """Get human-readable description for prompt category"""
    descriptions = {
        PromptCategory.OPERATIONAL: "Operational prompts for business processes",
        PromptCategory.ANALYTICAL: "Analytical prompts for data analysis and reporting",
        PromptCategory.COORDINATION: "Coordination prompts for multi-agent workflows",
        PromptCategory.SUPPORT: "Support prompts for customer service and assistance",
        PromptCategory.INTEGRATION: "Integration prompts for protocol interactions"
    }
    return descriptions.get(category, "Unknown category")


def _get_prompt_type_description(prompt_type: PromptType) -> str:
    """Get human-readable description for prompt type"""
    descriptions = {
        PromptType.BUSINESS_SEARCH: "Search for available business services",
        PromptType.BOOKING_CREATION: "Create bookings for business services",
        PromptType.PAYMENT_PROCESSING: "Process payments and financial transactions",
        PromptType.CUSTOMER_SUPPORT: "Handle customer support inquiries",
        PromptType.BUSINESS_ANALYTICS: "Generate business analytics and reports",
        PromptType.A2A_COORDINATION: "Coordinate multi-agent workflows",
        PromptType.AP2_PAYMENT_FLOW: "Process AP2 payment workflows"
    }
    return descriptions.get(prompt_type, "Unknown prompt type")


# Example usage endpoints for common business scenarios

@router.post("/examples/business-search")
async def example_business_search(
    business_name: str,
    location: str,
    service_category: str,
    customer_requirements: str,
    prompt_executor: MCPPromptExecutor = Depends(get_prompt_executor)
):
    """
    Example: Execute business search prompt
    
    A convenience endpoint for executing business search prompts with common parameters.
    """
    try:
        variables = {
            "business_name": business_name,
            "business_type": "general",  # Could be parameterized
            "location": location,
            "service_category": service_category,
            "customer_requirements": customer_requirements,
            "search_criteria": ""
        }
        
        result = await prompt_executor.execute_prompt("business_search", variables)
        
        return MCPPromptResponse(
            success=result["success"],
            execution_id=result.get("execution_id"),
            result=result.get("result"),
            error=result.get("error"),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute business search: {str(e)}")


@router.post("/examples/booking-creation")
async def example_booking_creation(
    business_name: str,
    service_name: str,
    customer_name: str,
    customer_email: str,
    booking_datetime: str,
    duration: str,
    quantity: int,
    prompt_executor: MCPPromptExecutor = Depends(get_prompt_executor)
):
    """
    Example: Execute booking creation prompt
    
    A convenience endpoint for executing booking creation prompts with common parameters.
    """
    try:
        variables = {
            "business_name": business_name,
            "service_name": service_name,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": "",  # Optional
            "booking_datetime": booking_datetime,
            "duration": duration,
            "quantity": quantity,
            "special_requirements": "",
            "payment_method": "credit_card"  # Default
        }
        
        result = await prompt_executor.execute_prompt("booking_creation", variables)
        
        return MCPPromptResponse(
            success=result["success"],
            execution_id=result.get("execution_id"),
            result=result.get("result"),
            error=result.get("error"),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute booking creation: {str(e)}")


@router.post("/examples/ap2-payment")
async def example_ap2_payment(
    business_name: str,
    payment_intent: str,
    amount: float,
    currency: str,
    customer_id: str,
    agent_id: str,
    payment_method_id: str,
    prompt_executor: MCPPromptExecutor = Depends(get_prompt_executor)
):
    """
    Example: Execute AP2 payment flow prompt
    
    A convenience endpoint for executing AP2 payment flow prompts with common parameters.
    """
    try:
        variables = {
            "business_name": business_name,
            "payment_intent": payment_intent,
            "amount": amount,
            "currency": currency,
            "customer_id": customer_id,
            "agent_id": agent_id,
            "payment_method_id": payment_method_id,
            "payment_constraints": "{}",
            "mandate_expiry": ""
        }
        
        result = await prompt_executor.execute_prompt("ap2_payment_flow", variables)
        
        return MCPPromptResponse(
            success=result["success"],
            execution_id=result.get("execution_id"),
            result=result.get("result"),
            error=result.get("error"),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute AP2 payment flow: {str(e)}")
