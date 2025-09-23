"""
Connection Pool Manager for High-Performance HTTP Operations
Implements connection pooling, keep-alive, and performance optimizations
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging
from datetime import datetime, timedelta
import weakref

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolConfig:
    """Configuration for HTTP connection pools"""
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: int = 30  # seconds
    connect_timeout: int = 10  # seconds
    read_timeout: int = 30  # seconds
    write_timeout: int = 10  # seconds
    pool_timeout: int = 5  # seconds
    retries: int = 3
    backoff_factor: float = 0.1


@dataclass
class PoolStats:
    """Statistics for connection pool monitoring"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    requests_per_second: float = 0.0
    average_response_time_ms: float = 0.0
    error_rate: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


class ConnectionPoolManager:
    """
    Manages HTTP connection pools for optimal performance.
    Implements connection reuse, keep-alive, and intelligent pooling.
    """
    
    def __init__(self):
        self._pools: Dict[str, httpx.AsyncClient] = {}
        self._pool_configs: Dict[str, ConnectionPoolConfig] = {}
        self._pool_stats: Dict[str, PoolStats] = {}
        self._lock = asyncio.Lock()
        
        # Performance tracking
        self._request_times: Dict[str, List[float]] = {}
        self._error_counts: Dict[str, int] = {}
        self._request_counts: Dict[str, int] = {}
        
        # Cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    def create_pool(
        self, 
        name: str, 
        base_url: str, 
        config: ConnectionPoolConfig
    ) -> httpx.AsyncClient:
        """Create a new connection pool with specified configuration"""
        
        # Configure HTTP client with connection pooling
        limits = httpx.Limits(
            max_connections=config.max_connections,
            max_keepalive_connections=config.max_keepalive_connections,
            keepalive_expiry=config.keepalive_expiry
        )
        
        timeout = httpx.Timeout(
            connect=config.connect_timeout,
            read=config.read_timeout,
            write=config.write_timeout,
            pool=config.pool_timeout
        )
        
        # Create HTTP client with retry transport
        transport = httpx.AsyncHTTPTransport(
            limits=limits,
            retries=config.retries,
            http2=True  # Enable HTTP/2 for better performance
        )
        
        client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            follow_redirects=True
        )
        
        # Store pool and configuration
        self._pools[name] = client
        self._pool_configs[name] = config
        self._pool_stats[name] = PoolStats()
        
        # Initialize tracking
        self._request_times[name] = []
        self._error_counts[name] = 0
        self._request_counts[name] = 0
        
        logger.info(f"Created connection pool '{name}' for {base_url}")
        return client
    
    def get_pool(self, name: str) -> Optional[httpx.AsyncClient]:
        """Get existing connection pool"""
        return self._pools.get(name)
    
    def get_or_create_pool(
        self, 
        name: str, 
        base_url: str, 
        config: ConnectionPoolConfig
    ) -> httpx.AsyncClient:
        """Get existing pool or create new one"""
        pool = self.get_pool(name)
        if pool is None:
            pool = self.create_pool(name, base_url, config)
        return pool
    
    @asynccontextmanager
    async def get_client(self, pool_name: str):
        """Context manager for getting HTTP client with automatic cleanup"""
        pool = self.get_pool(pool_name)
        if not pool:
            raise ValueError(f"Connection pool '{pool_name}' not found")
        
        try:
            yield pool
        finally:
            # Update statistics
            await self._update_pool_stats(pool_name)
    
    async def make_request(
        self,
        pool_name: str,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with performance tracking"""
        start_time = datetime.utcnow()
        
        try:
            async with self.get_client(pool_name) as client:
                response = await client.request(method, url, **kwargs)
                
                # Track successful request
                await self._track_request(pool_name, start_time, success=True)
                
                return response
                
        except Exception as e:
            # Track failed request
            await self._track_request(pool_name, start_time, success=False)
            logger.error(f"Request failed for pool '{pool_name}': {e}")
            raise
    
    async def _track_request(self, pool_name: str, start_time: datetime, success: bool):
        """Track request performance and statistics"""
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # ms
        
        # Update request times (keep last 100 requests)
        if pool_name in self._request_times:
            self._request_times[pool_name].append(response_time)
            if len(self._request_times[pool_name]) > 100:
                self._request_times[pool_name].pop(0)
        
        # Update request count
        self._request_counts[pool_name] = self._request_counts.get(pool_name, 0) + 1
        
        # Update error count
        if not success:
            self._error_counts[pool_name] = self._error_counts.get(pool_name, 0) + 1
    
    async def _update_pool_stats(self, pool_name: str):
        """Update pool statistics"""
        if pool_name not in self._pool_stats:
            return
        
        stats = self._pool_stats[pool_name]
        pool = self._pools.get(pool_name)
        
        if pool and hasattr(pool._transport, '_pool'):
            # Get actual connection pool stats
            transport_pool = pool._transport._pool
            stats.total_connections = getattr(transport_pool, 'size', 0)
            stats.active_connections = getattr(transport_pool, 'num_connections', 0)
            stats.idle_connections = stats.total_connections - stats.active_connections
        
        # Calculate performance metrics
        request_times = self._request_times.get(pool_name, [])
        if request_times:
            stats.average_response_time_ms = sum(request_times) / len(request_times)
        
        request_count = self._request_counts.get(pool_name, 0)
        error_count = self._error_counts.get(pool_name, 0)
        
        if request_count > 0:
            stats.error_rate = (error_count / request_count) * 100
        
        # Calculate requests per second (simplified)
        stats.requests_per_second = request_count / 60.0  # Rough estimate
        
        stats.last_updated = datetime.utcnow()
    
    async def get_pool_stats(self, pool_name: str) -> Optional[PoolStats]:
        """Get statistics for a specific pool"""
        await self._update_pool_stats(pool_name)
        return self._pool_stats.get(pool_name)
    
    async def get_all_stats(self) -> Dict[str, PoolStats]:
        """Get statistics for all pools"""
        for pool_name in self._pools.keys():
            await self._update_pool_stats(pool_name)
        return self._pool_stats.copy()
    
    async def optimize_pool(self, pool_name: str) -> Dict[str, Any]:
        """Analyze and suggest optimizations for a pool"""
        stats = await self.get_pool_stats(pool_name)
        config = self._pool_configs.get(pool_name)
        
        if not stats or not config:
            return {"error": "Pool not found"}
        
        optimizations = []
        
        # Analyze connection usage
        if stats.active_connections / config.max_connections > 0.8:
            optimizations.append({
                "type": "increase_connections",
                "current": config.max_connections,
                "suggested": config.max_connections * 2,
                "reason": "High connection utilization (>80%)"
            })
        
        # Analyze response times
        if stats.average_response_time_ms > 1000:  # 1 second
            optimizations.append({
                "type": "increase_timeout",
                "current": config.read_timeout,
                "suggested": config.read_timeout * 2,
                "reason": f"High response time ({stats.average_response_time_ms:.1f}ms)"
            })
        
        # Analyze error rate
        if stats.error_rate > 5:  # 5%
            optimizations.append({
                "type": "increase_retries",
                "current": config.retries,
                "suggested": config.retries + 2,
                "reason": f"High error rate ({stats.error_rate:.1f}%)"
            })
        
        # Analyze keep-alive usage
        if stats.idle_connections > config.max_keepalive_connections * 0.9:
            optimizations.append({
                "type": "increase_keepalive",
                "current": config.max_keepalive_connections,
                "suggested": config.max_keepalive_connections * 2,
                "reason": "High keep-alive utilization"
            })
        
        return {
            "pool_name": pool_name,
            "current_stats": stats,
            "current_config": config,
            "optimizations": optimizations,
            "optimization_score": self._calculate_optimization_score(stats, config)
        }
    
    def _calculate_optimization_score(self, stats: PoolStats, config: ConnectionPoolConfig) -> float:
        """Calculate optimization score (0-100, higher is better)"""
        score = 100.0
        
        # Penalize high response times
        if stats.average_response_time_ms > 500:
            score -= min(30, (stats.average_response_time_ms - 500) / 10)
        
        # Penalize high error rates
        if stats.error_rate > 1:
            score -= min(40, stats.error_rate * 4)
        
        # Penalize low throughput
        if stats.requests_per_second < 10:
            score -= min(20, (10 - stats.requests_per_second) * 2)
        
        return max(0, score)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup task for connection pools"""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
                # Close idle connections that exceed expiry
                for pool_name, pool in self._pools.items():
                    if hasattr(pool._transport, '_pool'):
                        transport_pool = pool._transport._pool
                        # This would implement actual cleanup logic
                        # For now, just update stats
                        await self._update_pool_stats(pool_name)
                
                logger.debug("Performed periodic connection pool cleanup")
                
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")
    
    async def close_all(self):
        """Close all connection pools"""
        for pool_name, pool in self._pools.items():
            try:
                await pool.aclose()
                logger.info(f"Closed connection pool: {pool_name}")
            except Exception as e:
                logger.error(f"Error closing pool '{pool_name}': {e}")
        
        self._pools.clear()
        self._pool_configs.clear()
        self._pool_stats.clear()
        
        # Cancel cleanup task
        if not self._cleanup_task.done():
            self._cleanup_task.cancel()
    
    def __del__(self):
        """Cleanup on destruction"""
        if not self._cleanup_task.done():
            self._cleanup_task.cancel()


# Global connection pool manager
_pool_manager: Optional[ConnectionPoolManager] = None


def get_connection_pool_manager() -> ConnectionPoolManager:
    """Get the global connection pool manager"""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = ConnectionPoolManager()
    return _pool_manager


# Pre-configured pools for common services
AP2_POOL_CONFIG = ConnectionPoolConfig(
    max_connections=50,
    max_keepalive_connections=10,
    keepalive_expiry=60,
    connect_timeout=15,
    read_timeout=45,
    retries=3,
    backoff_factor=0.2
)

A2A_POOL_CONFIG = ConnectionPoolConfig(
    max_connections=30,
    max_keepalive_connections=8,
    keepalive_expiry=45,
    connect_timeout=10,
    read_timeout=30,
    retries=2,
    backoff_factor=0.1
)

REGISTRY_POOL_CONFIG = ConnectionPoolConfig(
    max_connections=20,
    max_keepalive_connections=5,
    keepalive_expiry=30,
    connect_timeout=8,
    read_timeout=20,
    retries=2,
    backoff_factor=0.1
)
