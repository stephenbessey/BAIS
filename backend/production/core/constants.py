"""
BAIS Application Constants
Centralized constants to eliminate magic numbers and improve maintainability
"""

from typing import Final


class DatabaseLimits:
    """Database-related limits and constraints"""
    DEFAULT_QUERY_LIMIT: Final[int] = 100  # Optimal for UI pagination performance
    MAX_QUERY_LIMIT: Final[int] = 1000  # Prevents excessive data retrieval
    DEFAULT_OFFSET: Final[int] = 0
    
    # Connection pool settings
    DEFAULT_POOL_SIZE: Final[int] = 10  # Based on typical web app usage
    MAX_POOL_OVERFLOW: Final[int] = 20  # Allows burst capacity
    POOL_TIMEOUT_SECONDS: Final[int] = 30  # Prevents hanging connections
    POOL_RECYCLE_HOURS: Final[int] = 1  # Prevents stale connections


class BusinessLimits:
    """Business entity limits and constraints"""
    MAX_SERVICES_PER_BUSINESS: Final[int] = 50  # Database constraint optimization
    MIN_SERVICES_PER_BUSINESS: Final[int] = 1  # Business requirement
    
    # API key limits
    DEFAULT_RATE_LIMIT_PER_HOUR: Final[int] = 1000  # Based on tier pricing
    MAX_RATE_LIMIT_PER_HOUR: Final[int] = 10000  # Premium tier limit
    MIN_RATE_LIMIT_PER_HOUR: Final[int] = 100  # Basic tier minimum
    
    # Session limits
    MAX_CONCURRENT_SESSIONS: Final[int] = 10  # Infrastructure capacity limit
    MIN_CONCURRENT_SESSIONS: Final[int] = 1
    SESSION_TIMEOUT_MINUTES: Final[int] = 30  # Security best practice


class ValidationLimits:
    """Validation and input limits"""
    # String length limits
    MAX_BUSINESS_NAME_LENGTH: Final[int] = 255  # Database column limit
    MIN_BUSINESS_NAME_LENGTH: Final[int] = 1
    MAX_DESCRIPTION_LENGTH: Final[int] = 1000  # UI display optimization
    
    # Service limits
    MAX_SERVICE_NAME_LENGTH: Final[int] = 255
    MAX_SERVICE_DESCRIPTION_LENGTH: Final[int] = 500
    MAX_PARAMETER_NAME_LENGTH: Final[int] = 50
    
    # Location limits
    MAX_ADDRESS_LENGTH: Final[int] = 255
    MAX_CITY_LENGTH: Final[int] = 100
    MAX_STATE_LENGTH: Final[int] = 50
    MAX_POSTAL_CODE_LENGTH: Final[int] = 20
    MAX_COUNTRY_CODE_LENGTH: Final[int] = 5
    
    # Contact limits
    MAX_WEBSITE_LENGTH: Final[int] = 255
    MAX_PHONE_LENGTH: Final[int] = 20
    MAX_EMAIL_LENGTH: Final[int] = 255


class OAuthLimits:
    """OAuth 2.0 related limits"""
    # Token expiration times
    ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 60  # Security best practice
    REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 30  # Balance security vs UX
    
    # Authorization code limits
    AUTHORIZATION_CODE_EXPIRE_MINUTES: Final[int] = 10  # OAuth 2.0 spec recommendation
    MAX_REDIRECT_URI_LENGTH: Final[int] = 255
    
    # Client limits
    MAX_CLIENT_NAME_LENGTH: Final[int] = 255
    MAX_SCOPE_LENGTH: Final[int] = 1000
    MAX_GRANT_TYPE_LENGTH: Final[int] = 50


class APIResponseLimits:
    """API response size and performance limits"""
    MAX_RESPONSE_SIZE_MB: Final[int] = 10  # Network optimization
    DEFAULT_TIMEOUT_SECONDS: Final[int] = 30  # User experience balance
    MAX_TIMEOUT_SECONDS: Final[int] = 300  # Prevents hanging requests
    MIN_TIMEOUT_SECONDS: Final[int] = 5
    
    # Retry configuration
    MAX_RETRY_ATTEMPTS: Final[int] = 3  # Reliability vs performance
    RETRY_BASE_DELAY_SECONDS: Final[int] = 1
    MAX_RETRY_DELAY_SECONDS: Final[int] = 30


class SecurityLimits:
    """Security-related limits and constraints"""
    # Password and secret limits
    MIN_PASSWORD_LENGTH: Final[int] = 8  # Security standard
    MAX_PASSWORD_LENGTH: Final[int] = 128  # Prevent DoS attacks
    
    # API key limits
    API_KEY_LENGTH: Final[int] = 32  # Cryptographic strength
    API_KEY_PREFIX_LENGTH: Final[int] = 8  # Identification prefix
    
    # Rate limiting
    DEFAULT_RATE_LIMIT_PER_MINUTE: Final[int] = 100  # API protection
    BURST_RATE_LIMIT_PER_MINUTE: Final[int] = 200  # Allow burst traffic


class WorkflowLimits:
    """Workflow and process limits"""
    # Workflow step limits
    MAX_WORKFLOW_STEPS: Final[int] = 20  # Complexity management
    MIN_WORKFLOW_STEPS: Final[int] = 1
    MAX_STEP_TIMEOUT_MINUTES: Final[int] = 1440  # 24 hours max
    DEFAULT_STEP_TIMEOUT_MINUTES: Final[int] = 30
    
    # Retry configuration
    MAX_RETRY_ATTEMPTS_PER_STEP: Final[int] = 10
    DEFAULT_RETRY_ATTEMPTS: Final[int] = 3


class IntegrationLimits:
    """External integration limits"""
    # MCP server limits
    MAX_MCP_ENDPOINT_LENGTH: Final[int] = 255
    MCP_REQUEST_TIMEOUT_SECONDS: Final[int] = 30
    
    # A2A integration limits
    MAX_A2A_DISCOVERY_URL_LENGTH: Final[int] = 255
    A2A_DISCOVERY_TIMEOUT_SECONDS: Final[int] = 10
    
    # Webhook limits
    MAX_WEBHOOK_URL_LENGTH: Final[int] = 255
    WEBHOOK_TIMEOUT_SECONDS: Final[int] = 15
    MAX_WEBHOOK_EVENTS: Final[int] = 50


class MonitoringLimits:
    """Monitoring and logging limits"""
    # Log retention
    LOG_RETENTION_DAYS: Final[int] = 30  # Compliance and storage balance
    MAX_LOG_ENTRY_LENGTH: Final[int] = 10000  # Prevent log flooding
    
    # Metrics collection
    METRICS_COLLECTION_INTERVAL_SECONDS: Final[int] = 60
    MAX_METRICS_HISTORY_DAYS: Final[int] = 90
    
    # Health check limits
    HEALTH_CHECK_TIMEOUT_SECONDS: Final[int] = 5
    HEALTH_CHECK_INTERVAL_SECONDS: Final[int] = 30


class ErrorLimits:
    """Error handling and reporting limits"""
    MAX_ERROR_MESSAGE_LENGTH: Final[int] = 1000  # User-friendly error messages
    MAX_ERROR_STACK_TRACE_LENGTH: Final[int] = 5000  # Debug information
    MAX_ERROR_CONTEXT_LENGTH: Final[int] = 2000  # Additional context
    
    # Error rate limits
    MAX_ERRORS_PER_MINUTE: Final[int] = 100  # Prevent error flooding
    ERROR_RATE_ALERT_THRESHOLD: Final[float] = 0.1  # 10% error rate threshold


class SSEConnectionLimits:
    """Server-Sent Events connection limits"""
    # Connection management
    MAX_CLIENTS_PER_CONNECTION: Final[int] = 1000  # Prevents resource exhaustion
    CLIENT_TIMEOUT_SECONDS: Final[int] = 300  # 5 minutes for inactive clients
    PING_INTERVAL_SECONDS: Final[int] = 30  # Keep-alive ping frequency
    
    # Queue limits
    MAX_QUEUE_SIZE: Final[int] = 100  # Prevents memory issues
    QUEUE_CLEANUP_INTERVAL_SECONDS: Final[int] = 300  # 5 minutes cleanup cycle
    
    # Event limits
    MAX_EVENT_SIZE_BYTES: Final[int] = 1024 * 1024  # 1MB max event size
    MAX_EVENTS_PER_SECOND: Final[int] = 100  # Rate limiting for events


class A2ALimits:
    """A2A protocol limits and timeouts"""
    # Task execution limits
    MAX_TASK_EXECUTION_TIME_SECONDS: Final[int] = 3600  # 1 hour max task time
    DEFAULT_TASK_TIMEOUT_SECONDS: Final[int] = 300  # 5 minutes default
    TASK_POLLING_INTERVAL_SECONDS: Final[int] = 1  # Task status polling
    
    # Agent discovery limits
    MAX_DISCOVERY_RESULTS: Final[int] = 50  # Limit discovery results
    DISCOVERY_TIMEOUT_SECONDS: Final[int] = 10  # Agent discovery timeout
    MAX_AGENT_CAPABILITIES: Final[int] = 20  # Limit agent capabilities
    
    # Network limits
    MAX_NETWORK_RETRIES: Final[int] = 3  # Network operation retries
    NETWORK_TIMEOUT_SECONDS: Final[int] = 30  # Network operation timeout


class AP2Limits:
    """AP2 protocol limits and constraints"""
    # Payment limits
    MAX_PAYMENT_AMOUNT: Final[float] = 1000000.0  # $1M max payment
    MIN_PAYMENT_AMOUNT: Final[float] = 0.01  # $0.01 min payment
    MAX_PAYMENT_RETRIES: Final[int] = 3  # Payment retry attempts
    
    # Mandate limits
    MANDATE_EXPIRY_HOURS: Final[int] = 24  # Default mandate expiry
    MAX_MANDATE_AMOUNT: Final[float] = 50000.0  # Max mandate amount
    MANDATE_SIGNATURE_TIMEOUT_SECONDS: Final[int] = 30  # Signature timeout
    
    # Webhook limits
    WEBHOOK_SIGNATURE_TIMEOUT_SECONDS: Final[int] = 300  # 5 minutes for timestamp validation
    WEBHOOK_REPLAY_WINDOW_SECONDS: Final[int] = 300  # 5 minutes replay protection
    MAX_WEBHOOK_RETRIES: Final[int] = 3  # Webhook delivery retries
    
    # Key management limits
    KEY_ROTATION_DAYS: Final[int] = 90  # Key rotation interval
    MAX_KEY_SIZE_BITS: Final[int] = 4096  # Maximum key size
    MIN_KEY_SIZE_BITS: Final[int] = 2048  # Minimum key size


class MCPLimits:
    """MCP protocol limits and constraints"""
    # Resource limits
    MAX_RESOURCE_SIZE_MB: Final[int] = 10  # Max resource size
    MAX_RESOURCE_URIS_PER_REQUEST: Final[int] = 100  # Batch resource requests
    RESOURCE_CACHE_TTL_SECONDS: Final[int] = 300  # 5 minutes cache TTL
    
    # Tool execution limits
    MAX_TOOL_EXECUTION_TIME_SECONDS: Final[int] = 600  # 10 minutes max
    MAX_TOOL_PARAMETERS: Final[int] = 50  # Max tool parameters
    TOOL_RESULT_SIZE_LIMIT_MB: Final[int] = 5  # Max tool result size
    
    # Prompt limits
    MAX_PROMPT_TEMPLATE_SIZE_KB: Final[int] = 100  # Max prompt template size
    MAX_PROMPT_VARIABLES: Final[int] = 100  # Max prompt variables
    PROMPT_RENDERING_TIMEOUT_SECONDS: Final[int] = 30  # Prompt rendering timeout
    
    # Subscription limits
    MAX_SUBSCRIPTIONS_PER_CLIENT: Final[int] = 100  # Client subscription limit
    DEFAULT_SUBSCRIPTION_EXPIRY_HOURS: Final[int] = 24  # Default expiry
    MAX_SUBSCRIPTION_FILTERS: Final[int] = 20  # Max filter criteria
    SUBSCRIPTION_CLEANUP_INTERVAL_SECONDS: Final[int] = 300  # 5 minutes cleanup


class CircuitBreakerLimits:
    """Circuit breaker configuration limits"""
    # Failure thresholds
    DEFAULT_FAILURE_THRESHOLD: Final[int] = 5  # Default failure count
    MAX_FAILURE_THRESHOLD: Final[int] = 50  # Maximum failure threshold
    MIN_FAILURE_THRESHOLD: Final[int] = 1  # Minimum failure threshold
    
    # Timeout limits
    DEFAULT_TIMEOUT_SECONDS: Final[int] = 30  # Default operation timeout
    MAX_TIMEOUT_SECONDS: Final[int] = 300  # Maximum timeout
    MIN_TIMEOUT_SECONDS: Final[int] = 1  # Minimum timeout
    
    # Recovery limits
    DEFAULT_RECOVERY_TIMEOUT_SECONDS: Final[int] = 60  # Default recovery time
    MAX_RECOVERY_TIMEOUT_SECONDS: Final[int] = 3600  # 1 hour max recovery
    MIN_RECOVERY_TIMEOUT_SECONDS: Final[int] = 10  # Minimum recovery time
    
    # Retry limits
    DEFAULT_MAX_RETRIES: Final[int] = 3  # Default retry count
    MAX_RETRIES: Final[int] = 10  # Maximum retries
    RETRY_BASE_DELAY_SECONDS: Final[float] = 1.0  # Base retry delay
    MAX_RETRY_DELAY_SECONDS: Final[float] = 60.0  # Maximum retry delay


class CacheLimits:
    """Caching system limits"""
    # Cache size limits
    DEFAULT_CACHE_SIZE_MB: Final[int] = 100  # Default cache size
    MAX_CACHE_SIZE_MB: Final[int] = 1000  # Maximum cache size
    MIN_CACHE_SIZE_MB: Final[int] = 10  # Minimum cache size
    
    # TTL limits
    DEFAULT_CACHE_TTL_SECONDS: Final[int] = 300  # 5 minutes default TTL
    MAX_CACHE_TTL_SECONDS: Final[int] = 86400  # 24 hours max TTL
    MIN_CACHE_TTL_SECONDS: Final[int] = 60  # 1 minute min TTL
    
    # Eviction limits
    CACHE_CLEANUP_INTERVAL_SECONDS: Final[int] = 600  # 10 minutes cleanup
    MAX_CACHE_ENTRIES: Final[int] = 10000  # Maximum cache entries


class LoggingLimits:
    """Logging and audit limits"""
    # Log level thresholds
    MAX_LOG_LEVEL: Final[str] = "ERROR"  # Maximum log level
    DEFAULT_LOG_LEVEL: Final[str] = "INFO"  # Default log level
    
    # Log size limits
    MAX_LOG_FILE_SIZE_MB: Final[int] = 100  # Maximum log file size
    MAX_LOG_FILES: Final[int] = 10  # Maximum number of log files
    
    # Audit limits
    MAX_AUDIT_EVENT_SIZE_BYTES: Final[int] = 10000  # Max audit event size
    AUDIT_RETENTION_DAYS: Final[int] = 365  # 1 year audit retention
    
    # Performance limits
    MAX_LOG_WRITE_DELAY_SECONDS: Final[float] = 1.0  # Max write delay
    LOG_BATCH_SIZE: Final[int] = 100  # Log batch processing size


class SecurityConstants:
    """Security-related constants"""
    # Cryptographic constants
    HASH_ALGORITHM: Final[str] = "SHA-256"  # Default hash algorithm
    SIGNATURE_ALGORITHM: Final[str] = "RSA-PSS"  # Default signature algorithm
    KEY_DERIVATION_ITERATIONS: Final[int] = 100000  # PBKDF2 iterations
    
    # Token constants
    JWT_ALGORITHM: Final[str] = "RS256"  # JWT signing algorithm
    JWT_ISSUER: Final[str] = "bais-system"  # JWT issuer
    JWT_AUDIENCE: Final[str] = "bais-clients"  # JWT audience
    
    # Security headers
    SECURITY_HEADER_PREFIX: Final[str] = "X-BAIS-"  # Custom header prefix
    CORS_MAX_AGE_SECONDS: Final[int] = 3600  # CORS preflight cache
    
    # Rate limiting
    RATE_LIMIT_WINDOW_SECONDS: Final[int] = 60  # Rate limit window
    RATE_LIMIT_BURST_MULTIPLIER: Final[float] = 2.0  # Burst allowance


class ProtocolConstants:
    """Protocol-specific constants"""
    # MCP Protocol
    MCP_PROTOCOL_VERSION: Final[str] = "2025-06-18"  # MCP specification version
    MCP_DEFAULT_TRANSPORT: Final[str] = "http"  # Default MCP transport
    
    # A2A Protocol
    A2A_PROTOCOL_VERSION: Final[str] = "1.0.0"  # A2A specification version
    A2A_DEFAULT_TRANSPORT: Final[str] = "http"  # Default A2A transport
    
    # AP2 Protocol
    AP2_PROTOCOL_VERSION: Final[str] = "1.0.0"  # AP2 specification version
    AP2_SIGNATURE_HEADER: Final[str] = "X-AP2-Signature"  # AP2 signature header
    
    # Content types
    JSON_CONTENT_TYPE: Final[str] = "application/json"  # JSON content type
    SSE_CONTENT_TYPE: Final[str] = "text/event-stream"  # SSE content type
    FORM_CONTENT_TYPE: Final[str] = "application/x-www-form-urlencoded"  # Form content type


class PerformanceConstants:
    """Performance optimization constants"""
    # Async limits
    MAX_CONCURRENT_REQUESTS: Final[int] = 1000  # Max concurrent requests
    DEFAULT_CONCURRENT_REQUESTS: Final[int] = 100  # Default concurrency
    
    # Batch processing
    DEFAULT_BATCH_SIZE: Final[int] = 100  # Default batch size
    MAX_BATCH_SIZE: Final[int] = 1000  # Maximum batch size
    MIN_BATCH_SIZE: Final[int] = 1  # Minimum batch size
    
    # Memory limits
    MAX_MEMORY_USAGE_PERCENT: Final[float] = 80.0  # Max memory usage
    MEMORY_CLEANUP_INTERVAL_SECONDS: Final[int] = 300  # 5 minutes cleanup
    
    # CPU limits
    MAX_CPU_USAGE_PERCENT: Final[float] = 90.0  # Max CPU usage
    CPU_MONITORING_INTERVAL_SECONDS: Final[int] = 60  # CPU monitoring interval


class ValidationConstants:
    """Input validation constants"""
    # Email validation
    EMAIL_REGEX: Final[str] = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # URI validation
    URI_REGEX: Final[str] = r'^[a-zA-Z][a-zA-Z0-9+.-]*:'
    
    # UUID validation
    UUID_REGEX: Final[str] = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    # Phone validation (basic)
    PHONE_REGEX: Final[str] = r'^\+?[1-9]\d{1,14}$'
    
    # Currency codes
    SUPPORTED_CURRENCIES: Final[tuple] = ('USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY')
    
    # Time zones
    DEFAULT_TIMEZONE: Final[str] = 'UTC'
    
    # Date formats
    ISO_DATE_FORMAT: Final[str] = '%Y-%m-%d'
    ISO_DATETIME_FORMAT: Final[str] = '%Y-%m-%dT%H:%M:%S.%fZ'


class BusinessConstants:
    """Business logic constants"""
    # Default business settings
    DEFAULT_CURRENCY: Final[str] = 'USD'
    DEFAULT_LANGUAGE: Final[str] = 'en'
    DEFAULT_COUNTRY: Final[str] = 'US'
    
    # Business types
    SUPPORTED_BUSINESS_TYPES: Final[tuple] = ('hotel', 'restaurant', 'retail', 'service', 'entertainment')
    
    # Service categories
    SUPPORTED_SERVICE_CATEGORIES: Final[tuple] = ('accommodation', 'dining', 'shopping', 'entertainment', 'transportation')
    
    # Booking constraints
    MAX_BOOKING_ADVANCE_DAYS: Final[int] = 365  # 1 year advance booking
    MIN_BOOKING_ADVANCE_HOURS: Final[int] = 1  # 1 hour minimum advance
    MAX_BOOKING_DURATION_DAYS: Final[int] = 30  # 30 days max duration
    
    # Pricing constraints
    MAX_PRICE_DECIMAL_PLACES: Final[int] = 2  # Standard currency precision
    MIN_PRICE: Final[float] = 0.01  # Minimum price
    MAX_PRICE: Final[float] = 999999.99  # Maximum price
