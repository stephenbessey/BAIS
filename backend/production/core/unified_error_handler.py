"""
Unified Error Handler - Implementation
Centralized error handling across all protocols (A2A, AP2, MCP) following best practices
"""

import logging
import uuid
import traceback
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from fastapi import HTTPException, status
import json

logger = logging.getLogger(__name__)


class ProtocolType(Enum):
    """Supported protocol types"""
    A2A = "a2a"
    AP2 = "ap2"
    MCP = "mcp"
    CROSS_PROTOCOL = "cross_protocol"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories across all protocols"""
    # Authentication & Authorization
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_DENIED = "authorization_denied"
    TOKEN_EXPIRED = "token_expired"
    INVALID_CREDENTIALS = "invalid_credentials"
    
    # Validation Errors
    INVALID_INPUT = "invalid_input"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_FORMAT = "invalid_format"
    CONSTRAINT_VIOLATION = "constraint_violation"
    
    # Protocol Specific Errors
    # A2A Errors
    AGENT_NOT_FOUND = "agent_not_found"
    TASK_EXECUTION_FAILED = "task_execution_failed"
    CAPABILITY_NOT_SUPPORTED = "capability_not_supported"
    AGENT_DISCOVERY_FAILED = "agent_discovery_failed"
    
    # AP2 Errors
    PAYMENT_FAILED = "payment_failed"
    MANDATE_INVALID = "mandate_invalid"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    WEBHOOK_SIGNATURE_INVALID = "webhook_signature_invalid"
    
    # MCP Errors
    RESOURCE_NOT_FOUND = "resource_not_found"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    PROMPT_RENDERING_FAILED = "prompt_rendering_failed"
    SSE_CONNECTION_FAILED = "sse_connection_failed"
    
    # System Errors
    INTERNAL_SERVER_ERROR = "internal_server_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Integration Errors
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    NETWORK_ERROR = "network_error"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    
    # Business Logic Errors
    BUSINESS_RULE_VIOLATION = "business_rule_violation"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    RESOURCE_LOCKED = "resource_locked"


@dataclass
class UnifiedError:
    """Unified error structure across all protocols"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol: ProtocolType = ProtocolType.CROSS_PROTOCOL
    category: ErrorCategory = ErrorCategory.INTERNAL_SERVER_ERROR
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: Optional[str] = None
    user_context: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization"""
        return {
            "error_id": self.error_id,
            "protocol": self.protocol.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
            "user_context": self.user_context,
            "suggested_actions": self.suggested_actions
        }


class UnifiedErrorHandler:
    """Unified error handler for all protocols following best practices"""
    
    def __init__(self):
        self._error_history: List[UnifiedError] = []
        self._max_history_size = 1000
        self._error_counts: Dict[str, int] = {}
        self._severity_thresholds = {
            ErrorSeverity.LOW: 100,
            ErrorSeverity.MEDIUM: 50,
            ErrorSeverity.HIGH: 20,
            ErrorSeverity.CRITICAL: 5
        }
    
    def handle_error(
        self,
        error: Exception,
        protocol: ProtocolType,
        context: Optional[Dict[str, Any]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> UnifiedError:
        """Handle any error and convert to unified format"""
        try:
            # Determine error category and severity
            category, severity = self._classify_error(error, protocol)
            
            # Create unified error
            unified_error = UnifiedError(
                protocol=protocol,
                category=category,
                severity=severity,
                message=str(error),
                details=self._extract_error_details(error, context),
                stack_trace=self._get_safe_stack_trace(error),
                user_context=user_context or {},
                suggested_actions=self._get_suggested_actions(category, protocol)
            )
            
            # Log the error
            self._log_error(unified_error)
            
            # Record in history
            self._record_error(unified_error)
            
            return unified_error
            
        except Exception as e:
            # Fallback error handling
            logger.error(f"Error in unified error handler: {e}")
            return UnifiedError(
                protocol=protocol,
                category=ErrorCategory.INTERNAL_SERVER_ERROR,
                severity=ErrorSeverity.CRITICAL,
                message=f"Error handling failed: {str(e)}",
                details={"original_error": str(error), "handler_error": str(e)}
            )
    
    def _classify_error(self, error: Exception, protocol: ProtocolType) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error into category and severity"""
        
        # Protocol-specific classification
        if protocol == ProtocolType.A2A:
            return self._classify_a2a_error(error)
        elif protocol == ProtocolType.AP2:
            return self._classify_ap2_error(error)
        elif protocol == ProtocolType.MCP:
            return self._classify_mcp_error(error)
        else:
            return self._classify_generic_error(error)
    
    def _classify_a2a_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify A2A protocol errors"""
        error_str = str(error).lower()
        
        if "agent not found" in error_str or "agent_not_found" in error_str:
            return ErrorCategory.AGENT_NOT_FOUND, ErrorSeverity.MEDIUM
        elif "task execution failed" in error_str or "task_execution_failed" in error_str:
            return ErrorCategory.TASK_EXECUTION_FAILED, ErrorSeverity.HIGH
        elif "capability not supported" in error_str or "capability_not_supported" in error_str:
            return ErrorCategory.CAPABILITY_NOT_SUPPORTED, ErrorSeverity.MEDIUM
        elif "discovery failed" in error_str or "discovery_failed" in error_str:
            return ErrorCategory.AGENT_DISCOVERY_FAILED, ErrorSeverity.MEDIUM
        elif "authentication" in error_str or "auth" in error_str:
            return ErrorCategory.AUTHENTICATION_FAILED, ErrorSeverity.HIGH
        elif "authorization" in error_str:
            return ErrorCategory.AUTHORIZATION_DENIED, ErrorSeverity.HIGH
        else:
            return ErrorCategory.INTERNAL_SERVER_ERROR, ErrorSeverity.MEDIUM
    
    def _classify_ap2_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify AP2 protocol errors"""
        error_str = str(error).lower()
        
        if "payment failed" in error_str or "payment_failed" in error_str:
            return ErrorCategory.PAYMENT_FAILED, ErrorSeverity.HIGH
        elif "mandate invalid" in error_str or "mandate_invalid" in error_str:
            return ErrorCategory.MANDATE_INVALID, ErrorSeverity.HIGH
        elif "insufficient funds" in error_str or "insufficient_funds" in error_str:
            return ErrorCategory.INSUFFICIENT_FUNDS, ErrorSeverity.HIGH
        elif "webhook signature" in error_str or "signature invalid" in error_str:
            return ErrorCategory.WEBHOOK_SIGNATURE_INVALID, ErrorSeverity.CRITICAL
        elif "authentication" in error_str or "auth" in error_str:
            return ErrorCategory.AUTHENTICATION_FAILED, ErrorSeverity.HIGH
        elif "authorization" in error_str:
            return ErrorCategory.AUTHORIZATION_DENIED, ErrorSeverity.HIGH
        else:
            return ErrorCategory.INTERNAL_SERVER_ERROR, ErrorSeverity.MEDIUM
    
    def _classify_mcp_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify MCP protocol errors"""
        error_str = str(error).lower()
        
        if "resource not found" in error_str or "resource_not_found" in error_str:
            return ErrorCategory.RESOURCE_NOT_FOUND, ErrorSeverity.MEDIUM
        elif "tool execution failed" in error_str or "tool_execution_failed" in error_str:
            return ErrorCategory.TOOL_EXECUTION_FAILED, ErrorSeverity.HIGH
        elif "prompt rendering failed" in error_str or "prompt_rendering_failed" in error_str:
            return ErrorCategory.PROMPT_RENDERING_FAILED, ErrorSeverity.MEDIUM
        elif "sse connection failed" in error_str or "sse_connection_failed" in error_str:
            return ErrorCategory.SSE_CONNECTION_FAILED, ErrorSeverity.MEDIUM
        elif "authentication" in error_str or "auth" in error_str:
            return ErrorCategory.AUTHENTICATION_FAILED, ErrorSeverity.HIGH
        elif "authorization" in error_str:
            return ErrorCategory.AUTHORIZATION_DENIED, ErrorSeverity.HIGH
        else:
            return ErrorCategory.INTERNAL_SERVER_ERROR, ErrorSeverity.MEDIUM
    
    def _classify_generic_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify generic errors"""
        error_str = str(error).lower()
        
        if "validation" in error_str or "invalid" in error_str:
            return ErrorCategory.INVALID_INPUT, ErrorSeverity.MEDIUM
        elif "timeout" in error_str:
            return ErrorCategory.TIMEOUT_ERROR, ErrorSeverity.HIGH
        elif "rate limit" in error_str:
            return ErrorCategory.RATE_LIMIT_EXCEEDED, ErrorSeverity.MEDIUM
        elif "service unavailable" in error_str:
            return ErrorCategory.SERVICE_UNAVAILABLE, ErrorSeverity.HIGH
        elif "network" in error_str:
            return ErrorCategory.NETWORK_ERROR, ErrorSeverity.HIGH
        else:
            return ErrorCategory.INTERNAL_SERVER_ERROR, ErrorSeverity.MEDIUM
    
    def _extract_error_details(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract relevant error details"""
        details = {}
        
        # Add context information
        if context:
            details.update(context)
        
        # Add error-specific details
        if hasattr(error, 'details'):
            details['error_details'] = error.details
        
        if hasattr(error, 'field'):
            details['field'] = error.field
        
        if hasattr(error, 'code'):
            details['error_code'] = error.code
        
        # Add HTTP status if available
        if hasattr(error, 'status_code'):
            details['status_code'] = error.status_code
        
        return details
    
    def _get_safe_stack_trace(self, error: Exception) -> Optional[str]:
        """Get stack trace safely (sanitized for production)"""
        try:
            # In production, you might want to limit stack trace details
            # or exclude certain sensitive information
            stack_trace = traceback.format_exc()
            
            # Sanitize stack trace (remove sensitive paths, etc.)
            # This is a simple example - you might want more sophisticated sanitization
            sanitized = stack_trace.replace('/opt/app/', '/app/')
            
            return sanitized
        except Exception:
            return None
    
    def _get_suggested_actions(self, category: ErrorCategory, protocol: ProtocolType) -> List[str]:
        """Get suggested actions based on error category"""
        suggestions = []
        
        if category == ErrorCategory.AUTHENTICATION_FAILED:
            suggestions.extend([
                "Check authentication credentials",
                "Verify token validity",
                "Contact system administrator if issue persists"
            ])
        elif category == ErrorCategory.AUTHORIZATION_DENIED:
            suggestions.extend([
                "Verify user permissions",
                "Check required scopes/roles",
                "Contact administrator for access"
            ])
        elif category == ErrorCategory.INVALID_INPUT:
            suggestions.extend([
                "Review input parameters",
                "Check data format requirements",
                "Refer to API documentation"
            ])
        elif category == ErrorCategory.PAYMENT_FAILED:
            suggestions.extend([
                "Verify payment method",
                "Check account balance",
                "Contact payment provider"
            ])
        elif category == ErrorCategory.TASK_EXECUTION_FAILED:
            suggestions.extend([
                "Check task parameters",
                "Verify agent capabilities",
                "Retry with different parameters"
            ])
        elif category == ErrorCategory.SERVICE_UNAVAILABLE:
            suggestions.extend([
                "Retry after a short delay",
                "Check service status",
                "Contact support if issue persists"
            ])
        elif category == ErrorCategory.RATE_LIMIT_EXCEEDED:
            suggestions.extend([
                "Wait before retrying",
                "Reduce request frequency",
                "Consider upgrading rate limits"
            ])
        else:
            suggestions.extend([
                "Retry the operation",
                "Check system status",
                "Contact support if issue persists"
            ])
        
        return suggestions
    
    def _log_error(self, error: UnifiedError):
        """Log error with appropriate level"""
        log_message = f"[{error.protocol.value}] {error.category.value}: {error.message}"
        log_context = {
            "error_id": error.error_id,
            "protocol": error.protocol.value,
            "category": error.category.value,
            "severity": error.severity.value,
            "details": error.details
        }
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=log_context)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=log_context)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=log_context)
        else:
            logger.info(log_message, extra=log_context)
    
    def _record_error(self, error: UnifiedError):
        """Record error in history and update counts"""
        # Add to history
        self._error_history.append(error)
        
        # Maintain history size
        if len(self._error_history) > self._max_history_size:
            self._error_history = self._error_history[-self._max_history_size:]
        
        # Update error counts
        error_key = f"{error.protocol.value}:{error.category.value}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
    
    def create_http_exception(self, unified_error: UnifiedError) -> HTTPException:
        """Convert unified error to HTTP exception"""
        # Map severity to HTTP status codes
        status_mapping = {
            ErrorSeverity.LOW: status.HTTP_400_BAD_REQUEST,
            ErrorSeverity.MEDIUM: status.HTTP_400_BAD_REQUEST,
            ErrorSeverity.HIGH: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorSeverity.CRITICAL: status.HTTP_500_INTERNAL_SERVER_ERROR
        }
        
        # Special cases for specific categories
        if unified_error.category == ErrorCategory.AUTHENTICATION_FAILED:
            http_status = status.HTTP_401_UNAUTHORIZED
        elif unified_error.category == ErrorCategory.AUTHORIZATION_DENIED:
            http_status = status.HTTP_403_FORBIDDEN
        elif unified_error.category == ErrorCategory.RESOURCE_NOT_FOUND:
            http_status = status.HTTP_404_NOT_FOUND
        elif unified_error.category == ErrorCategory.RATE_LIMIT_EXCEEDED:
            http_status = status.HTTP_429_TOO_MANY_REQUESTS
        elif unified_error.category == ErrorCategory.SERVICE_UNAVAILABLE:
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            http_status = status_mapping.get(unified_error.severity, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create error response
        error_response = {
            "error": {
                "id": unified_error.error_id,
                "protocol": unified_error.protocol.value,
                "category": unified_error.category.value,
                "message": unified_error.message,
                "suggested_actions": unified_error.suggested_actions
            }
        }
        
        return HTTPException(
            status_code=http_status,
            detail=error_response
        )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        return {
            "total_errors": len(self._error_history),
            "error_counts_by_category": self._error_counts.copy(),
            "recent_errors": [
                error.to_dict() for error in self._error_history[-10:]
            ],
            "severity_distribution": self._get_severity_distribution(),
            "protocol_distribution": self._get_protocol_distribution()
        }
    
    def _get_severity_distribution(self) -> Dict[str, int]:
        """Get distribution of errors by severity"""
        distribution = {}
        for error in self._error_history:
            severity = error.severity.value
            distribution[severity] = distribution.get(severity, 0) + 1
        return distribution
    
    def _get_protocol_distribution(self) -> Dict[str, int]:
        """Get distribution of errors by protocol"""
        distribution = {}
        for error in self._error_history:
            protocol = error.protocol.value
            distribution[protocol] = distribution.get(protocol, 0) + 1
        return distribution
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent errors"""
        return [
            error.to_dict() for error in self._error_history[-limit:]
        ]


# Global unified error handler instance
_unified_error_handler: Optional[UnifiedErrorHandler] = None


def get_unified_error_handler() -> UnifiedErrorHandler:
    """Get global unified error handler instance"""
    global _unified_error_handler
    if _unified_error_handler is None:
        _unified_error_handler = UnifiedErrorHandler()
    return _unified_error_handler


# Convenience functions for protocol-specific error handling

def handle_a2a_error(
    error: Exception, 
    context: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Handle A2A protocol errors"""
    handler = get_unified_error_handler()
    unified_error = handler.handle_error(error, ProtocolType.A2A, context, user_context)
    return handler.create_http_exception(unified_error)


def handle_ap2_error(
    error: Exception, 
    context: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Handle AP2 protocol errors"""
    handler = get_unified_error_handler()
    unified_error = handler.handle_error(error, ProtocolType.AP2, context, user_context)
    return handler.create_http_exception(unified_error)


def handle_mcp_error(
    error: Exception, 
    context: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Handle MCP protocol errors"""
    handler = get_unified_error_handler()
    unified_error = handler.handle_error(error, ProtocolType.MCP, context, user_context)
    return handler.create_http_exception(unified_error)


def handle_cross_protocol_error(
    error: Exception, 
    context: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Handle cross-protocol errors"""
    handler = get_unified_error_handler()
    unified_error = handler.handle_error(error, ProtocolType.CROSS_PROTOCOL, context, user_context)
    return handler.create_http_exception(unified_error)


if __name__ == "__main__":
    # Example usage
    handler = get_unified_error_handler()
    
    # Example A2A error
    try:
        raise Exception("Agent not found: agent_123")
    except Exception as e:
        http_exception = handle_a2a_error(e, {"agent_id": "agent_123"})
        print(f"A2A Error: {http_exception.status_code} - {http_exception.detail}")
    
    # Example AP2 error
    try:
        raise Exception("Payment failed: insufficient funds")
    except Exception as e:
        http_exception = handle_ap2_error(e, {"payment_id": "pay_123", "amount": 100.0})
        print(f"AP2 Error: {http_exception.status_code} - {http_exception.detail}")
    
    # Example MCP error
    try:
        raise Exception("Resource not found: availability://hotel-123")
    except Exception as e:
        http_exception = handle_mcp_error(e, {"resource_uri": "availability://hotel-123"})
        print(f"MCP Error: {http_exception.status_code} - {http_exception.detail}")
    
    # Get statistics
    stats = handler.get_error_statistics()
    print(f"Error Statistics: {json.dumps(stats, indent=2)}")
