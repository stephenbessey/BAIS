"""
MCP Authentication Service - OAuth 2.0 with Resource Indicators (RFC 8707)
Implements proper authentication following MCP 2025-06-18 specification
"""

import jwt
import httpx
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import json
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class AuthContext:
    """Authentication context following Clean Code principles"""
    user_id: str
    client_id: str
    scopes: List[str]
    resource_uri: str
    expires_at: datetime
    audience: str
    issuer: str
    
    def has_scope(self, required_scope: str) -> bool:
        """Check if context has required scope"""
        return required_scope in self.scopes
    
    def is_valid(self) -> bool:
        """Check if authentication is still valid"""
        return datetime.utcnow() < self.expires_at
    
    def has_resource_access(self, requested_uri: str) -> bool:
        """Check if user has access to specific resource URI"""
        # Extract resource type from URI
        if requested_uri.startswith(('availability://', 'service://', 'business://')):
            resource_type = requested_uri.split('://')[0]
            return f"resource:{resource_type}" in self.scopes or "resource:*" in self.scopes
        return True  # Default access for non-resource URIs


class JWKSClient:
    """JSON Web Key Set client for OAuth token verification"""
    
    def __init__(self, jwks_url: str):
        self.jwks_url = jwks_url
        self._keys_cache: Dict[str, Any] = {}
        self._cache_expiry: Optional[datetime] = None
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def get_signing_key(self, token: str) -> Any:
        """Get signing key for JWT token verification"""
        try:
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get('kid')
            
            if not key_id:
                raise HTTPException(401, "Token missing key ID")
            
            # Check cache first
            if self._is_cache_valid() and key_id in self._keys_cache:
                return self._keys_cache[key_id]
            
            # Fetch JWKS
            await self._fetch_jwks()
            
            if key_id not in self._keys_cache:
                raise HTTPException(401, f"Key ID {key_id} not found in JWKS")
            
            return self._keys_cache[key_id]
            
        except jwt.InvalidTokenError as e:
            raise HTTPException(401, f"Invalid token format: {e}")
        except Exception as e:
            logger.error(f"Error getting signing key: {e}")
            raise HTTPException(500, "Authentication service error")
    
    async def _fetch_jwks(self):
        """Fetch JWKS from OAuth provider"""
        try:
            response = await self._http_client.get(self.jwks_url)
            response.raise_for_status()
            
            jwks_data = response.json()
            self._keys_cache = {}
            
            # Parse JWK keys
            for key_data in jwks_data.get('keys', []):
                key_id = key_data.get('kid')
                if key_id:
                    # Convert JWK to RSA public key
                    public_key = self._jwk_to_rsa_public_key(key_data)
                    self._keys_cache[key_id] = public_key
            
            # Set cache expiry (5 minutes)
            self._cache_expiry = datetime.utcnow() + timedelta(minutes=5)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise HTTPException(503, "OAuth provider unavailable")
        except Exception as e:
            logger.error(f"Error fetching JWKS: {e}")
            raise HTTPException(500, "JWKS fetch error")
    
    def _jwk_to_rsa_public_key(self, jwk: Dict[str, Any]) -> rsa.RSAPublicKey:
        """Convert JWK to RSA public key"""
        try:
            # Extract key components
            n = jwt.utils.base64url_decode(jwk['n'])
            e = jwt.utils.base64url_decode(jwk['e'])
            
            # Create RSA public key
            public_numbers = rsa.RSAPublicNumbers(
                int.from_bytes(e, 'big'),
                int.from_bytes(n, 'big')
            )
            
            return public_numbers.public_key(backend=default_backend())
            
        except Exception as e:
            logger.error(f"Error converting JWK to RSA key: {e}")
            raise HTTPException(500, "Key conversion error")
    
    def _is_cache_valid(self) -> bool:
        """Check if JWKS cache is still valid"""
        return self._cache_expiry and datetime.utcnow() < self._cache_expiry
    
    async def close(self):
        """Close HTTP client"""
        await self._http_client.aclose()


class AuthenticationService:
    """OAuth 2.0 authentication with Resource Indicators (RFC 8707)"""
    
    def __init__(self, oauth_discovery_url: str, allowed_scopes: List[str]):
        self._oauth_discovery_url = oauth_discovery_url
        self._allowed_scopes = allowed_scopes
        self._jwks_client: Optional[JWKSClient] = None
        self._oauth_metadata: Optional[Dict[str, Any]] = None
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def initialize(self):
        """Initialize OAuth metadata and JWKS client"""
        try:
            await self._fetch_oauth_metadata()
            await self._initialize_jwks_client()
        except Exception as e:
            logger.error(f"Failed to initialize authentication service: {e}")
            raise
    
    async def validate_token(self, token: str, resource_uri: str) -> AuthContext:
        """
        Validate OAuth token following MCP 2025-06-18 specification
        Implements Resource Indicators per RFC 8707
        """
        if not token:
            raise HTTPException(401, "Missing authentication token")
        
        try:
            # Get signing key
            signing_key = await self._jwks_client.get_signing_key(token)
            
            # Extract expected audience (Resource Indicator)
            expected_audience = self._extract_resource_audience(resource_uri)
            
            # Decode and verify JWT token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=expected_audience,
                issuer=self._oauth_metadata.get('issuer'),
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True
                }
            )
            
            # Validate scopes
            token_scopes = payload.get('scope', '').split()
            if not self._has_required_scopes(token_scopes):
                raise HTTPException(403, "Insufficient permissions")
            
            # Validate token expiration
            exp_timestamp = payload.get('exp')
            if not exp_timestamp:
                raise HTTPException(401, "Token missing expiration")
            
            expires_at = datetime.fromtimestamp(exp_timestamp)
            if expires_at <= datetime.utcnow():
                raise HTTPException(401, "Token expired")
            
            return AuthContext(
                user_id=payload.get('sub'),
                client_id=payload.get('client_id'),
                scopes=token_scopes,
                resource_uri=resource_uri,
                expires_at=expires_at,
                audience=expected_audience,
                issuer=payload.get('iss')
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except jwt.InvalidAudienceError:
            raise HTTPException(401, "Invalid token audience")
        except jwt.InvalidIssuerError:
            raise HTTPException(401, "Invalid token issuer")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(401, "Invalid token")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(500, "Authentication service error")
    
    def _extract_resource_audience(self, resource_uri: str) -> str:
        """Extract audience for Resource Indicator validation per RFC 8707"""
        # For BAIS URIs like "availability://hotel-123"
        if resource_uri.startswith(('availability://', 'service://', 'business://')):
            resource_type = resource_uri.split('://')[0]
            return f"mcp-server:bais-{resource_type}"
        
        # Default audience for general MCP access
        return "mcp-server:bais-default"
    
    def _has_required_scopes(self, token_scopes: List[str]) -> bool:
        """Check if token has any of the required scopes"""
        if not self._allowed_scopes:
            return True  # No scope restrictions
        
        return any(scope in self._allowed_scopes for scope in token_scopes)
    
    async def _fetch_oauth_metadata(self):
        """Fetch OAuth provider metadata"""
        try:
            response = await self._http_client.get(self._oauth_discovery_url)
            response.raise_for_status()
            
            self._oauth_metadata = response.json()
            
            # Validate required metadata
            required_fields = ['issuer', 'jwks_uri', 'authorization_endpoint', 'token_endpoint']
            for field in required_fields:
                if field not in self._oauth_metadata:
                    raise ValueError(f"Missing required OAuth metadata field: {field}")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch OAuth metadata: {e}")
            raise HTTPException(503, "OAuth provider unavailable")
        except Exception as e:
            logger.error(f"Error fetching OAuth metadata: {e}")
            raise HTTPException(500, "OAuth metadata error")
    
    async def _initialize_jwks_client(self):
        """Initialize JWKS client with metadata"""
        if not self._oauth_metadata:
            raise ValueError("OAuth metadata not available")
        
        jwks_url = self._oauth_metadata.get('jwks_uri')
        if not jwks_url:
            raise ValueError("JWKS URI not found in OAuth metadata")
        
        self._jwks_client = JWKSClient(jwks_url)
    
    async def close(self):
        """Close HTTP clients"""
        if self._jwks_client:
            await self._jwks_client.close()
        await self._http_client.aclose()


# FastAPI dependency for authentication
security = HTTPBearer()

async def get_auth_context(
    auth: HTTPAuthorizationCredentials = Depends(security),
    resource_uri: str = "default"
) -> AuthContext:
    """FastAPI dependency for authentication"""
    # This would be injected from the application context
    # For now, we'll create a mock service for demonstration
    auth_service = AuthenticationService(
        oauth_discovery_url="https://oauth.example.com/.well-known/openid-configuration",
        allowed_scopes=["resource:read", "resource:write", "tool:execute"]
    )
    
    return await auth_service.validate_token(auth.credentials, resource_uri)


# Global authentication service instance
_auth_service: Optional[AuthenticationService] = None


def get_authentication_service() -> AuthenticationService:
    """Get the global authentication service instance"""
    global _auth_service
    if _auth_service is None:
        # In production, these would come from environment variables
        _auth_service = AuthenticationService(
            oauth_discovery_url="https://oauth.example.com/.well-known/openid-configuration",
            allowed_scopes=[
                "resource:read",
                "resource:write", 
                "tool:execute",
                "tool:admin",
                "business:read",
                "business:write"
            ]
        )
    return _auth_service


async def initialize_authentication_service():
    """Initialize the global authentication service"""
    auth_service = get_authentication_service()
    await auth_service.initialize()
    logger.info("Authentication service initialized successfully")


async def cleanup_authentication_service():
    """Cleanup the global authentication service"""
    global _auth_service
    if _auth_service:
        await _auth_service.close()
        _auth_service = None
    logger.info("Authentication service cleaned up")
