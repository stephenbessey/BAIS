from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

from .models import AP2Mandate, AP2Transaction, PaymentMethod, VerifiableCredential
from .ap2_mandate_validator import AP2MandateValidator, AP2MandateValidationError


@dataclass
class AP2ClientConfig:
    """Configuration for AP2 client - follows Parameter Object pattern"""
    base_url: str
    client_id: str
    private_key: str
    public_key: str
    timeout: int = 30


class AP2Client:
    """
    AP2 Protocol Client
    Handles all communication with AP2-compliant payment processors
    """
    
    def __init__(self, config: AP2ClientConfig):
        self._config = config
        self._http_client = httpx.AsyncClient(timeout=config.timeout)
        self._private_key = self._load_private_key(config.private_key)
        self._mandate_validator = AP2MandateValidator(config.public_key)
    
    async def create_intent_mandate(
        self, 
        user_id: str, 
        business_id: str, 
        intent_description: str,
        constraints: Dict[str, Any]
    ) -> AP2Mandate:
        """Create an Intent Mandate for user authorization"""
        mandate_data = {
            "type": "intent",
            "userId": user_id,
            "businessId": business_id,
            "description": intent_description,
            "constraints": constraints,
            "timestamp": datetime.utcnow().isoformat(),
            "expiresAt": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        # Sign the mandate
        signed_mandate = self._sign_mandate(mandate_data)
        
        # Submit to AP2 network
        response = await self._http_client.post(
            f"{self._config.base_url}/mandates/intent",
            json=signed_mandate,
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        
        return AP2Mandate.from_dict(response.json())
    
    async def create_cart_mandate(
        self,
        intent_mandate_id: str,
        cart_items: List[Dict[str, Any]],
        total_amount: float,
        currency: str
    ) -> AP2Mandate:
        """Create a Cart Mandate with specific items and pricing"""
        mandate_data = {
            "type": "cart",
            "intentMandateId": intent_mandate_id,
            "items": cart_items,
            "totalAmount": total_amount,
            "currency": currency,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        signed_mandate = self._sign_mandate(mandate_data)
        
        response = await self._http_client.post(
            f"{self._config.base_url}/mandates/cart",
            json=signed_mandate,
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        
        return AP2Mandate.from_dict(response.json())
    
    async def execute_payment(
        self,
        cart_mandate_id: str,
        payment_method: PaymentMethod
    ) -> AP2Transaction:
        """Execute payment using AP2 protocol"""
        transaction_data = {
            "cartMandateId": cart_mandate_id,
            "paymentMethod": payment_method.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = await self._http_client.post(
            f"{self._config.base_url}/transactions",
            json=transaction_data,
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        
        return AP2Transaction.from_dict(response.json())
    
    def _sign_mandate(self, mandate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sign mandate with private key for cryptographic verification"""
        mandate_json = json.dumps(mandate_data, sort_keys=True)
        signature = self._private_key.sign(
            mandate_json.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return {
            "mandate": mandate_data,
            "signature": signature.hex(),
            "publicKey": self._config.public_key
        }
    
    def _load_private_key(self, private_key_pem: str):
        """Load private key from PEM format"""
        return serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None
        )
    
    async def get_mandate(self, mandate_id: str) -> Optional[AP2Mandate]:
        """Retrieve a mandate by ID from AP2 network"""
        try:
            response = await self._http_client.get(
                f"{self._config.base_url}/mandates/{mandate_id}",
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            mandate = AP2Mandate.from_dict(response.json())
            
            # CRITICAL SECURITY: Validate mandate signature
            if not self._mandate_validator.verify_mandate(mandate):
                raise AP2MandateValidationError(f"Invalid signature for mandate {mandate_id}")
            
            return mandate
        except httpx.HTTPStatusError:
            return None
        except AP2MandateValidationError:
            # Log security violation
            print(f"SECURITY WARNING: Invalid mandate signature for {mandate_id}")
            return None
    
    async def revoke_mandate(self, mandate_id: str, reason: str = "user_requested") -> bool:
        """Revoke an active mandate"""
        try:
            response = await self._http_client.post(
                f"{self._config.base_url}/mandates/{mandate_id}/revoke",
                json={"reason": reason},
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError:
            return False
    
    async def get_transaction_status(self, transaction_id: str) -> Optional[AP2Transaction]:
        """Get transaction status from AP2 network"""
        try:
            response = await self._http_client.get(
                f"{self._config.base_url}/transactions/{transaction_id}",
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return AP2Transaction.from_dict(response.json())
        except httpx.HTTPStatusError:
            return None
    
    async def close(self):
        """Close the HTTP client"""
        await self._http_client.aclose()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for AP2 requests"""
        return {
            "Authorization": f"Bearer {self._config.client_id}",
            "Content-Type": "application/json",
            "AP2-Version": "1.0"
        }
    
    # MISSING IMPLEMENTATION: Complete payment workflow methods
    async def create_intent_mandate_with_constraints(
        self, 
        user_id: str, 
        business_id: str, 
        intent_description: str,
        constraints: Dict[str, Any],
        expiry_hours: int = 24
    ) -> AP2Mandate:
        """
        Create intent mandate with comprehensive constraints
        
        Args:
            user_id: User identifier
            business_id: Business identifier  
            intent_description: Description of user intent
            constraints: Payment constraints (max_amount, payment_methods, etc.)
            expiry_hours: Hours until mandate expires
            
        Returns:
            Created AP2Mandate
        """
        mandate_data = {
            "type": "intent",
            "userId": user_id,
            "businessId": business_id,
            "description": intent_description,
            "constraints": constraints,
            "timestamp": datetime.utcnow().isoformat(),
            "expiresAt": (datetime.utcnow() + timedelta(hours=expiry_hours)).isoformat()
        }
        
        signed_mandate = self._sign_mandate(mandate_data)
        
        response = await self._http_client.post(
            f"{self._config.base_url}/mandates/intent",
            json=signed_mandate,
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        
        return AP2Mandate.from_dict(response.json())
    
    async def create_cart_mandate_with_validation(
        self,
        intent_mandate_id: str,
        cart_items: List[Dict[str, Any]],
        total_amount: float,
        currency: str,
        validate_with_business: bool = True
    ) -> AP2Mandate:
        """
        Create cart mandate with business validation
        
        Args:
            intent_mandate_id: ID of the intent mandate
            cart_items: List of cart items
            total_amount: Total cart amount
            currency: Currency code
            validate_with_business: Whether to validate with business system
            
        Returns:
            Created AP2Mandate
        """
        # Validate intent mandate first
        intent_mandate = await self.get_mandate(intent_mandate_id)
        if not intent_mandate:
            raise ValueError(f"Intent mandate {intent_mandate_id} not found")
        
        if intent_mandate.status != "active":
            raise ValueError(f"Intent mandate {intent_mandate_id} is not active")
        
        # Validate against intent constraints
        constraints = intent_mandate.data.get("constraints", {})
        if "max_amount" in constraints and total_amount > constraints["max_amount"]:
            raise ValueError(f"Cart total {total_amount} exceeds maximum {constraints['max_amount']}")
        
        mandate_data = {
            "type": "cart",
            "intentMandateId": intent_mandate_id,
            "items": cart_items,
            "totalAmount": total_amount,
            "currency": currency,
            "timestamp": datetime.utcnow().isoformat(),
            "businessValidation": validate_with_business
        }
        
        signed_mandate = self._sign_mandate(mandate_data)
        
        response = await self._http_client.post(
            f"{self._config.base_url}/mandates/cart",
            json=signed_mandate,
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        
        return AP2Mandate.from_dict(response.json())
    
    async def execute_payment_with_verification(
        self,
        cart_mandate_id: str,
        payment_method: PaymentMethod,
        verification_required: bool = True
    ) -> AP2Transaction:
        """
        Execute payment with additional verification
        
        Args:
            cart_mandate_id: ID of the cart mandate
            payment_method: Payment method to use
            verification_required: Whether to require additional verification
            
        Returns:
            AP2Transaction result
        """
        # Validate cart mandate
        cart_mandate = await self.get_mandate(cart_mandate_id)
        if not cart_mandate:
            raise ValueError(f"Cart mandate {cart_mandate_id} not found")
        
        if cart_mandate.status != "active":
            raise ValueError(f"Cart mandate {cart_mandate_id} is not active")
        
        transaction_data = {
            "cartMandateId": cart_mandate_id,
            "paymentMethod": payment_method.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
            "verificationRequired": verification_required,
            "amount": cart_mandate.data.get("totalAmount"),
            "currency": cart_mandate.data.get("currency")
        }
        
        response = await self._http_client.post(
            f"{self._config.base_url}/transactions",
            json=transaction_data,
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        
        return AP2Transaction.from_dict(response.json())
