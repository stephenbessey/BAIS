"""
BAIS OAuth 2.0 Security Implementation
Production-grade OAuth 2.0 implementation for BAIS with granular permissions
"""

from fastapi import FastAPI, HTTPException, Depends, Form, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Set
import jwt
from datetime import datetime, timedelta
import hashlib
import secrets
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
import asyncio
import uuid
import bcrypt

# OAuth 2.0 Models
class OAuth2ClientCredentials(BaseModel):
    client_id: str = Field(..., min_length=10, max_length=255)
    client_secret: str = Field(..., min_length=32, max_length=255)
    client_name: str = Field(..., min_length=1, max_length=255)
    redirect_uris: List[str] = Field(..., min_items=1)
    scopes: List[str] = Field(default_factory=list)
    grant_types: List[str] = Field(default=["authorization_code", "client_credentials"])
    response_types: List[str] = Field(default=["code"])

class OAuth2AuthorizationRequest(BaseModel):
    response_type: str = Field(..., regex="^(code|token)$")
    client_id: str = Field(..., min_length=10)
    redirect_uri: str = Field(...)
    scope: Optional[str] = Field(None)
    state: Optional[str] = Field(None)
    business_id: Optional[str] = Field(None)

class OAuth2TokenRequest(BaseModel):
    grant_type: str = Field(..., regex="^(authorization_code|client_credentials|refresh_token)$")
    code: Optional[str] = Field(None)
    redirect_uri: Optional[str] = Field(None)
    client_id: str = Field(...)
    client_secret: str = Field(...)
    refresh_token: Optional[str] = Field(None)
    scope: Optional[str] = Field(None)

class OAuth2TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None

class OAuth2IntrospectionResponse(BaseModel):
    active: bool
    client_id: Optional[str] = None
    scope: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    business_id: Optional[str] = None
    agent_id: Optional[str] = None

class BAISPermission(BaseModel):
    """BAIS-specific permission model"""
    resource: str = Field(..., description="Resource type (business, service, booking)")
    action: str = Field(..., description="Action (read, write, book, cancel)")
    business_id: Optional[str] = Field(None, description="Specific business ID")
    service_id: Optional[str] = Field(None, description="Specific service ID")

class BAISScope(BaseModel):
    """BAIS OAuth scope definition"""
    name: str = Field(..., description="Scope name")
    description: str = Field(..., description="Human-readable description")
    permissions: List[BAISPermission] = Field(..., description="Permissions granted by this scope")

# Predefined BAIS scopes
BAIS_SCOPES = {
    "read": BAISScope(
        name="read",
        description="Read access to business information and services",
        permissions=[
            BAISPermission(resource="business", action="read"),
            BAISPermission(resource="service", action="read")
        ]
    ),
    "search": BAISScope(
        name="search",
        description="Search for available services and pricing",
        permissions=[
            BAISPermission(resource="business", action="read"),
            BAISPermission(resource="service", action="read"),
            BAISPermission(resource="availability", action="read")
        ]
    ),
    "book": BAISScope(
        name="book",
        description="Create and manage bookings",
        permissions=[
            BAISPermission(resource="business", action="read"),
            BAISPermission(resource="service", action="read"),
            BAISPermission(resource="availability", action="read"),
            BAISPermission(resource="booking", action="write")
        ]
    ),
    "manage": BAISScope(
        name="manage",
        description="Full management access for business owners",
        permissions=[
            BAISPermission(resource="business", action="write"),
            BAISPermission(resource="service", action="write"),
            BAISPermission(resource="booking", action="write"),
            BAISPermission(resource="booking", action="cancel")
        ]
    )
}

class BAISOAuth2Provider:
    """OAuth 2.0 Provider for BAIS with business-specific permissions"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 30
        
        # Storage (in production, use proper database)
        self.clients: Dict[str, OAuth2ClientCredentials] = {}
        self.authorization_codes: Dict[str, Dict[str, Any]] = {}
        self.access_tokens: Dict[str, Dict[str, Any]] = {}
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}
        
        # Initialize with default BAIS client
        self._initialize_default_clients()
    
    def _initialize_default_clients(self):
        """Initialize default OAuth clients for BAIS"""
        # Business management client
        business_client = OAuth2ClientCredentials(
            client_id="bais_business_mgmt",
            client_secret=self._hash_secret("bais_business_secret_2024"),
            client_name="BAIS Business Management",
            redirect_uris=["http://localhost:3000/auth/callback"],
            scopes=["read", "manage"],
            grant_types=["authorization_code", "client_credentials"]
        )
        self.clients[business_client.client_id] = business_client
        
        # Agent client
        agent_client = OAuth2ClientCredentials(
            client_id="bais_ai_agent",
            client_secret=self._hash_secret("bais_agent_secret_2024"),
            client_name="BAIS AI Agent",
            redirect_uris=["http://localhost:8000/auth/callback"],
            scopes=["read", "search", "book"],
            grant_types=["client_credentials"]
        )
        self.clients[agent_client.client_id] = agent_client
    
    def _hash_secret(self, secret: str) -> str:
        """Hash client secret"""
        return bcrypt.hashpw(secret.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_secret(self, secret: str, hashed: str) -> bool:
        """Verify client secret"""
        return bcrypt.checkpw(secret.encode('utf-8'), hashed.encode('utf-8'))
    
    def register_client(self, client_data: OAuth2ClientCredentials) -> str:
        """Register a new OAuth client"""
        # Hash the client secret
        client_data.client_secret = self._hash_secret(client_data.client_secret)
        
        # Store client
        self.clients[client_data.client_id] = client_data
        
        return client_data.client_id
    
    def validate_client(self, client_id: str, client_secret: str) -> bool:
        """Validate client credentials"""
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        return self._verify_secret(client_secret, client.client_secret)
    
    def create_authorization_code(self, 
                                 client_id: str, 
                                 redirect_uri: str,
                                 scope: str = None,
                                 state: str = None,
                                 business_id: str = None,
                                 agent_id: str = None) -> str:
        """Create authorization code for OAuth flow"""
        
        if client_id not in self.clients:
            raise ValueError("Invalid client_id")
        
        client = self.clients[client_id]
        if redirect_uri not in client.redirect_uris:
            raise ValueError("Invalid redirect_uri")
        
        # Generate authorization code
        code = secrets.token_urlsafe(32)
        
        # Store authorization code data
        self.authorization_codes[code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "business_id": business_id,
            "agent_id": agent_id,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        }
        
        return code
    
    def exchange_code_for_token(self, request: OAuth2TokenRequest) -> OAuth2TokenResponse:
        """Exchange authorization code for access token"""
        
        # Validate client
        if not self.validate_client(request.client_id, request.client_secret):
            raise HTTPException(status_code=401, detail="Invalid client credentials")
        
        if request.grant_type == "authorization_code":
            return self._handle_authorization_code_grant(request)
        elif request.grant_type == "client_credentials":
            return self._handle_client_credentials_grant(request)
        elif request.grant_type == "refresh_token":
            return self._handle_refresh_token_grant(request)
        else:
            raise HTTPException(status_code=400, detail="Unsupported grant type")
    
    def _handle_authorization_code_grant(self, request: OAuth2TokenRequest) -> OAuth2TokenResponse:
        """Handle authorization code grant"""
        if not request.code:
            raise HTTPException(status_code=400, detail="Authorization code required")
        
        # Validate authorization code
        if request.code not in self.authorization_codes:
            raise HTTPException(status_code=400, detail="Invalid authorization code")
        
        code_data = self.authorization_codes[request.code]
        
        # Check expiration
        if datetime.utcnow() > code_data["expires_at"]:
            del self.authorization_codes[request.code]
            raise HTTPException(status_code=400, detail="Authorization code expired")
        
        # Validate client and redirect URI
        if code_data["client_id"] != request.client_id:
            raise HTTPException(status_code=400, detail="Client mismatch")
        
        if code_data["redirect_uri"] != request.redirect_uri:
            raise HTTPException(status_code=400, detail="Redirect URI mismatch")
        
        # Generate tokens
        access_token = self._create_access_token(
            client_id=request.client_id,
            scope=code_data["scope"],
            business_id=code_data["business_id"],
            agent_id=code_data["agent_id"]
        )
        
        refresh_token = self._create_refresh_token(
            client_id=request.client_id,
            scope=code_data["scope"],
            business_id=code_data["business_id"],
            agent_id=code_data["agent_id"]
        )
        
        # Clean up authorization code
        del self.authorization_codes[request.code]
        
        return OAuth2TokenResponse(
            access_token=access_token,
            expires_in=self.access_token_expire_minutes * 60,
            refresh_token=refresh_token,
            scope=code_data["scope"]
        )
    
    def _handle_client_credentials_grant(self, request: OAuth2TokenRequest) -> OAuth2TokenResponse:
        """Handle client credentials grant for machine-to-machine auth"""
        
        # Generate access token for client
        access_token = self._create_access_token(
            client_id=request.client_id,
            scope=request.scope or "read"
        )
        
        return OAuth2TokenResponse(
            access_token=access_token,
            expires_in=self.access_token_expire_minutes * 60,
            scope=request.scope or "read"
        )
    
    def _handle_refresh_token_grant(self, request: OAuth2TokenRequest) -> OAuth2TokenResponse:
        """Handle refresh token grant"""
        if not request.refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token required")
        
        # Validate refresh token
        if request.refresh_token not in self.refresh_tokens:
            raise HTTPException(status_code=400, detail="Invalid refresh token")
        
        token_data = self.refresh_tokens[request.refresh_token]
        
        # Check expiration
        if datetime.utcnow() > token_data["expires_at"]:
            del self.refresh_tokens[request.refresh_token]
            raise HTTPException(status_code=400, detail="Refresh token expired")
        
        # Generate new access token
        access_token = self._create_access_token(
            client_id=token_data["client_id"],
            scope=token_data["scope"],
            business_id=token_data["business_id"],
            agent_id=token_data["agent_id"]
        )
        
        return OAuth2TokenResponse(
            access_token=access_token,
            expires_in=self.access_token_expire_minutes * 60,
            scope=token_data["scope"]
        )
    
    def _create_access_token(self, 
                           client_id: str,
                           scope: str = None,
                           business_id: str = None,
                           agent_id: str = None) -> str:
        """Create JWT access token"""
        
        now = datetime.utcnow()
        expires = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "iss": "bais-oauth-provider",
            "sub": client_id,
            "aud": "bais-api",
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "client_id": client_id,
            "scope": scope,
            "token_type": "access_token"
        }
        
        if business_id:
            payload["business_id"] = business_id
        
        if agent_id:
            payload["agent_id"] = agent_id
        
        # Generate JWT
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store token metadata
        self.access_tokens[token] = {
            "client_id": client_id,
            "scope": scope,
            "business_id": business_id,
            "agent_id": agent_id,
            "created_at": now,
            "expires_at": expires
        }
        
        return token
    
    def _create_refresh_token(self,
                            client_id: str,
                            scope: str = None,
                            business_id: str = None,
                            agent_id: str = None) -> str:
        """Create refresh token"""
        
        token = secrets.token_urlsafe(64)
        expires = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        self.refresh_tokens[token] = {
            "client_id": client_id,
            "scope": scope,
            "business_id": business_id,
            "agent_id": agent_id,
            "created_at": datetime.utcnow(),
            "expires_at": expires
        }
        
        return token
    
    def introspect_token(self, token: str) -> OAuth2IntrospectionResponse:
        """Introspect access token"""
        try:
            # Decode JWT
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is still valid in our storage
            if token not in self.access_tokens:
                return OAuth2IntrospectionResponse(active=False)
            
            token_data = self.access_tokens[token]
            
            # Check expiration
            if datetime.utcnow() > token_data["expires_at"]:
                del self.access_tokens[token]
                return OAuth2IntrospectionResponse(active=False)
            
            return OAuth2IntrospectionResponse(
                active=True,
                client_id=payload.get("client_id"),
                scope=payload.get("scope"),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                business_id=payload.get("business_id"),
                agent_id=payload.get("agent_id")
            )
            
        except jwt.InvalidTokenError:
            return OAuth2IntrospectionResponse(active=False)
    
    def validate_token_permissions(self, token: str, required_permission: BAISPermission) -> bool:
        """Validate if token has required permissions"""
        introspection = self.introspect_token(token)
        
        if not introspection.active:
            return False
        
        # Check scope permissions
        token_scopes = introspection.scope.split() if introspection.scope else []
        
        for scope_name in token_scopes:
            if scope_name not in BAIS_SCOPES:
                continue
            
            scope = BAIS_SCOPES[scope_name]
            
            for permission in scope.permissions:
                if self._permission_matches(permission, required_permission, introspection):
                    return True
        
        return False
    
    def _permission_matches(self, 
                          granted: BAISPermission, 
                          required: BAISPermission,
                          token_info: OAuth2IntrospectionResponse) -> bool:
        """Check if granted permission matches required permission"""
        
        # Resource must match
        if granted.resource != required.resource:
            return False
        
        # Action must match
        if granted.action != required.action:
            return False
        
        # Business ID constraint
        if required.business_id:
            # If permission specifies business_id, it must match
            if granted.business_id and granted.business_id != required.business_id:
                return False
            
            # If token is business-scoped, it must match
            if token_info.business_id and token_info.business_id != required.business_id:
                return False
        
        # Service ID constraint
        if required.service_id:
            if granted.service_id and granted.service_id != required.service_id:
                return False
        
        return True

# FastAPI Integration
class BAISOAuth2Middleware:
    """FastAPI middleware for BAIS OAuth 2.0"""
    
    def __init__(self, oauth_provider: BAISOAuth2Provider):
        self.oauth_provider = oauth_provider
        self.security = HTTPBearer()
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> OAuth2IntrospectionResponse:
        """Verify OAuth 2.0 token"""
        if not credentials:
            raise HTTPException(status_code=401, detail="Authorization required")
        
        introspection = self.oauth_provider.introspect_token(credentials.credentials)
        
        if not introspection.active:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return introspection
    
    def require_permission(self, permission: BAISPermission):
        """Decorator factory for requiring specific permissions"""
        def permission_checker(token_info: OAuth2IntrospectionResponse = Depends(self.verify_token)):
            if not self.oauth_provider.validate_token_permissions(
                token_info.client_id,  # This needs to be the actual token
                permission
            ):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return token_info
        
        return permission_checker

# OAuth 2.0 Server endpoints
def create_oauth_app(oauth_provider: BAISOAuth2Provider) -> FastAPI:
    """Create OAuth 2.0 server app"""
    
    app = FastAPI(title="BAIS OAuth 2.0 Server", version="1.0.0")
    
    @app.get("/oauth/authorize")
    async def authorize(
        response_type: str,
        client_id: str,
        redirect_uri: str,
        scope: Optional[str] = None,
        state: Optional[str] = None,
        business_id: Optional[str] = None
    ):
        """OAuth 2.0 authorization endpoint"""
        
        try:
            # Validate client
            if client_id not in oauth_provider.clients:
                raise HTTPException(status_code=400, detail="Invalid client_id")
            
            client = oauth_provider.clients[client_id]
            
            if redirect_uri not in client.redirect_uris:
                raise HTTPException(status_code=400, detail="Invalid redirect_uri")
            
            # For demo purposes, auto-approve
            # In production, show consent screen
            code = oauth_provider.create_authorization_code(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope=scope,
                state=state,
                business_id=business_id
            )
            
            # Redirect with authorization code
            redirect_url = f"{redirect_uri}?code={code}"
            if state:
                redirect_url += f"&state={state}"
            
            return RedirectResponse(url=redirect_url)
            
        except Exception as e:
            error_url = f"{redirect_uri}?error=server_error&error_description={str(e)}"
            if state:
                error_url += f"&state={state}"
            return RedirectResponse(url=error_url)
    
    @app.post("/oauth/token", response_model=OAuth2TokenResponse)
    async def token(
        grant_type: str = Form(...),
        code: Optional[str] = Form(None),
        redirect_uri: Optional[str] = Form(None),
        client_id: str = Form(...),
        client_secret: str = Form(...),
        refresh_token: Optional[str] = Form(None),
        scope: Optional[str] = Form(None)
    ):
        """OAuth 2.0 token endpoint"""
        
        request = OAuth2TokenRequest(
            grant_type=grant_type,
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            scope=scope
        )
        
        return oauth_provider.exchange_code_for_token(request)
    
    @app.post("/oauth/introspect", response_model=OAuth2IntrospectionResponse)
    async def introspect(token: str = Form(...)):
        """OAuth 2.0 token introspection endpoint"""
        return oauth_provider.introspect_token(token)
    
    @app.get("/oauth/.well-known/authorization_server")
    async def authorization_server_metadata():
        """OAuth 2.0 Authorization Server Metadata"""
        return {
            "issuer": "https://auth.baintegrate.com",
            "authorization_endpoint": "/oauth/authorize",
            "token_endpoint": "/oauth/token",
            "introspection_endpoint": "/oauth/introspect",
            "response_types_supported": ["code", "token"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
            "scopes_supported": list(BAIS_SCOPES.keys()),
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"]
        }
    
    return app

# Example usage
if __name__ == "__main__":
    import uvicorn
    
    # Create OAuth provider
    oauth_provider = BAISOAuth2Provider()
    
    # Create OAuth server
    oauth_app = create_oauth_app(oauth_provider)
    
    # Run OAuth server
    uvicorn.run(oauth_app, host="0.0.0.0", port=8003)