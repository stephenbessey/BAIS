"""
OAuth 2.0 Authorization Service
Handles authorization code flows and permission validation
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException
from .oauth2_security import OAuth2TokenRequest, OAuth2TokenResponse, BAISPermission, OAuth2IntrospectionResponse, BAIS_SCOPES


class OAuth2AuthorizationService:
    """Manages OAuth 2.0 authorization flows and permissions"""
    
    def __init__(self, token_service, client_manager):
        self.token_service = token_service
        self.client_manager = client_manager
        self.authorization_codes: Dict[str, Dict[str, Any]] = {}
    
    def create_authorization_code(self, 
                                 client_id: str, 
                                 redirect_uri: str,
                                 scope: Optional[str] = None,
                                 state: Optional[str] = None,
                                 business_id: Optional[str] = None,
                                 agent_id: Optional[str] = None) -> str:
        """Create authorization code for OAuth flow"""
        
        if client_id not in self.client_manager.clients:
            raise ValueError("Invalid client_id")
        
        client = self.client_manager.clients[client_id]
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
    
    def handle_authorization_code_grant(self, request: OAuth2TokenRequest) -> OAuth2TokenResponse:
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
        access_token = self.token_service.create_access_token(
            client_id=request.client_id,
            scope=code_data["scope"],
            business_id=code_data["business_id"],
            agent_id=code_data["agent_id"]
        )
        
        refresh_token = self.token_service.create_refresh_token(
            client_id=request.client_id,
            scope=code_data["scope"],
            business_id=code_data["business_id"],
            agent_id=code_data["agent_id"]
        )
        
        # Clean up authorization code
        del self.authorization_codes[request.code]
        
        return OAuth2TokenResponse(
            access_token=access_token,
            expires_in=self.token_service.access_token_expire_minutes * 60,
            refresh_token=refresh_token,
            scope=code_data["scope"]
        )
    
    def handle_client_credentials_grant(self, request: OAuth2TokenRequest) -> OAuth2TokenResponse:
        """Handle client credentials grant for machine-to-machine auth"""
        
        # Generate access token for client
        access_token = self.token_service.create_access_token(
            client_id=request.client_id,
            scope=request.scope or "read"
        )
        
        return OAuth2TokenResponse(
            access_token=access_token,
            expires_in=self.token_service.access_token_expire_minutes * 60,
            scope=request.scope or "read"
        )
    
    def handle_refresh_token_grant(self, request: OAuth2TokenRequest) -> OAuth2TokenResponse:
        """Handle refresh token grant"""
        if not request.refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token required")
        
        # Validate refresh token
        token_data = self.token_service.validate_refresh_token(request.refresh_token)
        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid or expired refresh token")
        
        # Generate new access token
        access_token = self.token_service.create_access_token(
            client_id=token_data["client_id"],
            scope=token_data["scope"],
            business_id=token_data["business_id"],
            agent_id=token_data["agent_id"]
        )
        
        return OAuth2TokenResponse(
            access_token=access_token,
            expires_in=self.token_service.access_token_expire_minutes * 60,
            scope=token_data["scope"]
        )
    
    def validate_token_permissions(self, token: str, required_permission: BAISPermission) -> bool:
        """Validate if token has required permissions"""
        introspection = self.token_service.introspect_token(token)
        
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
