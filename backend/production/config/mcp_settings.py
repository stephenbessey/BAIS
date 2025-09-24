"""
MCP Configuration Management - Implementation
Centralized configuration for MCP server following best practices
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration following best practices"""
    host: str = "localhost"
    port: int = 5432
    database: str = "bais_mcp"
    username: str = "bais_user"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    def get_connection_string(self) -> str:
        """Get database connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class RedisConfig:
    """Redis configuration for caching and rate limiting"""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True


@dataclass
class SecurityConfig:
    """Security configuration following best practices"""
    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    rate_limit_burst: int = 10
    
    # Request limits
    max_request_size_mb: int = 10
    max_json_payload_size_kb: int = 100
    max_string_length: int = 1000
    
    # Security headers
    enable_security_headers: bool = True
    enable_cors: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    allowed_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # JWT settings
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # OAuth settings
    oauth_discovery_url: str = "https://oauth.example.com/.well-known/openid-configuration"
    oauth_client_id: str = "bais-mcp-client"
    oauth_client_secret: str = "your-oauth-secret"
    oauth_scopes: List[str] = field(default_factory=lambda: [
        "resource:read", "tool:execute", "prompt:read"
    ])


@dataclass
class LoggingConfig:
    """Logging configuration following best practices"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size_mb: int = 10
    backup_count: int = 5
    enable_json_logging: bool = False
    enable_audit_logging: bool = True
    audit_log_path: str = "/var/log/bais/mcp_audit.log"
    sensitive_data_fields: List[str] = field(default_factory=lambda: [
        "password", "token", "secret", "key", "authorization"
    ])


@dataclass
class AP2Config:
    """AP2 protocol configuration"""
    base_url: str = "https://ap2.example.com"
    client_id: str = "bais-ap2-client"
    private_key_path: str = "/etc/bais/keys/ap2_private.pem"
    public_key_path: str = "/etc/bais/keys/ap2_public.pem"
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: int = 1
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60


@dataclass
class A2AConfig:
    """A2A protocol configuration"""
    server_endpoint: str = "https://api.example.com/a2a/v1"
    agent_id: str = "bais-agent"
    registry_networks: List[str] = field(default_factory=lambda: [
        "https://registry1.example.com",
        "https://registry2.example.com"
    ])
    discovery_timeout_seconds: int = 30
    capability_refresh_interval_minutes: int = 60
    enable_reputation_scoring: bool = True
    min_reputation_score: float = 0.7


@dataclass
class MCPServerConfig:
    """Main MCP server configuration following best practices"""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    
    # Protocol settings
    protocol_version: str = "2025-06-18"
    server_name: str = "BAIS MCP Server"
    server_version: str = "1.0.0"
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ap2: AP2Config = field(default_factory=AP2Config)
    a2a: A2AConfig = field(default_factory=A2AConfig)
    
    # Feature flags
    enable_a2a: bool = True
    enable_ap2: bool = True
    enable_metrics: bool = True
    enable_health_checks: bool = True
    enable_graceful_shutdown: bool = True
    
    # Performance settings
    max_concurrent_requests: int = 100
    request_timeout_seconds: int = 30
    worker_count: int = 1
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Validate required fields
        if not self.security.jwt_secret_key or self.security.jwt_secret_key == "your-secret-key-change-in-production":
            issues.append("JWT secret key must be set for production")
        
        if not self.ap2.private_key_path or not Path(self.ap2.private_key_path).exists():
            issues.append(f"AP2 private key file not found: {self.ap2.private_key_path}")
        
        if not self.ap2.public_key_path or not Path(self.ap2.public_key_path).exists():
            issues.append(f"AP2 public key file not found: {self.ap2.public_key_path}")
        
        # Validate numeric ranges
        if self.security.rate_limit_per_minute <= 0:
            issues.append("Rate limit per minute must be positive")
        
        if self.max_concurrent_requests <= 0:
            issues.append("Max concurrent requests must be positive")
        
        # Validate URLs
        if not self.ap2.base_url.startswith(('http://', 'https://')):
            issues.append("AP2 base URL must start with http:// or https://")
        
        if not self.a2a.server_endpoint.startswith(('http://', 'https://')):
            issues.append("A2A server endpoint must start with http:// or https://")
        
        return issues


class MCPSettingsManager:
    """Configuration manager following best practices"""
    
    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path
        self._config: Optional[MCPServerConfig] = None
        self._environment_overrides: Dict[str, Any] = {}
    
    def load_config(self) -> MCPServerConfig:
        """Load configuration from file and environment"""
        if self._config is not None:
            return self._config
        
        # Load from file if provided
        if self._config_path and Path(self._config_path).exists():
            self._config = self._load_from_file(self._config_path)
        else:
            # Create default configuration
            self._config = MCPServerConfig()
        
        # Apply environment overrides
        self._apply_environment_overrides()
        
        # Validate configuration
        issues = self._config.validate_config()
        if issues:
            logger.warning(f"Configuration validation issues: {issues}")
        
        return self._config
    
    def _load_from_file(self, config_path: str) -> MCPServerConfig:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Convert nested dictionaries to dataclass instances
            return self._dict_to_config(config_data)
        
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            return MCPServerConfig()
    
    def _dict_to_config(self, config_data: Dict[str, Any]) -> MCPServerConfig:
        """Convert dictionary to MCPServerConfig instance"""
        # Handle nested configurations
        if 'database' in config_data:
            config_data['database'] = DatabaseConfig(**config_data['database'])
        
        if 'redis' in config_data:
            config_data['redis'] = RedisConfig(**config_data['redis'])
        
        if 'security' in config_data:
            config_data['security'] = SecurityConfig(**config_data['security'])
        
        if 'logging' in config_data:
            config_data['logging'] = LoggingConfig(**config_data['logging'])
        
        if 'ap2' in config_data:
            config_data['ap2'] = AP2Config(**config_data['ap2'])
        
        if 'a2a' in config_data:
            config_data['a2a'] = A2AConfig(**config_data['a2a'])
        
        return MCPServerConfig(**config_data)
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides"""
        if not self._config:
            return
        
        # Database overrides
        if os.getenv('DATABASE_HOST'):
            self._config.database.host = os.getenv('DATABASE_HOST')
        if os.getenv('DATABASE_PORT'):
            self._config.database.port = int(os.getenv('DATABASE_PORT'))
        if os.getenv('DATABASE_NAME'):
            self._config.database.database = os.getenv('DATABASE_NAME')
        if os.getenv('DATABASE_USER'):
            self._config.database.username = os.getenv('DATABASE_USER')
        if os.getenv('DATABASE_PASSWORD'):
            self._config.database.password = os.getenv('DATABASE_PASSWORD')
        
        # Redis overrides
        if os.getenv('REDIS_HOST'):
            self._config.redis.host = os.getenv('REDIS_HOST')
        if os.getenv('REDIS_PORT'):
            self._config.redis.port = int(os.getenv('REDIS_PORT'))
        if os.getenv('REDIS_PASSWORD'):
            self._config.redis.password = os.getenv('REDIS_PASSWORD')
        
        # Security overrides
        if os.getenv('JWT_SECRET_KEY'):
            self._config.security.jwt_secret_key = os.getenv('JWT_SECRET_KEY')
        if os.getenv('RATE_LIMIT_PER_MINUTE'):
            self._config.security.rate_limit_per_minute = int(os.getenv('RATE_LIMIT_PER_MINUTE'))
        
        # Server overrides
        if os.getenv('MCP_HOST'):
            self._config.host = os.getenv('MCP_HOST')
        if os.getenv('MCP_PORT'):
            self._config.port = int(os.getenv('MCP_PORT'))
        if os.getenv('MCP_DEBUG'):
            self._config.debug = os.getenv('MCP_DEBUG').lower() in ('true', '1', 'yes')
        
        # AP2 overrides
        if os.getenv('AP2_BASE_URL'):
            self._config.ap2.base_url = os.getenv('AP2_BASE_URL')
        if os.getenv('AP2_CLIENT_ID'):
            self._config.ap2.client_id = os.getenv('AP2_CLIENT_ID')
        
        # A2A overrides
        if os.getenv('A2A_SERVER_ENDPOINT'):
            self._config.a2a.server_endpoint = os.getenv('A2A_SERVER_ENDPOINT')
        if os.getenv('A2A_AGENT_ID'):
            self._config.a2a.agent_id = os.getenv('A2A_AGENT_ID')
    
    def get_config(self) -> MCPServerConfig:
        """Get current configuration"""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def reload_config(self) -> MCPServerConfig:
        """Reload configuration from file"""
        self._config = None
        return self.load_config()
    
    def update_config(self, updates: Dict[str, Any]) -> MCPServerConfig:
        """Update configuration with new values"""
        if not self._config:
            self._config = MCPServerConfig()
        
        # Apply updates recursively
        self._update_nested_config(self._config, updates)
        
        return self._config
    
    def _update_nested_config(self, config_obj: Any, updates: Dict[str, Any]):
        """Update nested configuration object"""
        for key, value in updates.items():
            if hasattr(config_obj, key):
                if isinstance(value, dict) and hasattr(getattr(config_obj, key), '__dict__'):
                    # Update nested configuration object
                    nested_obj = getattr(config_obj, key)
                    self._update_nested_config(nested_obj, value)
                else:
                    # Update simple attribute
                    setattr(config_obj, key, value)
    
    def save_config(self, config_path: str):
        """Save current configuration to file"""
        if not self._config:
            return
        
        config_dict = self._config_to_dict(self._config)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            logger.info(f"Configuration saved to {config_path}")
        
        except Exception as e:
            logger.error(f"Failed to save configuration to {config_path}: {e}")
    
    def _config_to_dict(self, config_obj: Any) -> Dict[str, Any]:
        """Convert configuration object to dictionary"""
        if hasattr(config_obj, '__dict__'):
            result = {}
            for key, value in config_obj.__dict__.items():
                if hasattr(value, '__dict__'):
                    result[key] = self._config_to_dict(value)
                else:
                    result[key] = value
            return result
        return config_obj


# Global configuration manager instance
_settings_manager: Optional[MCPSettingsManager] = None


def get_settings_manager(config_path: Optional[str] = None) -> MCPSettingsManager:
    """Get global settings manager instance"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = MCPSettingsManager(config_path)
    return _settings_manager


def get_mcp_config() -> MCPServerConfig:
    """Get MCP server configuration"""
    return get_settings_manager().get_config()


def reload_mcp_config() -> MCPServerConfig:
    """Reload MCP server configuration"""
    return get_settings_manager().reload_config()


# Configuration validation models for Pydantic
class DatabaseConfigModel(BaseModel):
    """Pydantic model for database configuration validation"""
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database: str = Field(default="bais_mcp", description="Database name")
    username: str = Field(default="bais_user", description="Database username")
    password: str = Field(default="", description="Database password")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=200, description="Maximum overflow connections")
    pool_timeout: int = Field(default=30, ge=1, le=300, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, ge=300, le=86400, description="Pool recycle time in seconds")


class SecurityConfigModel(BaseModel):
    """Pydantic model for security configuration validation"""
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000, description="Rate limit per minute")
    rate_limit_per_hour: int = Field(default=1000, ge=1, le=100000, description="Rate limit per hour")
    rate_limit_burst: int = Field(default=10, ge=1, le=1000, description="Rate limit burst")
    max_request_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum request size in MB")
    max_json_payload_size_kb: int = Field(default=100, ge=1, le=10000, description="Maximum JSON payload size in KB")
    max_string_length: int = Field(default=1000, ge=10, le=10000, description="Maximum string length")
    jwt_secret_key: str = Field(..., min_length=32, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", regex="^(HS256|HS384|HS512|RS256|RS384|RS512)$", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1, le=1440, description="JWT access token expire time in minutes")
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, le=365, description="JWT refresh token expire time in days")
    
    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v):
        if v == "your-secret-key-change-in-production":
            raise ValueError("JWT secret key must be changed from default value")
        return v


class MCPServerConfigModel(BaseModel):
    """Pydantic model for MCP server configuration validation"""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    reload: bool = Field(default=False, description="Auto-reload mode")
    protocol_version: str = Field(default="2025-06-18", description="MCP protocol version")
    server_name: str = Field(default="BAIS MCP Server", description="Server name")
    server_version: str = Field(default="1.0.0", description="Server version")
    max_concurrent_requests: int = Field(default=100, ge=1, le=10000, description="Maximum concurrent requests")
    request_timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    worker_count: int = Field(default=1, ge=1, le=100, description="Worker count")
    
    database: DatabaseConfigModel = Field(default_factory=DatabaseConfigModel)
    security: SecurityConfigModel = Field(default_factory=SecurityConfigModel)
    
    @validator('protocol_version')
    def validate_protocol_version(cls, v):
        supported_versions = ["2025-06-18"]
        if v not in supported_versions:
            raise ValueError(f"Unsupported protocol version. Supported: {supported_versions}")
        return v


if __name__ == "__main__":
    # Example usage
    settings_manager = get_settings_manager()
    config = settings_manager.load_config()
    
    print("MCP Server Configuration:")
    print(f"Host: {config.host}")
    print(f"Port: {config.port}")
    print(f"Debug: {config.debug}")
    print(f"Protocol Version: {config.protocol_version}")
    print(f"Database: {config.database.host}:{config.database.port}/{config.database.database}")
    print(f"Rate Limit: {config.security.rate_limit_per_minute} requests/minute")
    
    # Validate configuration
    issues = config.validate_config()
    if issues:
        print(f"\nConfiguration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\nConfiguration is valid!")
