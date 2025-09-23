"""
Enhanced Protocol Configuration Management
Implements Clean Code principles for configuration
"""

from typing import Optional, List
from pydantic import BaseSettings, Field, validator
from dataclasses import dataclass
import os


class A2ASettings(BaseSettings):
    """A2A Protocol Configuration with validation"""
    
    enabled: bool = Field(default=True, description="Enable A2A protocol")
    base_url: str = Field(default="http://localhost:8002", description="A2A server base URL")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout")
    max_task_timeout: int = Field(default=300, ge=30, le=3600, description="Maximum task timeout")
    max_concurrent_tasks: int = Field(default=100, ge=1, le=1000, description="Max concurrent tasks")
    discovery_cache_ttl: int = Field(default=300, ge=60, le=3600, description="Discovery cache TTL")
    
    @validator('base_url')
    def validate_base_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('A2A base URL must start with http:// or https://')
        return v
    
    class Config:
        env_prefix = "A2A_"


class AP2Settings(BaseSettings):
    """AP2 Payment Protocol Configuration with validation"""
    
    enabled: bool = Field(default=False, description="Enable AP2 payments")
    client_id: Optional[str] = Field(None, description="AP2 client ID")
    private_key: Optional[str] = Field(None, description="AP2 private key (PEM format)")
    public_key: Optional[str] = Field(None, description="AP2 public key (PEM format)")
    base_url: str = Field(default="https://ap2-network.example.com", description="AP2 network URL")
    timeout: int = Field(default=30, ge=5, le=120, description="Request timeout")
    mandate_expiry_hours: int = Field(default=24, ge=1, le=168, description="Default mandate expiry")
    verification_required: bool = Field(default=True, description="Require payment verification")
    
    @validator('enabled')
    def validate_enabled(cls, v, values):
        if v and not values.get('client_id'):
            raise ValueError('AP2_CLIENT_ID is required when AP2 is enabled')
        return v
    
    @validator('private_key')
    def validate_private_key(cls, v):
        if v and not v.startswith('-----BEGIN PRIVATE KEY-----'):
            raise ValueError('AP2 private key must be in PEM format')
        return v
    
    @validator('public_key') 
    def validate_public_key(cls, v):
        if v and not v.startswith('-----BEGIN PUBLIC KEY-----'):
            raise ValueError('AP2 public key must be in PEM format')
        return v
    
    class Config:
        env_prefix = "AP2_"


@dataclass(frozen=True)
class ProtocolConstants:
    """Protocol constants following Clean Code principles"""
    
    # A2A Constants
    A2A_AGENT_CARD_PATH: str = "/.well-known/agent.json"
    A2A_TASK_ENDPOINT: str = "/a2a/v1/tasks"
    A2A_DISCOVERY_ENDPOINT: str = "/a2a/v1/discover"
    A2A_MAX_AGENT_DESCRIPTION_LENGTH: int = 500
    A2A_MAX_CAPABILITY_NAME_LENGTH: int = 100
    
    # AP2 Constants  
    AP2_INTENT_MANDATE_TYPE: str = "intent"
    AP2_CART_MANDATE_TYPE: str = "cart"
    AP2_SIGNATURE_ALGORITHM: str = "RS256"
    AP2_MAX_MANDATE_SIZE_BYTES: int = 1024 * 10  # 10KB
    AP2_MIN_PAYMENT_AMOUNT: float = 0.01


class ValidationError(Exception):
    """Configuration validation error"""
    
    def __init__(self, message: str, field: str = None, value: any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class ConfigurationValidator:
    """Validates protocol configurations"""
    
    @staticmethod
    def validate_a2a_config(config: A2ASettings) -> List[str]:
        """Validate A2A configuration"""
        errors = []
        
        if config.enabled:
            if config.timeout_seconds > config.max_task_timeout:
                errors.append("A2A timeout cannot exceed max task timeout")
            
            if config.max_concurrent_tasks < 1:
                errors.append("A2A max concurrent tasks must be at least 1")
        
        return errors
    
    @staticmethod
    def validate_ap2_config(config: AP2Settings) -> List[str]:
        """Validate AP2 configuration"""
        errors = []
        
        if config.enabled:
            if not config.client_id:
                errors.append("AP2 client ID is required when enabled")
            
            if not config.private_key:
                errors.append("AP2 private key is required when enabled") 
            
            if not config.public_key:
                errors.append("AP2 public key is required when enabled")
            
            if config.mandate_expiry_hours < 1:
                errors.append("AP2 mandate expiry must be at least 1 hour")
        
        return errors
    
    @staticmethod
    def validate_all_configs(a2a: A2ASettings, ap2: AP2Settings) -> List[str]:
        """Validate all protocol configurations"""
        errors = []
        errors.extend(ConfigurationValidator.validate_a2a_config(a2a))
        errors.extend(ConfigurationValidator.validate_ap2_config(ap2))
        return errors


# Configuration factory
class ProtocolConfigurationFactory:
    """Factory for creating validated protocol configurations"""
    
    @staticmethod
    def create_a2a_config() -> A2ASettings:
        """Create validated A2A configuration"""
        config = A2ASettings()
        errors = ConfigurationValidator.validate_a2a_config(config)
        
        if errors:
            raise ValidationError(f"A2A configuration invalid: {'; '.join(errors)}")
        
        return config
    
    @staticmethod
    def create_ap2_config() -> AP2Settings:
        """Create validated AP2 configuration"""
        config = AP2Settings()
        errors = ConfigurationValidator.validate_ap2_config(config)
        
        if errors:
            raise ValidationError(f"AP2 configuration invalid: {'; '.join(errors)}")
        
        return config
    
    @staticmethod
    def create_all_configs() -> tuple[A2ASettings, AP2Settings]:
        """Create all protocol configurations with cross-validation"""
        a2a_config = A2ASettings()
        ap2_config = AP2Settings()
        
        errors = ConfigurationValidator.validate_all_configs(a2a_config, ap2_config)
        
        if errors:
            raise ValidationError(f"Protocol configuration invalid: {'; '.join(errors)}")
        
        return a2a_config, ap2_config


# Usage in main application
def get_validated_configs():
    """Get validated protocol configurations"""
    try:
        return ProtocolConfigurationFactory.create_all_configs()
    except ValidationError as e:
        print(f"Configuration error: {e}")
        raise
