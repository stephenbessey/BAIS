"""
Comprehensive Error Handling Strategy
Implements robust error handling for A2A and AP2 protocols

This module provides comprehensive error handling following clean code principles
and production-ready error management.
"""

from typing import Dict, Any, Optional, Type, Union, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import traceback
import logging
from abc import ABC, abstractmethod

from .protocol_configurations import A2A_CONFIG, AP2_CONFIG


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"
    SECURITY = "security"


@dataclass(frozen=True)
class ErrorContext:
    """Error context information"""
    request_id: str = None
    user_id: str = None
    business_id: str = None
    agent_id: str = None
    task_id: str = None
    endpoint: str = None
    method: str = None
    timestamp: datetime = None
    correlation_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.utcnow())


@dataclass(frozen=True)
class ErrorDetails:
    """Detailed error information"""
    error_code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: ErrorContext
    technical_details: Dict[str, Any] = None
    user_message: str = None
    retry_after_seconds: int = None
    error_id: str = None
    
    def __post_init__(self):
        if self.technical_details is None:
            object.__setattr__(self, 'technical_details', {})
        
        if self.user_message is None:
            object.__setattr__(self, 'user_message', self.message)
        
        if self.error_id is None:
            import uuid
            object.__setattr__(self, 'error_id', str(uuid.uuid4()))


class BAISError(Exception):
    """
    Base exception class for all BAIS errors
    
    Provides structured error handling with context and categorization
    """
    
    def __init__(
        self,
        error_code: str,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: ErrorContext = None,
        technical_details: Dict[str, Any] = None,
        user_message: str = None,
        retry_after_seconds: int = None
    ):
        super().__init__(message)
        
        self.error_details = ErrorDetails(
            error_code=error_code,
            message=message,
            category=category,
            severity=severity,
            context=context or ErrorContext(),
            technical_details=technical_details or {},
            user_message=user_message,
            retry_after_seconds=retry_after_seconds
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return asdict(self.error_details)


# Specific error classes
class ValidationError(BAISError):
    """Validation error"""
    def __init__(self, message: str, field: str = None, value: Any = None, context: ErrorContext = None):
        technical_details = {}
        if field:
            technical_details['field'] = field
        if value is not None:
            technical_details['value'] = str(value)
        
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            context=context,
            technical_details=technical_details
        )


class AuthenticationError(BAISError):
    """Authentication error"""
    def __init__(self, message: str = "Authentication failed", context: ErrorContext = None):
        super().__init__(
            error_code="AUTHENTICATION_ERROR",
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            context=context
        )


class AuthorizationError(BAISError):
    """Authorization error"""
    def __init__(self, message: str = "Access denied", required_scopes: List[str] = None, context: ErrorContext = None):
        technical_details = {}
        if required_scopes:
            technical_details['required_scopes'] = required_scopes
        
        super().__init__(
            error_code="AUTHORIZATION_ERROR",
            message=message,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            technical_details=technical_details
        )


class BusinessLogicError(BAISError):
    """Business logic error"""
    def __init__(self, message: str, operation: str = None, context: ErrorContext = None):
        technical_details = {}
        if operation:
            technical_details['operation'] = operation
        
        super().__init__(
            error_code="BUSINESS_LOGIC_ERROR",
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            technical_details=technical_details
        )


class ExternalServiceError(BAISError):
    """External service error"""
    def __init__(
        self, 
        message: str, 
        service_name: str, 
        status_code: int = None, 
        retry_after_seconds: int = None,
        context: ErrorContext = None
    ):
        technical_details = {
            'service_name': service_name,
            'status_code': status_code
        }
        
        super().__init__(
            error_code="EXTERNAL_SERVICE_ERROR",
            message=message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            technical_details=technical_details,
            retry_after_seconds=retry_after_seconds
        )


class DatabaseError(BAISError):
    """Database error"""
    def __init__(self, message: str, operation: str = None, context: ErrorContext = None):
        technical_details = {}
        if operation:
            technical_details['operation'] = operation
        
        super().__init__(
            error_code="DATABASE_ERROR",
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            context=context,
            technical_details=technical_details
        )


class NetworkError(BAISError):
    """Network error"""
    def __init__(
        self, 
        message: str, 
        endpoint: str = None, 
        retry_after_seconds: int = None,
        context: ErrorContext = None
    ):
        technical_details = {}
        if endpoint:
            technical_details['endpoint'] = endpoint
        
        super().__init__(
            error_code="NETWORK_ERROR",
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            technical_details=technical_details,
            retry_after_seconds=retry_after_seconds
        )


class SecurityError(BAISError):
    """Security error"""
    def __init__(self, message: str, security_violation: str = None, context: ErrorContext = None):
        technical_details = {}
        if security_violation:
            technical_details['security_violation'] = security_violation
        
        super().__init__(
            error_code="SECURITY_ERROR",
            message=message,
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.CRITICAL,
            context=context,
            technical_details=technical_details
        )


class SystemError(BAISError):
    """System error"""
    def __init__(self, message: str, component: str = None, context: ErrorContext = None):
        technical_details = {}
        if component:
            technical_details['component'] = component
        
        super().__init__(
            error_code="SYSTEM_ERROR",
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            context=context,
            technical_details=technical_details
        )


class ErrorHandler(ABC):
    """Abstract base class for error handlers"""
    
    @abstractmethod
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle an error and return error details"""
        pass


class A2AErrorHandler(ErrorHandler):
    """Error handler for A2A protocol errors"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle A2A protocol errors"""
        
        if isinstance(error, ValidationError):
            return self._handle_validation_error(error, context)
        elif isinstance(error, AuthenticationError):
            return self._handle_authentication_error(error, context)
        elif isinstance(error, AuthorizationError):
            return self._handle_authorization_error(error, context)
        elif isinstance(error, ExternalServiceError):
            return self._handle_external_service_error(error, context)
        elif isinstance(error, NetworkError):
            return self._handle_network_error(error, context)
        else:
            return self._handle_generic_error(error, context)
    
    def _handle_validation_error(self, error: ValidationError, context: ErrorContext) -> ErrorDetails:
        """Handle validation errors"""
        self.logger.warning(f"A2A validation error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'technical_details': error.error_details.technical_details
        })
        return error.error_details
    
    def _handle_authentication_error(self, error: AuthenticationError, context: ErrorContext) -> ErrorDetails:
        """Handle authentication errors"""
        self.logger.error(f"A2A authentication error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'security_alert': True
        })
        return error.error_details
    
    def _handle_authorization_error(self, error: AuthorizationError, context: ErrorContext) -> ErrorDetails:
        """Handle authorization errors"""
        self.logger.warning(f"A2A authorization error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'technical_details': error.error_details.technical_details
        })
        return error.error_details
    
    def _handle_external_service_error(self, error: ExternalServiceError, context: ErrorContext) -> ErrorDetails:
        """Handle external service errors"""
        self.logger.error(f"A2A external service error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'technical_details': error.error_details.technical_details
        })
        return error.error_details
    
    def _handle_network_error(self, error: NetworkError, context: ErrorContext) -> ErrorDetails:
        """Handle network errors"""
        self.logger.error(f"A2A network error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'technical_details': error.error_details.technical_details
        })
        return error.error_details
    
    def _handle_generic_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle generic errors"""
        error_details = ErrorDetails(
            error_code="UNKNOWN_ERROR",
            message=str(error),
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            technical_details={
                'exception_type': type(error).__name__,
                'traceback': traceback.format_exc()
            }
        )
        
        self.logger.error(f"A2A unknown error: {error}", extra={
            'error_code': error_details.error_code,
            'context': asdict(context),
            'technical_details': error_details.technical_details
        })
        
        return error_details


class AP2ErrorHandler(ErrorHandler):
    """Error handler for AP2 protocol errors"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle AP2 protocol errors"""
        
        if isinstance(error, ValidationError):
            return self._handle_validation_error(error, context)
        elif isinstance(error, SecurityError):
            return self._handle_security_error(error, context)
        elif isinstance(error, BusinessLogicError):
            return self._handle_business_logic_error(error, context)
        elif isinstance(error, ExternalServiceError):
            return self._handle_external_service_error(error, context)
        elif isinstance(error, DatabaseError):
            return self._handle_database_error(error, context)
        else:
            return self._handle_generic_error(error, context)
    
    def _handle_validation_error(self, error: ValidationError, context: ErrorContext) -> ErrorDetails:
        """Handle validation errors"""
        self.logger.warning(f"AP2 validation error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'technical_details': error.error_details.technical_details
        })
        return error.error_details
    
    def _handle_security_error(self, error: SecurityError, context: ErrorContext) -> ErrorDetails:
        """Handle security errors"""
        self.logger.critical(f"AP2 security error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'technical_details': error.error_details.technical_details,
            'security_alert': True
        })
        return error.error_details
    
    def _handle_business_logic_error(self, error: BusinessLogicError, context: ErrorContext) -> ErrorDetails:
        """Handle business logic errors"""
        self.logger.warning(f"AP2 business logic error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'technical_details': error.error_details.technical_details
        })
        return error.error_details
    
    def _handle_external_service_error(self, error: ExternalServiceError, context: ErrorContext) -> ErrorDetails:
        """Handle external service errors"""
        self.logger.error(f"AP2 external service error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'technical_details': error.error_details.technical_details
        })
        return error.error_details
    
    def _handle_database_error(self, error: DatabaseError, context: ErrorContext) -> ErrorDetails:
        """Handle database errors"""
        self.logger.error(f"AP2 database error: {error.error_details.message}", extra={
            'error_code': error.error_details.error_code,
            'context': asdict(context),
            'technical_details': error.error_details.technical_details
        })
        return error.error_details
    
    def _handle_generic_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle generic errors"""
        error_details = ErrorDetails(
            error_code="UNKNOWN_ERROR",
            message=str(error),
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            technical_details={
                'exception_type': type(error).__name__,
                'traceback': traceback.format_exc()
            }
        )
        
        self.logger.error(f"AP2 unknown error: {error}", extra={
            'error_code': error_details.error_code,
            'context': asdict(context),
            'technical_details': error_details.technical_details
        })
        
        return error_details


class ComprehensiveErrorManager:
    """
    Comprehensive error management system
    
    Provides centralized error handling for all BAIS components
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.a2a_handler = A2AErrorHandler(self.logger)
        self.ap2_handler = AP2ErrorHandler(self.logger)
        self.error_metrics = {}
    
    def handle_error(
        self, 
        error: Exception, 
        protocol: str = "generic",
        context: ErrorContext = None
    ) -> ErrorDetails:
        """
        Handle error with appropriate handler
        
        Args:
            error: Exception to handle
            protocol: Protocol type ("a2a", "ap2", "generic")
            context: Error context
            
        Returns:
            ErrorDetails with error information
        """
        if context is None:
            context = ErrorContext()
        
        # Route to appropriate handler
        if protocol == "a2a":
            error_details = self.a2a_handler.handle_error(error, context)
        elif protocol == "ap2":
            error_details = self.ap2_handler.handle_error(error, context)
        else:
            error_details = self._handle_generic_error(error, context)
        
        # Update metrics
        self._update_error_metrics(error_details)
        
        return error_details
    
    def _handle_generic_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle generic errors"""
        error_details = ErrorDetails(
            error_code="UNKNOWN_ERROR",
            message=str(error),
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            technical_details={
                'exception_type': type(error).__name__,
                'traceback': traceback.format_exc()
            }
        )
        
        self.logger.error(f"Generic error: {error}", extra={
            'error_code': error_details.error_code,
            'context': asdict(context),
            'technical_details': error_details.technical_details
        })
        
        return error_details
    
    def _update_error_metrics(self, error_details: ErrorDetails) -> None:
        """Update error metrics"""
        category = error_details.category.value
        severity = error_details.severity.value
        
        if category not in self.error_metrics:
            self.error_metrics[category] = {}
        
        if severity not in self.error_metrics[category]:
            self.error_metrics[category][severity] = 0
        
        self.error_metrics[category][severity] += 1
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error metrics"""
        return {
            'metrics': self.error_metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def create_error_context(
        self,
        request_id: str = None,
        user_id: str = None,
        business_id: str = None,
        agent_id: str = None,
        task_id: str = None,
        endpoint: str = None,
        method: str = None,
        correlation_id: str = None
    ) -> ErrorContext:
        """Create error context"""
        return ErrorContext(
            request_id=request_id,
            user_id=user_id,
            business_id=business_id,
            agent_id=agent_id,
            task_id=task_id,
            endpoint=endpoint,
            method=method,
            correlation_id=correlation_id
        )


# Global error manager instance
_error_manager = ComprehensiveErrorManager()


def get_error_manager() -> ComprehensiveErrorManager:
    """Get global error manager instance"""
    return _error_manager


def handle_a2a_error(error: Exception, context: ErrorContext = None) -> ErrorDetails:
    """Handle A2A error"""
    return _error_manager.handle_error(error, "a2a", context)


def handle_ap2_error(error: Exception, context: ErrorContext = None) -> ErrorDetails:
    """Handle AP2 error"""
    return _error_manager.handle_error(error, "ap2", context)


def handle_generic_error(error: Exception, context: ErrorContext = None) -> ErrorDetails:
    """Handle generic error"""
    return _error_manager.handle_error(error, "generic", context)
