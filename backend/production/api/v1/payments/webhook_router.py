"""
AP2 Payment Webhook Router
Handles real-time payment status updates from AP2 network

This module implements the complete AP2 webhook functionality to complement
the existing monitoring metrics with actual webhook endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
import json
import hashlib
import hmac
from datetime import datetime
from pydantic import BaseModel, Field

from ...core.payments.payment_coordinator import PaymentCoordinator
from ...core.payments.ap2_client import AP2Client
from ...core.protocol_configurations import AP2_CONFIG, AP2EventType
from ...monitoring.metrics import track_webhook_processing

router = APIRouter(prefix="/webhooks", tags=["AP2 Webhooks"])


class PaymentWebhookData(BaseModel):
    """AP2 payment webhook data model"""
    event_type: str = Field(..., description="Type of webhook event")
    payment_id: str = Field(..., description="Payment identifier")
    mandate_id: str = Field(None, description="Mandate identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    signature: str = Field(..., description="Webhook signature")
    business_id: str = Field(..., description="Business identifier")
    status: str = Field(..., description="Payment status")
    amount: float = Field(None, description="Payment amount")
    currency: str = Field(None, description="Payment currency")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebhookValidationResult(BaseModel):
    """Webhook validation result"""
    is_valid: bool
    error_message: str = None
    signature_match: bool = False
    timestamp_valid: bool = False


class AP2WebhookValidator:
    """
    Validates AP2 webhook signatures and data
    
    Implements proper security validation for webhook endpoints
    """
    
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret.encode('utf-8')
    
    def validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Validate webhook signature using HMAC-SHA256
        
        Args:
            payload: Raw webhook payload
            signature: Signature from webhook header
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Remove 'sha256=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.webhook_secret,
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures using constant-time comparison
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            print(f"Webhook signature validation error: {e}")
            return False
    
    def validate_webhook_data(self, webhook_data: PaymentWebhookData) -> WebhookValidationResult:
        """
        Validate webhook data structure and content
        
        Args:
            webhook_data: Webhook data to validate
            
        Returns:
            WebhookValidationResult with validation status
        """
        result = WebhookValidationResult(is_valid=True)
        
        try:
            # Validate event type
            try:
                AP2EventType(webhook_data.event_type)
            except ValueError:
                result.is_valid = False
                result.error_message = f"Invalid event type: {webhook_data.event_type}"
                return result
            
            # Validate timestamp (not too old)
            now = datetime.utcnow()
            time_diff = abs((now - webhook_data.timestamp).total_seconds())
            if time_diff > AP2_CONFIG.WEBHOOK_TIMEOUT_SECONDS * 10:  # Allow 10x timeout for timestamp validation
                result.timestamp_valid = False
                result.is_valid = False
                result.error_message = f"Webhook timestamp too old: {time_diff} seconds"
                return result
            
            result.timestamp_valid = True
            
            # Validate required fields based on event type
            if webhook_data.event_type in [AP2EventType.PAYMENT_COMPLETED.value, AP2EventType.PAYMENT_FAILED.value]:
                if not webhook_data.amount or webhook_data.amount <= 0:
                    result.is_valid = False
                    result.error_message = "Amount is required for payment events"
                    return result
                
                if not webhook_data.currency:
                    result.is_valid = False
                    result.error_message = "Currency is required for payment events"
                    return result
            
            if webhook_data.event_type in [AP2EventType.MANDATE_REVOKED.value, AP2EventType.MANDATE_EXPIRED.value]:
                if not webhook_data.mandate_id:
                    result.is_valid = False
                    result.error_message = "Mandate ID is required for mandate events"
                    return result
            
            return result
            
        except Exception as e:
            result.is_valid = False
            result.error_message = f"Webhook data validation error: {str(e)}"
            return result


def get_payment_coordinator() -> PaymentCoordinator:
    """FastAPI dependency for getting payment coordinator"""
    # This would be injected via dependency injection in a real application
    from ...core.payments.ap2_client import AP2Client, AP2ClientConfig
    from ...core.business_query_repository import BusinessQueryRepository
    from ...config.ap2_settings import get_ap2_client_config
    
    ap2_config = AP2ClientConfig(**get_ap2_client_config())
    ap2_client = AP2Client(ap2_config)
    business_repo = BusinessQueryRepository(None)  # Would be injected properly
    
    return PaymentCoordinator(ap2_client, business_repo)


def get_webhook_validator() -> AP2WebhookValidator:
    """FastAPI dependency for getting webhook validator"""
    # This would get the webhook secret from configuration
    webhook_secret = "your-webhook-secret"  # Should come from environment/config
    return AP2WebhookValidator(webhook_secret)


@router.post("/payment-status")
@track_webhook_processing("payment_status")
async def handle_payment_webhook(
    request: Request,
    webhook_data: PaymentWebhookData,
    coordinator: PaymentCoordinator = Depends(get_payment_coordinator),
    validator: AP2WebhookValidator = Depends(get_webhook_validator)
) -> Dict[str, str]:
    """
    Handle real-time payment status updates from AP2 network
    
    This endpoint processes webhook notifications for payment events
    and updates the internal payment state accordingly.
    """
    try:
        # Get raw request body for signature validation
        raw_body = await request.body()
        payload = raw_body.decode('utf-8')
        
        # Get signature from headers
        signature = request.headers.get(AP2_CONFIG.WEBHOOK_SIGNATURE_HEADER)
        if not signature:
            raise HTTPException(status_code=401, detail="Missing webhook signature")
        
        # Validate webhook signature
        if not validator.validate_webhook_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Validate webhook data
        validation_result = validator.validate_webhook_data(webhook_data)
        if not validation_result.is_valid:
            raise HTTPException(status_code=400, detail=validation_result.error_message)
        
        # Process webhook based on event type
        event_type = AP2EventType(webhook_data.event_type)
        
        if event_type == AP2EventType.PAYMENT_COMPLETED:
            await _handle_payment_completion(webhook_data, coordinator)
        elif event_type == AP2EventType.PAYMENT_FAILED:
            await _handle_payment_failure(webhook_data, coordinator)
        elif event_type == AP2EventType.MANDATE_REVOKED:
            await _handle_mandate_revocation(webhook_data, coordinator)
        elif event_type == AP2EventType.MANDATE_EXPIRED:
            await _handle_mandate_expiry(webhook_data, coordinator)
        elif event_type == AP2EventType.PAYMENT_AUTHORIZED:
            await _handle_payment_authorization(webhook_data, coordinator)
        elif event_type == AP2EventType.PAYMENT_DECLINED:
            await _handle_payment_decline(webhook_data, coordinator)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported event type: {webhook_data.event_type}")
        
        return {
            "status": "processed",
            "event_id": webhook_data.payment_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


async def _handle_payment_completion(webhook_data: PaymentWebhookData, coordinator: PaymentCoordinator) -> None:
    """Handle payment completion webhook"""
    try:
        # Update payment status in coordinator
        # This would integrate with the actual payment coordinator logic
        print(f"Payment completed: {webhook_data.payment_id}, Amount: {webhook_data.amount} {webhook_data.currency}")
        
        # Notify business system of payment completion
        await coordinator.handle_payment_completion(webhook_data)
        
    except Exception as e:
        print(f"Error handling payment completion: {e}")
        raise


async def _handle_payment_failure(webhook_data: PaymentWebhookData, coordinator: PaymentCoordinator) -> None:
    """Handle payment failure webhook"""
    try:
        print(f"Payment failed: {webhook_data.payment_id}, Reason: {webhook_data.metadata.get('failure_reason', 'Unknown')}")
        
        # Notify business system of payment failure
        await coordinator.handle_payment_failure(webhook_data)
        
    except Exception as e:
        print(f"Error handling payment failure: {e}")
        raise


async def _handle_mandate_revocation(webhook_data: PaymentWebhookData, coordinator: PaymentCoordinator) -> None:
    """Handle mandate revocation webhook"""
    try:
        print(f"Mandate revoked: {webhook_data.mandate_id}")
        
        # Update mandate status
        await coordinator.handle_mandate_revocation(webhook_data)
        
    except Exception as e:
        print(f"Error handling mandate revocation: {e}")
        raise


async def _handle_mandate_expiry(webhook_data: PaymentWebhookData, coordinator: PaymentCoordinator) -> None:
    """Handle mandate expiry webhook"""
    try:
        print(f"Mandate expired: {webhook_data.mandate_id}")
        
        # Update mandate status
        await coordinator.handle_mandate_expiry(webhook_data)
        
    except Exception as e:
        print(f"Error handling mandate expiry: {e}")
        raise


async def _handle_payment_authorization(webhook_data: PaymentWebhookData, coordinator: PaymentCoordinator) -> None:
    """Handle payment authorization webhook"""
    try:
        print(f"Payment authorized: {webhook_data.payment_id}")
        
        # Update payment authorization status
        await coordinator.handle_payment_authorization(webhook_data)
        
    except Exception as e:
        print(f"Error handling payment authorization: {e}")
        raise


async def _handle_payment_decline(webhook_data: PaymentWebhookData, coordinator: PaymentCoordinator) -> None:
    """Handle payment decline webhook"""
    try:
        print(f"Payment declined: {webhook_data.payment_id}")
        
        # Update payment decline status
        await coordinator.handle_payment_decline(webhook_data)
        
    except Exception as e:
        print(f"Error handling payment decline: {e}")
        raise


@router.post("/mandate-status")
@track_webhook_processing("mandate_status")
async def handle_mandate_webhook(
    request: Request,
    webhook_data: PaymentWebhookData,
    coordinator: PaymentCoordinator = Depends(get_payment_coordinator),
    validator: AP2WebhookValidator = Depends(get_webhook_validator)
) -> Dict[str, str]:
    """
    Handle mandate status updates from AP2 network
    
    This endpoint processes webhook notifications for mandate events
    such as creation, revocation, and expiry.
    """
    try:
        # Validate webhook (same validation logic as payment webhook)
        raw_body = await request.body()
        payload = raw_body.decode('utf-8')
        
        signature = request.headers.get(AP2_CONFIG.WEBHOOK_SIGNATURE_HEADER)
        if not signature:
            raise HTTPException(status_code=401, detail="Missing webhook signature")
        
        if not validator.validate_webhook_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        validation_result = validator.validate_webhook_data(webhook_data)
        if not validation_result.is_valid:
            raise HTTPException(status_code=400, detail=validation_result.error_message)
        
        # Process mandate events
        if webhook_data.event_type == AP2EventType.MANDATE_REVOKED.value:
            await _handle_mandate_revocation(webhook_data, coordinator)
        elif webhook_data.event_type == AP2EventType.MANDATE_EXPIRED.value:
            await _handle_mandate_expiry(webhook_data, coordinator)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported mandate event type: {webhook_data.event_type}")
        
        return {
            "status": "processed",
            "event_id": webhook_data.mandate_id or webhook_data.payment_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mandate webhook processing failed: {str(e)}")


@router.get("/health")
async def webhook_health_check() -> Dict[str, str]:
    """Health check endpoint for webhook service"""
    return {
        "status": "healthy",
        "service": "ap2-webhooks",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.post("/test")
async def test_webhook_endpoint(
    test_data: PaymentWebhookData,
    validator: AP2WebhookValidator = Depends(get_webhook_validator)
) -> Dict[str, Any]:
    """
    Test endpoint for webhook validation (development only)
    
    This endpoint allows testing webhook validation without requiring
    actual webhook signatures.
    """
    validation_result = validator.validate_webhook_data(test_data)
    
    return {
        "validation_result": validation_result.dict(),
        "test_data": test_data.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }
