"""
Structured Logging Configuration for BAIS with AP2 Integration
"""

import logging
import sys
from typing import Dict, Any
import structlog
from pythonjsonlogger import jsonlogger


class AP2PaymentFilter(logging.Filter):
    """Filter to identify AP2 payment-related log entries"""
    
    def filter(self, record):
        # Add AP2 context to payment-related logs
        if hasattr(record, 'pathname') and 'payments' in record.pathname:
            record.component = 'ap2-payments'
        return True


class SecurityEventFilter(logging.Filter):
    """Filter for security-sensitive events"""
    
    def filter(self, record):
        # Mark security-related events
        security_keywords = ['auth', 'webhook', 'signature', 'mandate', 'token']
        if any(keyword in record.getMessage().lower() for keyword in security_keywords):
            record.security_sensitive = True
        return True


def configure_logging(environment: str = "production", log_level: str = "INFO"):
    """Configure structured logging for BAIS with AP2 integration"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if environment == "production" else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    log_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}'
    
    if environment == "development":
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Root logger configuration
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/app/logs/bais-ap2.log') if environment == "production" else logging.NullHandler()
        ]
    )
    
    # Add filters
    root_logger = logging.getLogger()
    root_logger.addFilter(AP2PaymentFilter())
    root_logger.addFilter(SecurityEventFilter())
    
    # Configure specific loggers
    loggers_config = {
        'backend.production.core.payments': {
            'level': 'DEBUG' if environment == "development" else 'INFO',
            'handlers': ['payment_handler'] if environment == "production" else []
        },
        'backend.production.services.payment_service': {
            'level': 'INFO',
            'handlers': ['payment_handler'] if environment == "production" else []
        },
        'ap2_webhook_processor': {
            'level': 'INFO',
            'handlers': ['webhook_handler'] if environment == "production" else []
        },
        'uvicorn.access': {
            'level': 'INFO',
            'handlers': ['access_handler'] if environment == "production" else []
        }
    }
    
    # Create file handlers for production
    if environment == "production":
        handlers = {
            'payment_handler': logging.FileHandler('/app/logs/payments.log'),
            'webhook_handler': logging.FileHandler('/app/logs/webhooks.log'),
            'access_handler': logging.FileHandler('/app/logs/access.log')
        }
        
        # Apply JSON formatter to file handlers
        json_formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d'
        )
        
        for handler_name, handler in handlers.items():
            handler.setFormatter(json_formatter)
            logging.getLogger().addHandler(handler)
    
    # Configure third-party loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    return structlog.get_logger()
