"""
Security Audit Logger - Clean Code Implementation
Comprehensive audit logging for security events following Clean Code principles
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

from .constants import LoggingLimits


class AuditEventType(Enum):
    """Audit event types for security monitoring"""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_ATTEMPT = "auth_attempt"
    TOKEN_CREATED = "token_created"
    TOKEN_REVOKED = "token_revoked"
    TOKEN_EXPIRED = "token_expired"
    
    MANDATE_CREATED = "mandate_created"
    MANDATE_SIGNED = "mandate_signed"
    MANDATE_VERIFIED = "mandate_verified"
    MANDATE_REVOKED = "mandate_revoked"
    MANDATE_EXPIRED = "mandate_expired"
    
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_CANCELLED = "payment_cancelled"
    
    RESOURCE_ACCESS = "resource_access"
    RESOURCE_MODIFIED = "resource_modified"
    RESOURCE_DELETED = "resource_deleted"
    
    TOOL_EXECUTION = "tool_execution"
    TOOL_EXECUTION_SUCCESS = "tool_execution_success"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    
    ADMIN_ACTION = "admin_action"
    CONFIGURATION_CHANGE = "configuration_change"
    USER_PERMISSION_CHANGE = "user_permission_change"
    
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    
    API_ACCESS = "api_access"
    API_ERROR = "api_error"
    
    SYSTEM_EVENT = "system_event"
    SYSTEM_ERROR = "system_error"


class AuditEventSeverity(Enum):
    """Audit event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_id: str
    event_type: AuditEventType
    severity: AuditEventSeverity
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    client_ip: Optional[str]
    user_agent: Optional[str]
    action: str
    resource: str
    resource_id: Optional[str]
    status: str
    message: str
    metadata: Dict[str, Any]
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


class SecurityAuditLogger:
    """
    Security audit logger following Clean Code principles
    Logs all security-relevant events for compliance and forensics
    """
    
    def __init__(self, log_file: Optional[str] = None):
        self._setup_logger(log_file or self._get_default_log_file())
        self._event_count = 0
        self._max_events_per_day = 100000  # Prevent log flooding
    
    def _setup_logger(self, log_file: str):
        """Setup audit logger with proper configuration"""
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # File handler for audit logs
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # JSON formatter for structured logging
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        
        # Console handler for critical events
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(console_handler)
        
        self.log_file = log_file
    
    def _get_default_log_file(self) -> str:
        """Get default log file path"""
        # Try to use system log directory, fallback to local
        log_paths = [
            "/var/log/bais/security_audit.log",
            "logs/security_audit.log",
            "security_audit.log"
        ]
        
        for path in log_paths:
            log_dir = os.path.dirname(path)
            if log_dir and os.path.exists(log_dir):
                return path
        
        # Use current directory if no log directory exists
        return "security_audit.log"
    
    def _should_log_event(self) -> bool:
        """Check if we should log the event (rate limiting)"""
        # Simple rate limiting - in production, use more sophisticated approach
        return self._event_count < self._max_events_per_day
    
    def _create_audit_event(
        self,
        event_type: AuditEventType,
        severity: AuditEventSeverity,
        user_id: Optional[str],
        session_id: Optional[str],
        client_ip: Optional[str],
        user_agent: Optional[str],
        action: str,
        resource: str,
        resource_id: Optional[str],
        status: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> AuditEvent:
        """Create audit event with proper validation"""
        
        # Validate message length
        if len(message) > LoggingLimits.MAX_AUDIT_EVENT_SIZE_BYTES:
            message = message[:LoggingLimits.MAX_AUDIT_EVENT_SIZE_BYTES - 50] + "... [truncated]"
        
        # Validate metadata
        if metadata and len(str(metadata)) > LoggingLimits.MAX_AUDIT_EVENT_SIZE_BYTES:
            metadata = {"error": "metadata_too_large"}
        
        return AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            action=action,
            resource=resource,
            resource_id=resource_id,
            status=status,
            message=message,
            metadata=metadata or {},
            correlation_id=correlation_id
        )
    
    def _log_event(self, event: AuditEvent):
        """Log audit event with proper formatting"""
        if not self._should_log_event():
            self.logger.warning("Audit log rate limit exceeded, dropping event")
            return
        
        try:
            # Convert to JSON and log
            event_json = json.dumps(event.to_dict(), ensure_ascii=False)
            self.logger.info(event_json)
            self._event_count += 1
            
            # Log critical events to console as well
            if event.severity == AuditEventSeverity.CRITICAL:
                self.logger.critical(f"CRITICAL SECURITY EVENT: {event.action} - {event.message}")
                
        except Exception as e:
            # Fallback logging for audit logger errors
            fallback_msg = f"AUDIT_LOGGER_ERROR: Failed to log event - {str(e)}"
            self.logger.error(fallback_msg)
    
    def log_auth_success(
        self,
        user_id: str,
        method: str,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log successful authentication"""
        event = self._create_audit_event(
            event_type=AuditEventType.AUTH_SUCCESS,
            severity=AuditEventSeverity.INFO,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            action="authenticate",
            resource="auth_endpoint",
            resource_id=None,
            status="success",
            message=f"User {user_id} authenticated successfully via {method}",
            metadata={"method": method, **(metadata or {})}
        )
        self._log_event(event)
    
    def log_auth_failure(
        self,
        user_id: str,
        method: str,
        reason: str,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log failed authentication"""
        severity = AuditEventSeverity.WARNING
        if "brute_force" in reason.lower() or "rate_limit" in reason.lower():
            severity = AuditEventSeverity.ERROR
        
        event = self._create_audit_event(
            event_type=AuditEventType.AUTH_FAILURE,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            action="authenticate",
            resource="auth_endpoint",
            resource_id=None,
            status="failure",
            message=f"Authentication failed for user {user_id} via {method}: {reason}",
            metadata={"method": method, "reason": reason, **(metadata or {})}
        )
        self._log_event(event)
    
    def log_token_created(
        self,
        user_id: str,
        token_type: str,
        expires_at: datetime,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log token creation"""
        event = self._create_audit_event(
            event_type=AuditEventType.TOKEN_CREATED,
            severity=AuditEventSeverity.INFO,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=None,
            action="token_create",
            resource="token_service",
            resource_id=token_type,
            status="success",
            message=f"Token created for user {user_id}, type: {token_type}",
            metadata={"token_type": token_type, "expires_at": expires_at.isoformat(), **(metadata or {})}
        )
        self._log_event(event)
    
    def log_payment_event(
        self,
        event_type: AuditEventType,
        payment_id: str,
        user_id: str,
        amount: float,
        currency: str,
        status: str,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log payment-related event"""
        severity_map = {
            AuditEventType.PAYMENT_COMPLETED: AuditEventSeverity.INFO,
            AuditEventType.PAYMENT_FAILED: AuditEventSeverity.ERROR,
            AuditEventType.PAYMENT_INITIATED: AuditEventSeverity.INFO,
            AuditEventType.PAYMENT_CANCELLED: AuditEventSeverity.WARNING
        }
        
        event = self._create_audit_event(
            event_type=event_type,
            severity=severity_map.get(event_type, AuditEventSeverity.INFO),
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=None,
            action="payment_processing",
            resource=f"payment/{payment_id}",
            resource_id=payment_id,
            status=status,
            message=f"Payment {event_type.value}: {payment_id} for user {user_id}, amount: {amount} {currency}",
            metadata={"payment_id": payment_id, "amount": amount, "currency": currency, **(metadata or {})}
        )
        self._log_event(event)
    
    def log_mandate_event(
        self,
        event_type: AuditEventType,
        mandate_id: str,
        user_id: str,
        mandate_type: str,
        amount: float,
        currency: str,
        status: str,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log mandate-related event"""
        severity_map = {
            AuditEventType.MANDATE_CREATED: AuditEventSeverity.INFO,
            AuditEventType.MANDATE_SIGNED: AuditEventSeverity.INFO,
            AuditEventType.MANDATE_VERIFIED: AuditEventSeverity.INFO,
            AuditEventType.MANDATE_REVOKED: AuditEventSeverity.WARNING,
            AuditEventType.MANDATE_EXPIRED: AuditEventSeverity.WARNING
        }
        
        event = self._create_audit_event(
            event_type=event_type,
            severity=severity_map.get(event_type, AuditEventSeverity.INFO),
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=None,
            action="mandate_processing",
            resource=f"mandate/{mandate_id}",
            resource_id=mandate_id,
            status=status,
            message=f"Mandate {event_type.value}: {mandate_id} for user {user_id}, type: {mandate_type}, amount: {amount} {currency}",
            metadata={"mandate_id": mandate_id, "mandate_type": mandate_type, "amount": amount, "currency": currency, **(metadata or {})}
        )
        self._log_event(event)
    
    def log_security_violation(
        self,
        violation_type: str,
        details: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log security violation"""
        event = self._create_audit_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=AuditEventSeverity.CRITICAL,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            action="security_check",
            resource="security_monitor",
            resource_id=None,
            status="violation_detected",
            message=f"Security violation detected: {violation_type} - {details}",
            metadata={"violation_type": violation_type, "details": details, **(metadata or {})}
        )
        self._log_event(event)
    
    def log_rate_limit_exceeded(
        self,
        user_id: Optional[str],
        endpoint: str,
        limit: int,
        window: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log rate limit exceeded"""
        event = self._create_audit_event(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditEventSeverity.WARNING,
            user_id=user_id,
            session_id=None,
            client_ip=client_ip,
            user_agent=user_agent,
            action="rate_limit_check",
            resource=endpoint,
            resource_id=None,
            status="limit_exceeded",
            message=f"Rate limit exceeded for endpoint {endpoint}: {limit} requests per {window}",
            metadata={"endpoint": endpoint, "limit": limit, "window": window, **(metadata or {})}
        )
        self._log_event(event)
    
    def log_api_access(
        self,
        user_id: Optional[str],
        method: str,
        endpoint: str,
        status_code: int,
        response_time_ms: float,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log API access"""
        severity = AuditEventSeverity.INFO
        if status_code >= 500:
            severity = AuditEventSeverity.ERROR
        elif status_code >= 400:
            severity = AuditEventSeverity.WARNING
        
        event = self._create_audit_event(
            event_type=AuditEventType.API_ACCESS,
            severity=severity,
            user_id=user_id,
            session_id=None,
            client_ip=client_ip,
            user_agent=user_agent,
            action="api_access",
            resource=endpoint,
            resource_id=None,
            status=str(status_code),
            message=f"API access: {method} {endpoint} - {status_code} ({response_time_ms}ms)",
            metadata={"method": method, "status_code": status_code, "response_time_ms": response_time_ms, **(metadata or {})}
        )
        self._log_event(event)
    
    def log_admin_action(
        self,
        admin_user_id: str,
        action: str,
        target_resource: str,
        target_id: Optional[str],
        changes: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log administrative action"""
        event = self._create_audit_event(
            event_type=AuditEventType.ADMIN_ACTION,
            severity=AuditEventSeverity.WARNING,
            user_id=admin_user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=None,
            action=f"admin_{action}",
            resource=target_resource,
            resource_id=target_id,
            status="completed",
            message=f"Admin action: {admin_user_id} performed {action} on {target_resource}",
            metadata={"admin_action": action, "changes": changes or {}, **(metadata or {})}
        )
        self._log_event(event)
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics"""
        try:
            # Count events by type (simplified - in production, use proper log analysis)
            stats = {
                "total_events": self._event_count,
                "log_file": self.log_file,
                "max_events_per_day": self._max_events_per_day,
                "events_remaining": max(0, self._max_events_per_day - self._event_count),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            return {"error": f"Failed to get statistics: {str(e)}"}
    
    def clear_event_count(self):
        """Clear daily event count (call at midnight)"""
        self._event_count = 0


# Singleton audit logger instance
_audit_logger: Optional[SecurityAuditLogger] = None


def get_audit_logger(log_file: Optional[str] = None) -> SecurityAuditLogger:
    """Get singleton audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = SecurityAuditLogger(log_file)
    return _audit_logger


# Convenience functions for common audit operations
def log_auth_success(user_id: str, method: str, **kwargs):
    """Log successful authentication"""
    logger = get_audit_logger()
    logger.log_auth_success(user_id, method, **kwargs)


def log_auth_failure(user_id: str, method: str, reason: str, **kwargs):
    """Log failed authentication"""
    logger = get_audit_logger()
    logger.log_auth_failure(user_id, method, reason, **kwargs)


def log_security_violation(violation_type: str, details: str, **kwargs):
    """Log security violation"""
    logger = get_audit_logger()
    logger.log_security_violation(violation_type, details, **kwargs)


def log_rate_limit_exceeded(user_id: Optional[str], endpoint: str, limit: int, window: str, **kwargs):
    """Log rate limit exceeded"""
    logger = get_audit_logger()
    logger.log_rate_limit_exceeded(user_id, endpoint, limit, window, **kwargs)


if __name__ == "__main__":
    # Example usage
    logger = get_audit_logger()
    
    # Log some test events
    logger.log_auth_success("user123", "password", client_ip="192.168.1.1")
    logger.log_auth_failure("hacker123", "password", "invalid_password", client_ip="192.168.1.100")
    logger.log_security_violation("brute_force", "Multiple failed login attempts", user_id="hacker123", client_ip="192.168.1.100")
    logger.log_payment_event(AuditEventType.PAYMENT_COMPLETED, "pay_123", "user123", 150.0, "USD", "completed")
    
    # Get statistics
    stats = logger.get_log_statistics()
    print(f"Audit log statistics: {json.dumps(stats, indent=2)}")
