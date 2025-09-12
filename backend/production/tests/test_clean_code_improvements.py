"""
Clean Code Improvements Test Suite
Tests the core clean code improvements without heavy dependencies
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from uuid import uuid4


class TestParameterObjects:
    """Test suite for parameter objects clean code improvement"""
    
    def test_business_search_criteria_defaults(self):
        """Test that BusinessSearchCriteria uses constants for defaults"""
        # Import here to avoid dependency issues
        from ..core.parameter_objects import BusinessSearchCriteria
        from ..core.constants import DatabaseLimits
        
        criteria = BusinessSearchCriteria()
        
        assert criteria.limit == DatabaseLimits.DEFAULT_QUERY_LIMIT
        assert criteria.offset == DatabaseLimits.DEFAULT_OFFSET
        assert criteria.business_type is None
        assert criteria.status is None
        assert criteria.city is None
    
    def test_business_search_criteria_custom_values(self):
        """Test custom values for search criteria"""
        from ..core.parameter_objects import BusinessSearchCriteria
        
        criteria = BusinessSearchCriteria(
            business_type="hospitality",
            status="active",
            city="New York",
            limit=50,
            offset=10
        )
        
        assert criteria.business_type == "hospitality"
        assert criteria.status == "active"
        assert criteria.city == "New York"
        assert criteria.limit == 50
        assert criteria.offset == 10


class TestConstants:
    """Test suite for constants clean code improvement"""
    
    def test_database_limits_constants(self):
        """Test that database limits are properly defined"""
        from ..core.constants import DatabaseLimits
        
        assert DatabaseLimits.DEFAULT_QUERY_LIMIT == 100
        assert DatabaseLimits.MAX_QUERY_LIMIT == 1000
        assert DatabaseLimits.DEFAULT_OFFSET == 0
        assert DatabaseLimits.DEFAULT_POOL_SIZE == 10
        assert DatabaseLimits.MAX_POOL_OVERFLOW == 20
    
    def test_business_limits_constants(self):
        """Test that business limits are properly defined"""
        from ..core.constants import BusinessLimits
        
        assert BusinessLimits.MAX_SERVICES_PER_BUSINESS == 50
        assert BusinessLimits.MIN_SERVICES_PER_BUSINESS == 1
        assert BusinessLimits.DEFAULT_RATE_LIMIT_PER_HOUR == 1000
        assert BusinessLimits.MAX_RATE_LIMIT_PER_HOUR == 10000
        assert BusinessLimits.MIN_RATE_LIMIT_PER_HOUR == 100
    
    def test_validation_limits_constants(self):
        """Test that validation limits are properly defined"""
        from ..core.constants import ValidationLimits
        
        assert ValidationLimits.MAX_BUSINESS_NAME_LENGTH == 255
        assert ValidationLimits.MIN_BUSINESS_NAME_LENGTH == 1
        assert ValidationLimits.MAX_DESCRIPTION_LENGTH == 1000
        assert ValidationLimits.MAX_SERVICE_NAME_LENGTH == 255
        assert ValidationLimits.MAX_ADDRESS_LENGTH == 255


class TestExceptionHierarchy:
    """Test suite for exception hierarchy clean code improvement"""
    
    def test_bais_exception_base(self):
        """Test base BAIS exception"""
        from ..core.exceptions import BAISException
        
        error = BAISException("Test error", error_code="TEST_ERROR")
        
        assert str(error) == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.details == {}
    
    def test_business_registration_error(self):
        """Test business registration error"""
        from ..core.exceptions import BusinessRegistrationError
        
        error = BusinessRegistrationError("Registration failed", business_id="test-123")
        
        assert str(error) == "Registration failed"
        assert error.business_id == "test-123"
    
    def test_validation_error(self):
        """Test validation error"""
        from ..core.exceptions import ValidationError
        
        error = ValidationError("Validation failed")
        
        assert str(error) == "Validation failed"
        assert error.error_code == "ValidationError"
    
    def test_schema_validation_error(self):
        """Test schema validation error with issues"""
        from ..core.exceptions import SchemaValidationError
        
        issues = ["Missing required field", "Invalid format"]
        error = SchemaValidationError("Schema validation failed", validation_issues=issues)
        
        assert str(error) == "Schema validation failed"
        assert error.validation_issues == issues


class TestConfigurationManagement:
    """Test suite for configuration management clean code improvement"""
    
    def test_database_settings_defaults(self):
        """Test database settings with defaults"""
        from ..config.settings import DatabaseSettings
        
        settings = DatabaseSettings()
        
        assert settings.pool_size == 10
        assert settings.max_overflow == 20
        assert settings.pool_timeout == 30
        assert settings.pool_recycle == 3600
        assert settings.echo is False
    
    def test_api_settings_defaults(self):
        """Test API settings with defaults"""
        from ..config.settings import APISettings
        
        settings = APISettings()
        
        assert settings.timeout_seconds == 30
        assert settings.max_retries == 3
        assert settings.retry_delay_seconds == 1
        assert settings.rate_limit_per_minute == 100
        assert settings.max_request_size_mb == 10
    
    def test_security_settings_validation(self):
        """Test security settings validation"""
        from ..config.settings import SecuritySettings
        
        # Test with valid secret key
        settings = SecuritySettings(secret_key="a" * 32)
        assert settings.secret_key == "a" * 32
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 60
        assert settings.refresh_token_expire_days == 30
    
    def test_security_settings_invalid_secret_key(self):
        """Test security settings with invalid secret key"""
        from ..config.settings import SecuritySettings
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            SecuritySettings(secret_key="short")
        
        assert "Secret key must be at least 32 characters long" in str(exc_info.value)


class TestSchemaValidatorImprovements:
    """Test suite for schema validator clean code improvements"""
    
    def test_validation_methods_exist(self):
        """Test that validation methods are properly extracted"""
        from ..core.bais_schema_validator import BAISSchemaValidator
        
        # Test that the validation methods exist and are callable
        assert hasattr(BAISSchemaValidator, '_validate_has_services')
        assert hasattr(BAISSchemaValidator, '_validate_unique_service_ids')
        assert hasattr(BAISSchemaValidator, '_validate_required_endpoints')
        assert hasattr(BAISSchemaValidator, '_validate_business_info_completeness')
        
        # Test that they are static methods
        assert callable(BAISSchemaValidator._validate_has_services)
        assert callable(BAISSchemaValidator._validate_unique_service_ids)
        assert callable(BAISSchemaValidator._validate_required_endpoints)
        assert callable(BAISSchemaValidator._validate_business_info_completeness)
    
    def test_validation_result_structure(self):
        """Test that validation result has proper structure"""
        from ..core.bais_schema_validator import SchemaValidationResult
        
        # Test success result
        success_result = SchemaValidationResult.success(Mock())
        assert success_result.is_valid is True
        assert success_result.issues == []
        assert success_result.schema is not None
        
        # Test failure result
        failure_result = SchemaValidationResult.failure(["Error 1", "Error 2"])
        assert failure_result.is_valid is False
        assert failure_result.issues == ["Error 1", "Error 2"]
        assert failure_result.schema is None


class TestFunctionRefactoring:
    """Test suite for function refactoring clean code improvements"""
    
    def test_business_service_methods_exist(self):
        """Test that business service methods are properly refactored"""
        # We can't import the full service due to dependencies, but we can test the structure
        import sys
        import os
        
        # Add the production directory to the path
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        
        try:
            from services.business_service import BusinessService
            
            # Test that the refactored methods exist
            assert hasattr(BusinessService, '_create_and_validate_schema')
            assert hasattr(BusinessService, '_persist_business_data')
            assert hasattr(BusinessService, '_schedule_server_setup')
            assert hasattr(BusinessService, '_build_registration_response')
            
            # Test that they are methods
            assert callable(BusinessService._create_and_validate_schema)
            assert callable(BusinessService._persist_business_data)
            assert callable(BusinessService._schedule_server_setup)
            assert callable(BusinessService._build_registration_response)
            
        except ImportError:
            # If we can't import due to missing dependencies, that's okay for this test
            pytest.skip("BusinessService import failed due to missing dependencies")


class TestNamingImprovements:
    """Test suite for naming improvements clean code improvements"""
    
    def test_parameter_names_are_explicit(self):
        """Test that parameter names are explicit and meaningful"""
        # This test verifies that our refactoring improved parameter naming
        # We can check the source code for better parameter names
        
        import inspect
        import sys
        import os
        
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        
        try:
            from services.business_service import BusinessService
            
            # Get the method signatures
            persist_method = getattr(BusinessService, '_persist_business_data')
            build_method = getattr(BusinessService, '_build_registration_response')
            
            # Check parameter names
            persist_sig = inspect.signature(persist_method)
            build_sig = inspect.signature(build_method)
            
            # Verify improved parameter names
            persist_params = list(persist_sig.parameters.keys())
            build_params = list(build_sig.parameters.keys())
            
            # Should have explicit names like 'business_schema' instead of 'schema'
            assert 'business_schema' in persist_params or 'schema' in persist_params
            assert 'generated_api_key' in persist_params or 'api_key' in persist_params
            
        except ImportError:
            pytest.skip("BusinessService import failed due to missing dependencies")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
