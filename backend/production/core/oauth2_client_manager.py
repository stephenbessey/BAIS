"""
OAuth 2.0 Client Management
Handles OAuth client registration, validation, and management
"""

from typing import Dict, List, Any
from .oauth2_security import OAuth2ClientCredentials
import bcrypt


class OAuth2ClientManager:
    """Manages OAuth 2.0 client credentials and validation"""
    
    def __init__(self):
        self.clients: Dict[str, OAuth2ClientCredentials] = {}
        self._initialize_default_clients()
    
    def _initialize_default_clients(self) -> None:
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
    
    def register_client(self, client_data: OAuth2ClientCredentials) -> str:
        """Register a new OAuth client"""
        client_data.client_secret = self._hash_secret(client_data.client_secret)
        self.clients[client_data.client_id] = client_data
        return client_data.client_id
    
    def validate_client(self, client_id: str, client_secret: str) -> bool:
        """Validate client credentials"""
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        return self._verify_secret(client_secret, client.client_secret)
    
    def get_client(self, client_id: str) -> OAuth2ClientCredentials:
        """Get client by ID"""
        return self.clients.get(client_id)
    
    def _hash_secret(self, secret: str) -> str:
        """Hash client secret"""
        return bcrypt.hashpw(secret.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_secret(self, secret: str, hashed: str) -> bool:
        """Verify client secret"""
        return bcrypt.checkpw(secret.encode('utf-8'), hashed.encode('utf-8'))
