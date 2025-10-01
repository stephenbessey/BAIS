"""
BAIS Platform - Official ACP Commerce API

Official Agentic Commerce Protocol API endpoints implementing the
ACP specification for checkout, orders, and payment processing.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from ...core.database_models import DatabaseManager
from ...services.commerce.acp_official_compliance import (
    OfficialACPIntegrationService, ACPCheckoutSession, ACPOrder,
    ACPDelegatedPaymentToken, ACPProduct, ACPWebhookEvent,
    ACPMoney, ACPPaymentMethod, ACPOrderStatus
)
import httpx


# Request/Response Models
class ACPCheckoutRequest(BaseModel):
    """ACP checkout initialization request"""
    merchant_id: str = Field(..., description="Merchant identifier")
    line_items: List[Dict[str, Any]] = Field(..., description="Order line items")
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('line_items')
    def validate_line_items(cls, v):
        if not v:
            raise ValueError("Line items cannot be empty")
        for item in v:
            if "price" not in item or "quantity" not in item:
                raise ValueError("Line items must have price and quantity")
        return v


class ACPCheckoutUpdateRequest(BaseModel):
    """ACP checkout update request"""
    line_items: Optional[List[Dict[str, Any]]] = None
    customer_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ACPPaymentTokenRequest(BaseModel):
    """ACP delegated payment token request"""
    merchant_id: str = Field(..., description="Merchant identifier")
    amount: Dict[str, Any] = Field(..., description="Payment amount")
    payment_method: str = Field(..., description="Payment method")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        valid_methods = [method.value for method in ACPPaymentMethod]
        if v not in valid_methods:
            raise ValueError(f"Invalid payment method. Must be one of: {valid_methods}")
        return v


class ACPCheckoutCompleteRequest(BaseModel):
    """ACP checkout completion request"""
    payment_token: Dict[str, Any] = Field(..., description="Delegated payment token")
    
    @validator('payment_token')
    def validate_payment_token(cls, v):
        required_fields = ["id", "merchant_id", "amount", "payment_method"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Payment token missing required field: {field}")
        return v


class ACPWebhookRequest(BaseModel):
    """ACP webhook event request"""
    type: str = Field(..., description="Event type")
    id: str = Field(..., description="Event identifier")
    created: int = Field(..., description="Unix timestamp")
    data: Dict[str, Any] = Field(..., description="Event data")
    merchant_id: str = Field(..., description="Merchant identifier")


# Router
router = APIRouter(prefix="/v1/commerce", tags=["ACP Commerce"])


def get_acp_service(db_manager: DatabaseManager = Depends()) -> OfficialACPIntegrationService:
    """Dependency to get ACP service instance"""
    return OfficialACPIntegrationService(db_manager.session, httpx.AsyncClient())


@router.post("/checkout/initialize", response_model=Dict[str, Any])
async def initialize_checkout(
    request: ACPCheckoutRequest,
    acp_service: OfficialACPIntegrationService = Depends(get_acp_service)
) -> JSONResponse:
    """
    Initialize ACP checkout session
    
    Creates a new checkout session with line items and calculates totals.
    """
    try:
        session = await acp_service.initialize_checkout(
            merchant_id=request.merchant_id,
            line_items=request.line_items,
            customer_id=request.customer_id
        )
        
        # Add metadata if provided
        if request.metadata:
            session.metadata.update(request.metadata)
        
        return JSONResponse(
            content=session.dict(),
            status_code=201,
            headers={
                "Location": f"/v1/commerce/checkout/{session.id}",
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout initialization failed: {str(e)}")


@router.get("/checkout/{session_id}", response_model=Dict[str, Any])
async def get_checkout_session(
    session_id: str,
    acp_service: OfficialACPIntegrationService = Depends(get_acp_service)
) -> JSONResponse:
    """
    Get ACP checkout session
    
    Retrieves an existing checkout session by ID.
    """
    try:
        if session_id not in acp_service.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = acp_service.sessions[session_id]
        
        # Check expiration
        if datetime.utcnow() > session.expires_at:
            raise HTTPException(status_code=410, detail="Session expired")
        
        return JSONResponse(content=session.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session retrieval failed: {str(e)}")


@router.put("/checkout/{session_id}", response_model=Dict[str, Any])
async def update_checkout_session(
    session_id: str,
    request: ACPCheckoutUpdateRequest,
    acp_service: OfficialACPIntegrationService = Depends(get_acp_service)
) -> JSONResponse:
    """
    Update ACP checkout session
    
    Updates an existing checkout session with new line items or customer info.
    """
    try:
        updates = {}
        if request.line_items is not None:
            updates["line_items"] = request.line_items
        if request.customer_id is not None:
            updates["customer_id"] = request.customer_id
        if request.metadata is not None:
            updates["metadata"] = request.metadata
        
        session = await acp_service.update_checkout_session(session_id, updates)
        
        return JSONResponse(content=session.dict())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session update failed: {str(e)}")


@router.post("/payment-tokens", response_model=Dict[str, Any])
async def create_payment_token(
    request: ACPPaymentTokenRequest,
    acp_service: OfficialACPIntegrationService = Depends(get_acp_service)
) -> JSONResponse:
    """
    Create ACP delegated payment token
    
    Creates a delegated payment token for secure agent transactions.
    """
    try:
        # Convert amount dict to ACPMoney
        amount = ACPMoney(
            amount=request.amount["amount"],
            currency=request.amount.get("currency", "USD")
        )
        
        # Convert payment method string to enum
        payment_method = ACPPaymentMethod(request.payment_method)
        
        token = await acp_service.create_delegated_payment_token(
            merchant_id=request.merchant_id,
            amount=amount,
            payment_method=payment_method,
            metadata=request.metadata
        )
        
        return JSONResponse(
            content=token.dict(),
            status_code=201,
            headers={
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment token creation failed: {str(e)}")


@router.post("/checkout/{session_id}/complete", response_model=Dict[str, Any])
async def complete_checkout(
    session_id: str,
    request: ACPCheckoutCompleteRequest,
    acp_service: OfficialACPIntegrationService = Depends(get_acp_service)
) -> JSONResponse:
    """
    Complete ACP checkout with payment token
    
    Completes the checkout process using a delegated payment token.
    """
    try:
        # Convert payment token dict to ACPDelegatedPaymentToken
        payment_token = ACPDelegatedPaymentToken(
            id=request.payment_token["id"],
            merchant_id=request.payment_token["merchant_id"],
            amount=ACPMoney(
                amount=request.payment_token["amount"]["amount"],
                currency=request.payment_token["amount"].get("currency", "USD")
            ),
            payment_method=ACPPaymentMethod(request.payment_token["payment_method"]),
            expires_at=datetime.fromisoformat(request.payment_token["expires_at"]),
            metadata=request.payment_token.get("metadata", {})
        )
        
        order = await acp_service.complete_checkout(session_id, payment_token)
        
        return JSONResponse(
            content=order.dict(),
            status_code=201,
            headers={
                "Location": f"/v1/commerce/orders/{order.id}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout completion failed: {str(e)}")


@router.get("/orders/{order_id}", response_model=Dict[str, Any])
async def get_order(
    order_id: str,
    acp_service: OfficialACPIntegrationService = Depends(get_acp_service)
) -> JSONResponse:
    """
    Get ACP order
    
    Retrieves an order by ID.
    """
    try:
        if order_id not in acp_service.orders:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order = acp_service.orders[order_id]
        
        return JSONResponse(content=order.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order retrieval failed: {str(e)}")


@router.get("/products", response_model=List[Dict[str, Any]])
async def get_products(
    merchant_id: str,
    acp_service: OfficialACPIntegrationService = Depends(get_acp_service)
) -> JSONResponse:
    """
    Get ACP product catalog
    
    Retrieves the merchant's product catalog.
    """
    try:
        products = await acp_service.get_product_catalog(merchant_id)
        
        # Convert ACPProduct objects to dicts
        product_dicts = [product.__dict__ for product in products]
        
        return JSONResponse(content=product_dicts)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product catalog retrieval failed: {str(e)}")


@router.post("/webhooks")
async def handle_webhook(
    request: ACPWebhookRequest,
    x_acp_signature: Optional[str] = Header(None),
    acp_service: OfficialACPIntegrationService = Depends(get_acp_service)
) -> JSONResponse:
    """
    Handle ACP webhook events
    
    Processes incoming webhook events from payment processors or other services.
    """
    try:
        # Create webhook event
        event = ACPWebhookEvent(
            type=request.type,
            id=request.id,
            created=request.created,
            data=request.data,
            merchant_id=request.merchant_id
        )
        
        # Process webhook
        await acp_service.handle_webhook_event(event)
        
        return JSONResponse(
            content={"received": True},
            status_code=200
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    ACP Commerce API health check
    
    Returns the health status of the ACP Commerce API.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "acp-commerce",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "specification": "ACP 1.0.0"
        }
    )
