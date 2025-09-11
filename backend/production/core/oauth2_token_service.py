"""
OAuth 2.0 Token Service
Handles JWT token creation, validation, and introspection
"""

import jwt
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from .oauth2_security import OAuth2TokenResponse, OAuth2IntrospectionResponse


class OAuth2TokenService:
    """Manages OAuth 2.0 token operations"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 30
        
        # Storage (in production, use proper database)
        self.access_tokens: Dict[str, Dict[str, Any]] = {}
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}
    
    def create_access_token(self, 
                          client_id: str,
                          scope: Optional[str] = None,
                          business_id: Optional[str] = None,
                          agent_id: Optional[str] = None) -> str:
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
    
    def create_refresh_token(self,
                           client_id: str,
                           scope: Optional[str] = None,
                           business_id: Optional[str] = None,
                           agent_id: Optional[str] = None) -> str:
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
    
    def validate_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Validate refresh token and return token data"""
        if refresh_token not in self.refresh_tokens:
            return None
        
        token_data = self.refresh_tokens[refresh_token]
        
        # Check expiration
        if datetime.utcnow() > token_data["expires_at"]:
            del self.refresh_tokens[refresh_token]
            return None
        
        return token_data
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token"""
        if token in self.access_tokens:
            del self.access_tokens[token]
            return True
        return False
