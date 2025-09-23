"""
A2A Processor Manager
Manages A2A task processor lifecycle with proper dependency injection

This module fixes the critical global state violation by implementing
proper dependency injection and lifecycle management.
"""

from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
from dataclasses import dataclass

from .a2a_task_processor import A2ATaskProcessor
from .mcp_server_generator import BusinessSystemAdapter
from .payments.payment_coordinator import PaymentCoordinator
from .payments.ap2_client import AP2Client, AP2ClientConfig
from ..config.ap2_settings import get_ap2_client_config


@dataclass(frozen=True)
class A2AConfiguration:
    """A2A Protocol configuration constants"""
    DEFAULT_TIMEOUT_SECONDS: int = 30
    MAX_TASK_TIMEOUT_SECONDS: int = 300
    MAX_CONCURRENT_TASKS: int = 100
    TASK_CLEANUP_INTERVAL_MINUTES: int = 60
    DISCOVERY_CACHE_TTL_MINUTES: int = 5
    MAX_RETRY_ATTEMPTS: int = 3
    HEARTBEAT_INTERVAL_SECONDS: int = 30


class A2AProcessorManager:
    """
    Manages A2A task processor with proper dependency injection
    
    This class eliminates the global state violation by providing
    proper lifecycle management and dependency injection.
    """
    
    def __init__(
        self, 
        config: A2AConfiguration,
        business_config: Dict[str, Any],
        ap2_config: Optional[AP2ClientConfig] = None
    ):
        self.config = config
        self.business_config = business_config
        self.ap2_config = ap2_config
        self._processor: Optional[A2ATaskProcessor] = None
        self._lock = asyncio.Lock()
        self._initialization_attempts = 0
        self._max_initialization_attempts = 3
    
    async def get_processor(self) -> A2ATaskProcessor:
        """
        Get A2A task processor with lazy initialization
        
        Returns:
            A2ATaskProcessor instance
            
        Raises:
            RuntimeError: If processor initialization fails
        """
        if self._processor is None:
            async with self._lock:
                if self._processor is None:
                    self._processor = await self._create_processor()
        
        return self._processor
    
    async def _create_processor(self) -> A2ATaskProcessor:
        """
        Create A2A task processor with proper dependencies
        
        Returns:
            A2ATaskProcessor instance
            
        Raises:
            RuntimeError: If processor creation fails
        """
        try:
            self._initialization_attempts += 1
            
            # Create business system adapter
            adapter = BusinessSystemAdapter(self.business_config)
            
            # Create AP2 client if configuration provided
            ap2_client = None
            if self.ap2_config:
                ap2_client = AP2Client(self.ap2_config)
            
            # Create payment coordinator with proper dependency injection
            from ..core.business_query_repository import BusinessQueryRepository
            business_repository = BusinessQueryRepository()
            coordinator = PaymentCoordinator(ap2_client, business_repository)
            
            # Create processor
            processor = A2ATaskProcessor(adapter, coordinator)
            
            # Reset initialization attempts on success
            self._initialization_attempts = 0
            
            return processor
            
        except Exception as e:
            if self._initialization_attempts >= self._max_initialization_attempts:
                raise RuntimeError(
                    f"Failed to create A2A processor after {self._max_initialization_attempts} attempts: {e}"
                ) from e
            else:
                # Retry with exponential backoff
                await asyncio.sleep(2 ** self._initialization_attempts)
                return await self._create_processor()
    
    async def reset_processor(self) -> None:
        """
        Reset processor instance (useful for testing or configuration changes)
        """
        async with self._lock:
            if self._processor is not None:
                # Cleanup existing processor if needed
                await self._cleanup_processor()
                self._processor = None
                self._initialization_attempts = 0
    
    async def _cleanup_processor(self) -> None:
        """Cleanup processor resources"""
        if self._processor is not None:
            # Cleanup active tasks
            for task_id, task_status in list(self._processor.active_tasks.items()):
                if task_status.status in ["pending", "running"]:
                    # Cancel active tasks
                    task_status.status = "cancelled"
                    task_status.message = "Processor reset"
    
    def get_processor_status(self) -> Dict[str, Any]:
        """
        Get processor status information
        
        Returns:
            Dictionary with processor status
        """
        if self._processor is None:
            return {
                "initialized": False,
                "active_tasks": 0,
                "initialization_attempts": self._initialization_attempts
            }
        
        return {
            "initialized": True,
            "active_tasks": len(self._processor.active_tasks),
            "initialization_attempts": self._initialization_attempts,
            "max_concurrent_tasks": self.config.MAX_CONCURRENT_TASKS,
            "task_timeout_seconds": self.config.MAX_TASK_TIMEOUT_SECONDS
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on processor
        
        Returns:
            Health check results
        """
        try:
            processor = await self.get_processor()
            
            return {
                "status": "healthy",
                "processor_initialized": True,
                "active_tasks": len(processor.active_tasks),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "processor_initialized": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


class A2AProcessorManagerFactory:
    """Factory for creating A2A processor managers"""
    
    @staticmethod
    def create_default_manager(business_config: Dict[str, Any]) -> A2AProcessorManager:
        """
        Create default A2A processor manager
        
        Args:
            business_config: Business configuration
            
        Returns:
            A2AProcessorManager instance
        """
        config = A2AConfiguration()
        
        # Try to get AP2 configuration
        ap2_config = None
        try:
            ap2_client_config = get_ap2_client_config()
            ap2_config = AP2ClientConfig(**ap2_client_config)
        except Exception:
            # AP2 configuration not available, processor will work without it
            pass
        
        return A2AProcessorManager(
            config=config,
            business_config=business_config,
            ap2_config=ap2_config
        )
    
    @staticmethod
    def create_manager_with_config(
        config: A2AConfiguration,
        business_config: Dict[str, Any],
        ap2_config: Optional[AP2ClientConfig] = None
    ) -> A2AProcessorManager:
        """
        Create A2A processor manager with custom configuration
        
        Args:
            config: A2A configuration
            business_config: Business configuration
            ap2_config: Optional AP2 client configuration
            
        Returns:
            A2AProcessorManager instance
        """
        return A2AProcessorManager(
            config=config,
            business_config=business_config,
            ap2_config=ap2_config
        )
    
    @staticmethod
    def create_test_manager() -> A2AProcessorManager:
        """
        Create A2A processor manager for testing
        
        Returns:
            A2AProcessorManager instance with test configuration
        """
        test_config = A2AConfiguration(
            DEFAULT_TIMEOUT_SECONDS=5,
            MAX_TASK_TIMEOUT_SECONDS=30,
            MAX_CONCURRENT_TASKS=10
        )
        
        test_business_config = {
            "test_mode": True,
            "mock_responses": True
        }
        
        return A2AProcessorManager(
            config=test_config,
            business_config=test_business_config,
            ap2_config=None
        )


# Global container for dependency injection (replaces global state)
class A2ADependencyContainer:
    """
    Dependency container for A2A components
    
    This provides a clean way to manage dependencies without global state
    """
    
    def __init__(self):
        self._manager: Optional[A2AProcessorManager] = None
        self._lock = asyncio.Lock()
    
    async def get_processor_manager(self, business_config: Dict[str, Any] = None) -> A2AProcessorManager:
        """
        Get processor manager instance
        
        Args:
            business_config: Business configuration (used for initialization)
            
        Returns:
            A2AProcessorManager instance
        """
        if self._manager is None:
            async with self._lock:
                if self._manager is None:
                    if business_config is None:
                        business_config = {}
                    self._manager = A2AProcessorManagerFactory.create_default_manager(business_config)
        
        return self._manager
    
    def set_processor_manager(self, manager: A2AProcessorManager) -> None:
        """
        Set processor manager instance (useful for testing)
        
        Args:
            manager: A2AProcessorManager instance
        """
        self._manager = manager
    
    async def reset(self) -> None:
        """Reset the container"""
        async with self._lock:
            if self._manager is not None:
                await self._manager.reset_processor()
                self._manager = None


# Global container instance (singleton pattern, but properly managed)
_container = A2ADependencyContainer()


def get_processor_manager(business_config: Dict[str, Any] = None) -> A2AProcessorManager:
    """
    Get processor manager from global container
    
    This function provides a clean interface for getting the processor manager
    while maintaining proper dependency injection.
    
    Args:
        business_config: Business configuration
        
    Returns:
        A2AProcessorManager instance
    """
    import asyncio
    
    # Run async function in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, 
                    _container.get_processor_manager(business_config)
                )
                return future.result()
        else:
            return loop.run_until_complete(_container.get_processor_manager(business_config))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(_container.get_processor_manager(business_config))


def get_container() -> A2ADependencyContainer:
    """
    Get the global dependency container
    
    Returns:
        A2ADependencyContainer instance
    """
    return _container
