"""
Enhanced Error Handling for A2A and AP2 Protocols
Implements Clean Code error handling with structured logging
"""

import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from pydantic import BaseModel


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    BUSINESS_LOGIC = "business_logic"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Error context for comprehensive error tracking"""
    timestamp: datetime
    request_id: str
    user_id: Optional[str] = None
    business_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    protocol: Optional[str] = None  # 'a2a' or 'ap2'
    task_id: Optional[str] = None
    mandate_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class ProtocolError(Exception):
    """Base protocol error with enhanced context"""
    
    def __init__(self, 
                 message: str, 
                 category: ErrorCategory,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 context: Optional[ErrorContext] = None,
                 cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context
        self.cause = cause
        self.error_id = self._generate_error_id()
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID"""
        import uuid
        return f"ERR_{uuid.uuid4().hex[:8].upper()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging"""
        return {
            "error_id": self.error_id,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": asdict(self.context) if self.context else None,
            "cause": str(self.cause) if self.cause else None,
            "traceback": traceback.format_exc() if self.cause else None
        }


class A2AError(ProtocolError):
    """A2A protocol specific errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)
        if self.context:
            self.context.protocol = "a2a"


class A2ATaskError(A2AError):
    """A2A task execution errors"""
    
    def __init__(self, message: str, task_id: str, **kwargs):
        super().__init__(message, category=ErrorCategory.BUSINESS_LOGIC, **kwargs)
        if self.context:
            self.context.task_id = task_id


class A2ADiscoveryError(A2AError):
    """A2A agent discovery errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class AP2Error(ProtocolError):
    """AP2 protocol specific errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)
        if self.context:
            self.context.protocol = "ap2"


class AP2AuthenticationError(AP2Error):
    """AP2 authentication errors"""
    
    def __init__(self, message: str, mandate_id: str = None, **kwargs):
        super().__init__(message, category=ErrorCategory.AUTHENTICATION, 
                        severity=ErrorSeverity.HIGH, **kwargs)
        if self.context and mandate_id:
            self.context.mandate_id = mandate_id


class AP2PaymentError(AP2Error):
    """AP2 payment processing errors"""
    
    def __init__(self, message: str, transaction_id: str = None, **kwargs):
        super().__init__(message, category=ErrorCategory.BUSINESS_LOGIC,
                        severity=ErrorSeverity.HIGH, **kwargs)
        if self.context:
            self.context.additional_data = {
                "transaction_id": transaction_id
            }


class StructuredLogger:
    """Structured logger for protocol operations"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup structured logging format"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_protocol_operation(self, 
                             protocol: str,
                             operation: str, 
                             status: str,
                             context: Dict[str, Any] = None):
        """Log protocol operation with structured data"""
        log_data = {
            "protocol": protocol,
            "operation": operation,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            **(context or {})
        }
        
        self.logger.info(f"Protocol operation: {operation}", extra=log_data)
    
    def log_error(self, error: ProtocolError):
        """Log protocol error with full context"""
        error_data = error.to_dict()
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error: {error.message}", extra=error_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error: {error.message}", extra=error_data)
        else:
            self.logger.warning(f"Error: {error.message}", extra=error_data)
    
    def log_a2a_task(self, task_id: str, status: str, details: Dict[str, Any] = None):
        """Log A2A task lifecycle events"""
        self.log_protocol_operation(
            protocol="a2a",
            operation="task_execution",
            status=status,
            context={
                "task_id": task_id,
                **(details or {})
            }
        )
    
    def log_ap2_payment(self, mandate_id: str, status: str, details: Dict[str, Any] = None):
        """Log AP2 payment lifecycle events"""
        self.log_protocol_operation(
            protocol="ap2", 
            operation="payment_processing",
            status=status,
            context={
                "mandate_id": mandate_id,
                **(details or {})
            }
        )


class ErrorHandler:
    """Centralized error handler for protocols"""
    
    def __init__(self):
        self.logger = StructuredLogger("protocol_error_handler")
    
    def handle_a2a_error(self, error: A2AError) -> Dict[str, Any]:
        """Handle A2A protocol errors"""
        self.logger.log_error(error)
        
        return {
            "error_id": error.error_id,
            "message": self._get_user_friendly_message(error),
            "category": error.category.value,
            "protocol": "a2a"
        }
    
    def handle_ap2_error(self, error: AP2Error) -> Dict[str, Any]:
        """Handle AP2 protocol errors"""
        self.logger.log_error(error)
        
        return {
            "error_id": error.error_id,
            "message": self._get_user_friendly_message(error),
            "category": error.category.value,
            "protocol": "ap2"
        }
    
    def _get_user_friendly_message(self, error: ProtocolError) -> str:
        """Convert technical errors to user-friendly messages"""
        category_messages = {
            ErrorCategory.VALIDATION: "Invalid request data provided",
            ErrorCategory.AUTHENTICATION: "Authentication failed",
            ErrorCategory.AUTHORIZATION: "Access denied",
            ErrorCategory.NETWORK: "Network communication error",
            ErrorCategory.BUSINESS_LOGIC: "Business rule validation failed",
            ErrorCategory.CONFIGURATION: "System configuration error",
            ErrorCategory.SYSTEM: "Internal system error"
        }
        
        return category_messages.get(error.category, "An unexpected error occurred")


# Usage examples
def example_a2a_error_handling():
    """Example of using enhanced A2A error handling"""
    logger = StructuredLogger("a2a_service")
    error_handler = ErrorHandler()
    
    try:
        # Simulate A2A task execution
        logger.log_a2a_task("task_123", "started", {"operation": "hotel_search"})
        
        # Simulate error
        raise A2ATaskError(
            "Hotel service unavailable",
            task_id="task_123",
            severity=ErrorSeverity.HIGH,
            context=ErrorContext(
                timestamp=datetime.utcnow(),
                request_id="req_456",
                endpoint="/a2a/v1/tasks"
            )
        )
        
    except A2ATaskError as e:
        error_response = error_handler.handle_a2a_error(e)
        logger.log_a2a_task("task_123", "failed", {"error_id": e.error_id})
        return error_response


def example_ap2_error_handling():
    """Example of using enhanced AP2 error handling"""
    logger = StructuredLogger("ap2_service")
    error_handler = ErrorHandler()
    
    try:
        # Simulate AP2 payment
        logger.log_ap2_payment("mandate_789", "initiated", {"amount": 150.00})
        
        # Simulate authentication error
        raise AP2AuthenticationError(
            "Invalid mandate signature",
            mandate_id="mandate_789",
            context=ErrorContext(
                timestamp=datetime.utcnow(),
                request_id="req_101",
                business_id="business_202",
                endpoint="/ap2/v1/payments"
            )
        )
        
    except AP2AuthenticationError as e:
        error_response = error_handler.handle_ap2_error(e)
        logger.log_ap2_payment("mandate_789", "failed", {"error_id": e.error_id})
        return error_response
