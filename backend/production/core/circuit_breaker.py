"""
Circuit Breaker Pattern Implementation
Provides resilience for AP2 payment processing and external service calls
"""

import asyncio
import time
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds to wait before trying again
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: int = 30  # Timeout for individual operations
    expected_exception: type = Exception  # Exception type to count as failure


class CircuitBreaker:
    """
    Circuit breaker implementation for resilient service calls.
    Prevents cascading failures and provides automatic recovery.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker {self.name} is OPEN. "
                        f"Last failure: {self.last_failure_time}"
                    )
        
        try:
            # Execute the function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            await self._on_success()
            return result
            
        except asyncio.TimeoutError:
            await self._on_failure()
            raise CircuitBreakerTimeoutException(
                f"Circuit breaker {self.name}: Operation timed out after {self.config.timeout}s"
            )
        except self.config.expected_exception as e:
            await self._on_failure()
            logger.warning(f"Circuit breaker {self.name}: Operation failed: {e}")
            raise
        except Exception as e:
            # Unexpected exceptions don't count as circuit breaker failures
            logger.error(f"Circuit breaker {self.name}: Unexpected error: {e}")
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    async def _on_success(self):
        """Handle successful operation"""
        async with self._lock:
            self.last_success_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed operation"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker {self.name} transitioning to OPEN "
                    f"after {self.failure_count} failures"
                )
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        async def _reset():
            async with self._lock:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.last_failure_time = None
                logger.info(f"Circuit breaker {self.name} manually reset to CLOSED")
        
        asyncio.create_task(_reset())


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreakerTimeoutException(Exception):
    """Raised when operation times out"""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers"""
    
    def __init__(self):
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    def create_circuit(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Create a new circuit breaker"""
        circuit = CircuitBreaker(name, config)
        self._circuits[name] = circuit
        logger.info(f"Created circuit breaker: {name}")
        return circuit
    
    def get_circuit(self, name: str) -> Optional[CircuitBreaker]:
        """Get existing circuit breaker"""
        return self._circuits.get(name)
    
    def get_or_create_circuit(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Get existing circuit or create new one"""
        circuit = self.get_circuit(name)
        if circuit is None:
            circuit = self.create_circuit(name, config)
        return circuit
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers"""
        return {name: circuit.get_state() for name, circuit in self._circuits.items()}
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for circuit in self._circuits.values():
            circuit.reset()


# Global circuit breaker manager
_circuit_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager"""
    global _circuit_manager
    if _circuit_manager is None:
        _circuit_manager = CircuitBreakerManager()
    return _circuit_manager


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator for applying circuit breaker to functions"""
    if config is None:
        config = CircuitBreakerConfig()
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            circuit = manager.get_or_create_circuit(name, config)
            return await circuit.call(func, *args, **kwargs)
        return wrapper
    return decorator


# AP2-specific circuit breaker configurations
AP2_PAYMENT_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30,
    success_threshold=2,
    timeout=15,
    expected_exception=Exception
)

AP2_MANDATE_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=3,
    timeout=20,
    expected_exception=Exception
)

A2A_DISCOVERY_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=120,
    success_threshold=2,
    timeout=30,
    expected_exception=Exception
)
