from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import asyncio
from enum import Enum
import uuid
from datetime import datetime

from .ap2_client import AP2Client
from .models import PaymentWorkflow, PaymentStatus, BusinessIntent
from ..business_query_repository import BusinessQueryRepository
from ..exceptions import ValidationError, IntegrationError
from ..workflow_event_bus import publish_workflow_event, WorkflowEventType
from ..circuit_breaker import (
    get_circuit_breaker_manager, 
    CircuitBreakerConfig, 
    AP2_PAYMENT_CONFIG, 
    AP2_MANDATE_CONFIG,
    CircuitBreakerOpenException,
    CircuitBreakerTimeoutException
)


class PaymentWorkflowStep(Enum):
    """Payment workflow steps"""
    INTENT_MANDATE = "intent_mandate"
    CART_MANDATE = "cart_mandate"
    PAYMENT_EXECUTION = "payment_execution"
    CONFIRMATION = "confirmation"


@dataclass
class PaymentCoordinationRequest:
    """Request for payment coordination - Parameter Object pattern"""
    user_id: str
    business_id: str
    agent_id: str
    intent_description: str
    cart_items: List[Dict[str, Any]]
    payment_constraints: Dict[str, Any]
    payment_method_id: str


class PaymentCoordinator:
    """
    Coordinates complex payment workflows using AP2 protocol with circuit breaker protection
    Implements Command pattern for workflow management
    """
    
    def __init__(
        self, 
        ap2_client: AP2Client, 
        business_repository: BusinessQueryRepository
    ):
        self._ap2_client = ap2_client
        self._business_repository = business_repository
        self._active_workflows: Dict[str, PaymentWorkflow] = {}
        
        # Initialize circuit breakers for different AP2 operations
        self._circuit_manager = get_circuit_breaker_manager()
        self._mandate_circuit = self._circuit_manager.get_or_create_circuit(
            "ap2_mandate_operations", AP2_MANDATE_CONFIG
        )
        self._payment_circuit = self._circuit_manager.get_or_create_circuit(
            "ap2_payment_execution", AP2_PAYMENT_CONFIG
        )
    
    async def initiate_payment_workflow(
        self, 
        request: PaymentCoordinationRequest
    ) -> PaymentWorkflow:
        """Initiate a complete payment workflow"""
        
        # Validate business exists and is AP2-enabled
        business = self._business_repository.find_by_id(request.business_id)
        if not business or not business.ap2_enabled:
            raise ValueError(f"Business {request.business_id} not found or not AP2-enabled")
        
        # Create workflow
        workflow = PaymentWorkflow(
            user_id=request.user_id,
            business_id=request.business_id,
            agent_id=request.agent_id,
            status=PaymentStatus.INITIALIZING
        )
        
        self._active_workflows[workflow.id] = workflow
        
        try:
            # Execute workflow steps
            await self._execute_intent_mandate_step(workflow, request)
            await self._execute_cart_mandate_step(workflow, request)
            await self._execute_payment_step(workflow, request)
            
            workflow.status = PaymentStatus.COMPLETED
            
            # Publish payment completion event
            await publish_workflow_event(
                event_type=WorkflowEventType.PAYMENT_COMPLETED,
                workflow_id=workflow.id,
                business_id=request.business_id,
                user_id=request.user_id,
                data={
                    "amount": total_amount,
                    "currency": request.currency or "USD",
                    "payment_method": request.payment_method_id
                }
            )
            
        except ValidationError as e:
            workflow.status = PaymentStatus.FAILED
            workflow.error_message = f"Validation error: {str(e)}"
            raise
        except IntegrationError as e:
            workflow.status = PaymentStatus.FAILED
            workflow.error_message = f"Integration error: {str(e)}"
            raise
        except Exception as e:
            workflow.status = PaymentStatus.FAILED
            workflow.error_message = f"Unexpected error: {str(e)}"
            
            # Publish payment failure event
            await publish_workflow_event(
                event_type=WorkflowEventType.PAYMENT_FAILED,
                workflow_id=workflow.id,
                business_id=request.business_id,
                user_id=request.user_id,
                data={
                    "error_message": str(e),
                    "error_type": type(e).__name__
                }
            )
            
            from ..exceptions import BAISException
            raise BAISException(f"Payment workflow failed: {str(e)}")
        
        return workflow
    
    async def _execute_intent_mandate_step(
        self, 
        workflow: PaymentWorkflow, 
        request: PaymentCoordinationRequest
    ) -> None:
        """Execute intent mandate creation with circuit breaker protection"""
        workflow.current_step = PaymentWorkflowStep.INTENT_MANDATE
        
        try:
            intent_mandate = await self._mandate_circuit.call(
                self._ap2_client.create_intent_mandate,
                user_id=request.user_id,
                business_id=request.business_id,
                intent_description=request.intent_description,
                constraints=request.payment_constraints
            )
            
            workflow.intent_mandate_id = intent_mandate.id
            workflow.status = PaymentStatus.INTENT_AUTHORIZED
            
        except CircuitBreakerOpenException as e:
            workflow.status = PaymentStatus.FAILED
            workflow.error_message = "Payment service temporarily unavailable"
            raise IntegrationError(f"AP2 mandate service unavailable: {str(e)}")
        except CircuitBreakerTimeoutException as e:
            workflow.status = PaymentStatus.FAILED
            workflow.error_message = "Payment service timeout"
            raise IntegrationError(f"AP2 mandate service timeout: {str(e)}")
    
    async def _execute_cart_mandate_step(
        self, 
        workflow: PaymentWorkflow, 
        request: PaymentCoordinationRequest
    ) -> None:
        """Execute cart mandate creation with circuit breaker protection"""
        workflow.current_step = PaymentWorkflowStep.CART_MANDATE
        
        total_amount = sum(item.get('price', 0) * item.get('quantity', 1) 
                          for item in request.cart_items)
        
        try:
            cart_mandate = await self._mandate_circuit.call(
                self._ap2_client.create_cart_mandate,
                intent_mandate_id=workflow.intent_mandate_id,
                cart_items=request.cart_items,
                total_amount=total_amount,
                currency=request.currency or "USD"
            )
            
            workflow.cart_mandate_id = cart_mandate.id
            workflow.status = PaymentStatus.CART_CONFIRMED
            
        except CircuitBreakerOpenException as e:
            workflow.status = PaymentStatus.FAILED
            workflow.error_message = "Payment service temporarily unavailable"
            raise IntegrationError(f"AP2 cart mandate service unavailable: {str(e)}")
        except CircuitBreakerTimeoutException as e:
            workflow.status = PaymentStatus.FAILED
            workflow.error_message = "Payment service timeout"
            raise IntegrationError(f"AP2 cart mandate service timeout: {str(e)}")
    
    async def _execute_payment_step(
        self, 
        workflow: PaymentWorkflow, 
        request: PaymentCoordinationRequest
    ) -> None:
        """Execute actual payment with circuit breaker protection"""
        workflow.current_step = PaymentWorkflowStep.PAYMENT_EXECUTION
        
        # Get payment method (this would integrate with user's payment methods)
        payment_method = await self._get_payment_method(request.payment_method_id)
        
        try:
            transaction = await self._payment_circuit.call(
                self._ap2_client.execute_payment,
                cart_mandate_id=workflow.cart_mandate_id,
                payment_method=payment_method
            )
            
            workflow.transaction_id = transaction.id
            workflow.status = PaymentStatus.PAYMENT_PROCESSING
            
        except CircuitBreakerOpenException as e:
            workflow.status = PaymentStatus.FAILED
            workflow.error_message = "Payment execution service temporarily unavailable"
            raise IntegrationError(f"AP2 payment execution service unavailable: {str(e)}")
        except CircuitBreakerTimeoutException as e:
            workflow.status = PaymentStatus.FAILED
            workflow.error_message = "Payment execution timeout"
            raise IntegrationError(f"AP2 payment execution timeout: {str(e)}")
    
    async def _get_payment_method(self, payment_method_id: str):
        """Get payment method details - placeholder for integration"""
        # This would integrate with user payment methods storage
        pass
    
    def get_workflow_status(self, workflow_id: str) -> Optional[PaymentWorkflow]:
        """Get current status of a payment workflow"""
        return self._active_workflows.get(workflow_id)
