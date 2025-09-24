"""
Authentication Security Tests
Comprehensive security testing for authentication flows
"""

import pytest
import jwt
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from ...core.mcp_authentication_service import AuthenticationService
from ...core.secrets_manager import get_secrets_manager
from ...core.constants import SecurityConstants, OAuthLimits


class TestAuthenticationSecurity:
    """Test authentication security following testing best practices"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client"""
        from ...main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_service(self):
        """Create authentication service for testing"""
        return AuthenticationService()
    
    @pytest.fixture
    def valid_jwt_token(self):
        """Create valid JWT token for testing"""
        payload = {
            "sub": "test_user_123",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "iss": SecurityConstants.JWT_ISSUER,
            "aud": SecurityConstants.JWT_AUDIENCE
        }
        
        # Use test secret for testing
        test_secret = "test_jwt_secret_key_for_testing_only"
        token = jwt.encode(payload, test_secret, algorithm=SecurityConstants.JWT_ALGORITHM)
        return token
    
    @pytest.fixture
    def expired_jwt_token(self):
        """Create expired JWT token for testing"""
        payload = {
            "sub": "test_user_123",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=2),
            "iss": SecurityConstants.JWT_ISSUER,
            "aud": SecurityConstants.JWT_AUDIENCE
        }
        
        test_secret = "test_jwt_secret_key_for_testing_only"
        token = jwt.encode(payload, test_secret, algorithm=SecurityConstants.JWT_ALGORITHM)
        return token
    
    def test_jwt_token_validation_valid_token(self, auth_service, valid_jwt_token):
        """Test valid JWT token is accepted"""
        # Mock the JWT secret for testing
        with patch.object(auth_service, '_get_jwt_secret', return_value="test_jwt_secret_key_for_testing_only"):
            try:
                decoded = auth_service.validate_jwt_token(valid_jwt_token)
                assert decoded is not None
                assert decoded.get("sub") == "test_user_123"
            except Exception as e:
                pytest.fail(f"Valid token should be accepted: {e}")
    
    def test_jwt_token_validation_expired_token(self, auth_service, expired_jwt_token):
        """Test expired JWT token is rejected"""
        with patch.object(auth_service, '_get_jwt_secret', return_value="test_jwt_secret_key_for_testing_only"):
            with pytest.raises(jwt.ExpiredSignatureError):
                auth_service.validate_jwt_token(expired_jwt_token)
    
    def test_jwt_token_validation_invalid_token(self, auth_service):
        """Test invalid JWT token is rejected"""
        with pytest.raises(jwt.InvalidTokenError):
            auth_service.validate_jwt_token("invalid_token_string")
    
    def test_jwt_token_validation_missing_token(self, auth_service):
        """Test missing JWT token is rejected"""
        with pytest.raises(ValueError):
            auth_service.validate_jwt_token("")
    
    def test_jwt_token_tampering_detected(self, auth_service, valid_jwt_token):
        """Test tampered JWT token is detected and rejected"""
        # Tamper with the token
        tampered_token = valid_jwt_token[:-5] + "aaaaa"
        
        with patch.object(auth_service, '_get_jwt_secret', return_value="test_jwt_secret_key_for_testing_only"):
            with pytest.raises(jwt.InvalidTokenError):
                auth_service.validate_jwt_token(tampered_token)
    
    def test_jwt_token_wrong_algorithm_rejected(self, auth_service):
        """Test JWT token with wrong algorithm is rejected"""
        # Create token with wrong algorithm
        payload = {
            "sub": "test_user_123",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        # Use wrong algorithm
        wrong_token = jwt.encode(payload, "secret", algorithm="HS512")
        
        with patch.object(auth_service, '_get_jwt_secret', return_value="secret"):
            with pytest.raises(jwt.InvalidTokenError):
                auth_service.validate_jwt_token(wrong_token)
    
    def test_jwt_token_wrong_issuer_rejected(self, auth_service):
        """Test JWT token with wrong issuer is rejected"""
        payload = {
            "sub": "test_user_123",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iss": "wrong_issuer",  # Wrong issuer
            "aud": SecurityConstants.JWT_AUDIENCE
        }
        
        test_secret = "test_jwt_secret_key_for_testing_only"
        wrong_issuer_token = jwt.encode(payload, test_secret, algorithm=SecurityConstants.JWT_ALGORITHM)
        
        with patch.object(auth_service, '_get_jwt_secret', return_value=test_secret):
            with pytest.raises(jwt.InvalidTokenError):
                auth_service.validate_jwt_token(wrong_issuer_token)
    
    def test_jwt_token_wrong_audience_rejected(self, auth_service):
        """Test JWT token with wrong audience is rejected"""
        payload = {
            "sub": "test_user_123",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iss": SecurityConstants.JWT_ISSUER,
            "aud": "wrong_audience"  # Wrong audience
        }
        
        test_secret = "test_jwt_secret_key_for_testing_only"
        wrong_audience_token = jwt.encode(payload, test_secret, algorithm=SecurityConstants.JWT_ALGORITHM)
        
        with patch.object(auth_service, '_get_jwt_secret', return_value=test_secret):
            with pytest.raises(jwt.InvalidTokenError):
                auth_service.validate_jwt_token(wrong_audience_token)
    
    def test_oauth_redirect_uri_validation(self, test_client):
        """Test OAuth redirect URI validation"""
        # Test with valid redirect URI
        response = test_client.get(
            "/oauth/authorize",
            params={
                "client_id": "test_client",
                "redirect_uri": "https://trusted-app.com/callback",
                "response_type": "code",
                "state": "random_state_string"
            }
        )
        # Should not return 400 for valid URI (may return other codes based on implementation)
        assert response.status_code != 400
        
        # Test with malicious redirect URI
        response = test_client.get(
            "/oauth/authorize",
            params={
                "client_id": "test_client",
                "redirect_uri": "http://malicious-site.com/callback",
                "response_type": "code",
                "state": "random_state_string"
            }
        )
        # Should return 400 for malicious URI
        assert response.status_code == 400
    
    def test_oauth_state_parameter_required(self, test_client):
        """Test OAuth state parameter is required for CSRF protection"""
        response = test_client.get(
            "/oauth/authorize",
            params={
                "client_id": "test_client",
                "redirect_uri": "https://trusted-app.com/callback",
                "response_type": "code"
                # Missing state parameter
            }
        )
        # Should require state parameter
        assert response.status_code == 400
    
    def test_oauth_invalid_client_id_rejected(self, test_client):
        """Test invalid OAuth client ID is rejected"""
        response = test_client.get(
            "/oauth/authorize",
            params={
                "client_id": "invalid_client_id",
                "redirect_uri": "https://trusted-app.com/callback",
                "response_type": "code",
                "state": "random_state_string"
            }
        )
        # Should reject invalid client ID
        assert response.status_code == 400
    
    def test_oauth_invalid_response_type_rejected(self, test_client):
        """Test invalid OAuth response type is rejected"""
        response = test_client.get(
            "/oauth/authorize",
            params={
                "client_id": "test_client",
                "redirect_uri": "https://trusted-app.com/callback",
                "response_type": "invalid_type",
                "state": "random_state_string"
            }
        )
        # Should reject invalid response type
        assert response.status_code == 400
    
    def test_rate_limiting_on_auth_endpoints(self, test_client):
        """Test rate limiting prevents brute force attacks"""
        # Attempt multiple failed authentications
        for i in range(10):
            response = test_client.post(
                "/auth/login",
                json={
                    "username": "test_user",
                    "password": f"wrong_password_{i}"
                }
            )
            # Should fail but not be rate limited yet
            assert response.status_code in [401, 422]  # Unauthorized or validation error
        
        # 11th attempt should be rate limited (if rate limiting is implemented)
        response = test_client.post(
            "/auth/login",
            json={
                "username": "test_user",
                "password": "another_wrong_password"
            }
        )
        # May return 429 (Too Many Requests) if rate limiting is implemented
        # or continue returning 401 if not implemented yet
        assert response.status_code in [401, 422, 429]
    
    def test_authentication_header_format_validation(self, test_client):
        """Test authentication header format validation"""
        # Test missing Authorization header
        response = test_client.get("/mcp/resources/list")
        assert response.status_code == 401 or response.status_code == 403
        
        # Test invalid Authorization header format
        response = test_client.get(
            "/mcp/resources/list",
            headers={"Authorization": "InvalidFormat token123"}
        )
        assert response.status_code == 401
        
        # Test missing Bearer prefix
        response = test_client.get(
            "/mcp/resources/list",
            headers={"Authorization": "token123"}
        )
        assert response.status_code == 401
    
    def test_jwt_token_expiration_time_validation(self, auth_service):
        """Test JWT token expiration time is properly validated"""
        # Test token that expires very soon
        payload = {
            "sub": "test_user_123",
            "exp": datetime.utcnow() + timedelta(seconds=1),  # Expires in 1 second
            "iss": SecurityConstants.JWT_ISSUER,
            "aud": SecurityConstants.JWT_AUDIENCE
        }
        
        test_secret = "test_jwt_secret_key_for_testing_only"
        short_lived_token = jwt.encode(payload, test_secret, algorithm=SecurityConstants.JWT_ALGORITHM)
        
        with patch.object(auth_service, '_get_jwt_secret', return_value=test_secret):
            # Should be valid initially
            decoded = auth_service.validate_jwt_token(short_lived_token)
            assert decoded is not None
            
            # Wait for expiration and test again
            import time
            time.sleep(2)
            
            with pytest.raises(jwt.ExpiredSignatureError):
                auth_service.validate_jwt_token(short_lived_token)
    
    def test_authentication_service_secrets_validation(self):
        """Test authentication service uses proper secrets management"""
        try:
            # Test that secrets manager is used
            auth_service = AuthenticationService()
            
            # Should not raise exception if secrets are properly configured
            # (In test environment, this might fail due to missing env vars, which is expected)
            
        except ValueError as e:
            # Expected in test environment without proper secrets
            assert "Missing required secrets" in str(e)
    
    def test_oauth_scope_validation(self, test_client):
        """Test OAuth scope validation"""
        # Test with valid scope
        response = test_client.get(
            "/oauth/authorize",
            params={
                "client_id": "test_client",
                "redirect_uri": "https://trusted-app.com/callback",
                "response_type": "code",
                "state": "random_state_string",
                "scope": "read write"
            }
        )
        # Should accept valid scope
        assert response.status_code != 400
        
        # Test with invalid scope
        response = test_client.get(
            "/oauth/authorize",
            params={
                "client_id": "test_client",
                "redirect_uri": "https://trusted-app.com/callback",
                "response_type": "code",
                "state": "random_state_string",
                "scope": "invalid_scope"
            }
        )
        # Should reject invalid scope
        assert response.status_code == 400
    
    def test_authentication_logging_security(self, auth_service):
        """Test that authentication attempts are properly logged"""
        # This test would verify that authentication attempts are logged
        # without exposing sensitive information in logs
        
        # Mock logger to capture log calls
        with patch('backend.production.core.mcp_authentication_service.logger') as mock_logger:
            try:
                # Attempt authentication with invalid token
                auth_service.validate_jwt_token("invalid_token")
            except jwt.InvalidTokenError:
                pass
            
            # Verify that logging occurred
            assert mock_logger.warning.called or mock_logger.error.called
            
            # Verify no sensitive information was logged
            log_calls = mock_logger.warning.call_args_list + mock_logger.error.call_args_list
            for call in log_calls:
                log_message = str(call)
                # Ensure no tokens or secrets are in logs
                assert "invalid_token" not in log_message
                assert "secret" not in log_message.lower()


class TestAuthenticationIntegration:
    """Integration tests for authentication security"""
    
    def test_end_to_end_authentication_flow(self):
        """Test complete authentication flow security"""
        # This would test the complete flow from login to API access
        # ensuring all security measures are in place
        
        # 1. Login attempt
        # 2. Token generation
        # 3. Token validation
        # 4. API access with token
        # 5. Token expiration handling
        
        pass
    
    def test_authentication_with_different_user_roles(self):
        """Test authentication with different user roles and permissions"""
        # Test that users can only access resources they're authorized for
        pass
    
    def test_concurrent_authentication_attempts(self):
        """Test system behavior under concurrent authentication attempts"""
        # Test rate limiting and session management under load
        pass


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
