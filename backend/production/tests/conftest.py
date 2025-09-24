"""
Test Configuration - Implementation
Shared test fixtures and configuration for cross-protocol integration tests
"""

import pytest
import asyncio
import os
import tempfile
from typing import Dict, Any, AsyncGenerator
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from ..core.constants import (
    DatabaseLimits, BusinessLimits, OAuthLimits, APIResponseLimits,
    SecurityLimits, WorkflowLimits, IntegrationLimits, MonitoringLimits,
    ErrorLimits, SSEConnectionLimits, A2ALimits, AP2Limits, MCPLimits,
    CircuitBreakerLimits, CacheLimits, LoggingLimits, SecurityConstants,
    ProtocolConstants, PerformanceConstants, ValidationConstants, BusinessConstants
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_business_schema():
    """Mock business schema for testing"""
    schema = Mock()
    schema.business_info = Mock()
    schema.business_info.name = "Test Hotel"
    schema.business_info.id = "hotel_123"
    schema.business_info.type = "hotel"
    schema.business_info.description = "A test hotel for integration testing"
    schema.business_info.location = Mock()
    schema.business_info.location.address = "123 Test Street"
    schema.business_info.location.city = "Test City"
    schema.business_info.location.country = "Test Country"
    schema.business_info.contact = Mock()
    schema.business_info.contact.email = "test@hotel.com"
    schema.business_info.contact.phone = "+1-555-0123"
    
    return schema


@pytest.fixture
async def mock_business_adapter():
    """Mock business system adapter for testing"""
    adapter = Mock()
    adapter.get_available_resources = AsyncMock(return_value=[
        {
            "uri": "availability://hotel-123",
            "name": "Room Availability",
            "description": "Real-time room availability",
            "type": "availability"
        },
        {
            "uri": "pricing://hotel-123",
            "name": "Room Pricing",
            "description": "Dynamic room pricing",
            "type": "pricing"
        }
    ])
    
    adapter.get_available_tools = AsyncMock(return_value=[
        {
            "name": "book_room",
            "description": "Book a hotel room",
            "input_schema": {
                "type": "object",
                "properties": {
                    "room_type": {"type": "string"},
                    "check_in": {"type": "string"},
                    "check_out": {"type": "string"},
                    "guests": {"type": "integer"}
                }
            }
        },
        {
            "name": "cancel_booking",
            "description": "Cancel a hotel booking",
            "input_schema": {
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string"}
                }
            }
        }
    ])
    
    adapter.get_resource_content = AsyncMock(return_value={
        "available_rooms": 5,
        "price_per_night": 150.0,
        "currency": "USD",
        "room_types": ["standard", "deluxe", "suite"],
        "amenities": ["wifi", "pool", "gym"]
    })
    
    adapter.execute_tool = AsyncMock(return_value={
        "booking_id": "book_123",
        "status": "confirmed",
        "total_amount": 300.0,
        "currency": "USD",
        "confirmation_code": "ABC123"
    })
    
    return adapter


@pytest.fixture
async def mock_ap2_client_config():
    """Mock AP2 client configuration for testing"""
    config = Mock()
    config.base_url = "https://test-ap2.example.com"
    config.client_id = "test_client_123"
    config.private_key = "test_private_key"
    config.public_key = "test_public_key"
    config.webhook_secret = "test_webhook_secret"
    config.timeout_seconds = AP2Limits.MANDATE_SIGNATURE_TIMEOUT_SECONDS
    config.max_retries = AP2Limits.MAX_PAYMENT_RETRIES
    
    return config


@pytest.fixture
async def mock_oauth_client():
    """Mock OAuth client for testing"""
    client = Mock()
    client.client_id = "test_oauth_client"
    client.client_secret = "test_client_secret"
    client.redirect_uris = ["https://test.example.com/callback"]
    client.grant_types = ["authorization_code", "refresh_token"]
    client.scopes = ["read", "write", "admin"]
    client.access_token_expire_minutes = OAuthLimits.ACCESS_TOKEN_EXPIRE_MINUTES
    client.refresh_token_expire_days = OAuthLimits.REFRESH_TOKEN_EXPIRE_DAYS
    
    return client


@pytest.fixture
async def test_database_url():
    """Test database URL for integration tests"""
    # Use in-memory SQLite for testing
    return "sqlite:///:memory:"


@pytest.fixture
async def test_redis_url():
    """Test Redis URL for caching tests"""
    # Use mock Redis for testing
    return "redis://localhost:6379/15"


@pytest.fixture
async def mock_http_client():
    """Mock HTTP client for external service calls"""
    client = Mock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    client.patch = AsyncMock()
    
    # Default successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"status": "success"})
    mock_response.text = "OK"
    
    client.get.return_value = mock_response
    client.post.return_value = mock_response
    client.put.return_value = mock_response
    client.delete.return_value = mock_response
    client.patch.return_value = mock_response
    
    return client


@pytest.fixture
async def mock_logger():
    """Mock logger for testing"""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    logger.exception = Mock()
    
    return logger


@pytest.fixture
async def test_temp_directory():
    """Temporary directory for test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
async def mock_environment_variables():
    """Mock environment variables for testing"""
    test_env = {
        "BAIS_ENV": "test",
        "BAIS_DEBUG": "true",
        "BAIS_LOG_LEVEL": "DEBUG",
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/15",
        "JWT_SECRET_KEY": "test_jwt_secret_key",
        "JWT_ALGORITHM": SecurityConstants.JWT_ALGORITHM,
        "JWT_ISSUER": SecurityConstants.JWT_ISSUER,
        "JWT_AUDIENCE": SecurityConstants.JWT_AUDIENCE,
        "OAUTH_CLIENT_ID": "test_oauth_client",
        "OAUTH_CLIENT_SECRET": "test_client_secret",
        "AP2_BASE_URL": "https://test-ap2.example.com",
        "AP2_CLIENT_ID": "test_ap2_client",
        "AP2_PRIVATE_KEY": "test_private_key",
        "AP2_PUBLIC_KEY": "test_public_key",
        "AP2_WEBHOOK_SECRET": "test_webhook_secret",
        "MCP_PROTOCOL_VERSION": ProtocolConstants.MCP_PROTOCOL_VERSION,
        "A2A_PROTOCOL_VERSION": ProtocolConstants.A2A_PROTOCOL_VERSION,
        "AP2_PROTOCOL_VERSION": ProtocolConstants.AP2_PROTOCOL_VERSION,
        "MAX_CONCURRENT_REQUESTS": str(PerformanceConstants.DEFAULT_CONCURRENT_REQUESTS),
        "DEFAULT_TIMEOUT_SECONDS": str(APIResponseLimits.DEFAULT_TIMEOUT_SECONDS),
        "RATE_LIMIT_PER_MINUTE": str(SecurityLimits.DEFAULT_RATE_LIMIT_PER_MINUTE),
        "CACHE_TTL_SECONDS": str(CacheLimits.DEFAULT_CACHE_TTL_SECONDS),
        "LOG_RETENTION_DAYS": str(LoggingLimits.AUDIT_RETENTION_DAYS),
        "MAX_PAYMENT_AMOUNT": str(AP2Limits.MAX_PAYMENT_AMOUNT),
        "MIN_PAYMENT_AMOUNT": str(AP2Limits.MIN_PAYMENT_AMOUNT),
        "MANDATE_EXPIRY_HOURS": str(AP2Limits.MANDATE_EXPIRY_HOURS),
        "MAX_SUBSCRIPTIONS_PER_CLIENT": str(MCPLimits.MAX_SUBSCRIPTIONS_PER_CLIENT),
        "SSE_CLIENT_TIMEOUT_SECONDS": str(SSEConnectionLimits.CLIENT_TIMEOUT_SECONDS),
        "SSE_PING_INTERVAL_SECONDS": str(SSEConnectionLimits.PING_INTERVAL_SECONDS),
        "A2A_TASK_TIMEOUT_SECONDS": str(A2ALimits.DEFAULT_TASK_TIMEOUT_SECONDS),
        "MCP_TOOL_TIMEOUT_SECONDS": str(MCPLimits.MAX_TOOL_EXECUTION_TIME_SECONDS),
        "DEFAULT_CURRENCY": BusinessConstants.DEFAULT_CURRENCY,
        "DEFAULT_LANGUAGE": BusinessConstants.DEFAULT_LANGUAGE,
        "DEFAULT_COUNTRY": BusinessConstants.DEFAULT_COUNTRY,
        "SUPPORTED_CURRENCIES": ",".join(ValidationConstants.SUPPORTED_CURRENCIES),
        "DEFAULT_TIMEZONE": ValidationConstants.DEFAULT_TIMEZONE
    }
    
    # Store original environment
    original_env = os.environ.copy()
    
    # Set test environment
    os.environ.update(test_env)
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
async def test_constants_validation():
    """Validate that all test constants are properly configured"""
    constants_validation = {
        "database_limits": {
            "default_query_limit": DatabaseLimits.DEFAULT_QUERY_LIMIT,
            "max_query_limit": DatabaseLimits.MAX_QUERY_LIMIT,
            "default_pool_size": DatabaseLimits.DEFAULT_POOL_SIZE,
            "pool_timeout_seconds": DatabaseLimits.POOL_TIMEOUT_SECONDS
        },
        "business_limits": {
            "max_services_per_business": BusinessLimits.MAX_SERVICES_PER_BUSINESS,
            "default_rate_limit_per_hour": BusinessLimits.DEFAULT_RATE_LIMIT_PER_HOUR,
            "max_concurrent_sessions": BusinessLimits.MAX_CONCURRENT_SESSIONS,
            "session_timeout_minutes": BusinessLimits.SESSION_TIMEOUT_MINUTES
        },
        "oauth_limits": {
            "access_token_expire_minutes": OAuthLimits.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": OAuthLimits.REFRESH_TOKEN_EXPIRE_DAYS,
            "authorization_code_expire_minutes": OAuthLimits.AUTHORIZATION_CODE_EXPIRE_MINUTES
        },
        "api_response_limits": {
            "max_response_size_mb": APIResponseLimits.MAX_RESPONSE_SIZE_MB,
            "default_timeout_seconds": APIResponseLimits.DEFAULT_TIMEOUT_SECONDS,
            "max_retry_attempts": APIResponseLimits.MAX_RETRY_ATTEMPTS,
            "retry_base_delay_seconds": APIResponseLimits.RETRY_BASE_DELAY_SECONDS
        },
        "security_limits": {
            "min_password_length": SecurityLimits.MIN_PASSWORD_LENGTH,
            "max_password_length": SecurityLimits.MAX_PASSWORD_LENGTH,
            "api_key_length": SecurityLimits.API_KEY_LENGTH,
            "default_rate_limit_per_minute": SecurityLimits.DEFAULT_RATE_LIMIT_PER_MINUTE
        },
        "workflow_limits": {
            "max_workflow_steps": WorkflowLimits.MAX_WORKFLOW_STEPS,
            "max_step_timeout_minutes": WorkflowLimits.MAX_STEP_TIMEOUT_MINUTES,
            "default_step_timeout_minutes": WorkflowLimits.DEFAULT_STEP_TIMEOUT_MINUTES,
            "max_retry_attempts_per_step": WorkflowLimits.MAX_RETRY_ATTEMPTS_PER_STEP
        },
        "integration_limits": {
            "max_mcp_endpoint_length": IntegrationLimits.MAX_MCP_ENDPOINT_LENGTH,
            "mcp_request_timeout_seconds": IntegrationLimits.MCP_REQUEST_TIMEOUT_SECONDS,
            "max_a2a_discovery_url_length": IntegrationLimits.MAX_A2A_DISCOVERY_URL_LENGTH,
            "a2a_discovery_timeout_seconds": IntegrationLimits.A2A_DISCOVERY_TIMEOUT_SECONDS
        },
        "monitoring_limits": {
            "log_retention_days": MonitoringLimits.LOG_RETENTION_DAYS,
            "max_log_entry_length": MonitoringLimits.MAX_LOG_ENTRY_LENGTH,
            "metrics_collection_interval_seconds": MonitoringLimits.METRICS_COLLECTION_INTERVAL_SECONDS,
            "health_check_timeout_seconds": MonitoringLimits.HEALTH_CHECK_TIMEOUT_SECONDS
        },
        "error_limits": {
            "max_error_message_length": ErrorLimits.MAX_ERROR_MESSAGE_LENGTH,
            "max_error_stack_trace_length": ErrorLimits.MAX_ERROR_STACK_TRACE_LENGTH,
            "max_error_context_length": ErrorLimits.MAX_ERROR_CONTEXT_LENGTH,
            "max_errors_per_minute": ErrorLimits.MAX_ERRORS_PER_MINUTE,
            "error_rate_alert_threshold": ErrorLimits.ERROR_RATE_ALERT_THRESHOLD
        },
        "sse_connection_limits": {
            "max_clients_per_connection": SSEConnectionLimits.MAX_CLIENTS_PER_CONNECTION,
            "client_timeout_seconds": SSEConnectionLimits.CLIENT_TIMEOUT_SECONDS,
            "ping_interval_seconds": SSEConnectionLimits.PING_INTERVAL_SECONDS,
            "max_queue_size": SSEConnectionLimits.MAX_QUEUE_SIZE,
            "queue_cleanup_interval_seconds": SSEConnectionLimits.QUEUE_CLEANUP_INTERVAL_SECONDS
        },
        "a2a_limits": {
            "max_task_execution_time_seconds": A2ALimits.MAX_TASK_EXECUTION_TIME_SECONDS,
            "default_task_timeout_seconds": A2ALimits.DEFAULT_TASK_TIMEOUT_SECONDS,
            "task_polling_interval_seconds": A2ALimits.TASK_POLLING_INTERVAL_SECONDS,
            "max_discovery_results": A2ALimits.MAX_DISCOVERY_RESULTS,
            "discovery_timeout_seconds": A2ALimits.DISCOVERY_TIMEOUT_SECONDS
        },
        "ap2_limits": {
            "max_payment_amount": AP2Limits.MAX_PAYMENT_AMOUNT,
            "min_payment_amount": AP2Limits.MIN_PAYMENT_AMOUNT,
            "max_payment_retries": AP2Limits.MAX_PAYMENT_RETRIES,
            "mandate_expiry_hours": AP2Limits.MANDATE_EXPIRY_HOURS,
            "max_mandate_amount": AP2Limits.MAX_MANDATE_AMOUNT,
            "mandate_signature_timeout_seconds": AP2Limits.MANDATE_SIGNATURE_TIMEOUT_SECONDS,
            "webhook_signature_timeout_seconds": AP2Limits.WEBHOOK_SIGNATURE_TIMEOUT_SECONDS,
            "webhook_replay_window_seconds": AP2Limits.WEBHOOK_REPLAY_WINDOW_SECONDS,
            "max_webhook_retries": AP2Limits.MAX_WEBHOOK_RETRIES,
            "key_rotation_days": AP2Limits.KEY_ROTATION_DAYS,
            "max_key_size_bits": AP2Limits.MAX_KEY_SIZE_BITS,
            "min_key_size_bits": AP2Limits.MIN_KEY_SIZE_BITS
        },
        "mcp_limits": {
            "max_resource_size_mb": MCPLimits.MAX_RESOURCE_SIZE_MB,
            "max_resource_uris_per_request": MCPLimits.MAX_RESOURCE_URIS_PER_REQUEST,
            "resource_cache_ttl_seconds": MCPLimits.RESOURCE_CACHE_TTL_SECONDS,
            "max_tool_execution_time_seconds": MCPLimits.MAX_TOOL_EXECUTION_TIME_SECONDS,
            "max_tool_parameters": MCPLimits.MAX_TOOL_PARAMETERS,
            "tool_result_size_limit_mb": MCPLimits.TOOL_RESULT_SIZE_LIMIT_MB,
            "max_prompt_template_size_kb": MCPLimits.MAX_PROMPT_TEMPLATE_SIZE_KB,
            "max_prompt_variables": MCPLimits.MAX_PROMPT_VARIABLES,
            "prompt_rendering_timeout_seconds": MCPLimits.PROMPT_RENDERING_TIMEOUT_SECONDS,
            "max_subscriptions_per_client": MCPLimits.MAX_SUBSCRIPTIONS_PER_CLIENT,
            "default_subscription_expiry_hours": MCPLimits.DEFAULT_SUBSCRIPTION_EXPIRY_HOURS,
            "max_subscription_filters": MCPLimits.MAX_SUBSCRIPTION_FILTERS,
            "subscription_cleanup_interval_seconds": MCPLimits.SUBSCRIPTION_CLEANUP_INTERVAL_SECONDS
        }
    }
    
    return constants_validation


@pytest.fixture
async def performance_benchmarks():
    """Performance benchmarks for integration tests"""
    benchmarks = {
        "sse_connection_establishment": {
            "max_time_seconds": 1.0,
            "max_memory_mb": 10.0
        },
        "subscription_creation": {
            "max_time_seconds": 0.1,
            "max_memory_mb": 1.0
        },
        "event_publishing": {
            "max_time_seconds": 0.05,
            "max_memory_mb": 1.0
        },
        "error_handling": {
            "max_time_seconds": 0.01,
            "max_memory_mb": 0.5
        },
        "cross_protocol_workflow": {
            "max_time_seconds": 5.0,
            "max_memory_mb": 50.0
        },
        "concurrent_requests": {
            "max_time_seconds": 10.0,
            "max_memory_mb": 100.0,
            "min_throughput_per_second": 10
        }
    }
    
    return benchmarks


# Test markers for different types of tests
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.cross_protocol = pytest.mark.cross_protocol
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security
pytest.mark.api = pytest.mark.api
pytest.mark.database = pytest.mark.database
pytest.mark.redis = pytest.mark.redis
pytest.mark.websocket = pytest.mark.websocket
pytest.mark.sse = pytest.mark.sse
pytest.mark.a2a = pytest.mark.a2a
pytest.mark.ap2 = pytest.mark.ap2
pytest.mark.mcp = pytest.mark.mcp


# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "cross_protocol: mark test as a cross-protocol integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "api: mark test as an API test"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "redis: mark test as requiring Redis"
    )
    config.addinivalue_line(
        "markers", "websocket: mark test as requiring WebSocket"
    )
    config.addinivalue_line(
        "markers", "sse: mark test as requiring Server-Sent Events"
    )
    config.addinivalue_line(
        "markers", "a2a: mark test as testing A2A protocol"
    )
    config.addinivalue_line(
        "markers", "ap2: mark test as testing AP2 protocol"
    )
    config.addinivalue_line(
        "markers", "mcp: mark test as testing MCP protocol"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names"""
    for item in items:
        # Add protocol-specific markers based on test names
        if "a2a" in item.name.lower():
            item.add_marker(pytest.mark.a2a)
        if "ap2" in item.name.lower():
            item.add_marker(pytest.mark.ap2)
        if "mcp" in item.name.lower():
            item.add_marker(pytest.mark.mcp)
        
        # Add test type markers based on test names
        if "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        if "security" in item.name.lower():
            item.add_marker(pytest.mark.security)
        if "sse" in item.name.lower():
            item.add_marker(pytest.mark.sse)
        
        # Add cross-protocol marker for cross-protocol tests
        if "cross_protocol" in item.name.lower():
            item.add_marker(pytest.mark.cross_protocol)
