from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import asyncio
from enum import Enum
import uuid
from datetime import datetime

from .ap2_client import AP2Client
from .models import PaymentWorkflow, PaymentStatus, BusinessIntent
from .business_validator import PaymentBusinessValidator, BusinessValidationResult
from .payment_event_publisher import PaymentEventPublisher
from ..business_query_repository import BusinessQueryRepository
from ..exceptions import ValidationError, IntegrationError
from ..workflow_state_manager import WorkflowStateManager
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
    Implements Command pattern for workflow management with proper dependency injection
    """
    
    def __init__(
        self, 
        ap2_client: AP2Client, 
        business_repository: BusinessQueryRepository,
        workflow_state_manager: WorkflowStateManager,
        business_validator: PaymentBusinessValidator = None,
        event_publisher: PaymentEventPublisher = None
    ):
        self._ap2_client = ap2_client
        self._business_repository = business_repository
        self._workflow_state_manager = workflow_state_manager
        
        # Initialize extracted components (dependency injection)
        self._business_validator = business_validator or PaymentBusinessValidator(business_repository)
        self._event_publisher = event_publisher or PaymentEventPublisher()
        
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
        
        # Validate business using dedicated business validator
        validation_result = self._business_validator.validate_business_for_payment(request.business_id)
        if not validation_result.is_valid:
            raise ValidationError(f"Business validation failed: {'; '.join(validation_result.validation_errors)}")
        
        # Validate payment constraints
        self._business_validator.validate_payment_constraints(request.business_id, request.payment_constraints)
        
        # Validate cart items
        self._business_validator.validate_cart_items(request.business_id, request.cart_items)
        
        # Create workflow
        workflow = PaymentWorkflow(
            user_id=request.user_id,
            business_id=request.business_id,
            agent_id=request.agent_id,
            status=PaymentStatus.INITIALIZING
        )
        
        # Store workflow using state manager (no global state)
        await self._workflow_state_manager.create_workflow(workflow)
        
        try:
            # Execute workflow steps
            await self._execute_intent_mandate_step(workflow, request)
            await self._execute_cart_mandate_step(workflow, request)
            await self._execute_payment_step(workflow, request)
            
            # Update workflow status using state manager
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.COMPLETED
            )
            
            # Publish payment completion event using dedicated publisher
            await self._event_publisher.publish_payment_completed(
                workflow_id=workflow.id,
                business_id=request.business_id,
                user_id=request.user_id,
                transaction_id=workflow.transaction_id,
                amount=total_amount,
                currency=request.currency or "USD",
                payment_method=request.payment_method_id
            )
            
        except ValidationError as e:
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.FAILED, f"Validation error: {str(e)}"
            )
            raise
        except IntegrationError as e:
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.FAILED, f"Integration error: {str(e)}"
            )
            raise
        except Exception as e:
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.FAILED, f"Unexpected error: {str(e)}"
            )
            
            # Publish payment failure event using dedicated publisher
            await self._event_publisher.publish_payment_failed(
                workflow_id=workflow.id,
                business_id=request.business_id,
                user_id=request.user_id,
                error_message=str(e),
                error_code=type(e).__name__,
                transaction_id=workflow.transaction_id
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
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.INTENT_AUTHORIZED
            )
            
            # Publish mandate created event
            await self._event_publisher.publish_mandate_created(
                workflow_id=workflow.id,
                business_id=request.business_id,
                user_id=request.user_id,
                mandate_id=intent_mandate.id,
                mandate_type="intent"
            )
            
        except CircuitBreakerOpenException as e:
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.FAILED, "Payment service temporarily unavailable"
            )
            raise IntegrationError(f"AP2 mandate service unavailable: {str(e)}")
        except CircuitBreakerTimeoutException as e:
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.FAILED, "Payment service timeout"
            )
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
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.CART_CONFIRMED
            )
            
            # Publish cart mandate created event
            await self._event_publisher.publish_mandate_created(
                workflow_id=workflow.id,
                business_id=request.business_id,
                user_id=request.user_id,
                mandate_id=cart_mandate.id,
                mandate_type="cart",
                amount=total_amount,
                currency=request.currency or "USD"
            )
            
        except CircuitBreakerOpenException as e:
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.FAILED, "Payment service temporarily unavailable"
            )
            raise IntegrationError(f"AP2 cart mandate service unavailable: {str(e)}")
        except CircuitBreakerTimeoutException as e:
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.FAILED, "Payment service timeout"
            )
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
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.PAYMENT_PROCESSING
            )
            
            # Publish payment processing event
            await self._event_publisher.publish_payment_processing(
                workflow_id=workflow.id,
                business_id=request.business_id,
                user_id=request.user_id,
                transaction_id=transaction.id,
                amount=total_amount,
                currency=request.currency or "USD"
            )
            
        except CircuitBreakerOpenException as e:
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.FAILED, "Payment execution service temporarily unavailable"
            )
            raise IntegrationError(f"AP2 payment execution service unavailable: {str(e)}")
        except CircuitBreakerTimeoutException as e:
            await self._workflow_state_manager.update_workflow_status(
                workflow.id, PaymentStatus.FAILED, "Payment execution timeout"
            )
            raise IntegrationError(f"AP2 payment execution timeout: {str(e)}")
    
    async def _get_payment_method(self, payment_method_id: str):
        """Get payment method details - placeholder for integration"""
        # This would integrate with user payment methods storage
        pass
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[PaymentWorkflow]:
        """Get current status of a payment workflow"""
        try:
            return await self._workflow_state_manager.get_workflow(workflow_id)
        except NotFoundError:
            return None
