"""
BAIS Platform - Agentic Commerce Protocol (ACP) Integration Service

This service implements the Agentic Commerce Protocol to enable AI agents
to complete purchases directly within conversational interfaces while
keeping merchants in control of their commerce experience.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
import httpx
import hmac
import hashlib
from urllib.parse import urlencode

from pydantic import BaseModel, Field, validator
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...core.database_models import Business, BusinessService, Booking
from ...core.bais_schema_validator import BAISBusinessSchema, PaymentConfig


class PaymentMethod(str, Enum):
    """Supported payment methods for ACP"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"
    CRYPTOCURRENCY = "cryptocurrency"
    BUY_NOW_PAY_LATER = "buy_now_pay_later"


class PaymentTiming(str, Enum):
    """When payment is processed"""
    AT_CHECKOUT = "at_checkout"
    AT_BOOKING = "at_booking"
    ON_ARRIVAL = "on_arrival"
    AFTER_SERVICE = "after_service"


class OrderStatus(str, Enum):
    """Order status in ACP flow"""
    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_PROCESSING = "payment_processing"
    CONFIRMED = "confirmed"
    FULFILLING = "fulfilling"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class Money:
    """Money representation for ACP"""
    amount: float
    currency: str = "USD"
    
    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount, "currency": self.currency}


@dataclass
class Product:
    """Product representation for ACP"""
    id: str
    name: str
    description: str
    price: Money
    image_url: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ShippingOption:
    """Shipping option for ACP"""
    id: str
    name: str
    price: Money
    estimated_days: int
    description: Optional[str] = None


@dataclass
class TaxConfig:
    """Tax calculation configuration"""
    enabled: bool = True
    rate: float = 0.0  # Tax rate as decimal (0.08 = 8%)
    tax_id: Optional[str] = None
    exempt_categories: List[str] = None
    
    def __post_init__(self):
        if self.exempt_categories is None:
            self.exempt_categories = []


@dataclass
class ReturnsPolicy:
    """Returns policy configuration"""
    enabled: bool = True
    days_to_return: int = 30
    restocking_fee: float = 0.0
    description: str = "Standard return policy"


class DelegatedPaymentToken(BaseModel):
    """Delegated payment token for ACP"""
    token_id: str = Field(..., description="Unique token identifier")
    merchant_id: str = Field(..., description="Merchant identifier")
    amount: Money = Field(..., description="Authorized amount")
    currency: str = Field(default="USD")
    expires_at: datetime = Field(..., description="Token expiration")
    payment_method: PaymentMethod = Field(..., description="Payment method type")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SharedPaymentToken(BaseModel):
    """Shared payment token from payment provider"""
    provider: str = Field(..., description="Payment provider (stripe, etc.)")
    token: str = Field(..., description="Provider-specific token")
    amount: Money = Field(..., description="Token amount")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CheckoutSession(BaseModel):
    """ACP checkout session"""
    session_id: str = Field(..., description="Unique session identifier")
    merchant_id: str = Field(..., description="Merchant identifier")
    products: List[Product] = Field(..., description="Products in session")
    subtotal: Money = Field(..., description="Subtotal amount")
    tax: Money = Field(..., description="Tax amount")
    shipping: Optional[Money] = Field(None, description="Shipping cost")
    total: Money = Field(..., description="Total amount")
    status: OrderStatus = Field(default=OrderStatus.DRAFT)
    expires_at: datetime = Field(..., description="Session expiration")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StateUpdate(BaseModel):
    """Checkout state update"""
    products: Optional[List[Product]] = None
    shipping_option: Optional[ShippingOption] = None
    customer_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class OrderDetails(BaseModel):
    """Order details for payment processing"""
    session_id: str = Field(..., description="Checkout session ID")
    merchant_id: str = Field(..., description="Merchant identifier")
    customer_email: str = Field(..., description="Customer email")
    customer_name: str = Field(..., description="Customer name")
    billing_address: Dict[str, Any] = Field(..., description="Billing address")
    shipping_address: Optional[Dict[str, Any]] = None
    products: List[Product] = Field(..., description="Ordered products")
    total: Money = Field(..., description="Total amount")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaymentResult(BaseModel):
    """Payment processing result"""
    success: bool = Field(..., description="Payment success status")
    transaction_id: Optional[str] = Field(None, description="Transaction ID")
    payment_method: PaymentMethod = Field(..., description="Payment method used")
    amount: Money = Field(..., description="Amount charged")
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AcpRegistration(BaseModel):
    """ACP registration result"""
    business_id: str = Field(..., description="Business identifier")
    acp_endpoint: str = Field(..., description="ACP endpoint URL")
    product_feed_url: str = Field(..., description="Product feed URL")
    webhook_url: str = Field(..., description="Webhook endpoint URL")
    api_key: str = Field(..., description="API key for ACP")
    status: str = Field(default="active", description="Registration status")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CheckoutConfiguration(BaseModel):
    """ACP checkout configuration"""
    merchant_id: str = Field(..., description="Merchant identifier")
    supported_payment_methods: List[PaymentMethod] = Field(..., description="Supported payment methods")
    payment_timing: PaymentTiming = Field(default=PaymentTiming.AT_CHECKOUT)
    shipping_options: List[ShippingOption] = Field(default_factory=list)
    tax_config: TaxConfig = Field(default_factory=TaxConfig)
    returns_policy: ReturnsPolicy = Field(default_factory=ReturnsPolicy)
    webhook_url: str = Field(..., description="Webhook endpoint")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AcpWebhookEvent(BaseModel):
    """ACP webhook event"""
    event_type: str = Field(..., description="Event type")
    merchant_id: str = Field(..., description="Merchant identifier")
    session_id: str = Field(..., description="Session identifier")
    order_id: Optional[str] = Field(None, description="Order identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    signature: Optional[str] = Field(None, description="Webhook signature")


class AcpIntegrationService:
    """
    ACP Integration Service for BAIS Platform
    
    Handles Agentic Commerce Protocol integration, enabling AI agents
    to complete purchases while maintaining merchant control.
    """
    
    def __init__(self, db_session: Session, http_client: httpx.AsyncClient):
        self.db = db_session
        self.http = http_client
        self.sessions: Dict[str, CheckoutSession] = {}
        self.webhook_secret = "bais_acp_webhook_secret"  # Should be from config
        
    async def register_commerce_business(
        self, 
        business_id: str, 
        product_feed_url: str,
        webhook_config: Dict[str, Any]
    ) -> AcpRegistration:
        """
        Register a business for ACP-enabled commerce
        
        Args:
            business_id: Business identifier
            product_feed_url: URL to product catalog feed
            webhook_config: Webhook configuration
            
        Returns:
            AcpRegistration: Registration details
        """
        try:
            # Get business from database
            business = self.db.query(Business).filter(Business.id == business_id).first()
            if not business:
                raise HTTPException(status_code=404, detail="Business not found")
            
            # Generate ACP endpoint
            safe_name = business.name.lower().replace(' ', '-').strip()
            acp_endpoint = f"https://api.{safe_name}.com/acp"
            webhook_url = webhook_config.get('endpoint', f"{acp_endpoint}/webhooks")
            
            # Generate API key
            api_key = self._generate_api_key(business_id)
            
            # Create registration
            registration = AcpRegistration(
                business_id=business_id,
                acp_endpoint=acp_endpoint,
                product_feed_url=product_feed_url,
                webhook_url=webhook_url,
                api_key=api_key
            )
            
            # Store in database (would need new table for ACP registrations)
            # For now, we'll store in business metadata
            if not business.metadata:
                business.metadata = {}
            business.metadata['acp_registration'] = registration.dict()
            self.db.commit()
            
            return registration
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    
    async def generate_checkout_configuration(
        self, 
        business_schema: BAISBusinessSchema
    ) -> CheckoutConfiguration:
        """
        Transform BAIS schema to ACP checkout configuration
        
        Args:
            business_schema: BAIS business schema
            
        Returns:
            CheckoutConfiguration: ACP checkout configuration
        """
        try:
            # Extract payment methods from BAIS schema
            payment_methods = []
            for service in business_schema.services:
                for method in service.policies.payment.methods:
                    if method.value not in [m.value for m in payment_methods]:
                        payment_methods.append(PaymentMethod(method.value))
            
            # Determine payment timing
            payment_timing = PaymentTiming.AT_CHECKOUT
            if business_schema.services:
                first_service = business_schema.services[0]
                timing_mapping = {
                    "at_booking": PaymentTiming.AT_BOOKING,
                    "on_arrival": PaymentTiming.ON_ARRIVAL,
                    "after_service": PaymentTiming.AFTER_SERVICE
                }
                payment_timing = timing_mapping.get(
                    first_service.policies.payment.timing, 
                    PaymentTiming.AT_CHECKOUT
                )
            
            # Create tax configuration
            tax_config = TaxConfig(
                enabled=True,
                rate=0.08,  # Default 8% tax rate
                exempt_categories=[]
            )
            
            # Create returns policy
            returns_policy = ReturnsPolicy(
                enabled=True,
                days_to_return=30,
                description="Standard return policy"
            )
            
            return CheckoutConfiguration(
                merchant_id=business_schema.business_info.external_id,
                supported_payment_methods=payment_methods,
                payment_timing=payment_timing,
                shipping_options=[],  # Would be populated from business data
                tax_config=tax_config,
                returns_policy=returns_policy,
                webhook_url=f"https://api.{business_schema.business_info.name.lower().replace(' ', '-')}.com/acp/webhooks"
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Configuration generation failed: {str(e)}")
    
    async def initialize_checkout(
        self, 
        session_id: str, 
        products: List[Product]
    ) -> CheckoutSession:
        """
        Initialize a new checkout session
        
        Args:
            session_id: Unique session identifier
            products: Products to include in checkout
            
        Returns:
            CheckoutSession: Initialized checkout session
        """
        try:
            # Calculate totals
            subtotal_amount = sum(p.price.amount for p in products)
            subtotal = Money(amount=subtotal_amount, currency="USD")
            
            # Calculate tax (8% default)
            tax_amount = subtotal_amount * 0.08
            tax = Money(amount=tax_amount, currency="USD")
            
            # Calculate total
            total_amount = subtotal_amount + tax_amount
            total = Money(amount=total_amount, currency="USD")
            
            # Create session
            session = CheckoutSession(
                session_id=session_id,
                merchant_id="default_merchant",  # Would come from context
                products=products,
                subtotal=subtotal,
                tax=tax,
                total=total,
                expires_at=datetime.utcnow() + timedelta(minutes=30)
            )
            
            # Store session
            self.sessions[session_id] = session
            
            return session
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Checkout initialization failed: {str(e)}")
    
    async def update_checkout_state(
        self, 
        session_id: str, 
        updates: StateUpdate
    ) -> CheckoutSession:
        """
        Update checkout session state
        
        Args:
            session_id: Session identifier
            updates: State updates to apply
            
        Returns:
            CheckoutSession: Updated checkout session
        """
        try:
            if session_id not in self.sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.sessions[session_id]
            
            # Apply updates
            if updates.products:
                session.products = updates.products
                # Recalculate totals
                subtotal_amount = sum(p.price.amount for p in updates.products)
                session.subtotal = Money(amount=subtotal_amount, currency="USD")
                session.tax = Money(amount=subtotal_amount * 0.08, currency="USD")
                session.total = Money(amount=subtotal_amount * 1.08, currency="USD")
            
            if updates.shipping_option:
                shipping_cost = updates.shipping_option.price.amount
                session.shipping = updates.shipping_option.price
                session.total = Money(
                    amount=session.total.amount + shipping_cost,
                    currency="USD"
                )
            
            if updates.customer_info:
                session.metadata.update(updates.customer_info)
            
            if updates.metadata:
                session.metadata.update(updates.metadata)
            
            # Update session
            self.sessions[session_id] = session
            
            return session
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"State update failed: {str(e)}")
    
    async def handle_delegated_payment(
        self, 
        payment_token: SharedPaymentToken,
        order_details: OrderDetails
    ) -> PaymentResult:
        """
        Process payments via delegated tokens
        
        Args:
            payment_token: Delegated payment token
            order_details: Order details
            
        Returns:
            PaymentResult: Payment processing result
        """
        try:
            # Validate session
            if order_details.session_id not in self.sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.sessions[order_details.session_id]
            
            # Process payment based on provider
            if payment_token.provider == "stripe":
                result = await self._process_stripe_payment(payment_token, order_details)
            elif payment_token.provider == "bais_internal":
                result = await self._process_internal_payment(payment_token, order_details)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported payment provider: {payment_token.provider}")
            
            # Update session status
            if result.success:
                session.status = OrderStatus.CONFIRMED
                self.sessions[order_details.session_id] = session
                
                # Create booking record
                await self._create_booking_record(order_details, result)
            
            return result
            
        except Exception as e:
            return PaymentResult(
                success=False,
                payment_method=PaymentMethod.CREDIT_CARD,  # Default
                amount=order_details.total,
                error_message=str(e)
            )
    
    async def webhook_handler(self, event: AcpWebhookEvent) -> None:
        """
        Handle ACP webhook events
        
        Args:
            event: ACP webhook event
        """
        try:
            # Verify webhook signature
            if not self._verify_webhook_signature(event):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
            
            # Process event based on type
            if event.event_type == "payment.completed":
                await self._handle_payment_completed(event)
            elif event.event_type == "order.cancelled":
                await self._handle_order_cancelled(event)
            elif event.event_type == "order.fulfilled":
                await self._handle_order_fulfilled(event)
            else:
                # Log unknown event type
                print(f"Unknown webhook event type: {event.event_type}")
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")
    
    def _generate_api_key(self, business_id: str) -> str:
        """Generate API key for business"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        data = f"{business_id}:{timestamp}"
        signature = hmac.new(
            self.webhook_secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"acp_{business_id}_{timestamp}_{signature[:16]}"
    
    async def _process_stripe_payment(
        self, 
        payment_token: SharedPaymentToken, 
        order_details: OrderDetails
    ) -> PaymentResult:
        """Process payment via Stripe"""
        # This would integrate with actual Stripe API
        # For demo purposes, we'll simulate success
        return PaymentResult(
            success=True,
            transaction_id=f"stripe_{uuid.uuid4().hex[:16]}",
            payment_method=PaymentMethod.CREDIT_CARD,
            amount=order_details.total,
            metadata={"provider": "stripe", "token": payment_token.token}
        )
    
    async def _process_internal_payment(
        self, 
        payment_token: SharedPaymentToken, 
        order_details: OrderDetails
    ) -> PaymentResult:
        """Process payment via BAIS internal system"""
        # This would integrate with BAIS payment processing
        # For demo purposes, we'll simulate success
        return PaymentResult(
            success=True,
            transaction_id=f"bais_{uuid.uuid4().hex[:16]}",
            payment_method=PaymentMethod.CREDIT_CARD,
            amount=order_details.total,
            metadata={"provider": "bais", "token": payment_token.token}
        )
    
    async def _create_booking_record(
        self, 
        order_details: OrderDetails, 
        payment_result: PaymentResult
    ) -> None:
        """Create booking record in database"""
        try:
            # Find business
            business = self.db.query(Business).filter(
                Business.external_id == order_details.merchant_id
            ).first()
            
            if business:
                # Create booking
                booking = Booking(
                    business_id=business.id,
                    confirmation_number=f"ACP_{uuid.uuid4().hex[:8].upper()}",
                    agent_id="acp_agent",
                    customer_name=order_details.customer_name,
                    customer_email=order_details.customer_email,
                    booking_data=order_details.dict(),
                    total_amount=order_details.total.amount,
                    currency=order_details.total.currency,
                    payment_status="completed",
                    payment_data=payment_result.dict(),
                    ap2_transaction_id=payment_result.transaction_id
                )
                
                self.db.add(booking)
                self.db.commit()
                
        except Exception as e:
            print(f"Failed to create booking record: {e}")
    
    def _verify_webhook_signature(self, event: AcpWebhookEvent) -> bool:
        """Verify webhook signature"""
        if not event.signature:
            return False
        
        # Simple signature verification (in production, use proper HMAC)
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            event.json().encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(event.signature, expected_signature)
    
    async def _handle_payment_completed(self, event: AcpWebhookEvent) -> None:
        """Handle payment completed webhook"""
        print(f"Payment completed for session {event.session_id}")
        # Update booking status, send confirmation emails, etc.
    
    async def _handle_order_cancelled(self, event: AcpWebhookEvent) -> None:
        """Handle order cancelled webhook"""
        print(f"Order cancelled for session {event.session_id}")
        # Process cancellation, send notifications, etc.
    
    async def _handle_order_fulfilled(self, event: AcpWebhookEvent) -> None:
        """Handle order fulfilled webhook"""
        print(f"Order fulfilled for session {event.session_id}")
        # Update fulfillment status, send completion notifications, etc.


class CommerceBridge:
    """
    Commerce Bridge for ACP Integration
    
    Provides a clean interface for AI agents to interact with commerce functionality
    """
    
    def __init__(self, acp_service: AcpIntegrationService):
        self.acp = acp_service
    
    async def initialize_checkout(self, session_id: str, products: List[Product]) -> CheckoutSession:
        """Initialize checkout session"""
        return await self.acp.initialize_checkout(session_id, products)
    
    async def update_checkout_state(self, session_id: str, updates: StateUpdate) -> CheckoutSession:
        """Update checkout state"""
        return await self.acp.update_checkout_state(session_id, updates)
    
    async def process_payment(
        self, 
        session_id: str, 
        payment_token: DelegatedPaymentToken
    ) -> PaymentResult:
        """Process payment"""
        # Convert delegated token to shared token
        shared_token = SharedPaymentToken(
            provider="stripe",  # Would be determined from token
            token=payment_token.token_id,
            amount=payment_token.amount
        )
        
        # Get session for order details
        if session_id not in self.acp.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = self.acp.sessions[session_id]
        
        # Create order details
        order_details = OrderDetails(
            session_id=session_id,
            merchant_id=session.merchant_id,
            customer_email="customer@example.com",  # Would come from session metadata
            customer_name="Customer Name",  # Would come from session metadata
            billing_address={},  # Would come from session metadata
            products=session.products,
            total=session.total
        )
        
        return await self.acp.handle_delegated_payment(shared_token, order_details)
    
    async def webhook_handler(self, event: AcpWebhookEvent) -> None:
        """Handle webhook events"""
        await self.acp.webhook_handler(event)
