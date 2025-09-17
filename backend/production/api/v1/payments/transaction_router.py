"""
AP2 Transaction Management API Endpoints
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from datetime import datetime

from ...core.payments.payment_coordinator import PaymentCoordinator, PaymentCoordinationRequest
from ...core.payments.models import PaymentWorkflow, PaymentStatus, PaymentMethod, PaymentMethodType
from ...core.payments.ap2_client import AP2Client, AP2ClientConfig
from ...config.ap2_settings import get_ap2_client_config, is_ap2_enabled

router = APIRouter(prefix="/transactions", tags=["AP2 Transactions"])


class PaymentWorkflowRequest(BaseModel):
    """Request model for initiating payment workflows"""
    user_id: str = Field(..., description="User ID initiating the payment")
    business_id: str = Field(..., description="Business ID for the payment")
    agent_id: str = Field(..., description="Agent ID handling the payment")
    intent_description: str = Field(..., description="Description of payment intent")
    cart_items: List[Dict[str, Any]] = Field(..., description="Items in the cart")
    payment_constraints: Dict[str, Any] = Field(default_factory=dict, description="Payment constraints")
    payment_method_id: str = Field(..., description="Payment method ID to use")


class PaymentMethodRequest(BaseModel):
    """Request model for payment method operations"""
    type: PaymentMethodType = Field(..., description="Payment method type")
    display_name: str = Field(..., description="Display name for the payment method")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Payment method metadata")
    is_default: bool = Field(default=False, description="Whether this is the default payment method")


class TransactionResponse(BaseModel):
    """Response model for transaction operations"""
    id: str
    cart_mandate_id: str
    payment_method: Dict[str, Any]
    amount: float
    currency: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class PaymentWorkflowResponse(BaseModel):
    """Response model for payment workflow operations"""
    id: str
    user_id: str
    business_id: str
    agent_id: str
    status: str
    current_step: Optional[str] = None
    intent_mandate_id: Optional[str] = None
    cart_mandate_id: Optional[str] = None
    transaction_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


def get_payment_coordinator() -> PaymentCoordinator:
    """Dependency to get payment coordinator instance"""
    if not is_ap2_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AP2 service is not enabled or properly configured"
        )
    
    config = AP2ClientConfig(**get_ap2_client_config())
    ap2_client = AP2Client(config)
    
    # TODO: Inject proper business repository
    from ...core.business_query_repository import BusinessQueryRepository
    business_repo = BusinessQueryRepository()
    
    return PaymentCoordinator(ap2_client, business_repo)


@router.post("/workflows", response_model=PaymentWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment_workflow(
    request: PaymentWorkflowRequest,
    coordinator: PaymentCoordinator = Depends(get_payment_coordinator)
) -> PaymentWorkflowResponse:
    """
    Initiate a complete AP2 payment workflow
    
    This endpoint orchestrates the complete AP2 payment flow:
    1. Creates an intent mandate
    2. Creates a cart mandate
    3. Executes the payment transaction
    
    Returns the payment workflow with all mandate and transaction IDs.
    """
    try:
        coordination_request = PaymentCoordinationRequest(
            user_id=request.user_id,
            business_id=request.business_id,
            agent_id=request.agent_id,
            intent_description=request.intent_description,
            cart_items=request.cart_items,
            payment_constraints=request.payment_constraints,
            payment_method_id=request.payment_method_id
        )
        
        workflow = await coordinator.initiate_payment_workflow(coordination_request)
        
        return PaymentWorkflowResponse(
            id=workflow.id,
            user_id=workflow.user_id,
            business_id=workflow.business_id,
            agent_id=workflow.agent_id,
            status=workflow.status.value,
            current_step=workflow.current_step.value if workflow.current_step else None,
            intent_mandate_id=workflow.intent_mandate_id,
            cart_mandate_id=workflow.cart_mandate_id,
            transaction_id=workflow.transaction_id,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            completed_at=workflow.completed_at,
            error_message=workflow.error_message
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate payment workflow: {str(e)}"
        )


@router.get("/workflows/{workflow_id}", response_model=PaymentWorkflowResponse)
async def get_payment_workflow(
    workflow_id: str,
    coordinator: PaymentCoordinator = Depends(get_payment_coordinator)
) -> PaymentWorkflowResponse:
    """
    Get payment workflow status
    
    Returns the current status and details of a payment workflow.
    """
    try:
        workflow = coordinator.get_workflow_status(workflow_id)
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment workflow {workflow_id} not found"
            )
        
        return PaymentWorkflowResponse(
            id=workflow.id,
            user_id=workflow.user_id,
            business_id=workflow.business_id,
            agent_id=workflow.agent_id,
            status=workflow.status.value,
            current_step=workflow.current_step.value if workflow.current_step else None,
            intent_mandate_id=workflow.intent_mandate_id,
            cart_mandate_id=workflow.cart_mandate_id,
            transaction_id=workflow.transaction_id,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            completed_at=workflow.completed_at,
            error_message=workflow.error_message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment workflow: {str(e)}"
        )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    coordinator: PaymentCoordinator = Depends(get_payment_coordinator)
) -> TransactionResponse:
    """
    Get transaction details
    
    Returns the details of a specific transaction including status and payment method.
    """
    try:
        # Get AP2 client to retrieve transaction
        config = AP2ClientConfig(**get_ap2_client_config())
        ap2_client = AP2Client(config)
        
        transaction = await ap2_client.get_transaction_status(transaction_id)
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )
        
        return TransactionResponse(
            id=transaction.id,
            cart_mandate_id=transaction.cart_mandate_id,
            payment_method=transaction.payment_method.to_dict(),
            amount=transaction.amount,
            currency=transaction.currency,
            status=transaction.status,
            created_at=transaction.created_at,
            completed_at=transaction.completed_at,
            error_message=transaction.error_message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transaction: {str(e)}"
        )


@router.post("/payment-methods", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    request: PaymentMethodRequest,
    user_id: str = Field(..., description="User ID for the payment method")
) -> Dict[str, Any]:
    """
    Create a new payment method for a user
    
    This endpoint creates a payment method that can be used in AP2 transactions.
    """
    try:
        # TODO: Implement payment method creation and storage
        # This would integrate with user payment methods storage
        payment_method = PaymentMethod(
            id=f"pm_{datetime.utcnow().timestamp()}",
            type=request.type,
            display_name=request.display_name,
            metadata=request.metadata,
            is_default=request.is_default
        )
        
        return {
            "id": payment_method.id,
            "type": payment_method.type.value,
            "display_name": payment_method.display_name,
            "metadata": payment_method.metadata,
            "is_default": payment_method.is_default,
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment method: {str(e)}"
        )


@router.get("/payment-methods/{user_id}", response_model=List[Dict[str, Any]])
async def list_payment_methods(
    user_id: str
) -> List[Dict[str, Any]]:
    """
    List payment methods for a user
    
    Returns all payment methods associated with a user.
    """
    try:
        # TODO: Implement payment method listing
        # This would retrieve from user payment methods storage
        return []
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list payment methods: {str(e)}"
        )
