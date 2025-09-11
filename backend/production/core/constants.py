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
