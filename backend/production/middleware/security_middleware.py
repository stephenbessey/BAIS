"""
Security Middleware - Implementation
Rate limiting, audit logging, and security headers following MCP best practices
"""

import time
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Rate limit configuration"""
    limit: int
    window_seconds: int
    message: str = "Rate limit exceeded"


@dataclass
class AuditEvent:
    """Audit event for security logging"""
    event_type: str
    user_id: Optional[str]
    client_id: Optional[str]
    endpoint: str
    method: str
    status_code: int
    timestamp: datetime
    request_size: int
    response_size: int
    processing_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class RateLimiter:
    """Rate limiter implementation following best practices"""
    
    def __init__(self):
        # Store rate limit data: {client_id: deque of timestamps}
        self._clients: Dict[str, deque] = defaultdict(deque)
        self._limits: Dict[str, RateLimit] = {}
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def add_limit(self, endpoint: str, limit: RateLimit):
        """Add rate limit for specific endpoint"""
        self._limits[endpoint] = limit
    
    def is_allowed(self, client_id: str, endpoint: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed under rate limits
        Returns: (is_allowed, retry_after_seconds)
        """
        # Cleanup old entries periodically
        self._cleanup_if_needed()
        
        # Get rate limit for endpoint
        rate_limit = self._limits.get(endpoint)
        if not rate_limit:
            return True, None  # No rate limit configured
        
        now = time.time()
        window_start = now - rate_limit.window_seconds
        
        # Get client's request history
        client_requests = self._clients[client_id]
        
        # Remove requests outside the window
        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) >= rate_limit.limit:
            # Calculate retry after time
            oldest_request = client_requests[0]
            retry_after = int(oldest_request + rate_limit.window_seconds - now)
            return False, str(max(1, retry_after))
        
        # Add current request
        client_requests.append(now)
        return True, None
    
    def _cleanup_if_needed(self):
        """Cleanup old client data to prevent memory leaks"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = now - 3600  # Remove data older than 1 hour
        
        clients_to_remove = []
        for client_id, requests in self._clients.items():
            # Remove old requests
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # Remove clients with no requests
            if not requests:
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self._clients[client_id]
        
        self._last_cleanup = now


class AuditLogger:
    """Audit logger for security events following best practices"""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    async def log_request(self, request: Request, auth_context: Optional[Dict[str, Any]] = None):
        """Log incoming request"""
        try:
            # Extract request information
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            content_length = int(request.headers.get("content-length", 0))
            
            # Log request
            self._logger.info(
                "MCP request received",
                extra={
                    "event_type": "request_received",
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "content_length": content_length,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": auth_context.get("user_id") if auth_context else None,
                    "client_id": auth_context.get("client_id") if auth_context else None
                }
            )
        except Exception as e:
            self._logger.error(f"Error logging request: {e}")
    
    async def log_response(
        self, 
        request: Request, 
        response: Response, 
        processing_time_ms: float,
        auth_context: Optional[Dict[str, Any]] = None
    ):
        """Log response"""
        try:
            # Extract response information
            client_ip = self._get_client_ip(request)
            
            # Log response
            self._logger.info(
                "MCP response sent",
                extra={
                    "event_type": "response_sent",
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "client_ip": client_ip,
                    "processing_time_ms": processing_time_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": auth_context.get("user_id") if auth_context else None,
                    "client_id": auth_context.get("client_id") if auth_context else None
                }
            )
        except Exception as e:
            self._logger.error(f"Error logging response: {e}")
    
    async def log_security_event(
        self,
        event_type: str,
        request: Request,
        details: Dict[str, Any],
        auth_context: Optional[Dict[str, Any]] = None
    ):
        """Log security-related events"""
        try:
            client_ip = self._get_client_ip(request)
            
            self._logger.warning(
                f"Security event: {event_type}",
                extra={
                    "event_type": f"security_{event_type}",
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": client_ip,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": auth_context.get("user_id") if auth_context else None,
                    "client_id": auth_context.get("client_id") if auth_context else None,
                    "details": details
                }
            )
        except Exception as e:
            self._logger.error(f"Error logging security event: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers first (for reverse proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware:
    """Add security headers to responses"""
    
    def __init__(self, app: ASGIApp):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Add security headers
                headers.update({
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"x-xss-protection": b"1; mode=block",
                    b"strict-transport-security": b"max-age=31536000; includeSubDomains",
                    b"referrer-policy": b"strict-origin-when-cross-origin",
                    b"content-security-policy": b"default-src 'self'",
                    b"permissions-policy": b"geolocation=(), microphone=(), camera=()"
                })
                
                message["headers"] = list(headers.items())
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)


class MCPSecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware for MCP endpoints"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._rate_limiter = RateLimiter()
        self._audit_logger = AuditLogger(logger)
        
        # Configure rate limits for different endpoints
        self._setup_rate_limits()
    
    def _setup_rate_limits(self):
        """Setup rate limits for different MCP endpoints"""
        # Tool execution - more restrictive
        self._rate_limiter.add_limit(
            "/mcp/tools/call",
            RateLimit(limit=60, window_seconds=60, message="Tool execution rate limit exceeded")
        )
        
        # Resource access - moderate
        self._rate_limiter.add_limit(
            "/mcp/resources/read",
            RateLimit(limit=120, window_seconds=60, message="Resource access rate limit exceeded")
        )
        
        # Resource listing - less restrictive
        self._rate_limiter.add_limit(
            "/mcp/resources/list",
            RateLimit(limit=200, window_seconds=60, message="Resource listing rate limit exceeded")
        )
        
        # Tool listing - less restrictive
        self._rate_limiter.add_limit(
            "/mcp/tools/list",
            RateLimit(limit=200, window_seconds=60, message="Tool listing rate limit exceeded")
        )
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security middleware"""
        start_time = time.time()
        
        # Extract client identifier
        client_id = self._extract_client_id(request)
        
        # Check rate limits
        if not self._check_rate_limit(client_id, request):
            return await self._handle_rate_limit_exceeded(request)
        
        # Log request
        auth_context = self._extract_auth_context(request)
        await self._audit_logger.log_request(request, auth_context)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Log response
            await self._audit_logger.log_response(request, response, processing_time_ms, auth_context)
            
            # Add security headers
            response = self._add_security_headers(response)
            
            return response
            
        except Exception as e:
            # Log error
            processing_time_ms = (time.time() - start_time) * 1000
            
            await self._audit_logger.log_security_event(
                "error",
                request,
                {"error": str(e), "processing_time_ms": processing_time_ms},
                auth_context
            )
            
            # Re-raise the exception
            raise
    
    def _extract_client_id(self, request: Request) -> str:
        """Extract unique client identifier for rate limiting"""
        # Try to get authenticated user ID first
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Use token hash as client ID for authenticated requests
            token = auth_header[7:]  # Remove "Bearer " prefix
            return f"auth:{hashlib.sha256(token.encode()).hexdigest()[:16]}"
        
        # Fallback to IP address for unauthenticated requests
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"
    
    def _extract_auth_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract authentication context from request"""
        # This would extract user context from JWT token in real implementation
        # For now, return None
        return None
    
    def _check_rate_limit(self, client_id: str, request: Request) -> bool:
        """Check if request is within rate limits"""
        endpoint = request.url.path
        
        is_allowed, retry_after = self._rate_limiter.is_allowed(client_id, endpoint)
        
        if not is_allowed:
            # Log rate limit violation
            asyncio.create_task(self._audit_logger.log_security_event(
                "rate_limit_exceeded",
                request,
                {"retry_after": retry_after, "client_id": client_id},
                None
            ))
        
        return is_allowed
    
    async def _handle_rate_limit_exceeded(self, request: Request) -> JSONResponse:
        """Handle rate limit exceeded"""
        endpoint = request.url.path
        rate_limit = self._rate_limiter._limits.get(endpoint)
        
        if rate_limit:
            message = rate_limit.message
        else:
            message = "Rate limit exceeded"
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": message,
                "retry_after": 60  # Default retry after 60 seconds
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(rate_limit.limit if rate_limit else 100),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + 60))
            }
        )
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response"""
        # Security headers are added by SecurityHeadersMiddleware
        # This method is kept for consistency
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers first (for reverse proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"


# Global middleware instances
_security_middleware: Optional[MCPSecurityMiddleware] = None
_security_headers_middleware: Optional[SecurityHeadersMiddleware] = None


def get_security_middleware(app: ASGIApp) -> MCPSecurityMiddleware:
    """Get security middleware instance"""
    global _security_middleware
    if _security_middleware is None:
        _security_middleware = MCPSecurityMiddleware(app)
    return _security_middleware


def get_security_headers_middleware(app: ASGIApp) -> SecurityHeadersMiddleware:
    """Get security headers middleware instance"""
    global _security_headers_middleware
    if _security_headers_middleware is None:
        _security_headers_middleware = SecurityHeadersMiddleware(app)
    return _security_headers_middleware
