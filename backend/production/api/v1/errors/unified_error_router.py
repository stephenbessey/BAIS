"""
Unified Error Router - Implementation
FastAPI router for unified error handling across all protocols
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ...core.unified_error_handler import (
    UnifiedErrorHandler,
    UnifiedError,
    ProtocolType,
    ErrorCategory,
    ErrorSeverity,
    get_unified_error_handler
)
from ...core.mcp_authentication_service import AuthenticationService, AuthContext
from ...core.mcp_error_handler import MCPErrorHandler, ValidationError

router = APIRouter(prefix="/errors", tags=["Unified Error Handling"])


class ErrorStatisticsResponse(BaseModel):
    """Response model for error statistics"""
    total_errors: int = Field(..., description="Total number of errors recorded")
    error_counts_by_category: Dict[str, int] = Field(..., description="Error counts by category")
    severity_distribution: Dict[str, int] = Field(..., description="Distribution by severity")
    protocol_distribution: Dict[str, int] = Field(..., description="Distribution by protocol")
    recent_errors: List[Dict[str, Any]] = Field(..., description="Recent error examples")


class ErrorHistoryResponse(BaseModel):
    """Response model for error history"""
    errors: List[Dict[str, Any]] = Field(..., description="List of errors")
    total_count: int = Field(..., description="Total number of errors")
    limit: int = Field(..., description="Requested limit")


class ErrorCategoryInfo(BaseModel):
    """Information about error categories"""
    category: str = Field(..., description="Category name")
    description: str = Field(..., description="Category description")
    severity: str = Field(..., description="Default severity level")
    protocols: List[str] = Field(..., description="Associated protocols")


class ProtocolInfo(BaseModel):
    """Information about protocols"""
    protocol: str = Field(..., description="Protocol name")
    description: str = Field(..., description="Protocol description")
    error_categories: List[str] = Field(..., description="Supported error categories")


@router.get("/statistics", response_model=ErrorStatisticsResponse)
async def get_error_statistics(
    handler: UnifiedErrorHandler = Depends(get_unified_error_handler)
):
    """
    Get comprehensive error statistics across all protocols
    
    Returns aggregated error statistics including counts by category,
    severity distribution, and protocol distribution for monitoring purposes.
    """
    try:
        stats = handler.get_error_statistics()
        
        return ErrorStatisticsResponse(
            total_errors=stats["total_errors"],
            error_counts_by_category=stats["error_counts_by_category"],
            severity_distribution=stats["severity_distribution"],
            protocol_distribution=stats["protocol_distribution"],
            recent_errors=stats["recent_errors"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error statistics: {str(e)}")


@router.get("/history", response_model=ErrorHistoryResponse)
async def get_error_history(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of errors to return"),
    protocol: Optional[str] = Query(None, description="Filter by protocol type"),
    category: Optional[str] = Query(None, description="Filter by error category"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    handler: UnifiedErrorHandler = Depends(get_unified_error_handler)
):
    """
    Get error history with optional filtering
    
    Returns historical error data with optional filters for protocol,
    category, and severity level.
    """
    try:
        # Get all recent errors
        all_errors = handler.get_recent_errors(limit * 2)  # Get more to account for filtering
        
        # Apply filters
        filtered_errors = all_errors
        if protocol:
            filtered_errors = [e for e in filtered_errors if e.get("protocol") == protocol]
        if category:
            filtered_errors = [e for e in filtered_errors if e.get("category") == category]
        if severity:
            filtered_errors = [e for e in filtered_errors if e.get("severity") == severity]
        
        # Apply final limit
        filtered_errors = filtered_errors[:limit]
        
        return ErrorHistoryResponse(
            errors=filtered_errors,
            total_count=len(filtered_errors),
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error history: {str(e)}")


@router.get("/categories")
async def get_error_categories():
    """
    Get information about all error categories
    
    Returns detailed information about all supported error categories
    including their descriptions and associated protocols.
    """
    try:
        categories = []
        
        for category in ErrorCategory:
            category_info = _get_category_info(category)
            categories.append(ErrorCategoryInfo(
                category=category.value,
                description=category_info["description"],
                severity=category_info["severity"],
                protocols=category_info["protocols"]
            ))
        
        return {
            "categories": categories,
            "total_count": len(categories)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error categories: {str(e)}")


@router.get("/protocols")
async def get_protocol_info():
    """
    Get information about all supported protocols
    
    Returns detailed information about all supported protocols
    and their error handling capabilities.
    """
    try:
        protocols = []
        
        for protocol in ProtocolType:
            protocol_info = _get_protocol_info(protocol)
            protocols.append(ProtocolInfo(
                protocol=protocol.value,
                description=protocol_info["description"],
                error_categories=protocol_info["error_categories"]
            ))
        
        return {
            "protocols": protocols,
            "total_count": len(protocols)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get protocol info: {str(e)}")


@router.get("/severity-levels")
async def get_severity_levels():
    """
    Get information about error severity levels
    
    Returns information about all supported severity levels
    and their characteristics.
    """
    try:
        severity_levels = []
        
        for severity in ErrorSeverity:
            severity_info = _get_severity_info(severity)
            severity_levels.append({
                "level": severity.value,
                "description": severity_info["description"],
                "http_status_range": severity_info["http_status_range"],
                "requires_immediate_attention": severity_info["requires_immediate_attention"]
            })
        
        return {
            "severity_levels": severity_levels,
            "total_count": len(severity_levels)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get severity levels: {str(e)}")


@router.get("/health")
async def error_handler_health_check():
    """
    Health check endpoint for unified error handling service
    
    Returns the health status of the unified error handling system.
    """
    try:
        handler = get_unified_error_handler()
        stats = handler.get_error_statistics()
        
        # Check if error rates are within acceptable limits
        total_errors = stats["total_errors"]
        critical_errors = stats["severity_distribution"].get("critical", 0)
        
        health_status = "healthy"
        if critical_errors > 10:  # Threshold for critical errors
            health_status = "degraded"
        if critical_errors > 50:
            health_status = "unhealthy"
        
        return {
            "status": health_status,
            "service": "unified-error-handler",
            "total_errors": total_errors,
            "critical_errors": critical_errors,
            "supported_protocols": len(ProtocolType),
            "supported_categories": len(ErrorCategory),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "unified-error-handler",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _get_category_info(category: ErrorCategory) -> Dict[str, Any]:
    """Get detailed information about an error category"""
    category_info = {
        ErrorCategory.AUTHENTICATION_FAILED: {
            "description": "Authentication credentials are invalid or expired",
            "severity": "high",
            "protocols": ["a2a", "ap2", "mcp"]
        },
        ErrorCategory.AUTHORIZATION_DENIED: {
            "description": "User lacks required permissions for the operation",
            "severity": "high",
            "protocols": ["a2a", "ap2", "mcp"]
        },
        ErrorCategory.INVALID_INPUT: {
            "description": "Input data does not meet validation requirements",
            "severity": "medium",
            "protocols": ["a2a", "ap2", "mcp"]
        },
        ErrorCategory.AGENT_NOT_FOUND: {
            "description": "Requested agent could not be found or is unavailable",
            "severity": "medium",
            "protocols": ["a2a"]
        },
        ErrorCategory.TASK_EXECUTION_FAILED: {
            "description": "Task execution encountered an error",
            "severity": "high",
            "protocols": ["a2a"]
        },
        ErrorCategory.PAYMENT_FAILED: {
            "description": "Payment processing failed",
            "severity": "high",
            "protocols": ["ap2"]
        },
        ErrorCategory.MANDATE_INVALID: {
            "description": "Payment mandate is invalid or expired",
            "severity": "high",
            "protocols": ["ap2"]
        },
        ErrorCategory.WEBHOOK_SIGNATURE_INVALID: {
            "description": "Webhook signature verification failed",
            "severity": "critical",
            "protocols": ["ap2"]
        },
        ErrorCategory.RESOURCE_NOT_FOUND: {
            "description": "Requested resource could not be found",
            "severity": "medium",
            "protocols": ["mcp"]
        },
        ErrorCategory.TOOL_EXECUTION_FAILED: {
            "description": "Tool execution encountered an error",
            "severity": "high",
            "protocols": ["mcp"]
        },
        ErrorCategory.SSE_CONNECTION_FAILED: {
            "description": "Server-Sent Events connection failed",
            "severity": "medium",
            "protocols": ["mcp"]
        },
        ErrorCategory.INTERNAL_SERVER_ERROR: {
            "description": "Internal server error occurred",
            "severity": "high",
            "protocols": ["a2a", "ap2", "mcp"]
        },
        ErrorCategory.SERVICE_UNAVAILABLE: {
            "description": "Required service is currently unavailable",
            "severity": "high",
            "protocols": ["a2a", "ap2", "mcp"]
        },
        ErrorCategory.RATE_LIMIT_EXCEEDED: {
            "description": "Request rate limit has been exceeded",
            "severity": "medium",
            "protocols": ["a2a", "ap2", "mcp"]
        },
        ErrorCategory.NETWORK_ERROR: {
            "description": "Network communication error occurred",
            "severity": "high",
            "protocols": ["a2a", "ap2", "mcp"]
        }
    }
    
    return category_info.get(category, {
        "description": "Unknown error category",
        "severity": "medium",
        "protocols": ["a2a", "ap2", "mcp"]
    })


def _get_protocol_info(protocol: ProtocolType) -> Dict[str, Any]:
    """Get detailed information about a protocol"""
    protocol_info = {
        ProtocolType.A2A: {
            "description": "Agent-to-Agent protocol for multi-agent coordination",
            "error_categories": [
                "agent_not_found", "task_execution_failed", "capability_not_supported",
                "agent_discovery_failed", "authentication_failed", "authorization_denied"
            ]
        },
        ProtocolType.AP2: {
            "description": "Agent Payments protocol for secure payment processing",
            "error_categories": [
                "payment_failed", "mandate_invalid", "insufficient_funds",
                "webhook_signature_invalid", "authentication_failed", "authorization_denied"
            ]
        },
        ProtocolType.MCP: {
            "description": "Model Context Protocol for resource and tool access",
            "error_categories": [
                "resource_not_found", "tool_execution_failed", "prompt_rendering_failed",
                "sse_connection_failed", "authentication_failed", "authorization_denied"
            ]
        },
        ProtocolType.CROSS_PROTOCOL: {
            "description": "Cross-protocol integration and coordination",
            "error_categories": [
                "authentication_failed", "authorization_denied", "invalid_input",
                "internal_server_error", "service_unavailable", "network_error"
            ]
        }
    }
    
    return protocol_info.get(protocol, {
        "description": "Unknown protocol",
        "error_categories": []
    })


def _get_severity_info(severity: ErrorSeverity) -> Dict[str, Any]:
    """Get detailed information about a severity level"""
    severity_info = {
        ErrorSeverity.LOW: {
            "description": "Minor issue that doesn't affect core functionality",
            "http_status_range": "400-499",
            "requires_immediate_attention": False
        },
        ErrorSeverity.MEDIUM: {
            "description": "Moderate issue that may affect user experience",
            "http_status_range": "400-499",
            "requires_immediate_attention": False
        },
        ErrorSeverity.HIGH: {
            "description": "Serious issue that affects core functionality",
            "http_status_range": "500-599",
            "requires_immediate_attention": True
        },
        ErrorSeverity.CRITICAL: {
            "description": "Critical issue that requires immediate attention",
            "http_status_range": "500-599",
            "requires_immediate_attention": True
        }
    }
    
    return severity_info.get(severity, {
        "description": "Unknown severity level",
        "http_status_range": "500-599",
        "requires_immediate_attention": True
    })
