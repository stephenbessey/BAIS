from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from dataclasses import asdict

from .models import AP2Mandate, PaymentStatus, VerifiableCredential
from .ap2_client import AP2Client
from ..business_query_repository import BusinessQueryRepository


class MandateValidationError(Exception):
    """Raised when mandate validation fails"""
    pass


class MandateManager:
    """
    Manages AP2 mandate lifecycle
    Follows Single Responsibility for mandate operations
    """
    
    def __init__(self, ap2_client: AP2Client, business_repository: BusinessQueryRepository):
        self._ap2_client = ap2_client
        self._business_repository = business_repository
        self._active_mandates: Dict[str, AP2Mandate] = {}
    
    async def create_intent_mandate(
        self, 
        user_id: str,
        business_id: str,
        intent_description: str,
        constraints: Dict[str, Any],
        expiry_hours: int = 24
    ) -> AP2Mandate:
        """Create and validate an intent mandate"""
        
        # Validate business capability
        business = self._business_repository.find_by_id(business_id)
        if not business or not business.ap2_enabled:
            raise MandateValidationError(f"Business {business_id} is not AP2-enabled")
        
        # Validate constraints
        self._validate_intent_constraints(constraints, business)
        
        # Create mandate through AP2 client
        mandate = await self._ap2_client.create_intent_mandate(
            user_id=user_id,
            business_id=business_id,
            intent_description=intent_description,
            constraints=constraints
        )
        
        # Store in local cache
        self._active_mandates[mandate.id] = mandate
        
        return mandate
    
    async def create_cart_mandate(
        self,
        intent_mandate_id: str,
        cart_items: List[Dict[str, Any]],
        pricing_validation: bool = True
    ) -> AP2Mandate:
        """Create cart mandate from intent mandate"""
        
        # Validate intent mandate exists and is active
        intent_mandate = await self.get_mandate(intent_mandate_id)
        if not intent_mandate or intent_mandate.status != "active":
            raise MandateValidationError(f"Intent mandate {intent_mandate_id} not found or inactive")
        
        # Validate cart items against intent constraints
        self._validate_cart_items(cart_items, intent_mandate)
        
        # Calculate pricing
        total_amount, currency = self._calculate_cart_total(cart_items)
        
        # Optional: Real-time pricing validation with business
        if pricing_validation:
            await self._validate_pricing_with_business(
                intent_mandate.business_id, 
                cart_items, 
                total_amount
            )
        
        # Create cart mandate
        cart_mandate = await self._ap2_client.create_cart_mandate(
            intent_mandate_id=intent_mandate_id,
            cart_items=cart_items,
            total_amount=total_amount,
            currency=currency
        )
        
        # Update intent mandate status
        intent_mandate.status = "used"
        self._active_mandates[cart_mandate.id] = cart_mandate
        
        return cart_mandate
    
    async def get_mandate(self, mandate_id: str) -> Optional[AP2Mandate]:
        """Retrieve mandate by ID"""
        
        # Check local cache first
        if mandate_id in self._active_mandates:
            mandate = self._active_mandates[mandate_id]
            
            # Check if expired
            if mandate.expires_at and mandate.expires_at < datetime.utcnow():
                mandate.status = "expired"
                return mandate
            
            return mandate
        
        # Fetch from AP2 network if not in cache
        try:
            mandate = await self._ap2_client.get_mandate(mandate_id)
            self._active_mandates[mandate_id] = mandate
            return mandate
        except Exception:
            return None
    
    async def revoke_mandate(self, mandate_id: str, reason: str = "user_requested") -> bool:
        """Revoke an active mandate"""
        mandate = await self.get_mandate(mandate_id)
        
        if not mandate or mandate.status != "active":
            return False
        
        try:
            await self._ap2_client.revoke_mandate(mandate_id, reason)
            mandate.status = "revoked"
            return True
        except Exception:
            return False
    
    def _validate_intent_constraints(
        self, 
        constraints: Dict[str, Any], 
        business: Any
    ) -> None:
        """Validate intent constraints against business capabilities"""
        
        # Validate price constraints
        if "max_amount" in constraints:
            max_amount = constraints["max_amount"]
            if max_amount <= 0:
                raise MandateValidationError("Maximum amount must be positive")
        
        # Validate payment method constraints
        if "payment_methods" in constraints:
            requested_methods = set(constraints["payment_methods"])
            supported_methods = set(business.ap2_supported_payment_methods or [])
            
            if not requested_methods.issubset(supported_methods):
                unsupported = requested_methods - supported_methods
                raise MandateValidationError(f"Unsupported payment methods: {unsupported}")
        
        # Validate timing constraints
        if "expiry_time" in constraints:
            expiry = datetime.fromisoformat(constraints["expiry_time"])
            if expiry <= datetime.utcnow():
                raise MandateValidationError("Expiry time must be in the future")
    
    def _validate_cart_items(
        self, 
        cart_items: List[Dict[str, Any]], 
        intent_mandate: AP2Mandate
    ) -> None:
        """Validate cart items against intent mandate constraints"""
        
        constraints = intent_mandate.data.get("constraints", {})
        
        # Validate total amount against max_amount constraint
        if "max_amount" in constraints:
            total_amount, _ = self._calculate_cart_total(cart_items)
            if total_amount > constraints["max_amount"]:
                raise MandateValidationError(
                    f"Cart total {total_amount} exceeds maximum allowed {constraints['max_amount']}"
                )
        
        # Validate item categories if specified
        if "allowed_categories" in constraints:
            allowed_categories = set(constraints["allowed_categories"])
            for item in cart_items:
                item_category = item.get("category")
                if item_category and item_category not in allowed_categories:
                    raise MandateValidationError(
                        f"Item category '{item_category}' not allowed by intent mandate"
                    )
        
        # Validate quantity limits
        if "max_quantity_per_item" in constraints:
            max_qty = constraints["max_quantity_per_item"]
            for item in cart_items:
                if item.get("quantity", 1) > max_qty:
                    raise MandateValidationError(
                        f"Item quantity {item['quantity']} exceeds limit {max_qty}"
                    )
    
    def _calculate_cart_total(self, cart_items: List[Dict[str, Any]]) -> tuple[float, str]:
        """Calculate cart total amount and determine currency"""
        total = 0.0
        currency = "USD"  # Default currency
        
        for item in cart_items:
            price = item.get("price", 0)
            quantity = item.get("quantity", 1)
            total += price * quantity
            
            # Use currency from first item, assume all items same currency
            if "currency" in item and not currency:
                currency = item["currency"]
        
        return total, currency
    
    async def _validate_pricing_with_business(
        self,
        business_id: str,
        cart_items: List[Dict[str, Any]],
        expected_total: float
    ) -> None:
        """Validate pricing with business system in real-time"""
        
        business = self._business_repository.find_by_id(business_id)
        
        # Make real-time pricing check with business API
        try:
            # This would integrate with business pricing API
            # For now, we'll simulate validation
            pricing_response = await self._check_business_pricing(business, cart_items)
            
            if abs(pricing_response["total"] - expected_total) > 0.01:  # Allow for small rounding differences
                raise MandateValidationError(
                    f"Price mismatch: expected {expected_total}, business quoted {pricing_response['total']}"
                )
                
        except Exception as e:
            # Log the error but don't fail the mandate creation unless it's critical
            print(f"Warning: Could not validate pricing with business {business_id}: {e}")
    
    async def _check_business_pricing(self, business: Any, cart_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check pricing with business API - placeholder for real implementation"""
        # This would make actual API call to business pricing endpoint
        # For demo purposes, return the calculated total
        total, currency = self._calculate_cart_total(cart_items)
        return {"total": total, "currency": currency, "valid": True}
