"""
Secure Secrets Manager - Clean Code Implementation
Centralized secrets management following security best practices
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from cryptography.fernet import Fernet
import base64

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Centralized secrets management
    Ensures all secrets are loaded from environment variables
    """
    
    def __init__(self):
        self._validate_required_secrets()
        self._encryption_key = self._get_or_create_encryption_key()
    
    def _validate_required_secrets(self):
        """Validate all required secrets are present"""
        required_secrets = [
            'JWT_SECRET_KEY',
            'DATABASE_URL',
            'REDIS_URL',
            'AP2_CLIENT_ID',
            'AP2_PRIVATE_KEY',
            'A2A_AGENT_ID'
        ]
        
        missing = [s for s in required_secrets if not os.getenv(s)]
        if missing:
            logger.error(f"Missing required secrets: {', '.join(missing)}")
            raise ValueError(f"Missing required secrets: {', '.join(missing)}")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_env = os.getenv('ENCRYPTION_KEY')
        if key_env:
            try:
                return base64.urlsafe_b64decode(key_env.encode())
            except Exception as e:
                logger.warning(f"Invalid encryption key format: {e}")
        
        # Generate new key if not provided or invalid
        key = Fernet.generate_key()
        logger.warning("Generated new encryption key. Set ENCRYPTION_KEY environment variable for persistence.")
        return key
    
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> str:
        """Get secret from environment"""
        value = os.getenv(key, default)
        if value is None:
            logger.error(f"Secret not found: {key}")
            raise ValueError(f"Secret not found: {key}")
        return value
    
    @staticmethod
    def get_secret_or_none(key: str) -> Optional[str]:
        """Get secret or return None if not found"""
        return os.getenv(key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            fernet = Fernet(self._encryption_key)
            encrypted_data = fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            raise
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            fernet = Fernet(self._encryption_key)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise
    
    def get_database_url(self) -> str:
        """Get database URL"""
        return self.get_secret('DATABASE_URL')
    
    def get_redis_url(self) -> str:
        """Get Redis URL"""
        return self.get_secret('REDIS_URL')
    
    def get_jwt_secret(self) -> str:
        """Get JWT secret key"""
        return self.get_secret('JWT_SECRET_KEY')
    
    def get_ap2_credentials(self) -> Dict[str, str]:
        """Get AP2 credentials"""
        return {
            'client_id': self.get_secret('AP2_CLIENT_ID'),
            'private_key': self.get_secret('AP2_PRIVATE_KEY'),
            'public_key': self.get_secret_or_none('AP2_PUBLIC_KEY') or '',
            'webhook_secret': self.get_secret_or_none('AP2_WEBHOOK_SECRET') or ''
        }
    
    def get_a2a_credentials(self) -> Dict[str, str]:
        """Get A2A credentials"""
        return {
            'agent_id': self.get_secret('A2A_AGENT_ID'),
            'private_key': self.get_secret_or_none('A2A_PRIVATE_KEY') or '',
            'public_key': self.get_secret_or_none('A2A_PUBLIC_KEY') or ''
        }
    
    def get_oauth_credentials(self) -> Dict[str, str]:
        """Get OAuth credentials"""
        return {
            'client_id': self.get_secret_or_none('OAUTH_CLIENT_ID') or '',
            'client_secret': self.get_secret_or_none('OAUTH_CLIENT_SECRET') or '',
            'redirect_uri': self.get_secret_or_none('OAUTH_REDIRECT_URI') or ''
        }
    
    def validate_secrets_strength(self) -> Dict[str, Any]:
        """Validate strength of secrets"""
        results = {}
        
        # Check JWT secret strength
        jwt_secret = self.get_jwt_secret()
        results['jwt_secret'] = {
            'length': len(jwt_secret),
            'is_strong': len(jwt_secret) >= 32,
            'has_special_chars': any(c in jwt_secret for c in '!@#$%^&*()_+-=[]{}|;:,.<>?')
        }
        
        # Check encryption key
        results['encryption_key'] = {
            'present': bool(self._encryption_key),
            'length': len(self._encryption_key) if self._encryption_key else 0,
            'is_valid': len(self._encryption_key) == 32 if self._encryption_key else False
        }
        
        return results
    
    def get_secrets_summary(self) -> Dict[str, Any]:
        """Get summary of all secrets (without exposing values)"""
        secrets = {
            'jwt_secret': {'present': bool(self.get_secret_or_none('JWT_SECRET_KEY'))},
            'database_url': {'present': bool(self.get_secret_or_none('DATABASE_URL'))},
            'redis_url': {'present': bool(self.get_secret_or_none('REDIS_URL'))},
            'ap2_credentials': {
                'client_id': {'present': bool(self.get_secret_or_none('AP2_CLIENT_ID'))},
                'private_key': {'present': bool(self.get_secret_or_none('AP2_PRIVATE_KEY'))},
                'public_key': {'present': bool(self.get_secret_or_none('AP2_PUBLIC_KEY'))},
                'webhook_secret': {'present': bool(self.get_secret_or_none('AP2_WEBHOOK_SECRET'))}
            },
            'a2a_credentials': {
                'agent_id': {'present': bool(self.get_secret_or_none('A2A_AGENT_ID'))},
                'private_key': {'present': bool(self.get_secret_or_none('A2A_PRIVATE_KEY'))},
                'public_key': {'present': bool(self.get_secret_or_none('A2A_PUBLIC_KEY'))}
            },
            'oauth_credentials': {
                'client_id': {'present': bool(self.get_secret_or_none('OAUTH_CLIENT_ID'))},
                'client_secret': {'present': bool(self.get_secret_or_none('OAUTH_CLIENT_SECRET'))},
                'redirect_uri': {'present': bool(self.get_secret_or_none('OAUTH_REDIRECT_URI'))}
            }
        }
        
        return secrets


@lru_cache()
def get_secrets_manager() -> SecretsManager:
    """Singleton secrets manager"""
    return SecretsManager()


# Convenience functions
def get_database_url() -> str:
    """Get database URL"""
    return get_secrets_manager().get_database_url()


def get_redis_url() -> str:
    """Get Redis URL"""
    return get_secrets_manager().get_redis_url()


def get_jwt_secret() -> str:
    """Get JWT secret key"""
    return get_secrets_manager().get_jwt_secret()


def get_ap2_credentials() -> Dict[str, str]:
    """Get AP2 credentials"""
    return get_secrets_manager().get_ap2_credentials()


def get_a2a_credentials() -> Dict[str, str]:
    """Get A2A credentials"""
    return get_secrets_manager().get_a2a_credentials()


if __name__ == "__main__":
    # Example usage and validation
    try:
        manager = get_secrets_manager()
        
        print("✅ Secrets Manager initialized successfully")
        
        # Validate secrets strength
        strength = manager.validate_secrets_strength()
        print(f"JWT Secret Strength: {strength['jwt_secret']['is_strong']}")
        print(f"Encryption Key Valid: {strength['encryption_key']['is_valid']}")
        
        # Get summary
        summary = manager.get_secrets_summary()
        print(f"Secrets Summary: {summary}")
        
    except Exception as e:
        print(f"❌ Secrets Manager validation failed: {e}")
        print("Please ensure all required environment variables are set.")
