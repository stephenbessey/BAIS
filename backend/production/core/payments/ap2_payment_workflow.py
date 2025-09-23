"""
AP2 Payment Workflow Implementation
Complete implementation of AP2 payment workflow with cryptographic validation

This module implements the complete AP2 payment workflow as specified in the requirements,
addressing the critical gaps in payment coordination.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import uuid

from .ap2_client import AP2Client, AP2ClientConfig
from .ap2_mandate_validator import AP2MandateValidator, AP2MandateValidationError
from .models import AP2Mandate, AP2Transaction, PaymentMethod, PaymentWorkflow, PaymentStatus, PaymentWorkflowStep
from .payment_coordinator import PaymentCoordinationRequest


class AP2WorkflowStatus(Enum):
    """AP2 Workflow status enumeration"""
    INITIALIZING = "initializing"
    INTENT_CREATED = "intent_created"
    INTENT_AUTHORIZED = "intent_authorized"
    CART_CREATED = "cart_created"
    CART_AUTHORIZED = "cart_authorized"
    PAYMENT_PROCESSING = "payment_processing"
    PAYMENT_COMPLETED = "payment_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AP2WorkflowConstraints:
    """Constraints for AP2 payment workflow"""
    max_amount: float
    currency: str = "USD"
    allowed_payment_methods: List[str] = None
    expiry_hours: int = 24
    require_business_validation: bool = True
    require_user_confirmation: bool = False


@dataclass
class AP2WorkflowResult:
    """Result of AP2 payment workflow"""
    workflow_id: str
    status: AP2WorkflowStatus
    intent_mandate_id: Optional[str] = None
    cart_mandate_id: Optional[str] = None
    transaction_id: Optional[str] = None
    total_amount: float = 0.0
    currency: str = "USD"
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class AP2PaymentWorkflow:
    """
    Complete AP2 Payment Workflow Implementation
    
    Implements the full AP2 payment workflow with:
    - Intent mandate creation
    - Cart mandate creation  
    - Payment execution
    - Cryptographic validation
    - Error handling and rollback
    """
    
    def __init__(self, ap2_client: AP2Client, validator: AP2MandateValidator):
        self.ap2_client = ap2_client
        self.validator = validator
        self.active_workflows: Dict[str, AP2WorkflowResult] = {}
    
    async def process_payment_workflow(
        self, 
        request: PaymentCoordinationRequest,
        constraints: AP2WorkflowConstraints
    ) -> AP2WorkflowResult:
        """
        Process complete AP2 payment workflow
        
        Args:
            request: Payment coordination request
            constraints: Workflow constraints
            
        Returns:
            AP2WorkflowResult with workflow details
        """
        workflow_id = str(uuid.uuid4())
        workflow_result = AP2WorkflowResult(
            workflow_id=workflow_id,
            status=AP2WorkflowStatus.INITIALIZING
        )
        
        self.active_workflows[workflow_id] = workflow_result
        
        try:
            # Step 1: Create intent mandate
            await self._create_intent_mandate(workflow_result, request, constraints)
            
            # Step 2: Create cart mandate
            await self._create_cart_mandate(workflow_result, request, constraints)
            
            # Step 3: Execute payment
            await self._execute_payment(workflow_result, request)
            
            workflow_result.status = AP2WorkflowStatus.PAYMENT_COMPLETED
            workflow_result.completed_at = datetime.utcnow()
            
        except Exception as e:
            workflow_result.status = AP2WorkflowStatus.FAILED
            workflow_result.error_message = str(e)
            workflow_result.completed_at = datetime.utcnow()
            
            # Rollback any created mandates
            await self._rollback_workflow(workflow_result)
            
            raise
        
        return workflow_result
    
    async def _create_intent_mandate(
        self, 
        workflow_result: AP2WorkflowResult,
        request: PaymentCoordinationRequest,
        constraints: AP2WorkflowConstraints
    ) -> None:
        """Create intent mandate with constraints"""
        workflow_result.status = AP2WorkflowStatus.INTENT_CREATED
        
        intent_constraints = {
            "max_amount": constraints.max_amount,
            "currency": constraints.currency,
            "expiry_hours": constraints.expiry_hours,
            "business_validation_required": constraints.require_business_validation,
            "user_confirmation_required": constraints.require_user_confirmation
        }
        
        if constraints.allowed_payment_methods:
            intent_constraints["allowed_payment_methods"] = constraints.allowed_payment_methods
        
        intent_mandate = await self.ap2_client.create_intent_mandate_with_constraints(
            user_id=request.user_id,
            business_id=request.business_id,
            intent_description=request.intent_description,
            constraints=intent_constraints,
            expiry_hours=constraints.expiry_hours
        )
        
        # Validate the created mandate
        if not self.validator.verify_mandate(intent_mandate):
            raise AP2MandateValidationError("Invalid intent mandate signature")
        
        workflow_result.intent_mandate_id = intent_mandate.id
        workflow_result.status = AP2WorkflowStatus.INTENT_AUTHORIZED
    
    async def _create_cart_mandate(
        self,
        workflow_result: AP2WorkflowResult,
        request: PaymentCoordinationRequest,
        constraints: AP2WorkflowConstraints
    ) -> None:
        """Create cart mandate from intent mandate"""
        workflow_result.status = AP2WorkflowStatus.CART_CREATED
        
        # Calculate total amount
        total_amount = sum(
            item.get('price', 0) * item.get('quantity', 1) 
            for item in request.cart_items
        )
        
        if total_amount > constraints.max_amount:
            raise ValueError(f"Cart total {total_amount} exceeds maximum {constraints.max_amount}")
        
        cart_mandate = await self.ap2_client.create_cart_mandate_with_validation(
            intent_mandate_id=workflow_result.intent_mandate_id,
            cart_items=request.cart_items,
            total_amount=total_amount,
            currency=constraints.currency,
            validate_with_business=constraints.require_business_validation
        )
        
        # Validate the created mandate
        if not self.validator.verify_mandate(cart_mandate):
            raise AP2MandateValidationError("Invalid cart mandate signature")
        
        workflow_result.cart_mandate_id = cart_mandate.id
        workflow_result.total_amount = total_amount
        workflow_result.currency = constraints.currency
        workflow_result.status = AP2WorkflowStatus.CART_AUTHORIZED
    
    async def _execute_payment(
        self,
        workflow_result: AP2WorkflowResult,
        request: PaymentCoordinationRequest
    ) -> None:
        """Execute payment using cart mandate"""
        workflow_result.status = AP2WorkflowStatus.PAYMENT_PROCESSING
        
        # Get payment method (this would integrate with user payment methods)
        payment_method = await self._get_payment_method(request.payment_method_id)
        
        transaction = await self.ap2_client.execute_payment_with_verification(
            cart_mandate_id=workflow_result.cart_mandate_id,
            payment_method=payment_method,
            verification_required=True
        )
        
        workflow_result.transaction_id = transaction.id
    
    async def _get_payment_method(self, payment_method_id: str) -> PaymentMethod:
        """Get payment method details - placeholder for integration"""
        # This would integrate with user payment methods storage
        # For now, return a mock payment method
        from .models import PaymentMethodType
        
        return PaymentMethod(
            id=payment_method_id,
            type=PaymentMethodType.CREDIT_CARD,
            display_name="Mock Payment Method",
            metadata={"last_four": "1234"},
            is_default=True
        )
    
    async def _rollback_workflow(self, workflow_result: AP2WorkflowResult) -> None:
        """Rollback workflow by revoking mandates"""
        try:
            # Revoke cart mandate if created
            if workflow_result.cart_mandate_id:
                await self.ap2_client.revoke_mandate(
                    workflow_result.cart_mandate_id, 
                    "workflow_failed"
                )
            
            # Revoke intent mandate if created
            if workflow_result.intent_mandate_id:
                await self.ap2_client.revoke_mandate(
                    workflow_result.intent_mandate_id, 
                    "workflow_failed"
                )
                    
        except Exception as e:
            # Log rollback errors but don't raise
            print(f"Warning: Failed to rollback workflow {workflow_result.workflow_id}: {e}")
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[AP2WorkflowResult]:
        """Get current workflow status"""
        return self.active_workflows.get(workflow_id)
    
    async def cancel_workflow(self, workflow_id: str, reason: str = "user_requested") -> bool:
        """Cancel an active workflow"""
        workflow_result = self.active_workflows.get(workflow_id)
        if not workflow_result:
            return False
        
        if workflow_result.status in [AP2WorkflowStatus.PAYMENT_COMPLETED, AP2WorkflowStatus.FAILED, AP2WorkflowStatus.CANCELLED]:
            return False  # Cannot cancel completed workflows
        
        try:
            # Cancel the workflow
            workflow_result.status = AP2WorkflowStatus.CANCELLED
            workflow_result.completed_at = datetime.utcnow()
            workflow_result.error_message = f"Cancelled: {reason}"
            
            # Rollback mandates
            await self._rollback_workflow(workflow_result)
            
            return True
            
        except Exception as e:
            workflow_result.error_message = f"Cancel failed: {str(e)}"
            return False
    
    def cleanup_completed_workflows(self, max_age_hours: int = 24) -> int:
        """Clean up completed workflows older than max_age_hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        workflows_to_remove = []
        for workflow_id, workflow_result in self.active_workflows.items():
            if (workflow_result.completed_at and 
                workflow_result.completed_at < cutoff_time and
                workflow_result.status in [AP2WorkflowStatus.PAYMENT_COMPLETED, 
                                         AP2WorkflowStatus.FAILED, 
                                         AP2WorkflowStatus.CANCELLED]):
                workflows_to_remove.append(workflow_id)
        
        for workflow_id in workflows_to_remove:
            del self.active_workflows[workflow_id]
            cleaned_count += 1
        
        return cleaned_count


class AP2PaymentWorkflowFactory:
    """Factory for creating AP2 payment workflows"""
    
    @staticmethod
    def create_workflow(
        ap2_config: AP2ClientConfig,
        public_key_pem: str
    ) -> AP2PaymentWorkflow:
        """Create AP2 payment workflow with configuration"""
        ap2_client = AP2Client(ap2_config)
        validator = AP2MandateValidator(public_key_pem)
        return AP2PaymentWorkflow(ap2_client, validator)
    
    @staticmethod
    def create_workflow_with_validator(
        ap2_client: AP2Client,
        validator: AP2MandateValidator
    ) -> AP2PaymentWorkflow:
        """Create AP2 payment workflow with existing client and validator"""
        return AP2PaymentWorkflow(ap2_client, validator)


# Example usage and testing
async def example_payment_workflow():
    """Example of using the AP2 payment workflow"""
    
    # Configuration
    ap2_config = AP2ClientConfig(
        base_url="https://ap2.example.com",
        client_id="bais-client-123",
        private_key="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
        public_key="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
    )
    
    # Create workflow
    workflow = AP2PaymentWorkflowFactory.create_workflow(
        ap2_config, 
        ap2_config.public_key
    )
    
    # Create request
    request = PaymentCoordinationRequest(
        user_id="user-123",
        business_id="business-456",
        agent_id="agent-789",
        intent_description="Book hotel room for 2 nights",
        cart_items=[
            {"id": "room-1", "name": "Deluxe Room", "price": 200.0, "quantity": 2}
        ],
        payment_constraints={"max_amount": 500.0},
        payment_method_id="pm-123"
    )
    
    # Create constraints
    constraints = AP2WorkflowConstraints(
        max_amount=500.0,
        currency="USD",
        expiry_hours=24,
        require_business_validation=True
    )
    
    try:
        # Process workflow
        result = await workflow.process_payment_workflow(request, constraints)
        
        print(f"Workflow completed: {result.workflow_id}")
        print(f"Status: {result.status}")
        print(f"Transaction ID: {result.transaction_id}")
        
    except Exception as e:
        print(f"Workflow failed: {e}")
