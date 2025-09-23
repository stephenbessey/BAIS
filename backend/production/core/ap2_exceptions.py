"""
AP2 Protocol Specific Exceptions
Custom exception classes for AP2 payment protocol errors
"""

from typing import Optional, Dict, Any
from .exceptions import BAISException


class AP2Exception(BAISException):
    """Base exception for all AP2-related errors"""
    pass


class AP2MandateCreationError(AP2Exception):
    """Raised when AP2 mandate creation fails"""
    
    def __init__(
        self, 
        message: str, 
        mandate_type: Optional[str] = None,
        business_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.mandate_type = mandate_type
        self.business_id = business_id


class AP2MandateValidationError(AP2Exception):
    """Raised when AP2 mandate validation fails"""
    
    def __init__(
        self, 
        message: str, 
        mandate_id: Optional[str] = None,
        validation_field: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.mandate_id = mandate_id
        self.validation_field = validation_field


class AP2TransactionError(AP2Exception):
    """Raised when AP2 transaction processing fails"""
    
    def __init__(
        self, 
        message: str, 
        transaction_id: Optional[str] = None,
        payment_method: Optional[str] = None,
        amount: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.transaction_id = transaction_id
        self.payment_method = payment_method
        self.amount = amount


class AP2PaymentWorkflowError(AP2Exception):
    """Raised when AP2 payment workflow fails"""
    
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


class AP2WebhookValidationError(AP2Exception):
    """Raised when AP2 webhook validation fails"""
    
    def __init__(
        self, 
        message: str, 
        webhook_type: Optional[str] = None,
        signature: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.webhook_type = webhook_type
        self.signature = signature


class AP2NetworkError(AP2Exception):
    """Raised when AP2 network communication fails"""
    
    def __init__(
        self, 
        message: str, 
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.endpoint = endpoint
        self.status_code = status_code


class AP2CryptographicError(AP2Exception):
    """Raised when AP2 cryptographic operations fail"""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        algorithm: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.operation = operation
        self.algorithm = algorithm
