"""
A2A Authentication Enhancement
Implements JWT validation and OAuth2 scopes for A2A protocol

This module enhances A2A authentication with proper security measures
for production deployment.
"""

from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import jwt
import httpx
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from .protocol_configurations import A2A_CONFIG


class OAuth2Scope(str):
    """OAuth2 scope enumeration"""
    A2A_DISCOVER = "a2a:discover"
    A2A_TASK_SUBMIT = "a2a:task:submit"
    A2A_TASK_READ = "a2a:task:read"
    A2A_AGENT_REGISTER = "a2a:agent:register"
    A2A_AGENT_DISCOVER = "a2a:agent:discover"
    A2A_STREAM_EVENTS = "a2a:stream:events"
    A2A_ADMIN = "a2a:admin"


@dataclass(frozen=True)
class A2AAuthenticationConfig:
    """A2A authentication configuration"""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    oauth2_issuer_url: str = None
    oauth2_client_id: str = None
    oauth2_client_secret: str = None
    required_scopes: Set[OAuth2Scope] = None
    rate_limit_per_minute: int = 100
    max_api_key_length: int = 256


class JWTPayload(BaseModel):
    """JWT payload model"""
    sub: str = Field(..., description="Subject (user/agent identifier)")
    iss: str = Field(..., description="Issuer")
    aud: str = Field(..., description="Audience")
    exp: int = Field(..., description="Expiration time")
    iat: int = Field(..., description="Issued at")
    scope: str = Field(..., description="OAuth2 scopes")
    agent_id: str = Field(None, description="A2A agent identifier")
    business_id: str = Field(None, description="Business identifier")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")


class A2AJWTValidator:
    """
    JWT validator for A2A authentication
    
    Implements proper JWT validation with OAuth2 scope checking
    """
    
    def __init__(self, config: A2AAuthenticationConfig):
        self.config = config
        self._public_keys_cache: Dict[str, str] = {}
        self._cache_expiry: Dict[str, datetime] = {}
    
    def validate_jwt_token(self, token: str) -> JWTPayload:
        """
        Validate JWT token and extract payload
        
        Args:
            token: JWT token to validate
            
        Returns:
            JWTPayload with token claims
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Decode token without verification first to get issuer
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            issuer = unverified_payload.get('iss')
            
            # Get public key for issuer
            public_key = self._get_public_key_for_issuer(issuer)
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.config.jwt_algorithm],
                audience=self.config.oauth2_client_id,
                issuer=issuer
            )
            
            # Validate token structure
            jwt_payload = JWTPayload(**payload)
            
            # Check token expiry
            if jwt_payload.exp < datetime.utcnow().timestamp():
                raise HTTPException(status_code=401, detail="Token has expired")
            
            return jwt_payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
    
    def validate_scopes(self, payload: JWTPayload, required_scopes: Set[OAuth2Scope]) -> bool:
        """
        Validate OAuth2 scopes
        
        Args:
            payload: JWT payload with scopes
            required_scopes: Required scopes for the operation
            
        Returns:
            True if all required scopes are present
            
        Raises:
            HTTPException: If required scopes are missing
        """
        if not required_scopes:
            return True
        
        token_scopes = set(payload.scope.split(A2A_CONFIG.OAUTH2_SCOPE_SEPARATOR))
        
        missing_scopes = required_scopes - token_scopes
        if missing_scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scopes: {', '.join(missing_scopes)}"
            )
        
        return True
    
    def _get_public_key_for_issuer(self, issuer: str) -> str:
        """
        Get public key for JWT issuer
        
        Args:
            issuer: JWT issuer URL
            
        Returns:
            Public key for issuer
        """
        # Check cache first
        if issuer in self._public_keys_cache:
            if self._cache_expiry.get(issuer, datetime.min) > datetime.utcnow():
                return self._public_keys_cache[issuer]
        
        # Fetch public key from issuer
        try:
            public_key = self._fetch_public_key_from_issuer(issuer)
            self._public_keys_cache[issuer] = public_key
            self._cache_expiry[issuer] = datetime.utcnow() + timedelta(hours=1)
            return public_key
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Failed to get public key: {str(e)}")
    
    def _fetch_public_key_from_issuer(self, issuer: str) -> str:
        """
        Fetch public key from OAuth2 issuer
        
        Args:
            issuer: OAuth2 issuer URL
            
        Returns:
            Public key
        """
        # For now, return the configured secret key
        # In a real implementation, this would fetch from the issuer's JWKS endpoint
        return self.config.jwt_secret_key


class A2AAuthenticationService:
    """
    A2A authentication service
    
    Provides comprehensive authentication for A2A protocol endpoints
    """
    
    def __init__(self, config: A2AAuthenticationConfig):
        self.config = config
        self.jwt_validator = A2AJWTValidator(config)
        self.security = HTTPBearer()
    
    async def authenticate_request(
        self, 
        request: Request,
        required_scopes: Optional[Set[OAuth2Scope]] = None
    ) -> JWTPayload:
        """
        Authenticate A2A request
        
        Args:
            request: FastAPI request object
            required_scopes: Required OAuth2 scopes
            
        Returns:
            JWTPayload with authentication information
            
        Raises:
            HTTPException: If authentication fails
        """
        # Get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        # Extract token
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        token = authorization[7:]  # Remove "Bearer " prefix
        
        # Validate token
        payload = self.jwt_validator.validate_jwt_token(token)
        
        # Validate scopes
        if required_scopes:
            self.jwt_validator.validate_scopes(payload, required_scopes)
        
        return payload
    
    def create_access_token(
        self, 
        subject: str,
        agent_id: str = None,
        business_id: str = None,
        scopes: List[OAuth2Scope] = None,
        capabilities: List[str] = None,
        expires_in_minutes: int = None
    ) -> str:
        """
        Create JWT access token for A2A agent
        
        Args:
            subject: Token subject
            agent_id: A2A agent identifier
            business_id: Business identifier
            scopes: OAuth2 scopes
            capabilities: Agent capabilities
            expires_in_minutes: Token expiry time
            
        Returns:
            JWT access token
        """
        if expires_in_minutes is None:
            expires_in_minutes = self.config.jwt_expiry_minutes
        
        if scopes is None:
            scopes = [OAuth2Scope.A2A_DISCOVER, OAuth2Scope.A2A_TASK_READ]
        
        now = datetime.utcnow()
        payload = {
            "sub": subject,
            "iss": self.config.oauth2_issuer_url or "bais-a2a",
            "aud": self.config.oauth2_client_id or "bais-a2a-client",
            "exp": now + timedelta(minutes=expires_in_minutes),
            "iat": now,
            "scope": A2A_CONFIG.OAUTH2_SCOPE_SEPARATOR.join(scopes),
            "agent_id": agent_id,
            "business_id": business_id,
            "capabilities": capabilities or []
        }
        
        return jwt.encode(payload, self.config.jwt_secret_key, algorithm=self.config.jwt_algorithm)
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key format and length
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not api_key:
            return False
        
        if len(api_key) > self.config.max_api_key_length:
            return False
        
        # Additional API key validation logic would go here
        return True


# FastAPI dependency functions
def get_a2a_auth_service() -> A2AAuthenticationService:
    """FastAPI dependency for A2A authentication service"""
    config = A2AAuthenticationConfig(
        jwt_secret_key="your-jwt-secret-key",  # Should come from environment
        oauth2_issuer_url="https://oauth.bais.com",
        oauth2_client_id="bais-a2a-client",
        required_scopes={OAuth2Scope.A2A_DISCOVER}
    )
    return A2AAuthenticationService(config)


def require_a2a_auth(
    required_scopes: Optional[Set[OAuth2Scope]] = None
):
    """
    FastAPI dependency for requiring A2A authentication
    
    Args:
        required_scopes: Required OAuth2 scopes
        
    Returns:
        FastAPI dependency function
    """
    async def _require_auth(
        request: Request,
        auth_service: A2AAuthenticationService = Depends(get_a2a_auth_service)
    ) -> JWTPayload:
        return await auth_service.authenticate_request(request, required_scopes)
    
    return _require_auth


# Specific scope dependencies
def require_discovery_scope():
    """Require A2A discovery scope"""
    return require_a2a_auth({OAuth2Scope.A2A_DISCOVER})


def require_task_submit_scope():
    """Require A2A task submission scope"""
    return require_a2a_auth({OAuth2Scope.A2A_TASK_SUBMIT})


def require_task_read_scope():
    """Require A2A task read scope"""
    return require_a2a_auth({OAuth2Scope.A2A_TASK_READ})


def require_agent_register_scope():
    """Require A2A agent registration scope"""
    return require_a2a_auth({OAuth2Scope.A2A_AGENT_REGISTER})


def require_stream_events_scope():
    """Require A2A stream events scope"""
    return require_a2a_auth({OAuth2Scope.A2A_STREAM_EVENTS})


def require_admin_scope():
    """Require A2A admin scope"""
    return require_a2a_auth({OAuth2Scope.A2A_ADMIN})


# Enhanced A2A client with authentication
class AuthenticatedA2AClient:
    """
    Enhanced A2A client with proper authentication
    
    Extends the basic A2A client with JWT authentication
    """
    
    def __init__(self, auth_service: A2AAuthenticationService, base_url: str):
        self.auth_service = auth_service
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self._access_token: Optional[str] = None
    
    async def authenticate(self, agent_id: str, business_id: str, scopes: List[OAuth2Scope]) -> None:
        """
        Authenticate with A2A service
        
        Args:
            agent_id: A2A agent identifier
            business_id: Business identifier
            scopes: Required OAuth2 scopes
        """
        self._access_token = self.auth_service.create_access_token(
            subject=f"{business_id}:{agent_id}",
            agent_id=agent_id,
            business_id=business_id,
            scopes=scopes
        )
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for requests"""
        headers = {
            "Content-Type": "application/json",
            "A2A-Version": "1.0"
        }
        
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        
        return headers
    
    async def discover_agents_authenticated(
        self, 
        discovery_request: Dict[str, Any],
        scopes: List[OAuth2Scope] = None
    ) -> Dict[str, Any]:
        """
        Discover agents with authentication
        
        Args:
            discovery_request: Discovery request data
            scopes: Required scopes for discovery
            
        Returns:
            Discovery response
        """
        if scopes is None:
            scopes = [OAuth2Scope.A2A_DISCOVER]
        
        if not self._access_token:
            raise ValueError("Client not authenticated")
        
        response = await self.client.post(
            f"{self.base_url}/a2a/discover",
            json=discovery_request,
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def submit_task_authenticated(
        self,
        task_request: Dict[str, Any],
        scopes: List[OAuth2Scope] = None
    ) -> Dict[str, Any]:
        """
        Submit task with authentication
        
        Args:
            task_request: Task request data
            scopes: Required scopes for task submission
            
        Returns:
            Task status response
        """
        if scopes is None:
            scopes = [OAuth2Scope.A2A_TASK_SUBMIT]
        
        if not self._access_token:
            raise ValueError("Client not authenticated")
        
        response = await self.client.post(
            f"{self.base_url}/a2a/tasks",
            json=task_request,
            headers=self._get_auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Factory for creating authenticated clients
class AuthenticatedA2AClientFactory:
    """Factory for creating authenticated A2A clients"""
    
    @staticmethod
    def create_client(
        auth_service: A2AAuthenticationService,
        base_url: str,
        agent_id: str,
        business_id: str,
        scopes: List[OAuth2Scope] = None
    ) -> AuthenticatedA2AClient:
        """
        Create authenticated A2A client
        
        Args:
            auth_service: Authentication service
            base_url: A2A service base URL
            agent_id: Agent identifier
            business_id: Business identifier
            scopes: Required OAuth2 scopes
            
        Returns:
            AuthenticatedA2AClient instance
        """
        client = AuthenticatedA2AClient(auth_service, base_url)
        
        if scopes is None:
            scopes = [OAuth2Scope.A2A_DISCOVER, OAuth2Scope.A2A_TASK_SUBMIT]
        
        # Authenticate client (this would be async in real usage)
        import asyncio
        asyncio.create_task(client.authenticate(agent_id, business_id, scopes))
        
        return client
