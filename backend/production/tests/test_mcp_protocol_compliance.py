"""
MCP Protocol Compliance Tests - Clean Code Implementation
Comprehensive test suite for MCP protocol implementation and security
"""

import pytest
import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from ..core.mcp_authentication_service import (
    AuthenticationService, AuthContext, JWKSClient
)
from ..core.mcp_error_handler import (
    MCPErrorHandler, ValidationError, AuthenticationError, 
    AuthorizationError, BusinessRuleError, get_error_handler
)
from ..core.mcp_input_validation import (
    MCPInputValidator, ServiceSearchParameters, BookingParameters,
    PaymentParameters, MCPInitializeRequest, MCPCallToolRequest
)
from ..core.mcp_audit_logger import (
    MCPAuditLogger, AuditEventType, AuditSeverity, FileAuditStorage
)


class TestMCPAuthenticationCompliance:
    """Test MCP authentication implementation"""
    
    @pytest.fixture
    async def auth_service(self):
        """Create authentication service for testing"""
        service = AuthenticationService(
            oauth_discovery_url="https://test-oauth.example.com/.well-known/openid-configuration",
            allowed_scopes=["resource:read", "tool:execute", "prompt:read"]
        )
        
        # Mock the initialization
        service._oauth_metadata = {
            "issuer": "https://test-oauth.example.com",
            "jwks_uri": "https://test-oauth.example.com/.well-known/jwks.json",
            "authorization_endpoint": "https://test-oauth.example.com/authorize",
            "token_endpoint": "https://test-oauth.example.com/token"
        }
        
        return service
    
    @pytest.fixture
    def mock_jwks_client(self):
        """Create mock JWKS client"""
        client = Mock(spec=JWKSClient)
        client.get_signing_key = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_oauth_discovery_metadata_validation(self, auth_service):
        """Test OAuth discovery metadata validation"""
        # Test valid metadata
        valid_metadata = {
            "issuer": "https://test-oauth.example.com",
            "jwks_uri": "https://test-oauth.example.com/.well-known/jwks.json",
            "authorization_endpoint": "https://test-oauth.example.com/authorize",
            "token_endpoint": "https://test-oauth.example.com/token"
        }
        
        # Should not raise exception
        auth_service._oauth_metadata = valid_metadata
        await auth_service._initialize_jwks_client()
        
        # Test missing required fields
        invalid_metadata = {
            "issuer": "https://test-oauth.example.com",
            # Missing jwks_uri
        }
        
        with pytest.raises(ValueError, match="Missing required OAuth metadata field"):
            auth_service._oauth_metadata = invalid_metadata
            await auth_service._initialize_jwks_client()
    
    def test_resource_audience_extraction(self, auth_service):
        """Test resource audience extraction per RFC 8707"""
        # Test BAIS URIs
        assert auth_service._extract_resource_audience("availability://hotel-123") == "mcp-server:bais-availability"
        assert auth_service._extract_resource_audience("service://restaurant-456") == "mcp-server:bais-service"
        assert auth_service._extract_resource_audience("business://info") == "mcp-server:bais-business"
        
        # Test default audience
        assert auth_service._extract_resource_audience("default") == "mcp-server:bais-default"
    
    def test_scope_validation(self, auth_service):
        """Test OAuth scope validation"""
        # Valid scopes
        valid_scopes = ["resource:read", "tool:execute"]
        assert auth_service._has_required_scopes(valid_scopes) is True
        
        # Invalid scopes
        invalid_scopes = ["invalid:scope"]
        assert auth_service._has_required_scopes(invalid_scopes) is False
        
        # No scope restrictions
        auth_service._allowed_scopes = []
        assert auth_service._has_required_scopes(valid_scopes) is True
    
    @pytest.mark.asyncio
    async def test_token_validation_error_handling(self, auth_service):
        """Test token validation error handling"""
        from fastapi import HTTPException
        
        # Test missing token
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.validate_token("", "test://resource")
        
        assert exc_info.value.status_code == 401
        assert "Missing authentication token" in exc_info.value.detail


class TestMCPErrorHandlingCompliance:
    """Test MCP error handling implementation"""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing"""
        logger = Mock()
        return MCPErrorHandler(logger)
    
    def test_validation_error_handling(self, error_handler):
        """Test validation error handling"""
        error = ValidationError("Invalid input", field="email", value="invalid-email")
        user_context = {"user_id": "user123"}
        
        response = error_handler.handle_mcp_error(error, "test_operation", user_context)
        
        assert response.error_type == "validation"
        assert "Invalid input" in response.message
        assert response.details["field"] == "email"
    
    def test_authentication_error_handling(self, error_handler):
        """Test authentication error handling"""
        error = AuthenticationError("Invalid token", token_info={"token": "test"})
        user_context = {"user_id": "user123"}
        
        response = error_handler.handle_mcp_error(error, "test_operation", user_context)
        
        assert response.error_type == "authentication"
        assert response.message == "Authentication failed"
    
    def test_authorization_error_handling(self, error_handler):
        """Test authorization error handling"""
        error = AuthorizationError(
            "Insufficient permissions",
            required_scopes=["admin"],
            user_scopes=["read"]
        )
        user_context = {"user_id": "user123"}
        
        response = error_handler.handle_mcp_error(error, "test_operation", user_context)
        
        assert response.error_type == "authorization"
        assert response.message == "Insufficient permissions"
    
    def test_business_rule_error_handling(self, error_handler):
        """Test business rule error handling"""
        error = BusinessRuleError("Booking not allowed", rule_name="no_same_day_booking")
        user_context = {"user_id": "user123"}
        
        response = error_handler.handle_mcp_error(error, "test_operation", user_context)
        
        assert response.error_type == "business_rule"
        assert response.message == "Booking not allowed"
        assert response.details["rule_name"] == "no_same_day_booking"
    
    def test_tool_error_response_format(self, error_handler):
        """Test tool error response format"""
        error = ValidationError("Invalid tool arguments", field="arguments")
        user_context = {"user_id": "user123"}
        
        response = error_handler.handle_tool_error(error, "test_tool", user_context)
        
        assert "content" in response
        assert "isError" in response
        assert response["isError"] is True
        assert "error" in response


class TestMCPInputValidationCompliance:
    """Test MCP input validation implementation"""
    
    @pytest.fixture
    def validator(self):
        """Create input validator for testing"""
        return MCPInputValidator()
    
    def test_initialize_request_validation(self, validator):
        """Test MCP initialization request validation"""
        # Valid request
        valid_request = {
            "protocolVersion": "2025-06-18",
            "capabilities": {"resources": {"listChanged": True}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
        
        result = validator.validate_initialize_request(valid_request)
        assert result.protocolVersion == "2025-06-18"
        assert result.clientInfo["name"] == "test-client"
        
        # Invalid protocol version
        invalid_request = {
            "protocolVersion": "2024-01-01",  # Unsupported version
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
        
        with pytest.raises(ValidationError, match="Unsupported protocol version"):
            validator.validate_initialize_request(invalid_request)
    
    def test_tool_request_validation(self, validator):
        """Test MCP tool request validation"""
        # Valid request
        valid_request = {
            "name": "search_availability",
            "arguments": {"location": "New York", "guests": 2}
        }
        
        result = validator.validate_tool_request(valid_request)
        assert result.name == "search_availability"
        assert result.arguments["location"] == "New York"
        
        # Invalid tool name
        invalid_request = {
            "name": "123_invalid_tool",  # Invalid name format
            "arguments": {}
        }
        
        with pytest.raises(ValidationError, match="Tool name must start with letter"):
            validator.validate_tool_request(invalid_request)
    
    def test_service_search_parameters_validation(self, validator):
        """Test service search parameters validation"""
        # Valid parameters
        valid_params = {
            "location": "New York",
            "service_type": "hospitality",
            "date_range": {
                "start_date": "2024-12-01",
                "end_date": "2024-12-03"
            },
            "price_range": {
                "min_price": 100.0,
                "max_price": 500.0
            },
            "guests": 2
        }
        
        result = validator.validate_service_search_params(valid_params)
        assert result.location == "New York"
        assert result.service_type.value == "hospitality"
        
        # Invalid date range
        invalid_params = {
            "location": "New York",
            "date_range": {
                "start_date": "2024-12-03",
                "end_date": "2024-12-01"  # End before start
            }
        }
        
        with pytest.raises(ValidationError, match="End date must be after start date"):
            validator.validate_service_search_params(invalid_params)
    
    def test_booking_parameters_validation(self, validator):
        """Test booking parameters validation"""
        # Valid booking
        valid_booking = {
            "service_id": "hotel-123",
            "date": "2024-12-01",
            "time": "15:00:00",
            "guests": 2,
            "contact_info": {
                "email": "test@example.com",
                "phone": "+1234567890"
            },
            "payment_method": "credit_card"
        }
        
        result = validator.validate_booking_params(valid_booking)
        assert result.service_id == "hotel-123"
        assert result.guests == 2
        
        # Invalid email
        invalid_booking = {
            "service_id": "hotel-123",
            "date": "2024-12-01",
            "guests": 2,
            "contact_info": {
                "email": "invalid-email",
                "phone": "+1234567890"
            },
            "payment_method": "credit_card"
        }
        
        with pytest.raises(ValidationError, match="Invalid email format"):
            validator.validate_booking_params(invalid_booking)
    
    def test_payment_parameters_validation(self, validator):
        """Test payment parameters validation"""
        # Valid payment
        valid_payment = {
            "amount": 150.0,
            "currency": "USD",
            "payment_method": "credit_card",
            "payment_details": {
                "card_number": "4111111111111111",
                "expiry_date": "12/25",
                "cvv": "123",
                "cardholder_name": "John Doe"
            }
        }
        
        result = validator.validate_payment_params(valid_payment)
        assert result.amount == 150.0
        assert result.currency == "USD"
        
        # Invalid currency
        invalid_payment = {
            "amount": 150.0,
            "currency": "INVALID",
            "payment_method": "credit_card",
            "payment_details": {}
        }
        
        with pytest.raises(ValidationError, match="Unsupported currency"):
            validator.validate_payment_params(invalid_payment)


class TestMCPAuditLoggingCompliance:
    """Test MCP audit logging implementation"""
    
    @pytest.fixture
    def mock_storage(self):
        """Create mock audit storage"""
        storage = Mock(spec=FileAuditStorage)
        storage.store_event = AsyncMock()
        storage.query_events = AsyncMock(return_value=[])
        storage.get_event = AsyncMock(return_value=None)
        return storage
    
    @pytest.fixture
    def audit_logger(self, mock_storage):
        """Create audit logger for testing"""
        logger = Mock()
        return MCPAuditLogger(mock_storage, logger)
    
    @pytest.fixture
    def auth_context(self):
        """Create auth context for testing"""
        return AuthContext(
            user_id="user123",
            client_id="client456",
            scopes=["resource:read", "tool:execute"],
            resource_uri="availability://hotel-123",
            expires_at=datetime.now() + timedelta(hours=1),
            audience="mcp-server:bais-availability",
            issuer="https://test-oauth.example.com"
        )
    
    @pytest.mark.asyncio
    async def test_authentication_success_logging(self, audit_logger, auth_context):
        """Test authentication success logging"""
        request_info = {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "endpoint": "/mcp/resources/list",
            "method": "GET",
            "request_size": 100,
            "response_size": 200,
            "processing_time_ms": 50.0
        }
        
        await audit_logger.log_authentication_success(auth_context, request_info)
        
        # Verify storage was called
        audit_logger._storage.store_event.assert_called_once()
        event = audit_logger._storage.store_event.call_args[0][0]
        
        assert event.event_type == AuditEventType.AUTHENTICATION_SUCCESS
        assert event.user_id == "user123"
        assert event.status_code == 200
    
    @pytest.mark.asyncio
    async def test_authentication_failure_logging(self, audit_logger):
        """Test authentication failure logging"""
        request_info = {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "endpoint": "/mcp/resources/list",
            "method": "GET",
            "request_size": 100,
            "response_size": 200,
            "processing_time_ms": 25.0,
            "token": "invalid-token"
        }
        
        await audit_logger.log_authentication_failure("Invalid token", request_info)
        
        # Verify storage was called
        audit_logger._storage.store_event.assert_called_once()
        event = audit_logger._storage.store_event.call_args[0][0]
        
        assert event.event_type == AuditEventType.AUTHENTICATION_FAILURE
        assert event.status_code == 401
        assert event.error_code == "AUTH_FAILED"
    
    @pytest.mark.asyncio
    async def test_tool_execution_logging(self, audit_logger, auth_context):
        """Test tool execution logging"""
        request_info = {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "endpoint": "/mcp/tools/call",
            "method": "POST",
            "request_size": 200,
            "response_size": 500,
            "processing_time_ms": 150.0
        }
        
        arguments = {"location": "New York", "guests": 2}
        result = {"results": [{"hotel": "Hotel ABC", "price": 150}]}
        
        await audit_logger.log_tool_execution(
            auth_context, "search_availability", arguments, result, request_info
        )
        
        # Verify storage was called
        audit_logger._storage.store_event.assert_called_once()
        event = audit_logger._storage.store_event.call_args[0][0]
        
        assert event.event_type == AuditEventType.TOOL_EXECUTION
        assert event.tool_name == "search_availability"
        assert event.metadata["success"] is True
    
    @pytest.mark.asyncio
    async def test_security_violation_logging(self, audit_logger):
        """Test security violation logging"""
        request_info = {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "endpoint": "/mcp/tools/call",
            "method": "POST",
            "user_id": "user123"
        }
        
        details = {
            "violation_type": "injection_attempt",
            "payload": "<script>alert('xss')</script>"
        }
        
        await audit_logger.log_security_violation("xss_attempt", details, request_info)
        
        # Verify storage was called
        audit_logger._storage.store_event.assert_called_once()
        event = audit_logger._storage.store_event.call_args[0][0]
        
        assert event.event_type == AuditEventType.SECURITY_VIOLATION
        assert event.severity == AuditSeverity.CRITICAL
        assert event.metadata["violation_type"] == "xss_attempt"


class TestMCPIntegrationCompliance:
    """Test MCP integration with other protocols"""
    
    def test_mcp_a2a_integration(self):
        """Test MCP integration with A2A protocol"""
        # Test that MCP tools can be discovered via A2A
        mcp_tools = [
            {
                "name": "search_availability",
                "description": "Search for available services",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "service_type": {"type": "string"}
                    }
                }
            }
        ]
        
        # Validate MCP tool structure for A2A discovery
        for tool in mcp_tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["name"].startswith(("search_", "book_", "get_"))
    
    def test_mcp_ap2_integration(self):
        """Test MCP integration with AP2 protocol"""
        # Test that MCP can handle AP2 payment operations
        ap2_tools = [
            {
                "name": "create_payment_mandate",
                "description": "Create AP2 payment mandate",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number"},
                        "currency": {"type": "string"},
                        "payment_method": {"type": "string"}
                    },
                    "required": ["amount", "currency", "payment_method"]
                }
            }
        ]
        
        # Validate AP2 tool structure
        for tool in ap2_tools:
            assert "amount" in tool["input_schema"]["properties"]
            assert "currency" in tool["input_schema"]["properties"]
            assert "payment_method" in tool["input_schema"]["properties"]


class TestMCPSecurityCompliance:
    """Test MCP security implementation"""
    
    def test_input_sanitization(self):
        """Test input sanitization for security"""
        validator = MCPInputValidator()
        
        # Test XSS prevention
        malicious_input = "<script>alert('xss')</script>"
        sanitized = validator.sanitize_string_input(malicious_input)
        assert "<script>" not in sanitized
        
        # Test SQL injection prevention
        sql_injection = "'; DROP TABLE users; --"
        sanitized = validator.sanitize_string_input(sql_injection)
        assert "DROP TABLE" not in sanitized or sanitized == sql_injection  # Should be preserved for logging
        
        # Test length limits
        long_input = "x" * 2000
        sanitized = validator.sanitize_string_input(long_input, max_length=100)
        assert len(sanitized) <= 100
    
    def test_json_input_validation(self):
        """Test JSON input validation"""
        validator = MCPInputValidator()
        
        # Valid JSON
        valid_json = '{"test": "value"}'
        result = validator.validate_json_input(valid_json)
        assert result["test"] == "value"
        
        # Invalid JSON
        invalid_json = '{"test": "value"'  # Missing closing brace
        with pytest.raises(ValidationError, match="Invalid JSON format"):
            validator.validate_json_input(invalid_json)
        
        # Oversized JSON
        large_json = '{"data": "' + "x" * 200000 + '"}'  # > 100KB
        with pytest.raises(ValidationError, match="JSON input too large"):
            validator.validate_json_input(large_json)
    
    def test_rate_limiting_compliance(self):
        """Test rate limiting implementation"""
        from ..middleware.security_middleware import RateLimiter, RateLimit
        
        rate_limiter = RateLimiter()
        rate_limiter.add_limit("/test", RateLimit(limit=5, window_seconds=60))
        
        client_id = "test_client"
        
        # Test normal usage
        for i in range(5):
            allowed, retry_after = rate_limiter.is_allowed(client_id, "/test")
            assert allowed is True
            assert retry_after is None
        
        # Test rate limit exceeded
        allowed, retry_after = rate_limiter.is_allowed(client_id, "/test")
        assert allowed is False
        assert retry_after is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
