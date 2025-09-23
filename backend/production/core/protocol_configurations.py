"""
Protocol Configuration Constants
Centralized configuration for A2A and AP2 protocols

This module eliminates magic numbers and hardcoded values throughout
the codebase by providing centralized configuration constants.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from enum import Enum


class A2ATaskStatus(Enum):
    """A2A task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AP2EventType(Enum):
    """AP2 webhook event types"""
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    MANDATE_REVOKED = "mandate_revoked"
    MANDATE_EXPIRED = "mandate_expired"
    PAYMENT_AUTHORIZED = "payment_authorized"
    PAYMENT_DECLINED = "payment_declined"


class PaymentStatus(Enum):
    """Payment status enumeration"""
    INITIALIZING = "initializing"
    INTENT_AUTHORIZED = "intent_authorized"
    CART_CONFIRMED = "cart_confirmed"
    PAYMENT_PROCESSING = "payment_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class A2AConfiguration:
    """A2A Protocol configuration constants"""
    # Timeout configurations
    DEFAULT_TIMEOUT_SECONDS: int = 30
    MAX_TASK_TIMEOUT_SECONDS: int = 300
    MIN_TASK_TIMEOUT_SECONDS: int = 5
    
    # Concurrency configurations
    MAX_CONCURRENT_TASKS: int = 100
    MAX_CONCURRENT_DISCOVERIES: int = 50
    
    # Cleanup configurations
    TASK_CLEANUP_INTERVAL_MINUTES: int = 60
    MAX_TASK_AGE_HOURS: int = 24
    
    # Discovery configurations
    DISCOVERY_CACHE_TTL_MINUTES: int = 5
    MAX_DISCOVERY_RETRIES: int = 3
    DISCOVERY_TIMEOUT_SECONDS: int = 10
    
    # Streaming configurations
    HEARTBEAT_INTERVAL_SECONDS: int = 30
    MAX_STREAM_DURATION_HOURS: int = 1
    STREAM_BUFFER_SIZE: int = 1000
    
    # Agent registry configurations
    MAX_AGENT_REGISTRY_ENDPOINTS: int = 5
    AGENT_REGISTRY_TIMEOUT_SECONDS: int = 15
    AGENT_SCORE_THRESHOLD: float = 0.7
    
    # Authentication configurations
    JWT_EXPIRY_MINUTES: int = 60
    OAUTH2_SCOPE_SEPARATOR: str = " "
    MAX_API_KEY_LENGTH: int = 256
    
    # Rate limiting configurations
    DEFAULT_RATE_LIMIT_PER_MINUTE: int = 100
    MAX_RATE_LIMIT_PER_MINUTE: int = 1000
    RATE_LIMIT_BURST_SIZE: int = 10


@dataclass(frozen=True)
class AP2Configuration:
    """AP2 Protocol configuration constants"""
    # Mandate configurations
    DEFAULT_MANDATE_EXPIRY_HOURS: int = 24
    MAX_MANDATE_EXPIRY_HOURS: int = 168  # 7 days
    MIN_MANDATE_EXPIRY_HOURS: int = 1
    
    # Signature configurations
    SIGNATURE_ALGORITHM: str = "RS256"
    SIGNATURE_KEY_SIZE_BITS: int = 2048
    SIGNATURE_HASH_ALGORITHM: str = "SHA256"
    
    # Currency configurations
    DEFAULT_CURRENCY: str = "USD"
    SUPPORTED_CURRENCIES: List[str] = None
    CURRENCY_PRECISION_DECIMALS: int = 2
    
    # Payment method configurations
    DEFAULT_PAYMENT_METHOD_TYPES: List[str] = None
    MAX_PAYMENT_METHOD_METADATA_SIZE: int = 1024
    
    # Webhook configurations
    WEBHOOK_TIMEOUT_SECONDS: int = 10
    MAX_WEBHOOK_RETRIES: int = 3
    WEBHOOK_RETRY_DELAY_SECONDS: int = 5
    WEBHOOK_SIGNATURE_HEADER: str = "X-AP2-Signature"
    
    # Transaction configurations
    MAX_TRANSACTION_AMOUNT: float = 1000000.0
    MIN_TRANSACTION_AMOUNT: float = 0.01
    TRANSACTION_TIMEOUT_SECONDS: int = 300
    
    # Security configurations
    ENFORCE_HTTPS: bool = True
    REQUIRE_MANDATE_VERIFICATION: bool = True
    MAX_CONSTRAINT_VALIDATION_TIME_SECONDS: int = 5
    
    # Audit configurations
    AUDIT_LOG_RETENTION_DAYS: int = 365
    AUDIT_LOG_LEVEL: str = "INFO"
    
    def __post_init__(self):
        if self.SUPPORTED_CURRENCIES is None:
            object.__setattr__(self, 'SUPPORTED_CURRENCIES', [
                'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY'
            ])
        
        if self.DEFAULT_PAYMENT_METHOD_TYPES is None:
            object.__setattr__(self, 'DEFAULT_PAYMENT_METHOD_TYPES', [
                'credit_card', 'debit_card', 'bank_transfer', 'digital_wallet'
            ])


@dataclass(frozen=True)
class MCPConfiguration:
    """MCP Protocol configuration constants"""
    # Protocol version
    PROTOCOL_VERSION: str = "2025-06-18"
    
    # Resource configurations
    MAX_RESOURCES_PER_SERVER: int = 100
    MAX_RESOURCE_CONTENT_SIZE_MB: int = 10
    RESOURCE_CACHE_TTL_MINUTES: int = 15
    
    # Tool configurations
    MAX_TOOLS_PER_SERVER: int = 50
    MAX_TOOL_INPUT_SIZE_MB: int = 5
    TOOL_EXECUTION_TIMEOUT_SECONDS: int = 60
    
    # Prompt configurations
    MAX_PROMPTS_PER_SERVER: int = 25
    MAX_PROMPT_CONTENT_SIZE_MB: int = 2
    
    # Server configurations
    MAX_SERVER_NAME_LENGTH: int = 255
    MAX_SERVER_VERSION_LENGTH: int = 50
    SERVER_HEARTBEAT_INTERVAL_SECONDS: int = 30
    
    # Connection configurations
    MAX_CONCURRENT_CONNECTIONS: int = 100
    CONNECTION_TIMEOUT_SECONDS: int = 30
    CONNECTION_RETRY_ATTEMPTS: int = 3


@dataclass(frozen=True)
class BusinessConfiguration:
    """Business service configuration constants"""
    # Validation configurations
    MAX_BUSINESS_NAME_LENGTH: int = 255
    MIN_BUSINESS_NAME_LENGTH: int = 1
    MAX_BUSINESS_DESCRIPTION_LENGTH: int = 1000
    MAX_BUSINESS_ADDRESS_LENGTH: int = 255
    
    # Service configurations
    MAX_SERVICES_PER_BUSINESS: int = 50
    MIN_SERVICES_PER_BUSINESS: int = 1
    MAX_SERVICE_NAME_LENGTH: int = 255
    MAX_SERVICE_DESCRIPTION_LENGTH: int = 1000
    
    # API key configurations
    API_KEY_LENGTH: int = 64
    API_KEY_PREFIX_LENGTH: int = 8
    MAX_API_KEYS_PER_BUSINESS: int = 5
    API_KEY_EXPIRY_DAYS: int = 365
    
    # Rate limiting configurations
    DEFAULT_RATE_LIMIT_PER_HOUR: int = 1000
    MAX_RATE_LIMIT_PER_HOUR: int = 10000
    MIN_RATE_LIMIT_PER_HOUR: int = 100
    
    # Integration configurations
    MAX_INTEGRATION_ENDPOINTS: int = 10
    INTEGRATION_TIMEOUT_SECONDS: int = 30
    MAX_INTEGRATION_RETRIES: int = 3


@dataclass(frozen=True)
class DatabaseConfiguration:
    """Database configuration constants"""
    # Connection configurations
    DEFAULT_POOL_SIZE: int = 10
    MAX_POOL_OVERFLOW: int = 20
    POOL_TIMEOUT_SECONDS: int = 30
    POOL_RECYCLE_SECONDS: int = 3600
    
    # Query configurations
    DEFAULT_QUERY_LIMIT: int = 100
    MAX_QUERY_LIMIT: int = 1000
    DEFAULT_QUERY_OFFSET: int = 0
    
    # Transaction configurations
    TRANSACTION_TIMEOUT_SECONDS: int = 60
    MAX_TRANSACTION_RETRIES: int = 3
    
    # Migration configurations
    MIGRATION_BATCH_SIZE: int = 1000
    MIGRATION_TIMEOUT_MINUTES: int = 30


@dataclass(frozen=True)
class MonitoringConfiguration:
    """Monitoring and observability configuration constants"""
    # Metrics configurations
    METRICS_COLLECTION_INTERVAL_SECONDS: int = 60
    METRICS_RETENTION_DAYS: int = 30
    METRICS_BATCH_SIZE: int = 100
    
    # Logging configurations
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_ROTATION_SIZE_MB: int = 100
    LOG_RETENTION_DAYS: int = 30
    
    # Health check configurations
    HEALTH_CHECK_INTERVAL_SECONDS: int = 30
    HEALTH_CHECK_TIMEOUT_SECONDS: int = 5
    HEALTH_CHECK_RETRIES: int = 3
    
    # Alert configurations
    ALERT_COOLDOWN_MINUTES: int = 15
    MAX_ALERTS_PER_HOUR: int = 100
    ALERT_RETENTION_DAYS: int = 7


# Global configuration instances
A2A_CONFIG = A2AConfiguration()
AP2_CONFIG = AP2Configuration()
MCP_CONFIG = MCPConfiguration()
BUSINESS_CONFIG = BusinessConfiguration()
DATABASE_CONFIG = DatabaseConfiguration()
MONITORING_CONFIG = MonitoringConfiguration()


def get_config(config_type: str):
    """
    Get configuration by type
    
    Args:
        config_type: Type of configuration ('a2a', 'ap2', 'mcp', 'business', 'database', 'monitoring')
        
    Returns:
        Configuration instance
        
    Raises:
        ValueError: If config_type is not recognized
    """
    config_map = {
        'a2a': A2A_CONFIG,
        'ap2': AP2_CONFIG,
        'mcp': MCP_CONFIG,
        'business': BUSINESS_CONFIG,
        'database': DATABASE_CONFIG,
        'monitoring': MONITORING_CONFIG
    }
    
    if config_type not in config_map:
        raise ValueError(f"Unknown configuration type: {config_type}")
    
    return config_map[config_type]


def validate_configuration_value(value: Any, config_class: type, field_name: str) -> bool:
    """
    Validate a configuration value against its type definition
    
    Args:
        value: Value to validate
        config_class: Configuration class
        field_name: Field name to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Get field information
        import dataclasses
        fields = dataclasses.fields(config_class)
        field = next((f for f in fields if f.name == field_name), None)
        
        if field is None:
            return False
        
        # Basic type validation
        if hasattr(field.type, '__origin__'):
            # Handle generic types like List[str]
            return True  # Simplified validation
        else:
            return isinstance(value, field.type)
            
    except Exception:
        return False
