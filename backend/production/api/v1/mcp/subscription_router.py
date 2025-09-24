"""
MCP Subscription Router - Implementation
FastAPI router for MCP subscription management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ...core.mcp_subscription_manager import (
    MCPSubscriptionManager,
    MCPSubscription,
    SubscriptionType,
    SubscriptionStatus,
    SubscriptionFilter,
    NotificationEvent,
    get_subscription_manager
)
from ...core.mcp_authentication_service import AuthenticationService, AuthContext
from ...core.mcp_error_handler import MCPErrorHandler, ValidationError
from ...core.mcp_input_validation import MCPInputValidator

router = APIRouter(prefix="/mcp/subscriptions", tags=["MCP Subscriptions"])


class SubscriptionFilterRequest(BaseModel):
    """Request model for subscription filters"""
    resource_uris: Optional[List[str]] = Field(None, description="Specific resource URIs to monitor")
    resource_types: Optional[List[str]] = Field(None, description="Resource types to monitor")
    tool_names: Optional[List[str]] = Field(None, description="Tool names to monitor")
    prompt_names: Optional[List[str]] = Field(None, description="Prompt names to monitor")
    event_types: Optional[List[str]] = Field(None, description="Event types to monitor")
    metadata_filters: Dict[str, Any] = Field(default_factory=dict, description="Metadata filters")


class CreateSubscriptionRequest(BaseModel):
    """Request model for creating subscriptions"""
    subscription_type: str = Field(..., description="Type of subscription")
    filter_criteria: Optional[SubscriptionFilterRequest] = Field(None, description="Filter criteria")
    callback_url: Optional[str] = Field(None, description="Callback URL for notifications")
    expiry_hours: Optional[int] = Field(None, ge=1, le=8760, description="Subscription expiry in hours")


class SubscriptionResponse(BaseModel):
    """Response model for subscription operations"""
    subscription_id: str = Field(..., description="Subscription ID")
    client_id: str = Field(..., description="Client ID")
    subscription_type: str = Field(..., description="Subscription type")
    status: str = Field(..., description="Subscription status")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiry timestamp")
    notification_count: int = Field(..., description="Number of notifications sent")
    error_count: int = Field(..., description="Number of notification errors")


class SubscriptionListResponse(BaseModel):
    """Response model for subscription lists"""
    subscriptions: List[SubscriptionResponse] = Field(..., description="List of subscriptions")
    total_count: int = Field(..., description="Total number of subscriptions")


class SubscriptionStatisticsResponse(BaseModel):
    """Response model for subscription statistics"""
    total_subscriptions: int = Field(..., description="Total subscriptions")
    active_subscriptions: int = Field(..., description="Active subscriptions")
    subscriptions_by_type: Dict[str, int] = Field(..., description="Subscriptions by type")
    subscriptions_by_client: Dict[str, int] = Field(..., description="Subscriptions by client")
    total_clients: int = Field(..., description="Total clients with subscriptions")
    notification_callbacks: int = Field(..., description="Number of notification callbacks")


@router.post("/create", response_model=SubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    client_id: str = Query(..., description="Client ID for the subscription"),
    manager: MCPSubscriptionManager = Depends(get_subscription_manager)
):
    """
    Create a new MCP subscription
    
    Creates a subscription for real-time notifications based on the specified
    subscription type and filter criteria.
    """
    try:
        # Validate subscription type
        try:
            subscription_type = SubscriptionType(request.subscription_type)
        except ValueError:
            raise ValidationError(
                f"Invalid subscription type: {request.subscription_type}",
                field="subscription_type",
                details={"valid_types": [t.value for t in SubscriptionType]}
            )
        
        # Create filter criteria
        filter_criteria = None
        if request.filter_criteria:
            filter_criteria = SubscriptionFilter(
                resource_uris=request.filter_criteria.resource_uris,
                resource_types=request.filter_criteria.resource_types,
                tool_names=request.filter_criteria.tool_names,
                prompt_names=request.filter_criteria.prompt_names,
                event_types=request.filter_criteria.event_types,
                metadata_filters=request.filter_criteria.metadata_filters
            )
        
        # Create subscription
        subscription = await manager.create_subscription(
            client_id=client_id,
            subscription_type=subscription_type,
            filter_criteria=filter_criteria,
            callback_url=request.callback_url,
            expiry_hours=request.expiry_hours
        )
        
        return SubscriptionResponse(
            subscription_id=subscription.subscription_id,
            client_id=subscription.client_id,
            subscription_type=subscription.subscription_type.value,
            status=subscription.status.value,
            created_at=subscription.created_at,
            expires_at=subscription.expires_at,
            notification_count=subscription.notification_count,
            error_count=subscription.error_count
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")


@router.get("/list", response_model=SubscriptionListResponse)
async def list_subscriptions(
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    subscription_type: Optional[str] = Query(None, description="Filter by subscription type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    manager: MCPSubscriptionManager = Depends(get_subscription_manager)
):
    """
    List subscriptions with optional filtering
    
    Returns a list of subscriptions with optional filters for client ID,
    subscription type, and status.
    """
    try:
        # Validate filters
        if subscription_type:
            try:
                SubscriptionType(subscription_type)
            except ValueError:
                raise ValidationError(
                    f"Invalid subscription type: {subscription_type}",
                    field="subscription_type",
                    details={"valid_types": [t.value for t in SubscriptionType]}
                )
        
        if status:
            try:
                SubscriptionStatus(status)
            except ValueError:
                raise ValidationError(
                    f"Invalid status: {status}",
                    field="status",
                    details={"valid_statuses": [s.value for s in SubscriptionStatus]}
                )
        
        # Get subscriptions
        if client_id:
            subscriptions = await manager.get_client_subscriptions(client_id)
        elif subscription_type:
            subscriptions = await manager.get_subscriptions_by_type(SubscriptionType(subscription_type))
        else:
            # Get all subscriptions (this would need to be implemented in the manager)
            subscriptions = []
            for sub_id in manager._subscriptions.keys():
                sub = await manager.get_subscription(sub_id)
                if sub:
                    subscriptions.append(sub)
        
        # Apply status filter
        if status:
            subscriptions = [s for s in subscriptions if s.status.value == status]
        
        # Convert to response format
        subscription_responses = []
        for subscription in subscriptions:
            subscription_responses.append(SubscriptionResponse(
                subscription_id=subscription.subscription_id,
                client_id=subscription.client_id,
                subscription_type=subscription.subscription_type.value,
                status=subscription.status.value,
                created_at=subscription.created_at,
                expires_at=subscription.expires_at,
                notification_count=subscription.notification_count,
                error_count=subscription.error_count
            ))
        
        return SubscriptionListResponse(
            subscriptions=subscription_responses,
            total_count=len(subscription_responses)
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list subscriptions: {str(e)}")


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    manager: MCPSubscriptionManager = Depends(get_subscription_manager)
):
    """
    Get subscription details
    
    Returns detailed information about a specific subscription.
    """
    try:
        subscription = await manager.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")
        
        return SubscriptionResponse(
            subscription_id=subscription.subscription_id,
            client_id=subscription.client_id,
            subscription_type=subscription.subscription_type.value,
            status=subscription.status.value,
            created_at=subscription.created_at,
            expires_at=subscription.expires_at,
            notification_count=subscription.notification_count,
            error_count=subscription.error_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subscription: {str(e)}")


@router.delete("/{subscription_id}")
async def cancel_subscription(
    subscription_id: str,
    manager: MCPSubscriptionManager = Depends(get_subscription_manager)
):
    """
    Cancel a subscription
    
    Cancels an active subscription and stops all notifications.
    """
    try:
        success = await manager.cancel_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")
        
        return {
            "success": True,
            "message": f"Subscription {subscription_id} cancelled",
            "subscription_id": subscription_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {str(e)}")


@router.post("/{subscription_id}/pause")
async def pause_subscription(
    subscription_id: str,
    manager: MCPSubscriptionManager = Depends(get_subscription_manager)
):
    """
    Pause a subscription
    
    Temporarily pauses a subscription without cancelling it.
    """
    try:
        success = await manager.pause_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")
        
        return {
            "success": True,
            "message": f"Subscription {subscription_id} paused",
            "subscription_id": subscription_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pause subscription: {str(e)}")


@router.post("/{subscription_id}/resume")
async def resume_subscription(
    subscription_id: str,
    manager: MCPSubscriptionManager = Depends(get_subscription_manager)
):
    """
    Resume a paused subscription
    
    Resumes a previously paused subscription.
    """
    try:
        success = await manager.resume_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Subscription not found or not paused: {subscription_id}")
        
        return {
            "success": True,
            "message": f"Subscription {subscription_id} resumed",
            "subscription_id": subscription_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume subscription: {str(e)}")


@router.get("/statistics", response_model=SubscriptionStatisticsResponse)
async def get_subscription_statistics(
    manager: MCPSubscriptionManager = Depends(get_subscription_manager)
):
    """
    Get subscription statistics
    
    Returns comprehensive statistics about subscriptions for monitoring purposes.
    """
    try:
        stats = manager.get_statistics()
        
        return SubscriptionStatisticsResponse(
            total_subscriptions=stats["total_subscriptions"],
            active_subscriptions=stats["active_subscriptions"],
            subscriptions_by_type=stats["subscriptions_by_type"],
            subscriptions_by_client=stats["subscriptions_by_client"],
            total_clients=stats["total_clients"],
            notification_callbacks=stats["notification_callbacks"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subscription statistics: {str(e)}")


@router.get("/types")
async def get_subscription_types():
    """
    Get available subscription types
    
    Returns information about all available subscription types.
    """
    try:
        types = []
        
        for subscription_type in SubscriptionType:
            type_info = _get_subscription_type_info(subscription_type)
            types.append({
                "type": subscription_type.value,
                "description": type_info["description"],
                "supported_filters": type_info["supported_filters"],
                "example_events": type_info["example_events"]
            })
        
        return {
            "subscription_types": types,
            "total_count": len(types)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subscription types: {str(e)}")


@router.post("/publish-event")
async def publish_custom_event(
    event_type: str,
    data: Dict[str, Any],
    subscription_type: str = "custom_event",
    metadata: Optional[Dict[str, Any]] = None,
    manager: MCPSubscriptionManager = Depends(get_subscription_manager)
):
    """
    Publish a custom event (admin endpoint)
    
    Allows administrators to publish custom events for testing or manual triggering.
    """
    try:
        # Validate subscription type
        try:
            sub_type = SubscriptionType(subscription_type)
        except ValueError:
            raise ValidationError(
                f"Invalid subscription type: {subscription_type}",
                field="subscription_type",
                details={"valid_types": [t.value for t in SubscriptionType]}
            )
        
        # Create and publish event
        event = NotificationEvent(
            event_type=event_type,
            subscription_type=sub_type,
            data=data,
            metadata=metadata or {}
        )
        
        await manager.publish_event(event)
        
        return {
            "success": True,
            "message": f"Event {event_type} published",
            "event_id": event.event_id,
            "subscription_type": subscription_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish event: {str(e)}")


@router.get("/health")
async def subscription_health_check():
    """
    Health check endpoint for subscription service
    
    Returns the health status of the subscription management system.
    """
    try:
        manager = get_subscription_manager()
        stats = manager.get_statistics()
        
        # Check if subscription service is healthy
        total_subs = stats["total_subscriptions"]
        active_subs = stats["active_subscriptions"]
        
        health_status = "healthy"
        if active_subs == 0 and total_subs > 0:
            health_status = "degraded"  # All subscriptions inactive
        
        return {
            "status": health_status,
            "service": "mcp-subscriptions",
            "total_subscriptions": total_subs,
            "active_subscriptions": active_subs,
            "total_clients": stats["total_clients"],
            "supported_types": len(SubscriptionType),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "mcp-subscriptions",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _get_subscription_type_info(subscription_type: SubscriptionType) -> Dict[str, Any]:
    """Get detailed information about a subscription type"""
    type_info = {
        SubscriptionType.RESOURCE_CHANGE: {
            "description": "Subscribe to changes in specific resources",
            "supported_filters": ["resource_uris", "resource_types", "metadata_filters"],
            "example_events": ["resource_created", "resource_updated", "resource_deleted"]
        },
        SubscriptionType.RESOURCE_LIST_CHANGE: {
            "description": "Subscribe to changes in resource lists",
            "supported_filters": ["resource_types", "metadata_filters"],
            "example_events": ["resource_list_updated", "new_resource_available"]
        },
        SubscriptionType.TOOL_EXECUTION: {
            "description": "Subscribe to tool execution events",
            "supported_filters": ["tool_names", "metadata_filters"],
            "example_events": ["tool_executed", "tool_failed", "tool_completed"]
        },
        SubscriptionType.PROMPT_UPDATE: {
            "description": "Subscribe to prompt template updates",
            "supported_filters": ["prompt_names", "metadata_filters"],
            "example_events": ["prompt_updated", "prompt_created", "prompt_deleted"]
        },
        SubscriptionType.SERVER_STATE: {
            "description": "Subscribe to server state changes",
            "supported_filters": ["event_types", "metadata_filters"],
            "example_events": ["server_started", "server_stopped", "configuration_changed"]
        },
        SubscriptionType.CUSTOM_EVENT: {
            "description": "Subscribe to custom events",
            "supported_filters": ["event_types", "metadata_filters"],
            "example_events": ["custom_event", "business_event", "integration_event"]
        }
    }
    
    return type_info.get(subscription_type, {
        "description": "Unknown subscription type",
        "supported_filters": [],
        "example_events": []
    })
