"""
Secure Logging Module
Provides structured logging without sensitive data exposure
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class LogContext:
    """Logging context information"""
    user_id: Optional[str] = None
    business_id: Optional[str] = None
    workflow_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    session_id: Optional[str] = None


class SensitiveDataMasker:
    """Masks sensitive data in log messages"""
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = [
        (r'password["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'password="***"'),
        (r'api_key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'api_key="***"'),
        (r'token["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'token="***"'),
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'secret="***"'),
        (r'credit_card["\']?\s*[:=]\s*["\']?(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})', r'credit_card="****-****-****-****"'),
        (r'card_number["\']?\s*[:=]\s*["\']?(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})', r'card_number="****-****-****-****"'),
        (r'ssn["\']?\s*[:=]\s*["\']?(\d{3}-?\d{2}-?\d{4})', r'ssn="***-**-****"'),
        (r'email["\']?\s*[:=]\s*["\']?([^"\'\\s@]+@[^"\'\\s@]+)', r'email="***@***.***"'),
    ]
    
    @classmethod
    def mask_sensitive_data(cls, message: str) -> str:
        """Mask sensitive data in a log message"""
        masked_message = message
        
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            masked_message = re.sub(pattern, replacement, masked_message, flags=re.IGNORECASE)
        
        return masked_message
    
    @classmethod
    def mask_dict_values(cls, data: Dict[str, Any], sensitive_keys: List[str] = None) -> Dict[str, Any]:
        """Mask sensitive values in a dictionary"""
        if sensitive_keys is None:
            sensitive_keys = ['password', 'api_key', 'token', 'secret', 'credit_card', 'ssn', 'email']
        
        masked_data = {}
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    masked_data[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                else:
                    masked_data[key] = "***"
            elif isinstance(value, dict):
                masked_data[key] = cls.mask_dict_values(value, sensitive_keys)
            elif isinstance(value, list):
                masked_data[key] = [
                    cls.mask_dict_values(item, sensitive_keys) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked_data[key] = value
        
        return masked_data


class SecureFormatter(logging.Formatter):
    """Custom formatter that masks sensitive data"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sensitive data masking"""
        # Mask sensitive data in the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = SensitiveDataMasker.mask_sensitive_data(record.msg)
        
        # Mask sensitive data in extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                              'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process', 'getMessage', 'exc_info',
                              'exc_text', 'stack_info']:
                    if isinstance(value, str):
                        record.__dict__[key] = SensitiveDataMasker.mask_sensitive_data(value)
                    elif isinstance(value, dict):
                        record.__dict__[key] = SensitiveDataMasker.mask_dict_values(value)
        
        return super().format(record)


class SecureLogger:
    """Secure logger with structured logging and context"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Add secure formatter if not already present
        if not any(isinstance(handler.formatter, SecureFormatter) for handler in self.logger.handlers):
            handler = logging.StreamHandler()
            formatter = SecureFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(context)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _prepare_context(self, context: Optional[LogContext] = None, **kwargs) -> str:
        """Prepare logging context"""
        if context is None:
            context = LogContext()
        
        # Add any additional context from kwargs
        context_dict = asdict(context)
        context_dict.update({k: v for k, v in kwargs.items() if v is not None})
        
        return json.dumps(context_dict, default=str)
    
    def _log_with_context(self, level: int, message: str, context: Optional[LogContext] = None, 
                         exc_info: Optional[Any] = None, **kwargs) -> None:
        """Log message with context"""
        context_str = self._prepare_context(context, **kwargs)
        
        self.logger.log(
            level,
            message,
            extra={'context': context_str},
            exc_info=exc_info
        )
    
    def info(self, message: str, context: Optional[LogContext] = None, **kwargs) -> None:
        """Log info message with context"""
        self._log_with_context(logging.INFO, message, context, **kwargs)
    
    def warning(self, message: str, context: Optional[LogContext] = None, **kwargs) -> None:
        """Log warning message with context"""
        self._log_with_context(logging.WARNING, message, context, **kwargs)
    
    def error(self, message: str, context: Optional[LogContext] = None, 
              exc_info: Optional[Any] = None, **kwargs) -> None:
        """Log error message with context"""
        self._log_with_context(logging.ERROR, message, context, exc_info=exc_info, **kwargs)
    
    def debug(self, message: str, context: Optional[LogContext] = None, **kwargs) -> None:
        """Log debug message with context"""
        self._log_with_context(logging.DEBUG, message, context, **kwargs)
    
    def critical(self, message: str, context: Optional[LogContext] = None, 
                 exc_info: Optional[Any] = None, **kwargs) -> None:
        """Log critical message with context"""
        self._log_with_context(logging.CRITICAL, message, context, exc_info=exc_info, **kwargs)


# Global secure logger instances
_payment_logger: Optional[SecureLogger] = None
_a2a_logger: Optional[SecureLogger] = None
_webhook_logger: Optional[SecureLogger] = None
_business_logger: Optional[SecureLogger] = None


def get_payment_logger() -> SecureLogger:
    """Get secure logger for payment operations"""
    global _payment_logger
    if _payment_logger is None:
        _payment_logger = SecureLogger('bais.payments')
    return _payment_logger


def get_a2a_logger() -> SecureLogger:
    """Get secure logger for A2A operations"""
    global _a2a_logger
    if _a2a_logger is None:
        _a2a_logger = SecureLogger('bais.a2a')
    return _a2a_logger


def get_webhook_logger() -> SecureLogger:
    """Get secure logger for webhook operations"""
    global _webhook_logger
    if _webhook_logger is None:
        _webhook_logger = SecureLogger('bais.webhooks')
    return _webhook_logger


def get_business_logger() -> SecureLogger:
    """Get secure logger for business operations"""
    global _business_logger
    if _business_logger is None:
        _business_logger = SecureLogger('bais.business')
    return _business_logger


# Convenience functions for common logging scenarios
def log_payment_event(event_type: str, workflow_id: str, business_id: str = None, 
                     user_id: str = None, amount: float = None, **kwargs) -> None:
    """Log payment-related events securely"""
    context = LogContext(
        workflow_id=workflow_id,
        business_id=business_id,
        user_id=user_id
    )
    
    logger = get_payment_logger()
    logger.info(f"Payment event: {event_type}", context=context, amount=amount, **kwargs)


def log_a2a_event(event_type: str, task_id: str, agent_id: str = None, 
                 business_id: str = None, **kwargs) -> None:
    """Log A2A-related events securely"""
    context = LogContext(
        workflow_id=task_id,
        business_id=business_id
    )
    
    logger = get_a2a_logger()
    logger.info(f"A2A event: {event_type}", context=context, agent_id=agent_id, **kwargs)


def log_webhook_event(event_type: str, webhook_id: str, business_id: str = None, 
                     signature_hash: str = None, **kwargs) -> None:
    """Log webhook-related events securely"""
    context = LogContext(
        workflow_id=webhook_id,
        business_id=business_id
    )
    
    logger = get_webhook_logger()
    logger.info(f"Webhook event: {event_type}", context=context, 
               signature_hash=signature_hash, **kwargs)


def log_business_event(event_type: str, business_id: str, user_id: str = None, **kwargs) -> None:
    """Log business-related events securely"""
    context = LogContext(
        business_id=business_id,
        user_id=user_id
    )
    
    logger = get_business_logger()
    logger.info(f"Business event: {event_type}", context=context, **kwargs)
