"""
Payment Event Publisher - Implementation
Extracts event publishing logic from PaymentCoordinator to follow SRP
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..workflow_event_bus import publish_workflow_event, WorkflowEventType


class PaymentEventType(Enum):
    """Payment-specific event types"""
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_AUTHORIZED = "payment_authorized"
    PAYMENT_PROCESSING = "payment_processing"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_CANCELLED = "payment_cancelled"
    MANDATE_CREATED = "mandate_created"
    MANDATE_EXPIRED = "mandate_expired"
    MANDATE_REVOKED = "mandate_revoked"


@dataclass
class PaymentEventData:
    """Payment event data structure"""
    event_type: PaymentEventType
    workflow_id: str
    business_id: str
    user_id: str
    agent_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    payment_method: Optional[str] = None
    mandate_id: Optional[str] = None
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PaymentEventPublisher:
    """
    Publishes payment-related events to the workflow event bus.
    Follows Single Responsibility Principle by focusing only on event publishing.
    """
    
    def __init__(self):
        pass  # No dependencies needed - uses global event bus
    
    async def publish_payment_initiated(self, 
                                      workflow_id: str,
                                      business_id: str,
                                      user_id: str,
                                      agent_id: str,
                                      amount: float,
                                      currency: str,
                                      payment_method: str) -> None:
        """Publish payment initiated event"""
        await publish_workflow_event(
            event_type=WorkflowEventType.PAYMENT_INITIATED,
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "amount": amount,
                "currency": currency,
                "payment_method": payment_method,
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def publish_payment_authorized(self,
                                       workflow_id: str,
                                       business_id: str,
                                       user_id: str,
                                       mandate_id: str,
                                       amount: float,
                                       currency: str) -> None:
        """Publish payment authorized event"""
        await publish_workflow_event(
            event_type=WorkflowEventType.PAYMENT_INITIATED,  # Map to closest workflow event
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "mandate_id": mandate_id,
                "amount": amount,
                "currency": currency,
                "authorization_timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def publish_payment_processing(self,
                                       workflow_id: str,
                                       business_id: str,
                                       user_id: str,
                                       transaction_id: str,
                                       amount: float,
                                       currency: str) -> None:
        """Publish payment processing event"""
        await publish_workflow_event(
            event_type=WorkflowEventType.PAYMENT_INITIATED,  # Map to closest workflow event
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": currency,
                "processing_timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def publish_payment_completed(self,
                                      workflow_id: str,
                                      business_id: str,
                                      user_id: str,
                                      transaction_id: str,
                                      amount: float,
                                      currency: str,
                                      payment_method: str) -> None:
        """Publish payment completed event"""
        await publish_workflow_event(
            event_type=WorkflowEventType.PAYMENT_COMPLETED,
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": currency,
                "payment_method": payment_method,
                "completion_timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def publish_payment_failed(self,
                                   workflow_id: str,
                                   business_id: str,
                                   user_id: str,
                                   error_message: str,
                                   error_code: Optional[str] = None,
                                   transaction_id: Optional[str] = None) -> None:
        """Publish payment failed event"""
        await publish_workflow_event(
            event_type=WorkflowEventType.PAYMENT_FAILED,
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "error_message": error_message,
                "error_code": error_code,
                "transaction_id": transaction_id,
                "failure_timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def publish_mandate_created(self,
                                    workflow_id: str,
                                    business_id: str,
                                    user_id: str,
                                    mandate_id: str,
                                    mandate_type: str,
                                    amount: Optional[float] = None,
                                    currency: Optional[str] = None) -> None:
        """Publish mandate created event"""
        await publish_workflow_event(
            event_type=WorkflowEventType.MANDATE_CREATED,
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "mandate_id": mandate_id,
                "mandate_type": mandate_type,
                "amount": amount,
                "currency": currency,
                "creation_timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def publish_mandate_expired(self,
                                    workflow_id: str,
                                    business_id: str,
                                    user_id: str,
                                    mandate_id: str) -> None:
        """Publish mandate expired event"""
        await publish_workflow_event(
            event_type=WorkflowEventType.MANDATE_REVOKED,  # Map to closest workflow event
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "mandate_id": mandate_id,
                "expiry_timestamp": datetime.utcnow().isoformat(),
                "reason": "expired"
            }
        )
    
    async def publish_mandate_revoked(self,
                                    workflow_id: str,
                                    business_id: str,
                                    user_id: str,
                                    mandate_id: str,
                                    reason: str) -> None:
        """Publish mandate revoked event"""
        await publish_workflow_event(
            event_type=WorkflowEventType.MANDATE_REVOKED,
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "mandate_id": mandate_id,
                "revocation_timestamp": datetime.utcnow().isoformat(),
                "reason": reason
            }
        )
    
    async def publish_custom_payment_event(self,
                                         event_data: PaymentEventData) -> None:
        """Publish a custom payment event"""
        # Map payment event type to workflow event type
        workflow_event_type = self._map_payment_event_to_workflow_event(event_data.event_type)
        
        await publish_workflow_event(
            event_type=workflow_event_type,
            workflow_id=event_data.workflow_id,
            business_id=event_data.business_id,
            user_id=event_data.user_id,
            data={
                "payment_event_type": event_data.event_type.value,
                "agent_id": event_data.agent_id,
                "amount": event_data.amount,
                "currency": event_data.currency,
                "payment_method": event_data.payment_method,
                "mandate_id": event_data.mandate_id,
                "transaction_id": event_data.transaction_id,
                "error_message": event_data.error_message,
                "timestamp": datetime.utcnow().isoformat(),
                **event_data.metadata
            }
        )
    
    def _map_payment_event_to_workflow_event(self, payment_event_type: PaymentEventType) -> WorkflowEventType:
        """Map payment event type to workflow event type"""
        mapping = {
            PaymentEventType.PAYMENT_INITIATED: WorkflowEventType.PAYMENT_INITIATED,
            PaymentEventType.PAYMENT_AUTHORIZED: WorkflowEventType.PAYMENT_INITIATED,
            PaymentEventType.PAYMENT_PROCESSING: WorkflowEventType.PAYMENT_INITIATED,
            PaymentEventType.PAYMENT_COMPLETED: WorkflowEventType.PAYMENT_COMPLETED,
            PaymentEventType.PAYMENT_FAILED: WorkflowEventType.PAYMENT_FAILED,
            PaymentEventType.PAYMENT_CANCELLED: WorkflowEventType.PAYMENT_FAILED,
            PaymentEventType.MANDATE_CREATED: WorkflowEventType.MANDATE_CREATED,
            PaymentEventType.MANDATE_EXPIRED: WorkflowEventType.MANDATE_REVOKED,
            PaymentEventType.MANDATE_REVOKED: WorkflowEventType.MANDATE_REVOKED
        }
        
        return mapping.get(payment_event_type, WorkflowEventType.PAYMENT_INITIATED)
    
    async def publish_workflow_step_completed(self,
                                            workflow_id: str,
                                            business_id: str,
                                            user_id: str,
                                            step_name: str,
                                            step_data: Dict[str, Any]) -> None:
        """Publish workflow step completion event"""
        await publish_workflow_event(
            event_type=WorkflowEventType.TASK_UPDATED,
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "step_name": step_name,
                "step_data": step_data,
                "completion_timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def publish_workflow_step_failed(self,
                                         workflow_id: str,
                                         business_id: str,
                                         user_id: str,
                                         step_name: str,
                                         error_message: str,
                                         error_data: Dict[str, Any] = None) -> None:
        """Publish workflow step failure event"""
        if error_data is None:
            error_data = {}
        
        await publish_workflow_event(
            event_type=WorkflowEventType.TASK_FAILED,
            workflow_id=workflow_id,
            business_id=business_id,
            user_id=user_id,
            data={
                "step_name": step_name,
                "error_message": error_message,
                "failure_timestamp": datetime.utcnow().isoformat(),
                **error_data
            }
        )
