"""
Workflow Event Bus - Observer Pattern Implementation
Manages event-driven architecture for workflow status updates and notifications
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class WorkflowEventType(Enum):
    """Types of workflow events"""
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    MANDATE_CREATED = "mandate_created"
    MANDATE_REVOKED = "mandate_revoked"
    MANDATE_EXPIRED = "mandate_expired"
    A2A_TASK_STARTED = "a2a_task_started"
    A2A_TASK_COMPLETED = "a2a_task_completed"
    A2A_TASK_FAILED = "a2a_task_failed"
    BUSINESS_REGISTERED = "business_registered"
    BUSINESS_STATUS_CHANGED = "business_status_changed"


@dataclass
class WorkflowEvent:
    """Workflow event data structure"""
    event_type: WorkflowEventType
    workflow_id: str
    business_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowEventListener(ABC):
    """Abstract base class for workflow event listeners"""
    
    @abstractmethod
    async def handle_event(self, event: WorkflowEvent) -> None:
        """Handle a workflow event"""
        pass
    
    @abstractmethod
    def get_supported_events(self) -> List[WorkflowEventType]:
        """Get list of event types this listener supports"""
        pass


class WorkflowEventBus:
    """
    Event bus for workflow events using Observer pattern.
    
    This class manages event subscriptions and notifications,
    allowing components to react to workflow state changes.
    """
    
    def __init__(self):
        self._listeners: Dict[WorkflowEventType, List[WorkflowEventListener]] = {}
        self._event_history: List[WorkflowEvent] = []
        self._max_history_size = 1000
        self._lock = asyncio.Lock()
    
    def subscribe(self, event_type: WorkflowEventType, listener: WorkflowEventListener) -> None:
        """
        Subscribe a listener to a specific event type.
        
        Args:
            event_type: The type of event to listen for
            listener: The listener to notify when events occur
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
            logger.info(f"Subscribed listener {listener.__class__.__name__} to {event_type.value}")
    
    def unsubscribe(self, event_type: WorkflowEventType, listener: WorkflowEventListener) -> None:
        """
        Unsubscribe a listener from a specific event type.
        
        Args:
            event_type: The type of event to stop listening for
            listener: The listener to remove
        """
        if event_type in self._listeners and listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
            logger.info(f"Unsubscribed listener {listener.__class__.__name__} from {event_type.value}")
    
    async def publish(self, event: WorkflowEvent) -> None:
        """
        Publish an event to all subscribed listeners.
        
        Args:
            event: The event to publish
        """
        async with self._lock:
            # Add to event history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history_size:
                self._event_history.pop(0)
            
            # Notify listeners
            listeners = self._listeners.get(event.event_type, [])
            if not listeners:
                logger.debug(f"No listeners for event type {event.event_type.value}")
                return
            
            # Notify all listeners concurrently
            tasks = []
            for listener in listeners:
                if event.event_type in listener.get_supported_events():
                    tasks.append(self._notify_listener(listener, event))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(f"Published event {event.event_type.value} to {len(tasks)} listeners")
    
    async def _notify_listener(self, listener: WorkflowEventListener, event: WorkflowEvent) -> None:
        """Notify a single listener of an event"""
        try:
            await listener.handle_event(event)
        except Exception as e:
            logger.error(f"Error notifying listener {listener.__class__.__name__}: {e}")
    
    def get_event_history(self, event_type: Optional[WorkflowEventType] = None, limit: int = 100) -> List[WorkflowEvent]:
        """
        Get recent event history.
        
        Args:
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        history = self._event_history.copy()
        
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        return history[-limit:] if limit > 0 else history
    
    def get_listener_count(self, event_type: WorkflowEventType) -> int:
        """Get the number of listeners for a specific event type"""
        return len(self._listeners.get(event_type, []))
    
    def get_subscribed_events(self) -> List[WorkflowEventType]:
        """Get all event types that have listeners"""
        return list(self._listeners.keys())


# Concrete event listeners for common use cases

class PaymentNotificationListener(WorkflowEventListener):
    """Listener for payment-related events"""
    
    def __init__(self, notification_service: Any):
        self.notification_service = notification_service
    
    async def handle_event(self, event: WorkflowEvent) -> None:
        """Handle payment events by sending notifications"""
        if event.event_type == WorkflowEventType.PAYMENT_COMPLETED:
            await self.notification_service.send_payment_success_notification(
                event.user_id, event.workflow_id, event.data.get('amount', 0)
            )
        elif event.event_type == WorkflowEventType.PAYMENT_FAILED:
            await self.notification_service.send_payment_failure_notification(
                event.user_id, event.workflow_id, event.data.get('error_message', 'Unknown error')
            )
    
    def get_supported_events(self) -> List[WorkflowEventType]:
        return [WorkflowEventType.PAYMENT_COMPLETED, WorkflowEventType.PAYMENT_FAILED]


class AuditLogListener(WorkflowEventListener):
    """Listener for audit logging of all workflow events"""
    
    def __init__(self, audit_logger: Any):
        self.audit_logger = audit_logger
    
    async def handle_event(self, event: WorkflowEvent) -> None:
        """Log all workflow events for audit purposes"""
        await self.audit_logger.log_workflow_event(
            event_type=event.event_type.value,
            workflow_id=event.workflow_id,
            business_id=event.business_id,
            user_id=event.user_id,
            timestamp=event.timestamp,
            data=event.data
        )
    
    def get_supported_events(self) -> List[WorkflowEventType]:
        return list(WorkflowEventType)  # Support all event types


class MetricsListener(WorkflowEventListener):
    """Listener for workflow metrics collection"""
    
    def __init__(self, metrics_collector: Any):
        self.metrics_collector = metrics_collector
    
    async def handle_event(self, event: WorkflowEvent) -> None:
        """Collect metrics from workflow events"""
        await self.metrics_collector.record_workflow_event(
            event_type=event.event_type.value,
            business_id=event.business_id,
            timestamp=event.timestamp
        )
    
    def get_supported_events(self) -> List[WorkflowEventType]:
        return list(WorkflowEventType)  # Support all event types


# Global event bus instance
_workflow_event_bus: Optional[WorkflowEventBus] = None


def get_workflow_event_bus() -> WorkflowEventBus:
    """Get the global workflow event bus instance"""
    global _workflow_event_bus
    if _workflow_event_bus is None:
        _workflow_event_bus = WorkflowEventBus()
    return _workflow_event_bus


async def publish_workflow_event(
    event_type: WorkflowEventType,
    workflow_id: str,
    business_id: Optional[str] = None,
    user_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Convenience function to publish workflow events.
    
    Args:
        event_type: Type of event
        workflow_id: ID of the workflow
        business_id: ID of the business (optional)
        user_id: ID of the user (optional)
        data: Event data (optional)
        metadata: Additional metadata (optional)
    """
    event = WorkflowEvent(
        event_type=event_type,
        workflow_id=workflow_id,
        business_id=business_id,
        user_id=user_id,
        data=data or {},
        metadata=metadata or {}
    )
    
    event_bus = get_workflow_event_bus()
    await event_bus.publish(event)
