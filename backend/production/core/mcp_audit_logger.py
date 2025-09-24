"""
MCP Audit Logger - Clean Code Implementation
Comprehensive audit logging for security events and compliance
"""

import json
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from pathlib import Path

from .mcp_authentication_service import AuthContext


class AuditEventType(Enum):
    """Types of audit events"""
    AUTHENTICATION_SUCCESS = "auth_success"
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_GRANT = "authz_grant"
    AUTHORIZATION_DENY = "authz_deny"
    TOOL_EXECUTION = "tool_execution"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    RESOURCE_ACCESS = "resource_access"
    RESOURCE_ACCESS_DENIED = "resource_access_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INPUT_VALIDATION_FAILED = "input_validation_failed"
    SECURITY_VIOLATION = "security_violation"
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_CHANGE = "configuration_change"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event structure following Clean Code principles"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    client_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    endpoint: str
    method: str
    status_code: int
    request_size: int
    response_size: int
    processing_time_ms: float
    resource_uri: Optional[str]
    tool_name: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


class AuditStorage:
    """Abstract base class for audit storage implementations"""
    
    async def store_event(self, event: AuditEvent) -> None:
        """Store audit event"""
        raise NotImplementedError
    
    async def query_events(self, filters: Dict[str, Any], limit: int = 100) -> List[AuditEvent]:
        """Query audit events with filters"""
        raise NotImplementedError
    
    async def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Get specific audit event by ID"""
        raise NotImplementedError


class FileAuditStorage(AuditStorage):
    """File-based audit storage implementation"""
    
    def __init__(self, log_directory: str = "/var/log/bais/audit"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self._current_file = None
        self._file_lock = asyncio.Lock()
    
    async def store_event(self, event: AuditEvent) -> None:
        """Store audit event to file"""
        async with self._file_lock:
            # Rotate file daily
            await self._ensure_current_file()
            
            # Write event as JSON line
            event_json = json.dumps(event.to_dict(), ensure_ascii=False)
            self._current_file.write(event_json + '\n')
            self._current_file.flush()
    
    async def _ensure_current_file(self):
        """Ensure current log file is open and correct"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_directory / f"audit-{today}.log"
        
        if self._current_file is None or self._current_file.name != str(log_file):
            if self._current_file:
                self._current_file.close()
            
            self._current_file = open(log_file, 'a', encoding='utf-8')
    
    async def query_events(self, filters: Dict[str, Any], limit: int = 100) -> List[AuditEvent]:
        """Query audit events from files"""
        # This is a simplified implementation
        # In production, you'd use a proper database or search engine
        events = []
        
        # Read from today's log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_directory / f"audit-{today}.log"
        
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())
                        event = self._dict_to_event(event_data)
                        
                        # Apply filters
                        if self._matches_filters(event, filters):
                            events.append(event)
                            
                            if len(events) >= limit:
                                break
                    except (json.JSONDecodeError, KeyError):
                        continue  # Skip malformed entries
        
        return events
    
    async def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Get specific audit event by ID"""
        # Search through recent log files
        for days_back in range(7):  # Search last 7 days
            date = datetime.now().date() - timedelta(days=days_back)
            log_file = self.log_directory / f"audit-{date.strftime('%Y-%m-%d')}.log"
            
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            if event_data.get('event_id') == event_id:
                                return self._dict_to_event(event_data)
                        except (json.JSONDecodeError, KeyError):
                            continue
        
        return None
    
    def _dict_to_event(self, data: Dict[str, Any]) -> AuditEvent:
        """Convert dictionary to AuditEvent"""
        return AuditEvent(
            event_id=data['event_id'],
            event_type=AuditEventType(data['event_type']),
            severity=AuditSeverity(data['severity']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            user_id=data.get('user_id'),
            client_id=data.get('client_id'),
            session_id=data.get('session_id'),
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent'),
            endpoint=data['endpoint'],
            method=data['method'],
            status_code=data['status_code'],
            request_size=data['request_size'],
            response_size=data['response_size'],
            processing_time_ms=data['processing_time_ms'],
            resource_uri=data.get('resource_uri'),
            tool_name=data.get('tool_name'),
            error_code=data.get('error_code'),
            error_message=data.get('error_message'),
            metadata=data.get('metadata', {})
        )
    
    def _matches_filters(self, event: AuditEvent, filters: Dict[str, Any]) -> bool:
        """Check if event matches filters"""
        for key, value in filters.items():
            if key == 'event_type' and event.event_type != AuditEventType(value):
                return False
            elif key == 'severity' and event.severity != AuditSeverity(value):
                return False
            elif key == 'user_id' and event.user_id != value:
                return False
            elif key == 'start_time' and event.timestamp < value:
                return False
            elif key == 'end_time' and event.timestamp > value:
                return False
        
        return True


class MCPAuditLogger:
    """Main audit logger for MCP operations following Clean Code principles"""
    
    def __init__(self, storage: AuditStorage, logger: logging.Logger):
        self._storage = storage
        self._logger = logger
        self._event_queue = asyncio.Queue(maxsize=1000)
        self._processing_task = None
        self._start_processing_task()
    
    def _start_processing_task(self):
        """Start background task for processing audit events"""
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._process_events())
    
    async def _process_events(self):
        """Background task to process audit events"""
        while True:
            try:
                event = await self._event_queue.get()
                await self._storage.store_event(event)
                self._event_queue.task_done()
            except Exception as e:
                self._logger.error(f"Error processing audit event: {e}")
    
    async def log_authentication_success(
        self,
        auth_context: AuthContext,
        request_info: Dict[str, Any]
    ) -> None:
        """Log successful authentication"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.AUTHENTICATION_SUCCESS,
            severity=AuditSeverity.LOW,
            timestamp=datetime.now(timezone.utc),
            user_id=auth_context.user_id,
            client_id=auth_context.client_id,
            session_id=None,  # Would be extracted from request
            ip_address=request_info.get('ip_address'),
            user_agent=request_info.get('user_agent'),
            endpoint=request_info.get('endpoint', ''),
            method=request_info.get('method', ''),
            status_code=200,
            request_size=request_info.get('request_size', 0),
            response_size=request_info.get('response_size', 0),
            processing_time_ms=request_info.get('processing_time_ms', 0),
            resource_uri=auth_context.resource_uri,
            tool_name=None,
            error_code=None,
            error_message=None,
            metadata={
                'scopes': auth_context.scopes,
                'audience': auth_context.audience,
                'issuer': auth_context.issuer
            }
        )
        
        await self._queue_event(event)
    
    async def log_authentication_failure(
        self,
        error_message: str,
        request_info: Dict[str, Any]
    ) -> None:
        """Log failed authentication"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.AUTHENTICATION_FAILURE,
            severity=AuditSeverity.MEDIUM,
            timestamp=datetime.now(timezone.utc),
            user_id=None,
            client_id=None,
            session_id=None,
            ip_address=request_info.get('ip_address'),
            user_agent=request_info.get('user_agent'),
            endpoint=request_info.get('endpoint', ''),
            method=request_info.get('method', ''),
            status_code=401,
            request_size=request_info.get('request_size', 0),
            response_size=request_info.get('response_size', 0),
            processing_time_ms=request_info.get('processing_time_ms', 0),
            resource_uri=None,
            tool_name=None,
            error_code='AUTH_FAILED',
            error_message=error_message,
            metadata={
                'attempted_token': self._hash_token(request_info.get('token', '')),
                'failure_reason': error_message
            }
        )
        
        await self._queue_event(event)
    
    async def log_authorization_deny(
        self,
        auth_context: AuthContext,
        required_scopes: List[str],
        request_info: Dict[str, Any]
    ) -> None:
        """Log authorization denial"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.AUTHORIZATION_DENY,
            severity=AuditSeverity.MEDIUM,
            timestamp=datetime.now(timezone.utc),
            user_id=auth_context.user_id,
            client_id=auth_context.client_id,
            session_id=None,
            ip_address=request_info.get('ip_address'),
            user_agent=request_info.get('user_agent'),
            endpoint=request_info.get('endpoint', ''),
            method=request_info.get('method', ''),
            status_code=403,
            request_size=request_info.get('request_size', 0),
            response_size=request_info.get('response_size', 0),
            processing_time_ms=request_info.get('processing_time_ms', 0),
            resource_uri=auth_context.resource_uri,
            tool_name=request_info.get('tool_name'),
            error_code='AUTHZ_DENIED',
            error_message='Insufficient permissions',
            metadata={
                'required_scopes': required_scopes,
                'user_scopes': auth_context.scopes,
                'missing_scopes': [s for s in required_scopes if s not in auth_context.scopes]
            }
        )
        
        await self._queue_event(event)
    
    async def log_tool_execution(
        self,
        auth_context: AuthContext,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        request_info: Dict[str, Any]
    ) -> None:
        """Log tool execution"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.TOOL_EXECUTION,
            severity=AuditSeverity.LOW,
            timestamp=datetime.now(timezone.utc),
            user_id=auth_context.user_id,
            client_id=auth_context.client_id,
            session_id=None,
            ip_address=request_info.get('ip_address'),
            user_agent=request_info.get('user_agent'),
            endpoint=request_info.get('endpoint', ''),
            method=request_info.get('method', ''),
            status_code=200,
            request_size=request_info.get('request_size', 0),
            response_size=request_info.get('response_size', 0),
            processing_time_ms=request_info.get('processing_time_ms', 0),
            resource_uri=None,
            tool_name=tool_name,
            error_code=None,
            error_message=None,
            metadata={
                'arguments_hash': hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest(),
                'result_size': len(json.dumps(result)),
                'success': True
            }
        )
        
        await self._queue_event(event)
    
    async def log_tool_execution_failed(
        self,
        auth_context: AuthContext,
        tool_name: str,
        error: Exception,
        request_info: Dict[str, Any]
    ) -> None:
        """Log failed tool execution"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.TOOL_EXECUTION_FAILED,
            severity=AuditSeverity.MEDIUM,
            timestamp=datetime.now(timezone.utc),
            user_id=auth_context.user_id,
            client_id=auth_context.client_id,
            session_id=None,
            ip_address=request_info.get('ip_address'),
            user_agent=request_info.get('user_agent'),
            endpoint=request_info.get('endpoint', ''),
            method=request_info.get('method', ''),
            status_code=500,
            request_size=request_info.get('request_size', 0),
            response_size=request_info.get('response_size', 0),
            processing_time_ms=request_info.get('processing_time_ms', 0),
            resource_uri=None,
            tool_name=tool_name,
            error_code=type(error).__name__,
            error_message=str(error),
            metadata={
                'error_type': type(error).__name__,
                'success': False
            }
        )
        
        await self._queue_event(event)
    
    async def log_resource_access(
        self,
        auth_context: AuthContext,
        resource_uri: str,
        operation: str,
        request_info: Dict[str, Any]
    ) -> None:
        """Log resource access"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.RESOURCE_ACCESS,
            severity=AuditSeverity.LOW,
            timestamp=datetime.now(timezone.utc),
            user_id=auth_context.user_id,
            client_id=auth_context.client_id,
            session_id=None,
            ip_address=request_info.get('ip_address'),
            user_agent=request_info.get('user_agent'),
            endpoint=request_info.get('endpoint', ''),
            method=request_info.get('method', ''),
            status_code=200,
            request_size=request_info.get('request_size', 0),
            response_size=request_info.get('response_size', 0),
            processing_time_ms=request_info.get('processing_time_ms', 0),
            resource_uri=resource_uri,
            tool_name=None,
            error_code=None,
            error_message=None,
            metadata={
                'operation': operation,
                'resource_type': resource_uri.split('://')[0] if '://' in resource_uri else 'unknown'
            }
        )
        
        await self._queue_event(event)
    
    async def log_rate_limit_exceeded(
        self,
        client_id: str,
        endpoint: str,
        request_info: Dict[str, Any]
    ) -> None:
        """Log rate limit exceeded"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.HIGH,
            timestamp=datetime.now(timezone.utc),
            user_id=None,
            client_id=client_id,
            session_id=None,
            ip_address=request_info.get('ip_address'),
            user_agent=request_info.get('user_agent'),
            endpoint=endpoint,
            method=request_info.get('method', ''),
            status_code=429,
            request_size=request_info.get('request_size', 0),
            response_size=request_info.get('response_size', 0),
            processing_time_ms=request_info.get('processing_time_ms', 0),
            resource_uri=None,
            tool_name=None,
            error_code='RATE_LIMIT',
            error_message='Rate limit exceeded',
            metadata={
                'rate_limit_endpoint': endpoint
            }
        )
        
        await self._queue_event(event)
    
    async def log_security_violation(
        self,
        violation_type: str,
        details: Dict[str, Any],
        request_info: Dict[str, Any]
    ) -> None:
        """Log security violation"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=AuditSeverity.CRITICAL,
            timestamp=datetime.now(timezone.utc),
            user_id=request_info.get('user_id'),
            client_id=request_info.get('client_id'),
            session_id=None,
            ip_address=request_info.get('ip_address'),
            user_agent=request_info.get('user_agent'),
            endpoint=request_info.get('endpoint', ''),
            method=request_info.get('method', ''),
            status_code=400,
            request_size=request_info.get('request_size', 0),
            response_size=request_info.get('response_size', 0),
            processing_time_ms=request_info.get('processing_time_ms', 0),
            resource_uri=None,
            tool_name=None,
            error_code='SECURITY_VIOLATION',
            error_message=f'Security violation: {violation_type}',
            metadata={
                'violation_type': violation_type,
                'details': details
            }
        )
        
        await self._queue_event(event)
    
    async def _queue_event(self, event: AuditEvent) -> None:
        """Queue audit event for processing"""
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            # If queue is full, log the event directly to avoid blocking
            self._logger.warning("Audit event queue full, logging directly")
            await self._storage.store_event(event)
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.now(timezone.utc).isoformat()
        random_bytes = hashlib.sha256(timestamp.encode()).digest()[:8]
        return f"audit_{random_bytes.hex()}"
    
    def _hash_token(self, token: str) -> str:
        """Hash token for audit logging (for privacy)"""
        if not token:
            return ""
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    async def query_events(self, filters: Dict[str, Any], limit: int = 100) -> List[AuditEvent]:
        """Query audit events"""
        return await self._storage.query_events(filters, limit)
    
    async def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Get specific audit event"""
        return await self._storage.get_event(event_id)
    
    async def close(self):
        """Close audit logger and cleanup resources"""
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass


# Global audit logger instance
_audit_logger: Optional[MCPAuditLogger] = None


def get_audit_logger() -> MCPAuditLogger:
    """Get the global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        storage = FileAuditStorage()
        logger = logging.getLogger(__name__)
        _audit_logger = MCPAuditLogger(storage, logger)
    return _audit_logger


async def initialize_audit_logger():
    """Initialize the global audit logger"""
    audit_logger = get_audit_logger()
    logger.info("Audit logger initialized successfully")


async def cleanup_audit_logger():
    """Cleanup the global audit logger"""
    global _audit_logger
    if _audit_logger:
        await _audit_logger.close()
        _audit_logger = None
    logger.info("Audit logger cleaned up")
