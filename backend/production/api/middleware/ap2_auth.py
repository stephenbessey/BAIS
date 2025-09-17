"""
AP2 Authentication Middleware
Handles authentication and authorization for AP2 protocol requests
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature

from ...config.ap2_settings import ap2_settings, is_ap2_enabled
from ...core.payments.models import VerifiableCredential


class AP2AuthenticationError(Exception):
    """Raised when AP2 authentication fails"""
    pass


class AP2AuthMiddleware:
    """
    AP2 Authentication Middleware
    Handles verification of AP2 mandates and verifiable credentials
    """
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
        self._public_keys: Dict[str, Any] = {}
    
    async def verify_mandate_signature(
        self, 
        mandate_data: Dict[str, Any], 
        signature: str, 
        public_key_pem: str
    ) -> bool:
        """
        Verify the cryptographic signature of an AP2 mandate
        
        Args:
            mandate_data: The mandate data that was signed
            signature: The hex-encoded signature
            public_key_pem: The public key in PEM format
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Load the public key
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            
            # Prepare the data for verification
            mandate_json = json.dumps(mandate_data, sort_keys=True)
            signature_bytes = bytes.fromhex(signature)
            
            # Verify the signature
            public_key.verify(
                signature_bytes,
                mandate_json.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except (InvalidSignature, ValueError, Exception):
            return False
    
    async def verify_verifiable_credential(
        self, 
        credential: VerifiableCredential
    ) -> bool:
        """
        Verify a verifiable credential
        
        Args:
            credential: The verifiable credential to verify
            
        Returns:
            bool: True if credential is valid, False otherwise
        """
        try:
            # Check if credential is expired
            if credential.expires_at and credential.expires_at < datetime.utcnow():
                return False
            
            # Verify the proof (this would integrate with the credential issuer's verification)
            # For now, we'll do basic validation
            if not credential.proof or not credential.issuer:
                return False
            
            # TODO: Implement full credential verification with issuer
            return True
            
        except Exception:
            return False
    
    async def extract_mandate_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract AP2 mandate from request headers or body
        
        Args:
            request: The FastAPI request object
            
        Returns:
            Optional[Dict[str, Any]]: The mandate data if found, None otherwise
        """
        # Check for mandate in headers
        mandate_header = request.headers.get("X-AP2-Mandate")
        if mandate_header:
            try:
                return json.loads(mandate_header)
            except json.JSONDecodeError:
                pass
        
        # Check for mandate in request body (for POST requests)
        if request.method == "POST":
            try:
                body = await request.json()
                if "mandate" in body:
                    return body["mandate"]
            except Exception:
                pass
        
        return None
    
    async def authenticate_request(self, request: Request) -> Dict[str, Any]:
        """
        Authenticate an AP2 request
        
        Args:
            request: The FastAPI request object
            
        Returns:
            Dict[str, Any]: Authentication context including user and mandate info
            
        Raises:
            AP2AuthenticationError: If authentication fails
        """
        if not is_ap2_enabled():
            raise AP2AuthenticationError("AP2 service is not enabled")
        
        # Extract mandate from request
        mandate_data = await self.extract_mandate_from_request(request)
        if not mandate_data:
            raise AP2AuthenticationError("No AP2 mandate found in request")
        
        # Verify mandate signature
        signature = request.headers.get("X-AP2-Signature")
        public_key = request.headers.get("X-AP2-Public-Key")
        
        if not signature or not public_key:
            raise AP2AuthenticationError("Missing AP2 signature or public key")
        
        if not await self.verify_mandate_signature(mandate_data, signature, public_key):
            raise AP2AuthenticationError("Invalid AP2 mandate signature")
        
        # Check mandate expiry
        if "expiresAt" in mandate_data:
            expires_at = datetime.fromisoformat(mandate_data["expiresAt"])
            if expires_at < datetime.utcnow():
                raise AP2AuthenticationError("AP2 mandate has expired")
        
        # Return authentication context
        return {
            "mandate": mandate_data,
            "user_id": mandate_data.get("userId"),
            "business_id": mandate_data.get("businessId"),
            "mandate_type": mandate_data.get("type"),
            "authenticated": True
        }


# Global middleware instance
ap2_auth_middleware = AP2AuthMiddleware()


def require_ap2_auth(request: Request) -> Dict[str, Any]:
    """
    Dependency for AP2 authentication
    
    Use this as a FastAPI dependency to require AP2 authentication
    """
    try:
        return await ap2_auth_middleware.authenticate_request(request)
    except AP2AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"AP2 authentication failed: {str(e)}"
        )


def require_ap2_intent_mandate(request: Request) -> Dict[str, Any]:
    """
    Dependency for AP2 intent mandate authentication
    
    Use this as a FastAPI dependency to require a valid intent mandate
    """
    auth_context = require_ap2_auth(request)
    
    if auth_context["mandate_type"] != "intent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AP2 intent mandate required"
        )
    
    return auth_context


def require_ap2_cart_mandate(request: Request) -> Dict[str, Any]:
    """
    Dependency for AP2 cart mandate authentication
    
    Use this as a FastAPI dependency to require a valid cart mandate
    """
    auth_context = require_ap2_auth(request)
    
    if auth_context["mandate_type"] != "cart":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AP2 cart mandate required"
        )
    
    return auth_context


def optional_ap2_auth(request: Request) -> Optional[Dict[str, Any]]:
    """
    Optional AP2 authentication dependency
    
    Use this as a FastAPI dependency for optional AP2 authentication
    Returns None if no AP2 authentication is present
    """
    try:
        return await ap2_auth_middleware.authenticate_request(request)
    except AP2AuthenticationError:
        return None
