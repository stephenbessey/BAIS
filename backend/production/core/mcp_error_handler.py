"""
MCP Error Handler - Clean Code Implementation
Centralized error handling with proper exception types and security-conscious messaging
"""

import logging
import uuid
from enum import Enum
from typing import Union, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from fastapi import HTTPException


class ErrorType(Enum):
    """Error types for proper categorization"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_RULE = "business_rule"
    EXTERNAL_SERVICE = "external_service"
    INTERNAL = "internal"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"


class MCPError(Exception):
    """Base MCP error following Clean Code principles"""
    
    def __init__(self, message: str, error_type: ErrorType, details: Dict[str, Any] = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        super().__init__(message)


class ValidationError(MCPError):
    """Validation error for user input"""
    
    def __init__(self, message: str, field: str = None, value: Any = None, details: Dict[str, Any] = None):
        validation_details = {"field": field, "value": value}
        if details:
            validation_details.update(details)
        
        super().__init__(message, ErrorType.VALIDATION, validation_details)
        self.field = field
        self.value = value


class AuthenticationError(MCPError):
    """Authentication error"""
    
    def __init__(self, message: str, token_info: Dict[str, Any] = None, details: Dict[str, Any] = None):
        auth_details = {"token_info": token_info}
        if details:
            auth_details.update(details)
        
        super().__init__(message, ErrorType.AUTHENTICATION, auth_details)


class AuthorizationError(MCPError):
    """Authorization error"""
    
    def __init__(self, message: str, required_scopes: list = None, user_scopes: list = None, details: Dict[str, Any] = None):
        authz_details = {
            "required_scopes": required_scopes or [],
            "user_scopes": user_scopes or []
        }
        if details:
            authz_details.update(details)
        
        super().__init__(message, ErrorType.AUTHORIZATION, authz_details)
        self.required_scopes = required_scopes
        self.user_scopes = user_scopes


class BusinessRuleError(MCPError):
    """Business rule violation"""
    
    def __init__(self, message: str, rule_name: str, context: Dict[str, Any] = None, details: Dict[str, Any] = None):
        rule_details = {"rule_name": rule_name, "context": context or {}}
        if details:
            rule_details.update(details)
        
        super().__init__(message, ErrorType.BUSINESS_RULE, rule_details)
        self.rule_name = rule_name
        self.context = context


class ExternalServiceError(MCPError):
    """External service error"""
    
    def __init__(self, message: str, service_name: str, status_code: int = None, details: Dict[str, Any] = None):
        service_details = {
            "service_name": service_name,
            "status_code": status_code
        }
        if details:
            service_details.update(details)
        
        super().__init__(message, ErrorType.EXTERNAL_SERVICE, service_details)
        self.service_name = service_name
        self.status_code = status_code


class NotFoundError(MCPError):
    """Resource not found error"""
    
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None, details: Dict[str, Any] = None):
        not_found_details = {
            "resource_type": resource_type,
            "resource_id": resource_id
        }
        if details:
            not_found_details.update(details)
        
        super().__init__(message, ErrorType.NOT_FOUND, not_found_details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class RateLimitError(MCPError):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str, limit: int = None, window: int = None, retry_after: int = None, details: Dict[str, Any] = None):
        rate_limit_details = {
            "limit": limit,
            "window": window,
            "retry_after": retry_after
        }
        if details:
            rate_limit_details.update(details)
        
        super().__init__(message, ErrorType.RATE_LIMIT, rate_limit_details)
        self.limit = limit
        self.window = window
        self.retry_after = retry_after


@dataclass
class ErrorResponse:
    """Standardized error response"""
    error_id: str
    error_type: str
    message: str
    timestamp: str
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        result = {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp
        }
        if self.details:
            result["details"] = self.details
        return result


class MCPErrorHandler:
    """Centralized error handling following Clean Code principles"""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def handle_mcp_error(self, error: Exception, operation: str, user_context: Dict[str, Any] = None) -> ErrorResponse:
        """Handle MCP errors with proper categorization and logging"""
        
        if isinstance(error, ValidationError):
            return self._handle_validation_error(error, operation, user_context)
        elif isinstance(error, AuthenticationError):
            return self._handle_authentication_error(error, operation, user_context)
        elif isinstance(error, AuthorizationError):
            return self._handle_authorization_error(error, operation, user_context)
        elif isinstance(error, BusinessRuleError):
            return self._handle_business_rule_error(error, operation, user_context)
        elif isinstance(error, ExternalServiceError):
            return self._handle_external_service_error(error, operation, user_context)
        elif isinstance(error, NotFoundError):
            return self._handle_not_found_error(error, operation, user_context)
        elif isinstance(error, RateLimitError):
            return self._handle_rate_limit_error(error, operation, user_context)
        else:
            return self._handle_unexpected_error(error, operation, user_context)
    
    def _handle_validation_error(self, error: ValidationError, operation: str, user_context: Dict[str, Any]) -> ErrorResponse:
        """Handle validation errors with user-friendly messages"""
        self._logger.warning(
            f"Validation error in {operation}: {error.message}",
            extra={
                "error_id": error.error_id,
                "operation": operation,
                "field": error.field,
                "value": str(error.value) if error.value is not None else None,
                "user_context": user_context
            }
        )
        
        return ErrorResponse(
            error_id=error.error_id,
            error_type=error.error_type.value,
            message=error.message,
            timestamp=error.timestamp.isoformat(),
            details={"field": error.field} if error.field else None
        )
    
    def _handle_authentication_error(self, error: AuthenticationError, operation: str, user_context: Dict[str, Any]) -> ErrorResponse:
        """Handle authentication errors"""
        self._logger.warning(
            f"Authentication error in {operation}: {error.message}",
            extra={
                "error_id": error.error_id,
                "operation": operation,
                "user_context": user_context
            }
        )
        
        return ErrorResponse(
            error_id=error.error_id,
            error_type=error.error_type.value,
            message="Authentication failed",
            timestamp=error.timestamp.isoformat()
        )
    
    def _handle_authorization_error(self, error: AuthorizationError, operation: str, user_context: Dict[str, Any]) -> ErrorResponse:
        """Handle authorization errors"""
        self._logger.warning(
            f"Authorization error in {operation}: {error.message}",
            extra={
                "error_id": error.error_id,
                "operation": operation,
                "required_scopes": error.required_scopes,
                "user_scopes": error.user_scopes,
                "user_context": user_context
            }
        )
        
        return ErrorResponse(
            error_id=error.error_id,
            error_type=error.error_type.value,
            message="Insufficient permissions",
            timestamp=error.timestamp.isoformat()
        )
    
    def _handle_business_rule_error(self, error: BusinessRuleError, operation: str, user_context: Dict[str, Any]) -> ErrorResponse:
        """Handle business rule errors"""
        self._logger.warning(
            f"Business rule violation in {operation}: {error.message}",
            extra={
                "error_id": error.error_id,
                "operation": operation,
                "rule_name": error.rule_name,
                "context": error.context,
                "user_context": user_context
            }
        )
        
        return ErrorResponse(
            error_id=error.error_id,
            error_type=error.error_type.value,
            message=error.message,
            timestamp=error.timestamp.isoformat(),
            details={"rule_name": error.rule_name}
        )
    
    def _handle_external_service_error(self, error: ExternalServiceError, operation: str, user_context: Dict[str, Any]) -> ErrorResponse:
        """Handle external service errors"""
        self._logger.error(
            f"External service error in {operation}: {error.message}",
            extra={
                "error_id": error.error_id,
                "operation": operation,
                "service_name": error.service_name,
                "status_code": error.status_code,
                "user_context": user_context
            }
        )
        
        return ErrorResponse(
            error_id=error.error_id,
            error_type=error.error_type.value,
            message="External service temporarily unavailable",
            timestamp=error.timestamp.isoformat(),
            details={"service": error.service_name}
        )
    
    def _handle_not_found_error(self, error: NotFoundError, operation: str, user_context: Dict[str, Any]) -> ErrorResponse:
        """Handle not found errors"""
        self._logger.info(
            f"Resource not found in {operation}: {error.message}",
            extra={
                "error_id": error.error_id,
                "operation": operation,
                "resource_type": error.resource_type,
                "resource_id": error.resource_id,
                "user_context": user_context
            }
        )
        
        return ErrorResponse(
            error_id=error.error_id,
            error_type=error.error_type.value,
            message=error.message,
            timestamp=error.timestamp.isoformat(),
            details={
                "resource_type": error.resource_type,
                "resource_id": error.resource_id
            }
        )
    
    def _handle_rate_limit_error(self, error: RateLimitError, operation: str, user_context: Dict[str, Any]) -> ErrorResponse:
        """Handle rate limit errors"""
        self._logger.warning(
            f"Rate limit exceeded in {operation}: {error.message}",
            extra={
                "error_id": error.error_id,
                "operation": operation,
                "limit": error.limit,
                "window": error.window,
                "user_context": user_context
            }
        )
        
        return ErrorResponse(
            error_id=error.error_id,
            error_type=error.error_type.value,
            message="Rate limit exceeded",
            timestamp=error.timestamp.isoformat(),
            details={
                "limit": error.limit,
                "window": error.window,
                "retry_after": error.retry_after
            }
        )
    
    def _handle_unexpected_error(self, error: Exception, operation: str, user_context: Dict[str, Any]) -> ErrorResponse:
        """Handle unexpected errors with security-conscious messaging"""
        error_id = str(uuid.uuid4())
        
        self._logger.error(
            f"Unexpected error in {operation}: {str(error)}",
            extra={
                "error_id": error_id,
                "operation": operation,
                "user_context": user_context
            },
            exc_info=True
        )
        
        return ErrorResponse(
            error_id=error_id,
            error_type=ErrorType.INTERNAL.value,
            message="An unexpected error occurred. Please contact support if the issue persists.",
            timestamp=datetime.utcnow().isoformat()
        )
    
    def handle_tool_error(self, error: Exception, tool_name: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution errors and return MCP-compatible response"""
        error_response = self.handle_mcp_error(error, f"tool:{tool_name}", user_context)
        
        # Convert to MCP tool response format
        return {
            "content": [{
                "type": "text",
                "text": f"Error {error_response.error_id}: {error_response.message}"
            }],
            "isError": True,
            "error": error_response.to_dict()
        }
    
    def handle_resource_error(self, error: Exception, operation: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resource operation errors and return MCP-compatible response"""
        error_response = self.handle_mcp_error(error, f"resource:{operation}", user_context)
        
        # Convert to MCP resource response format
        return {
            "contents": [],
            "error": error_response.to_dict()
        }


# Global error handler instance
_error_handler: Optional[MCPErrorHandler] = None


def get_error_handler() -> MCPErrorHandler:
    """Get the global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = MCPErrorHandler(logging.getLogger(__name__))
    return _error_handler


# Convenience functions for common error scenarios
def raise_validation_error(message: str, field: str = None, value: Any = None):
    """Raise a validation error"""
    raise ValidationError(message, field, value)


def raise_business_rule_error(message: str, rule_name: str, context: Dict[str, Any] = None):
    """Raise a business rule error"""
    raise BusinessRuleError(message, rule_name, context)


def raise_not_found_error(resource_type: str, resource_id: str):
    """Raise a not found error"""
    raise NotFoundError(f"{resource_type} '{resource_id}' not found", resource_type, resource_id)


def raise_authorization_error(required_scopes: list, user_scopes: list):
    """Raise an authorization error"""
    raise AuthorizationError(
        "Insufficient permissions",
        required_scopes=required_scopes,
        user_scopes=user_scopes
    )
