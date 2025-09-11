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
        from .oauth2_client_manager import OAuth2ClientManager
        from .oauth2_token_service import OAuth2TokenService
        from .oauth2_authorization_service import OAuth2AuthorizationService
        
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        
        # Initialize services with single responsibilities
        self.client_manager = OAuth2ClientManager()
        self.token_service = OAuth2TokenService(self.secret_key)
        self.authorization_service = OAuth2AuthorizationService(
            self.token_service, 
            self.client_manager
        )
    
    def register_client(self, client_data: OAuth2ClientCredentials) -> str:
        """Register a new OAuth client"""
        return self.client_manager.register_client(client_data)
    
    def validate_client(self, client_id: str, client_secret: str) -> bool:
        """Validate client credentials"""
        return self.client_manager.validate_client(client_id, client_secret)
    
    def create_authorization_code(self, 
                                 client_id: str, 
                                 redirect_uri: str,
                                 scope: str = None,
                                 state: str = None,
                                 business_id: str = None,
                                 agent_id: str = None) -> str:
        """Create authorization code for OAuth flow"""
        return self.authorization_service.create_authorization_code(
            client_id, redirect_uri, scope, state, business_id, agent_id
        )
    
    def exchange_code_for_token(self, request: OAuth2TokenRequest) -> OAuth2TokenResponse:
        """Exchange authorization code for access token"""
        
        # Validate client
        if not self.validate_client(request.client_id, request.client_secret):
            raise HTTPException(status_code=401, detail="Invalid client credentials")
        
        if request.grant_type == "authorization_code":
            return self.authorization_service.handle_authorization_code_grant(request)
        elif request.grant_type == "client_credentials":
            return self.authorization_service.handle_client_credentials_grant(request)
        elif request.grant_type == "refresh_token":
            return self.authorization_service.handle_refresh_token_grant(request)
        else:
            raise HTTPException(status_code=400, detail="Unsupported grant type")
    
    def introspect_token(self, token: str) -> OAuth2IntrospectionResponse:
        """Introspect access token"""
        return self.token_service.introspect_token(token)
    
    def validate_token_permissions(self, token: str, required_permission: BAISPermission) -> bool:
        """Validate if token has required permissions"""
        return self.authorization_service.validate_token_permissions(token, required_permission)

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