"""
MCP Graceful Shutdown Handler - Implementation
Handles graceful shutdown of MCP server following best practices
"""

import asyncio
import signal
import logging
import time
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ShutdownPhase(Enum):
    """Phases of graceful shutdown"""
    STARTING = "starting"
    STOPPING_ACCEPTORS = "stopping_acceptors"
    WAITING_FOR_REQUESTS = "waiting_for_requests"
    STOPPING_SERVICES = "stopping_services"
    CLEANUP = "cleanup"
    COMPLETED = "completed"


class ShutdownReason(Enum):
    """Reasons for shutdown"""
    SIGNAL = "signal"
    MANUAL = "manual"
    ERROR = "error"
    HEALTH_CHECK_FAILURE = "health_check_failure"


@dataclass
class ShutdownTask:
    """Task to be executed during shutdown"""
    name: str
    task_func: Callable
    timeout_seconds: int = 30
    critical: bool = False
    dependencies: List[str] = field(default_factory=list)
    executed: bool = False
    error: Optional[Exception] = None
    execution_time_ms: Optional[float] = None


@dataclass
class ShutdownStatus:
    """Current shutdown status"""
    phase: ShutdownPhase
    reason: ShutdownReason
    start_time: datetime
    active_requests: int = 0
    completed_tasks: int = 0
    total_tasks: int = 0
    errors: List[str] = field(default_factory=list)
    estimated_completion_time: Optional[datetime] = None


class GracefulShutdownManager:
    """Graceful shutdown manager following best practices"""
    
    def __init__(self, shutdown_timeout_seconds: int = 60):
        self._shutdown_timeout = shutdown_timeout_seconds
        self._shutdown_tasks: List[ShutdownTask] = []
        self._active_requests = 0
        self._shutdown_in_progress = False
        self._shutdown_status: Optional[ShutdownStatus] = None
        self._request_lock = threading.Lock()
        self._shutdown_lock = threading.Lock()
        self._shutdown_event = asyncio.Event()
        self._original_signal_handlers: Dict[int, Any] = {}
    
    def register_shutdown_task(
        self, 
        name: str, 
        task_func: Callable, 
        timeout_seconds: int = 30,
        critical: bool = False,
        dependencies: List[str] = None
    ):
        """Register a task to be executed during shutdown"""
        task = ShutdownTask(
            name=name,
            task_func=task_func,
            timeout_seconds=timeout_seconds,
            critical=critical,
            dependencies=dependencies or []
        )
        self._shutdown_tasks.append(task)
        logger.info(f"Registered shutdown task: {name}")
    
    def register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        signals_to_handle = [signal.SIGTERM, signal.SIGINT]
        
        for sig in signals_to_handle:
            # Store original handler
            self._original_signal_handlers[sig] = signal.signal(sig, signal.SIG_IGN)
            
            # Set new handler
            signal.signal(sig, lambda s, f: asyncio.create_task(self._handle_shutdown_signal(s)))
        
        logger.info("Signal handlers registered for graceful shutdown")
    
    async def _handle_shutdown_signal(self, signum: int):
        """Handle shutdown signal"""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received shutdown signal: {signal_name}")
        
        await self.initiate_shutdown(ShutdownReason.SIGNAL, f"Signal: {signal_name}")
    
    async def initiate_shutdown(self, reason: ShutdownReason, message: str = ""):
        """Initiate graceful shutdown"""
        with self._shutdown_lock:
            if self._shutdown_in_progress:
                logger.warning("Shutdown already in progress")
                return
            
            self._shutdown_in_progress = True
            self._shutdown_status = ShutdownStatus(
                phase=ShutdownPhase.STARTING,
                reason=reason,
                start_time=datetime.now(),
                total_tasks=len(self._shutdown_tasks)
            )
        
        logger.info(f"Initiating graceful shutdown: {reason.value} - {message}")
        
        try:
            await self._execute_shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            if self._shutdown_status:
                self._shutdown_status.errors.append(str(e))
        finally:
            self._shutdown_event.set()
    
    async def _execute_shutdown(self):
        """Execute the shutdown process"""
        if not self._shutdown_status:
            return
        
        # Phase 1: Stop accepting new requests
        await self._stop_accepting_requests()
        
        # Phase 2: Wait for active requests to complete
        await self._wait_for_active_requests()
        
        # Phase 3: Stop services
        await self._stop_services()
        
        # Phase 4: Cleanup
        await self._cleanup()
        
        # Mark as completed
        self._shutdown_status.phase = ShutdownPhase.COMPLETED
        logger.info("Graceful shutdown completed")
    
    async def _stop_accepting_requests(self):
        """Stop accepting new requests"""
        self._shutdown_status.phase = ShutdownPhase.STOPPING_ACCEPTORS
        logger.info("Stopping request acceptors...")
        
        # This would be implemented to stop the web server from accepting new connections
        # For now, we'll simulate this
        await asyncio.sleep(0.1)
    
    async def _wait_for_active_requests(self):
        """Wait for active requests to complete"""
        self._shutdown_status.phase = ShutdownPhase.WAITING_FOR_REQUESTS
        logger.info("Waiting for active requests to complete...")
        
        start_wait = time.time()
        max_wait_time = min(30, self._shutdown_timeout // 2)  # Wait up to 30 seconds or half of total timeout
        
        while self._active_requests > 0 and (time.time() - start_wait) < max_wait_time:
            logger.info(f"Waiting for {self._active_requests} active requests to complete...")
            await asyncio.sleep(1)
        
        if self._active_requests > 0:
            logger.warning(f"Shutdown timeout reached with {self._active_requests} active requests")
            self._shutdown_status.errors.append(f"Timeout waiting for {self._active_requests} active requests")
    
    async def _stop_services(self):
        """Stop all registered services"""
        self._shutdown_status.phase = ShutdownPhase.STOPPING_SERVICES
        logger.info("Stopping services...")
        
        # Execute shutdown tasks in dependency order
        await self._execute_shutdown_tasks()
    
    async def _execute_shutdown_tasks(self):
        """Execute shutdown tasks with dependency resolution"""
        executed_tasks = set()
        remaining_tasks = {task.name: task for task in self._shutdown_tasks}
        
        while remaining_tasks:
            # Find tasks that can be executed (dependencies satisfied)
            ready_tasks = []
            for task_name, task in remaining_tasks.items():
                if all(dep in executed_tasks for dep in task.dependencies):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # Circular dependency or missing dependency
                remaining_names = list(remaining_tasks.keys())
                logger.error(f"Cannot resolve dependencies for tasks: {remaining_names}")
                self._shutdown_status.errors.append(f"Circular dependency in shutdown tasks: {remaining_names}")
                break
            
            # Execute ready tasks concurrently
            tasks = [self._execute_shutdown_task(task) for task in ready_tasks]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Mark tasks as executed
            for task in ready_tasks:
                executed_tasks.add(task.name)
                remaining_tasks.pop(task.name)
                self._shutdown_status.completed_tasks += 1
    
    async def _execute_shutdown_task(self, task: ShutdownTask):
        """Execute a single shutdown task"""
        start_time = time.time()
        
        try:
            logger.info(f"Executing shutdown task: {task.name}")
            
            # Execute task with timeout
            if asyncio.iscoroutinefunction(task.task_func):
                await asyncio.wait_for(task.task_func(), timeout=task.timeout_seconds)
            else:
                # Run synchronous task in thread pool
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, task.task_func),
                    timeout=task.timeout_seconds
                )
            
            task.executed = True
            task.execution_time_ms = (time.time() - start_time) * 1000
            logger.info(f"Shutdown task completed: {task.name} ({task.execution_time_ms:.2f}ms)")
        
        except asyncio.TimeoutError:
            error_msg = f"Shutdown task timeout: {task.name} ({task.timeout_seconds}s)"
            logger.error(error_msg)
            task.error = TimeoutError(error_msg)
            
            if task.critical:
                self._shutdown_status.errors.append(f"CRITICAL: {error_msg}")
            else:
                self._shutdown_status.errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"Shutdown task error: {task.name} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            task.error = e
            
            if task.critical:
                self._shutdown_status.errors.append(f"CRITICAL: {error_msg}")
            else:
                self._shutdown_status.errors.append(error_msg)
    
    async def _cleanup(self):
        """Final cleanup phase"""
        self._shutdown_status.phase = ShutdownPhase.CLEANUP
        logger.info("Performing final cleanup...")
        
        # Restore original signal handlers
        for sig, handler in self._original_signal_handlers.items():
            signal.signal(sig, handler)
        
        logger.info("Final cleanup completed")
    
    def increment_active_requests(self):
        """Increment active request counter"""
        with self._request_lock:
            self._active_requests += 1
    
    def decrement_active_requests(self):
        """Decrement active request counter"""
        with self._request_lock:
            self._active_requests = max(0, self._active_requests - 1)
    
    def get_active_requests_count(self) -> int:
        """Get current active requests count"""
        with self._request_lock:
            return self._active_requests
    
    def is_shutdown_in_progress(self) -> bool:
        """Check if shutdown is in progress"""
        return self._shutdown_in_progress
    
    def get_shutdown_status(self) -> Optional[ShutdownStatus]:
        """Get current shutdown status"""
        return self._shutdown_status
    
    async def wait_for_shutdown(self, timeout_seconds: Optional[int] = None):
        """Wait for shutdown to complete"""
        timeout = timeout_seconds or self._shutdown_timeout
        
        try:
            await asyncio.wait_for(self._shutdown_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for shutdown to complete")
            return False
        
        return True
    
    def estimate_shutdown_time(self) -> timedelta:
        """Estimate remaining shutdown time"""
        if not self._shutdown_status or self._shutdown_status.phase == ShutdownPhase.COMPLETED:
            return timedelta(0)
        
        # Simple estimation based on remaining tasks and active requests
        remaining_tasks = self._shutdown_status.total_tasks - self._shutdown_status.completed_tasks
        estimated_task_time = remaining_tasks * 5  # 5 seconds per task average
        estimated_request_time = self._active_requests * 2  # 2 seconds per request average
        
        return timedelta(seconds=estimated_task_time + estimated_request_time)


class ShutdownAwareRequestHandler:
    """Request handler that respects shutdown signals"""
    
    def __init__(self, shutdown_manager: GracefulShutdownManager):
        self._shutdown_manager = shutdown_manager
    
    async def handle_request(self, request_func: Callable, *args, **kwargs):
        """Handle request with shutdown awareness"""
        if self._shutdown_manager.is_shutdown_in_progress():
            raise RuntimeError("Server is shutting down")
        
        self._shutdown_manager.increment_active_requests()
        
        try:
            return await request_func(*args, **kwargs)
        finally:
            self._shutdown_manager.decrement_active_requests()


class HealthCheckShutdownTrigger:
    """Shutdown trigger based on health check failures"""
    
    def __init__(
        self, 
        shutdown_manager: GracefulShutdownManager,
        max_consecutive_failures: int = 3,
        failure_window_seconds: int = 300
    ):
        self._shutdown_manager = shutdown_manager
        self._max_consecutive_failures = max_consecutive_failures
        self._failure_window = failure_window_seconds
        self._recent_failures: List[datetime] = []
        self._lock = threading.Lock()
    
    def record_health_check_result(self, success: bool):
        """Record health check result"""
        with self._lock:
            now = datetime.now()
            
            if success:
                # Clear recent failures on success
                self._recent_failures.clear()
            else:
                # Add failure timestamp
                self._recent_failures.append(now)
                
                # Remove old failures outside window
                cutoff = now - timedelta(seconds=self._failure_window)
                self._recent_failures = [f for f in self._recent_failures if f > cutoff]
                
                # Check if we should trigger shutdown
                if len(self._recent_failures) >= self._max_consecutive_failures:
                    logger.error(f"Health check failure threshold reached: {len(self._recent_failures)} failures")
                    asyncio.create_task(
                        self._shutdown_manager.initiate_shutdown(
                            ShutdownReason.HEALTH_CHECK_FAILURE,
                            f"{len(self._recent_failures)} consecutive health check failures"
                        )
                    )
    
    def get_failure_count(self) -> int:
        """Get current failure count"""
        with self._lock:
            return len(self._recent_failures)


# Global shutdown manager instance
_shutdown_manager: Optional[GracefulShutdownManager] = None


def get_shutdown_manager(shutdown_timeout_seconds: int = 60) -> GracefulShutdownManager:
    """Get global shutdown manager instance"""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = GracefulShutdownManager(shutdown_timeout_seconds)
    return _shutdown_manager


# Convenience functions for common shutdown tasks
async def shutdown_database_connection():
    """Shutdown task for database connection"""
    logger.info("Closing database connections...")
    # Implement database connection cleanup
    await asyncio.sleep(0.1)  # Simulate cleanup time
    logger.info("Database connections closed")


async def shutdown_redis_connection():
    """Shutdown task for Redis connection"""
    logger.info("Closing Redis connections...")
    # Implement Redis connection cleanup
    await asyncio.sleep(0.1)  # Simulate cleanup time
    logger.info("Redis connections closed")


async def shutdown_http_clients():
    """Shutdown task for HTTP clients"""
    logger.info("Closing HTTP clients...")
    # Implement HTTP client cleanup
    await asyncio.sleep(0.1)  # Simulate cleanup time
    logger.info("HTTP clients closed")


async def shutdown_monitoring_service():
    """Shutdown task for monitoring service"""
    logger.info("Stopping monitoring service...")
    # Implement monitoring service cleanup
    await asyncio.sleep(0.1)  # Simulate cleanup time
    logger.info("Monitoring service stopped")


def register_default_shutdown_tasks(shutdown_manager: GracefulShutdownManager):
    """Register default shutdown tasks"""
    shutdown_manager.register_shutdown_task(
        "stop_acceptors",
        lambda: None,  # Placeholder - would stop HTTP server acceptors
        timeout_seconds=5,
        critical=True
    )
    
    shutdown_manager.register_shutdown_task(
        "shutdown_monitoring",
        shutdown_monitoring_service,
        timeout_seconds=10,
        dependencies=["stop_acceptors"]
    )
    
    shutdown_manager.register_shutdown_task(
        "shutdown_http_clients",
        shutdown_http_clients,
        timeout_seconds=15,
        dependencies=["stop_acceptors"]
    )
    
    shutdown_manager.register_shutdown_task(
        "shutdown_redis",
        shutdown_redis_connection,
        timeout_seconds=10,
        dependencies=["shutdown_http_clients"]
    )
    
    shutdown_manager.register_shutdown_task(
        "shutdown_database",
        shutdown_database_connection,
        timeout_seconds=15,
        critical=True,
        dependencies=["shutdown_redis"]
    )


if __name__ == "__main__":
    # Example usage
    async def main():
        shutdown_manager = get_shutdown_manager()
        
        # Register default tasks
        register_default_shutdown_tasks(shutdown_manager)
        
        # Register signal handlers
        shutdown_manager.register_signal_handlers()
        
        # Simulate some active requests
        for i in range(3):
            shutdown_manager.increment_active_requests()
        
        # Simulate request completion
        await asyncio.sleep(2)
        for i in range(3):
            shutdown_manager.decrement_active_requests()
        
        # Wait for shutdown (in real app, this would be triggered by signal)
        await asyncio.sleep(1)
        
        # Manually trigger shutdown for testing
        await shutdown_manager.initiate_shutdown(ShutdownReason.MANUAL, "Test shutdown")
        
        # Wait for shutdown to complete
        await shutdown_manager.wait_for_shutdown()
        
        # Print final status
        status = shutdown_manager.get_shutdown_status()
        if status:
            print(f"Shutdown completed: {status.phase.value}")
            print(f"Completed tasks: {status.completed_tasks}/{status.total_tasks}")
            if status.errors:
                print(f"Errors: {status.errors}")
    
    asyncio.run(main())
