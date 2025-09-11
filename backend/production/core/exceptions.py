"""
BAIS Application Exceptions
Custom exception classes for better error handling and debugging
"""

from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status


class BAISException(Exception):
    """Base exception for all BAIS-related errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ValidationError(BAISException):
    """Raised when validation fails"""
    pass


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails"""
    
    def __init__(
        self, 
        message: str, 
        validation_issues: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.validation_issues = validation_issues or []


class BusinessRegistrationError(BAISException):
    """Raised when business registration fails"""
    
    def __init__(
        self, 
        message: str, 
        business_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.business_id = business_id


class ServiceConfigurationError(BAISException):
    """Raised when service configuration is invalid"""
    
    def __init__(
        self, 
        message: str, 
        service_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.service_id = service_id


class AuthenticationError(BAISException):
    """Raised when authentication fails"""
    pass


class AuthorizationError(BAISException):
    """Raised when authorization fails"""
    
    def __init__(
        self, 
        message: str, 
        required_permission: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.required_permission = required_permission


class OAuthError(BAISException):
    """Raised when OAuth operations fail"""
    
    def __init__(
        self, 
        message: str, 
        oauth_error_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.oauth_error_code = oauth_error_code


class DatabaseError(BAISException):
    """Raised when database operations fail"""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.operation = operation


class IntegrationError(BAISException):
    """Raised when external integrations fail"""
    
    def __init__(
        self, 
        message: str, 
        integration_type: Optional[str] = None,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.integration_type = integration_type
        self.endpoint = endpoint


class ConfigurationError(BAISException):
    """Raised when configuration is invalid"""
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.config_key = config_key


class RateLimitError(BAISException):
    """Raised when rate limits are exceeded"""
    
    def __init__(
        self, 
        message: str, 
        limit: Optional[int] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.limit = limit
        self.retry_after = retry_after


class WorkflowError(BAISException):
    """Raised when workflow execution fails"""
    
    def __init__(
        self, 
        message: str, 
        workflow_id: Optional[str] = None,
        step: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.workflow_id = workflow_id
        self.step = step


class TimeoutError(BAISException):
    """Raised when operations timeout"""
    
    def __init__(
        self, 
        message: str, 
        timeout_seconds: Optional[int] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.operation = operation


# HTTP Exception converters
def convert_to_http_exception(exc: BAISException) -> HTTPException:
    """Convert BAIS exceptions to appropriate HTTP exceptions"""
    
    if isinstance(exc, ValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        )
    
    elif isinstance(exc, AuthenticationError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        )
    
    elif isinstance(exc, AuthorizationError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": exc.error_code,
                "message": exc.message,
                "required_permission": exc.required_permission,
                "details": exc.details
            }
        )
    
    elif isinstance(exc, (BusinessRegistrationError, ServiceConfigurationError)):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        )
    
    elif isinstance(exc, RateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": exc.error_code,
                "message": exc.message,
                "retry_after": exc.retry_after,
                "details": exc.details
            },
            headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        )
    
    elif isinstance(exc, TimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "error": exc.error_code,
                "message": exc.message,
                "timeout_seconds": exc.timeout_seconds,
                "details": exc.details
            }
        )
    
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        )
