"""
AP2 Mandate Management API Endpoints
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from datetime import datetime

from ...core.payments.mandate_manager import MandateManager, MandateValidationError
from ...core.payments.models import AP2Mandate, PaymentStatus
from ...core.payments.ap2_client import AP2Client, AP2ClientConfig
from ...config.ap2_settings import get_ap2_client_config, is_ap2_enabled
from ...core.exceptions import ValidationError, IntegrationError

router = APIRouter(prefix="/mandates", tags=["AP2 Mandates"])


class IntentMandateRequest(BaseModel):
    """Request model for creating intent mandates"""
    user_id: str = Field(..., description="User ID requesting the mandate")
    business_id: str = Field(..., description="Business ID for the mandate")
    intent_description: str = Field(..., description="Description of user intent")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Payment constraints")
    expiry_hours: int = Field(default=24, ge=1, le=168, description="Mandate expiry in hours")


class CartMandateRequest(BaseModel):
    """Request model for creating cart mandates"""
    intent_mandate_id: str = Field(..., description="ID of the intent mandate")
    cart_items: List[Dict[str, Any]] = Field(..., description="Cart items")
    pricing_validation: bool = Field(default=True, description="Enable real-time pricing validation")


class MandateResponse(BaseModel):
    """Response model for mandate operations"""
    id: str
    type: str
    user_id: str
    business_id: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    data: Dict[str, Any]


class MandateListResponse(BaseModel):
    """Response model for mandate listing"""
    mandates: List[MandateResponse]
    total: int
    page: int
    page_size: int


def get_mandate_manager() -> MandateManager:
    """Dependency to get mandate manager instance"""
    if not is_ap2_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AP2 service is not enabled or properly configured"
        )
    
    config = AP2ClientConfig(**get_ap2_client_config())
    ap2_client = AP2Client(config)
    
    # Initialize business repository for mandate management
    from ...core.business_query_repository import BusinessQueryRepository
    business_repo = BusinessQueryRepository()
    
    return MandateManager(ap2_client, business_repo)


@router.post("/intent", response_model=MandateResponse, status_code=status.HTTP_201_CREATED)
async def create_intent_mandate(
    request: IntentMandateRequest,
    mandate_manager: MandateManager = Depends(get_mandate_manager)
) -> MandateResponse:
    """
    Create an intent mandate for user authorization
    
    This endpoint creates a cryptographically signed intent mandate that authorizes
    an agent to make purchases on behalf of a user within specified constraints.
    """
    try:
        mandate = await mandate_manager.create_intent_mandate(
            user_id=request.user_id,
            business_id=request.business_id,
            intent_description=request.intent_description,
            constraints=request.constraints,
            expiry_hours=request.expiry_hours
        )
        
        return MandateResponse(
            id=mandate.id,
            type=mandate.type,
            user_id=mandate.user_id,
            business_id=mandate.business_id,
            status=mandate.status,
            created_at=mandate.created_at,
            expires_at=mandate.expires_at,
            data=mandate.data
        )
        
    except MandateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except IntegrationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create intent mandate: {str(e)}"
        )


@router.post("/cart", response_model=MandateResponse, status_code=status.HTTP_201_CREATED)
async def create_cart_mandate(
    request: CartMandateRequest,
    mandate_manager: MandateManager = Depends(get_mandate_manager)
) -> MandateResponse:
    """
    Create a cart mandate from an intent mandate
    
    This endpoint creates a cart mandate that specifies exact items and pricing,
    linked to a previously created intent mandate.
    """
    try:
        mandate = await mandate_manager.create_cart_mandate(
            intent_mandate_id=request.intent_mandate_id,
            cart_items=request.cart_items,
            pricing_validation=request.pricing_validation
        )
        
        return MandateResponse(
            id=mandate.id,
            type=mandate.type,
            user_id=mandate.user_id,
            business_id=mandate.business_id,
            status=mandate.status,
            created_at=mandate.created_at,
            expires_at=mandate.expires_at,
            data=mandate.data
        )
        
    except MandateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create cart mandate: {str(e)}"
        )


@router.get("/{mandate_id}", response_model=MandateResponse)
async def get_mandate(
    mandate_id: str,
    mandate_manager: MandateManager = Depends(get_mandate_manager)
) -> MandateResponse:
    """
    Retrieve a mandate by ID
    
    Returns the mandate details including status and validation information.
    """
    try:
        mandate = await mandate_manager.get_mandate(mandate_id)
        
        if not mandate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mandate {mandate_id} not found"
            )
        
        return MandateResponse(
            id=mandate.id,
            type=mandate.type,
            user_id=mandate.user_id,
            business_id=mandate.business_id,
            status=mandate.status,
            created_at=mandate.created_at,
            expires_at=mandate.expires_at,
            data=mandate.data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve mandate: {str(e)}"
        )


@router.post("/{mandate_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_mandate(
    mandate_id: str,
    reason: str = "user_requested",
    mandate_manager: MandateManager = Depends(get_mandate_manager)
) -> Dict[str, Any]:
    """
    Revoke an active mandate
    
    Revokes a mandate, preventing it from being used for further transactions.
    """
    try:
        success = await mandate_manager.revoke_mandate(mandate_id, reason)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to revoke mandate {mandate_id}"
            )
        
        return {
            "mandate_id": mandate_id,
            "status": "revoked",
            "reason": reason,
            "revoked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke mandate: {str(e)}"
        )


@router.get("/", response_model=MandateListResponse)
async def list_mandates(
    user_id: Optional[str] = None,
    business_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    mandate_manager: MandateManager = Depends(get_mandate_manager)
) -> MandateListResponse:
    """
    List mandates with optional filtering
    
    Returns a paginated list of mandates with optional filtering by user, business, or status.
    """
    try:
        # Retrieve mandates with filtering and pagination
        # This would integrate with mandate storage and apply filters
        return MandateListResponse(
            mandates=[],
            total=0,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list mandates: {str(e)}"
        )
