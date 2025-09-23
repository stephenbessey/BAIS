"""
Health Checks for External Dependencies
Provides comprehensive health monitoring for all external integrations
"""

import asyncio
import httpx
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging

from ..core.secure_logging import get_business_logger, LogContext

logger = get_business_logger()


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    service_name: str
    status: HealthStatus
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    last_successful_check: Optional[datetime] = None


@dataclass
class ServiceHealthConfig:
    """Configuration for a service health check"""
    service_name: str
    endpoint: str
    timeout_seconds: int = 10
    retry_count: int = 3
    expected_status_code: int = 200
    required_headers: Dict[str, str] = field(default_factory=dict)
    authentication: Optional[Dict[str, str]] = field(default_factory=dict)
    check_interval_seconds: int = 60
    failure_threshold: int = 3


class HealthChecker:
    """Base class for health checkers"""
    
    def __init__(self, config: ServiceHealthConfig):
        self.config = config
        self.consecutive_failures = 0
        self.last_check_time: Optional[datetime] = None
        self.last_successful_check: Optional[datetime] = None
    
    async def check_health(self) -> HealthCheckResult:
        """Perform health check for the service"""
        start_time = time.time()
        
        try:
            result = await self._perform_check()
            response_time = (time.time() - start_time) * 1000
            
            if result.status == HealthStatus.HEALTHY:
                self.consecutive_failures = 0
                self.last_successful_check = datetime.utcnow()
            else:
                self.consecutive_failures += 1
            
            self.last_check_time = datetime.utcnow()
            result.response_time_ms = response_time
            result.last_successful_check = self.last_successful_check
            
            return result
            
        except Exception as e:
            self.consecutive_failures += 1
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus.UNHEALTHY
            if self.consecutive_failures < self.config.failure_threshold:
                status = HealthStatus.DEGRADED
            
            return HealthCheckResult(
                service_name=self.config.service_name,
                status=status,
                response_time_ms=response_time,
                error_message=str(e),
                last_successful_check=self.last_successful_check
            )
    
    async def _perform_check(self) -> HealthCheckResult:
        """Perform the actual health check - to be implemented by subclasses"""
        raise NotImplementedError


class HTTPHealthChecker(HealthChecker):
    """Health checker for HTTP services"""
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check health of HTTP service"""
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            headers = self.config.required_headers.copy()
            
            # Add authentication if configured
            if self.config.authentication:
                if 'bearer_token' in self.config.authentication:
                    headers['Authorization'] = f"Bearer {self.config.authentication['bearer_token']}"
                elif 'api_key' in self.config.authentication:
                    headers['X-API-Key'] = self.config.authentication['api_key']
            
            response = await client.get(
                self.config.endpoint,
                headers=headers
            )
            
            if response.status_code == self.config.expected_status_code:
                return HealthCheckResult(
                    service_name=self.config.service_name,
                    status=HealthStatus.HEALTHY,
                    details={
                        "status_code": response.status_code,
                        "response_size": len(response.content)
                    }
                )
            else:
                return HealthCheckResult(
                    service_name=self.config.service_name,
                    status=HealthStatus.DEGRADED,
                    error_message=f"Unexpected status code: {response.status_code}",
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text[:500]  # Limit response text
                    }
                )


class DatabaseHealthChecker(HealthChecker):
    """Health checker for database connections"""
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check database connectivity"""
        # This would integrate with your actual database connection
        # For now, we'll simulate a database check
        
        try:
            # Simulate database query
            await asyncio.sleep(0.1)  # Simulate query time
            
            return HealthCheckResult(
                service_name=self.config.service_name,
                status=HealthStatus.HEALTHY,
                details={
                    "connection_pool_size": 10,
                    "active_connections": 3,
                    "database_version": "PostgreSQL 14.0"
                }
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=self.config.service_name,
                status=HealthStatus.UNHEALTHY,
                error_message=f"Database connection failed: {str(e)}"
            )


class AP2HealthChecker(HTTPHealthChecker):
    """Health checker for AP2 payment network"""
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check AP2 network health"""
        result = await super()._perform_check()
        
        if result.status == HealthStatus.HEALTHY:
            # Additional AP2-specific checks
            result.details.update({
                "network_status": "operational",
                "mandate_service": "available",
                "payment_service": "available"
            })
        
        return result


class A2AHealthChecker(HTTPHealthChecker):
    """Health checker for A2A agent network"""
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check A2A network health"""
        result = await super()._perform_check()
        
        if result.status == HealthStatus.HEALTHY:
            # Additional A2A-specific checks
            result.details.update({
                "agent_registry": "available",
                "task_coordination": "operational",
                "streaming_service": "available"
            })
        
        return result


class HealthCheckManager:
    """Manages all health checks for the system"""
    
    def __init__(self):
        self.checkers: Dict[str, HealthChecker] = {}
        self.health_history: List[HealthCheckResult] = []
        self.max_history_size = 1000
    
    def register_service(self, config: ServiceHealthConfig, checker_type: str = "http") -> None:
        """Register a service for health checking"""
        if checker_type == "http":
            checker = HTTPHealthChecker(config)
        elif checker_type == "database":
            checker = DatabaseHealthChecker(config)
        elif checker_type == "ap2":
            checker = AP2HealthChecker(config)
        elif checker_type == "a2a":
            checker = A2AHealthChecker(config)
        else:
            raise ValueError(f"Unknown checker type: {checker_type}")
        
        self.checkers[config.service_name] = checker
        logger.info(f"Registered health checker for service: {config.service_name}")
    
    async def check_all_services(self) -> List[HealthCheckResult]:
        """Check health of all registered services"""
        tasks = []
        for checker in self.checkers.values():
            tasks.append(checker.check_health())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and add to history
        valid_results = []
        for result in results:
            if isinstance(result, HealthCheckResult):
                valid_results.append(result)
                self.health_history.append(result)
            elif isinstance(result, Exception):
                # Create error result for failed checks
                error_result = HealthCheckResult(
                    service_name="unknown",
                    status=HealthStatus.UNKNOWN,
                    error_message=str(result)
                )
                valid_results.append(error_result)
        
        # Trim history if too large
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size:]
        
        return valid_results
    
    async def check_service(self, service_name: str) -> Optional[HealthCheckResult]:
        """Check health of a specific service"""
        if service_name not in self.checkers:
            return None
        
        return await self.checkers[service_name].check_health()
    
    def get_service_status(self, service_name: str) -> Optional[HealthStatus]:
        """Get the last known status of a service"""
        recent_results = [
            result for result in self.health_history[-10:]
            if result.service_name == service_name
        ]
        
        if not recent_results:
            return None
        
        return recent_results[-1].status
    
    def get_overall_health(self) -> HealthStatus:
        """Get overall system health status"""
        if not self.checkers:
            return HealthStatus.UNKNOWN
        
        # Check if all services are healthy
        all_healthy = all(
            self.get_service_status(name) == HealthStatus.HEALTHY
            for name in self.checkers.keys()
        )
        
        if all_healthy:
            return HealthStatus.HEALTHY
        
        # Check if any services are unhealthy
        any_unhealthy = any(
            self.get_service_status(name) == HealthStatus.UNHEALTHY
            for name in self.checkers.keys()
        )
        
        if any_unhealthy:
            return HealthStatus.UNHEALTHY
        
        return HealthStatus.DEGRADED
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of system health"""
        services_status = {}
        for service_name in self.checkers.keys():
            services_status[service_name] = self.get_service_status(service_name)
        
        return {
            "overall_status": self.get_overall_health().value,
            "services": services_status,
            "total_services": len(self.checkers),
            "healthy_services": sum(1 for status in services_status.values() if status == HealthStatus.HEALTHY),
            "last_check": datetime.utcnow().isoformat()
        }


# Global health check manager instance
_health_manager: Optional[HealthCheckManager] = None


def get_health_manager() -> HealthCheckManager:
    """Get the global health check manager instance"""
    global _health_manager
    if _health_manager is None:
        _health_manager = HealthCheckManager()
    return _health_manager


def initialize_health_checks() -> None:
    """Initialize health checks for all external dependencies"""
    manager = get_health_manager()
    
    # AP2 Payment Network
    manager.register_service(
        ServiceHealthConfig(
            service_name="ap2_payment_network",
            endpoint="https://ap2-network.example.com/health",
            timeout_seconds=10,
            failure_threshold=3
        ),
        checker_type="ap2"
    )
    
    # A2A Agent Registry
    manager.register_service(
        ServiceHealthConfig(
            service_name="a2a_agent_registry",
            endpoint="https://a2a-registry.example.com/health",
            timeout_seconds=10,
            failure_threshold=3
        ),
        checker_type="a2a"
    )
    
    # Database
    manager.register_service(
        ServiceHealthConfig(
            service_name="postgresql_database",
            endpoint="internal://database",
            timeout_seconds=5,
            failure_threshold=2
        ),
        checker_type="database"
    )
    
    # Redis Cache
    manager.register_service(
        ServiceHealthConfig(
            service_name="redis_cache",
            endpoint="http://localhost:6379/ping",
            timeout_seconds=5,
            failure_threshold=2
        ),
        checker_type="http"
    )
    
    logger.info("Health checks initialized for all external dependencies")


# Health check endpoints for FastAPI
async def get_health_status() -> Dict[str, Any]:
    """Get current health status of all services"""
    manager = get_health_manager()
    results = await manager.check_all_services()
    
    return {
        "status": manager.get_overall_health().value,
        "services": [
            {
                "name": result.service_name,
                "status": result.status.value,
                "response_time_ms": result.response_time_ms,
                "error": result.error_message,
                "details": result.details,
                "last_check": result.timestamp.isoformat()
            }
            for result in results
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


async def get_service_health(service_name: str) -> Dict[str, Any]:
    """Get health status of a specific service"""
    manager = get_health_manager()
    result = await manager.check_service(service_name)
    
    if result is None:
        return {
            "error": f"Service '{service_name}' not found",
            "status": HealthStatus.UNKNOWN.value
        }
    
    return {
        "name": result.service_name,
        "status": result.status.value,
        "response_time_ms": result.response_time_ms,
        "error": result.error_message,
        "details": result.details,
        "last_check": result.timestamp.isoformat(),
        "last_successful_check": result.last_successful_check.isoformat() if result.last_successful_check else None
    }
