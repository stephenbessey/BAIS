"""
BAIS Application Configuration
Centralized configuration management using Pydantic BaseSettings
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    url: str = Field(
        default="postgresql://user:password@localhost/bais_db",
        description="Database connection URL"
    )
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=200, description="Maximum pool overflow")
    pool_timeout: int = Field(default=30, ge=1, le=300, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, ge=300, le=86400, description="Pool recycle time in seconds")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    
    class Config:
        env_prefix = "DB_"


class APISettings(BaseSettings):
    """API configuration settings"""
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Default API timeout")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=1, ge=1, le=60, description="Base retry delay")
    rate_limit_per_minute: int = Field(default=100, ge=1, le=10000, description="Rate limit per minute")
    max_request_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum request size in MB")
    
    class Config:
        env_prefix = "API_"


class SecuritySettings(BaseSettings):
    """Security configuration settings"""
    secret_key: str = Field(..., description="Application secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=60, ge=1, le=1440, description="Access token expiration")
    refresh_token_expire_days: int = Field(default=30, ge=1, le=365, description="Refresh token expiration")
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"], description="CORS allowed origins")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    class Config:
        env_prefix = "SECURITY_"


class MonitoringSettings(BaseSettings):
    """Monitoring and logging configuration"""
    log_level: str = Field(default="INFO", description="Logging level")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, ge=1000, le=65535, description="Metrics server port")
    health_check_interval: int = Field(default=30, ge=5, le=300, description="Health check interval in seconds")
    log_retention_days: int = Field(default=30, ge=1, le=365, description="Log retention period")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    class Config:
        env_prefix = "MONITORING_"


class BAISSettings(BaseSettings):
    """BAIS-specific configuration"""
    version: str = Field(default="1.0.0", description="BAIS version")
    schema_validation_enabled: bool = Field(default=True, description="Enable schema validation")
    mock_mode: bool = Field(default=False, description="Enable mock mode for testing")
    default_business_type: str = Field(default="hospitality", description="Default business type")
    environment: str = Field(default="development", description="Application environment")
    
    @validator('environment')
    def validate_environment(cls, v):
        valid_envs = ['development', 'testing', 'staging', 'production']
        if v.lower() not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v.lower()
    
    class Config:
        env_prefix = "BAIS_"


class OAuthSettings(BaseSettings):
    """OAuth 2.0 configuration"""
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(..., description="OAuth client secret")
    authorization_endpoint: str = Field(default="/oauth/authorize", description="Authorization endpoint")
    token_endpoint: str = Field(default="/oauth/token", description="Token endpoint")
    introspection_endpoint: str = Field(default="/oauth/introspect", description="Token introspection endpoint")
    
    class Config:
        env_prefix = "OAUTH_"


class Settings(BaseSettings):
    """Main application settings"""
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    bais: BAISSettings = Field(default_factory=BAISSettings)
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)
    
    # Application metadata
    app_name: str = Field(default="BAIS Production Server", description="Application name")
    app_description: str = Field(
        default="Business-Agent Integration Standard Production Implementation",
        description="Application description"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


def get_database_url() -> str:
    """Get database URL from settings"""
    settings = get_settings()
    return settings.database.url


def get_secret_key() -> str:
    """Get secret key from settings"""
    settings = get_settings()
    return settings.security.secret_key


def get_cors_origins() -> List[str]:
    """Get CORS origins from settings"""
    settings = get_settings()
    return settings.security.cors_origins


def is_development() -> bool:
    """Check if running in development environment"""
    settings = get_settings()
    return settings.bais.environment == "development"


def is_production() -> bool:
    """Check if running in production environment"""
    settings = get_settings()
    return settings.bais.environment == "production"
