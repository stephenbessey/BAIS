"""
MCP Subscription Manager - Clean Code Implementation
Manages real-time subscriptions for MCP protocol following Clean Code principles
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Callable, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


class SubscriptionType(Enum):
    """Types of MCP subscriptions"""
    RESOURCE_CHANGE = "resource_change"
    RESOURCE_LIST_CHANGE = "resource_list_change"
    TOOL_EXECUTION = "tool_execution"
    PROMPT_UPDATE = "prompt_update"
    SERVER_STATE = "server_state"
    CUSTOM_EVENT = "custom_event"


class SubscriptionStatus(Enum):
    """Subscription status"""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class SubscriptionFilter:
    """Filter criteria for subscriptions"""
    resource_uris: Optional[List[str]] = None
    resource_types: Optional[List[str]] = None
    tool_names: Optional[List[str]] = None
    prompt_names: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    metadata_filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPSubscription:
    """MCP subscription following Clean Code principles"""
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str = ""
    subscription_type: SubscriptionType = SubscriptionType.RESOURCE_CHANGE
    filter_criteria: SubscriptionFilter = field(default_factory=SubscriptionFilter)
    callback_url: Optional[str] = None
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_notification: Optional[datetime] = None
    notification_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_active(self) -> bool:
        """Check if subscription is active"""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        
        return True
    
    def is_expired(self) -> bool:
        """Check if subscription has expired"""
        return self.expires_at and datetime.now() > self.expires_at
    
    def should_notify(self, event_data: Dict[str, Any]) -> bool:
        """Check if subscription should receive notification for event"""
        if not self.is_active():
            return False
        
        # Apply filter criteria
        return self._matches_filters(event_data)
    
    def _matches_filters(self, event_data: Dict[str, Any]) -> bool:
        """Check if event matches subscription filters"""
        filters = self.filter_criteria
        
        # Check resource URI filter
        if filters.resource_uris:
            event_uri = event_data.get("resource_uri")
            if event_uri and event_uri not in filters.resource_uris:
                return False
        
        # Check resource type filter
        if filters.resource_types:
            event_type = event_data.get("resource_type")
            if event_type and event_type not in filters.resource_types:
                return False
        
        # Check tool name filter
        if filters.tool_names:
            tool_name = event_data.get("tool_name")
            if tool_name and tool_name not in filters.tool_names:
                return False
        
        # Check prompt name filter
        if filters.prompt_names:
            prompt_name = event_data.get("prompt_name")
            if prompt_name and prompt_name not in filters.prompt_names:
                return False
        
        # Check event type filter
        if filters.event_types:
            event_type = event_data.get("event_type")
            if event_type and event_type not in filters.event_types:
                return False
        
        # Check metadata filters
        if filters.metadata_filters:
            event_metadata = event_data.get("metadata", {})
            for key, value in filters.metadata_filters.items():
                if event_metadata.get(key) != value:
                    return False
        
        return True


@dataclass
class NotificationEvent:
    """Notification event for subscriptions"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    subscription_type: SubscriptionType = SubscriptionType.CUSTOM_EVENT
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPSubscriptionManager:
    """Manages MCP subscriptions following Clean Code principles"""
    
    def __init__(self, max_subscriptions_per_client: int = None, default_expiry_hours: int = None):
        from .constants import MCPLimits
        self._max_subscriptions_per_client = max_subscriptions_per_client or MCPLimits.MAX_SUBSCRIPTIONS_PER_CLIENT
        self._default_expiry_hours = default_expiry_hours or MCPLimits.DEFAULT_SUBSCRIPTION_EXPIRY_HOURS
        self._subscriptions: Dict[str, MCPSubscription] = {}
        self._client_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._type_subscriptions: Dict[SubscriptionType, Set[str]] = defaultdict(set)
        self._notification_callbacks: List[Callable] = []
        self._cleanup_task: Optional[asyncio.Task] = None
        self._notification_queue: asyncio.Queue = asyncio.Queue()
    
    async def start(self):
        """Start the subscription manager"""
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_subscriptions())
        logger.info("MCP Subscription Manager started")
    
    async def stop(self):
        """Stop the subscription manager"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("MCP Subscription Manager stopped")
    
    async def create_subscription(
        self,
        client_id: str,
        subscription_type: SubscriptionType,
        filter_criteria: Optional[SubscriptionFilter] = None,
        callback_url: Optional[str] = None,
        expiry_hours: Optional[int] = None
    ) -> MCPSubscription:
        """Create a new MCP subscription"""
        try:
            # Check subscription limits
            client_subs = self._client_subscriptions.get(client_id, set())
            if len(client_subs) >= self._max_subscriptions_per_client:
                raise ValueError(f"Client {client_id} has reached maximum subscription limit")
            
            # Create subscription
            expires_at = None
            if expiry_hours:
                expires_at = datetime.now() + timedelta(hours=expiry_hours)
            elif self._default_expiry_hours:
                expires_at = datetime.now() + timedelta(hours=self._default_expiry_hours)
            
            subscription = MCPSubscription(
                client_id=client_id,
                subscription_type=subscription_type,
                filter_criteria=filter_criteria or SubscriptionFilter(),
                callback_url=callback_url,
                expires_at=expires_at
            )
            
            # Store subscription
            self._subscriptions[subscription.subscription_id] = subscription
            self._client_subscriptions[client_id].add(subscription.subscription_id)
            self._type_subscriptions[subscription_type].add(subscription.subscription_id)
            
            logger.info(f"Created subscription {subscription.subscription_id} for client {client_id}")
            
            return subscription
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            raise
    
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription"""
        try:
            subscription = self._subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            # Update status
            subscription.status = SubscriptionStatus.CANCELLED
            
            # Remove from indexes
            self._client_subscriptions[subscription.client_id].discard(subscription_id)
            self._type_subscriptions[subscription.subscription_type].discard(subscription_id)
            
            logger.info(f"Cancelled subscription {subscription_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            return False
    
    async def pause_subscription(self, subscription_id: str) -> bool:
        """Pause a subscription"""
        try:
            subscription = self._subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            subscription.status = SubscriptionStatus.PAUSED
            logger.info(f"Paused subscription {subscription_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause subscription {subscription_id}: {e}")
            return False
    
    async def resume_subscription(self, subscription_id: str) -> bool:
        """Resume a paused subscription"""
        try:
            subscription = self._subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            if subscription.status == SubscriptionStatus.PAUSED:
                subscription.status = SubscriptionStatus.ACTIVE
                logger.info(f"Resumed subscription {subscription_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to resume subscription {subscription_id}: {e}")
            return False
    
    async def get_subscription(self, subscription_id: str) -> Optional[MCPSubscription]:
        """Get subscription by ID"""
        return self._subscriptions.get(subscription_id)
    
    async def get_client_subscriptions(self, client_id: str) -> List[MCPSubscription]:
        """Get all subscriptions for a client"""
        subscription_ids = self._client_subscriptions.get(client_id, set())
        return [self._subscriptions[sid] for sid in subscription_ids if sid in self._subscriptions]
    
    async def get_subscriptions_by_type(self, subscription_type: SubscriptionType) -> List[MCPSubscription]:
        """Get all subscriptions of a specific type"""
        subscription_ids = self._type_subscriptions.get(subscription_type, set())
        return [self._subscriptions[sid] for sid in subscription_ids if sid in self._subscriptions]
    
    async def publish_event(self, event: NotificationEvent):
        """Publish an event to relevant subscriptions"""
        try:
            # Find matching subscriptions
            matching_subscriptions = []
            
            # Get subscriptions by type
            type_subs = await self.get_subscriptions_by_type(event.subscription_type)
            
            for subscription in type_subs:
                if subscription.should_notify(event.data):
                    matching_subscriptions.append(subscription)
            
            # Notify matching subscriptions
            for subscription in matching_subscriptions:
                await self._notify_subscription(subscription, event)
            
            logger.debug(f"Published event {event.event_id} to {len(matching_subscriptions)} subscriptions")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
    
    async def _notify_subscription(self, subscription: MCPSubscription, event: NotificationEvent):
        """Notify a specific subscription"""
        try:
            # Update subscription stats
            subscription.last_notification = datetime.now()
            subscription.notification_count += 1
            
            # Create notification payload
            notification = {
                "subscription_id": subscription.subscription_id,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "metadata": event.metadata
            }
            
            # Call notification callbacks
            for callback in self._notification_callbacks:
                try:
                    await callback(subscription, notification)
                except Exception as e:
                    logger.error(f"Error in notification callback: {e}")
            
            # If callback URL is provided, make HTTP request
            if subscription.callback_url:
                await self._send_http_notification(subscription, notification)
            
        except Exception as e:
            subscription.error_count += 1
            logger.error(f"Failed to notify subscription {subscription.subscription_id}: {e}")
    
    async def _send_http_notification(self, subscription: MCPSubscription, notification: Dict[str, Any]):
        """Send HTTP notification to callback URL"""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    subscription.callback_url,
                    json=notification,
                    timeout=10.0
                )
                response.raise_for_status()
                
                logger.debug(f"HTTP notification sent to {subscription.callback_url}")
                
        except Exception as e:
            subscription.error_count += 1
            logger.error(f"Failed to send HTTP notification to {subscription.callback_url}: {e}")
    
    def add_notification_callback(self, callback: Callable):
        """Add a notification callback function"""
        self._notification_callbacks.append(callback)
    
    def remove_notification_callback(self, callback: Callable):
        """Remove a notification callback function"""
        if callback in self._notification_callbacks:
            self._notification_callbacks.remove(callback)
    
    async def _cleanup_expired_subscriptions(self):
        """Background task to cleanup expired subscriptions"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                expired_subscriptions = []
                for subscription_id, subscription in self._subscriptions.items():
                    if subscription.is_expired():
                        expired_subscriptions.append(subscription_id)
                
                for subscription_id in expired_subscriptions:
                    subscription = self._subscriptions[subscription_id]
                    subscription.status = SubscriptionStatus.EXPIRED
                    
                    # Remove from indexes
                    self._client_subscriptions[subscription.client_id].discard(subscription_id)
                    self._type_subscriptions[subscription.subscription_type].discard(subscription_id)
                    
                    logger.info(f"Expired subscription {subscription_id}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in subscription cleanup: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get subscription manager statistics"""
        active_subscriptions = sum(1 for sub in self._subscriptions.values() if sub.is_active())
        total_subscriptions = len(self._subscriptions)
        
        type_counts = {}
        for sub_type in SubscriptionType:
            type_counts[sub_type.value] = len(self._type_subscriptions[sub_type])
        
        client_counts = {}
        for client_id, subscription_ids in self._client_subscriptions.items():
            client_counts[client_id] = len(subscription_ids)
        
        return {
            "total_subscriptions": total_subscriptions,
            "active_subscriptions": active_subscriptions,
            "subscriptions_by_type": type_counts,
            "subscriptions_by_client": client_counts,
            "total_clients": len(self._client_subscriptions),
            "notification_callbacks": len(self._notification_callbacks)
        }


# Global subscription manager instance
_subscription_manager: Optional[MCPSubscriptionManager] = None


def get_subscription_manager() -> MCPSubscriptionManager:
    """Get global subscription manager instance"""
    global _subscription_manager
    if _subscription_manager is None:
        _subscription_manager = MCPSubscriptionManager()
    return _subscription_manager


# Convenience functions for common subscription operations

async def subscribe_to_resource_changes(
    client_id: str,
    resource_uris: Optional[List[str]] = None,
    callback_url: Optional[str] = None
) -> MCPSubscription:
    """Subscribe to resource changes"""
    manager = get_subscription_manager()
    filter_criteria = SubscriptionFilter(resource_uris=resource_uris)
    return await manager.create_subscription(
        client_id=client_id,
        subscription_type=SubscriptionType.RESOURCE_CHANGE,
        filter_criteria=filter_criteria,
        callback_url=callback_url
    )


async def subscribe_to_tool_executions(
    client_id: str,
    tool_names: Optional[List[str]] = None,
    callback_url: Optional[str] = None
) -> MCPSubscription:
    """Subscribe to tool execution events"""
    manager = get_subscription_manager()
    filter_criteria = SubscriptionFilter(tool_names=tool_names)
    return await manager.create_subscription(
        client_id=client_id,
        subscription_type=SubscriptionType.TOOL_EXECUTION,
        filter_criteria=filter_criteria,
        callback_url=callback_url
    )


async def subscribe_to_prompt_updates(
    client_id: str,
    prompt_names: Optional[List[str]] = None,
    callback_url: Optional[str] = None
) -> MCPSubscription:
    """Subscribe to prompt updates"""
    manager = get_subscription_manager()
    filter_criteria = SubscriptionFilter(prompt_names=prompt_names)
    return await manager.create_subscription(
        client_id=client_id,
        subscription_type=SubscriptionType.PROMPT_UPDATE,
        filter_criteria=filter_criteria,
        callback_url=callback_url
    )


async def publish_resource_change_event(
    resource_uri: str,
    change_type: str,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
):
    """Publish a resource change event"""
    manager = get_subscription_manager()
    event = NotificationEvent(
        event_type=change_type,
        subscription_type=SubscriptionType.RESOURCE_CHANGE,
        data={
            "resource_uri": resource_uri,
            "change_type": change_type,
            **data
        },
        metadata=metadata or {}
    )
    await manager.publish_event(event)


async def publish_tool_execution_event(
    tool_name: str,
    execution_result: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
):
    """Publish a tool execution event"""
    manager = get_subscription_manager()
    event = NotificationEvent(
        event_type="tool_executed",
        subscription_type=SubscriptionType.TOOL_EXECUTION,
        data={
            "tool_name": tool_name,
            "execution_result": execution_result
        },
        metadata=metadata or {}
    )
    await manager.publish_event(event)


if __name__ == "__main__":
    # Example usage
    async def main():
        manager = get_subscription_manager()
        await manager.start()
        
        # Create a subscription
        subscription = await subscribe_to_resource_changes(
            client_id="client_123",
            resource_uris=["availability://hotel-123"],
            callback_url="https://example.com/webhook"
        )
        
        print(f"Created subscription: {subscription.subscription_id}")
        
        # Publish an event
        await publish_resource_change_event(
            resource_uri="availability://hotel-123",
            change_type="updated",
            data={"available_rooms": 5, "price": 150.0}
        )
        
        # Get statistics
        stats = manager.get_statistics()
        print(f"Statistics: {stats}")
        
        await manager.stop()
    
    asyncio.run(main())
