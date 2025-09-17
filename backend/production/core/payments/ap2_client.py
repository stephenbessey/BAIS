from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

from .models import AP2Mandate, AP2Transaction, PaymentMethod, VerifiableCredential


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
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for AP2 requests"""
        return {
            "Authorization": f"Bearer {self._config.client_id}",
            "Content-Type": "application/json",
            "AP2-Version": "1.0"
        }
