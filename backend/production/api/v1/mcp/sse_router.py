"""
MCP SSE Router - Implementation
FastAPI router for MCP Server-Sent Events endpoints
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from ...core.mcp_sse_transport import (
    MCPSSEHandler, 
    MCPSSEIntegration, 
    get_sse_transport_manager,
    MCPSSEEvent
)
from ...core.mcp_authentication_service import AuthenticationService, AuthContext
from ...core.mcp_error_handler import MCPErrorHandler, ValidationError
from ...core.mcp_input_validation import MCPInputValidator

router = APIRouter(prefix="/mcp/sse", tags=["MCP SSE"])


def get_sse_handler() -> MCPSSEHandler:
    """Get SSE handler dependency"""
    transport_manager = get_sse_transport_manager()
    return MCPSSEHandler(transport_manager)


def get_sse_integration() -> MCPSSEIntegration:
    """Get SSE integration dependency"""
    transport_manager = get_sse_transport_manager()
    return MCPSSEIntegration(transport_manager)


@router.get("/connect")
async def connect_sse_stream(
    request: Request,
    subscriptions: Optional[str] = Query(None, description="Comma-separated list of subscription types"),
    sse_handler: MCPSSEHandler = Depends(get_sse_handler)
):
    """
    Connect to MCP Server-Sent Events stream
    
    This endpoint establishes a persistent SSE connection for real-time MCP protocol updates.
    Clients can subscribe to specific event types for targeted notifications.
    
    Subscription types:
    - resources: Resource updates and changes
    - tools: Tool execution results and status
    - prompts: Prompt template updates
    - a2a_tasks: A2A task coordination updates
    - ap2_payments: AP2 payment workflow updates
    """
    try:
        # Parse subscription types
        subscription_list = []
        if subscriptions:
            subscription_list = [s.strip() for s in subscriptions.split(",") if s.strip()]
        
        # Validate subscription types
        valid_subscriptions = {"resources", "tools", "prompts", "a2a_tasks", "ap2_payments"}
        for subscription in subscription_list:
            if subscription not in valid_subscriptions:
                raise ValidationError(
                    f"Invalid subscription type: {subscription}",
                    field="subscriptions",
                    details={"valid_types": list(valid_subscriptions)}
                )
        
        # Generate client ID
        client_id = str(uuid.uuid4())
        
        # Extract client information
        client_info = {
            "user_agent": request.headers.get("user-agent", ""),
            "remote_addr": request.client.host if request.client else "unknown",
            "subscriptions": subscription_list,
            "connected_at": datetime.now().isoformat()
        }
        
        # Establish SSE connection
        return await sse_handler.handle_sse_connection(
            request=request,
            client_id=client_id,
            subscriptions=subscription_list
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to establish SSE connection: {str(e)}")


@router.post("/subscribe")
async def subscribe_to_events(
    client_id: str,
    subscription_type: str,
    action: str = "subscribe",
    sse_handler: MCPSSEHandler = Depends(get_sse_handler)
):
    """
    Subscribe or unsubscribe to specific event types
    
    Actions:
    - subscribe: Subscribe to the specified event type
    - unsubscribe: Unsubscribe from the specified event type
    
    Event types:
    - resources: Resource updates and changes
    - tools: Tool execution results and status
    - prompts: Prompt template updates
    - a2a_tasks: A2A task coordination updates
    - ap2_payments: AP2 payment workflow updates
    """
    try:
        # Validate action
        if action not in {"subscribe", "unsubscribe"}:
            raise ValidationError(
                "Invalid action. Must be 'subscribe' or 'unsubscribe'",
                field="action"
            )
        
        # Validate subscription type
        valid_subscriptions = {"resources", "tools", "prompts", "a2a_tasks", "ap2_payments"}
        if subscription_type not in valid_subscriptions:
            raise ValidationError(
                f"Invalid subscription type: {subscription_type}",
                field="subscription_type",
                details={"valid_types": list(valid_subscriptions)}
            )
        
        # Handle subscription request
        result = await sse_handler.handle_subscription_request(
            client_id=client_id,
            subscription_type=subscription_type,
            action=action
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subscription request failed: {str(e)}")


@router.get("/clients")
async def get_active_clients():
    """
    Get information about active SSE clients
    
    Returns the count and basic information about currently connected SSE clients.
    Useful for monitoring and debugging.
    """
    try:
        transport_manager = get_sse_transport_manager()
        
        return {
            "active_clients": await transport_manager.get_active_clients_count(),
            "timestamp": datetime.now().isoformat(),
            "transport_status": "active"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get client information: {str(e)}")


@router.post("/broadcast")
async def broadcast_event(
    event_type: str,
    data: Dict[str, Any],
    subscription_type: Optional[str] = None,
    sse_integration: MCPSSEIntegration = Depends(get_sse_integration)
):
    """
    Broadcast event to all subscribed clients (admin endpoint)
    
    This endpoint allows administrators to broadcast custom events to all
    connected SSE clients or clients subscribed to specific event types.
    
    Event types should follow MCP protocol conventions:
    - resource_updated: Resource changes
    - tool_executed: Tool execution results
    - prompt_updated: Prompt template changes
    - a2a_task_update: A2A task status changes
    - ap2_payment_update: AP2 payment status changes
    """
    try:
        # Validate event type
        if not event_type or not event_type.strip():
            raise ValidationError("Event type cannot be empty", field="event_type")
        
        # Create and broadcast event
        event = MCPSSEEvent(
            event_type=event_type,
            data=data,
            id=str(uuid.uuid4())
        )
        
        transport_manager = get_sse_transport_manager()
        await transport_manager.broadcast_event(event, subscription_type)
        
        return {
            "success": True,
            "message": f"Event '{event_type}' broadcasted successfully",
            "event_id": event.id,
            "subscription_filter": subscription_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to broadcast event: {str(e)}")


@router.get("/status")
async def get_sse_status():
    """
    Get SSE transport status and health information
    
    Returns detailed status information about the SSE transport system,
    including client counts, connection health, and transport statistics.
    """
    try:
        transport_manager = get_sse_transport_manager()
        
        return {
            "status": "active",
            "active_clients": await transport_manager.get_active_clients_count(),
            "transport_type": "sse",
            "protocol_version": "2025-06-18",
            "supported_subscriptions": [
                "resources",
                "tools", 
                "prompts",
                "a2a_tasks",
                "ap2_payments"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SSE status: {str(e)}")


# Integration endpoints for other protocols

@router.post("/notify/resource-update")
async def notify_resource_update(
    resource_uri: str,
    update_data: Dict[str, Any],
    sse_integration: MCPSSEIntegration = Depends(get_sse_integration)
):
    """Notify clients of resource updates"""
    try:
        await sse_integration.notify_resource_update(resource_uri, update_data)
        
        return {
            "success": True,
            "message": f"Resource update notification sent for {resource_uri}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to notify resource update: {str(e)}")


@router.post("/notify/tool-execution")
async def notify_tool_execution(
    tool_name: str,
    execution_result: Dict[str, Any],
    sse_integration: MCPSSEIntegration = Depends(get_sse_integration)
):
    """Notify clients of tool execution results"""
    try:
        await sse_integration.notify_tool_execution(tool_name, execution_result)
        
        return {
            "success": True,
            "message": f"Tool execution notification sent for {tool_name}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to notify tool execution: {str(e)}")


@router.post("/notify/a2a-task-update")
async def notify_a2a_task_update(
    task_id: str,
    task_status: str,
    task_data: Dict[str, Any],
    sse_integration: MCPSSEIntegration = Depends(get_sse_integration)
):
    """Notify clients of A2A task updates"""
    try:
        await sse_integration.notify_a2a_task_update(task_id, task_status, task_data)
        
        return {
            "success": True,
            "message": f"A2A task update notification sent for {task_id}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to notify A2A task update: {str(e)}")


@router.post("/notify/ap2-payment-update")
async def notify_ap2_payment_update(
    payment_id: str,
    payment_status: str,
    payment_data: Dict[str, Any],
    sse_integration: MCPSSEIntegration = Depends(get_sse_integration)
):
    """Notify clients of AP2 payment updates"""
    try:
        await sse_integration.notify_ap2_payment_update(payment_id, payment_status, payment_data)
        
        return {
            "success": True,
            "message": f"AP2 payment update notification sent for {payment_id}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to notify AP2 payment update: {str(e)}")
