# ============================================================================
# BAIS Platform - Infrastructure Management Utilities
# Best practices: Single Responsibility, Clear Intent, Testability
# ============================================================================

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import asyncpg
import redis.asyncio as redis
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# ============================================================================
# Configuration and Constants
# ============================================================================

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration for clear intent."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class DatabaseMetrics:
    """Database metrics data class following best practices."""
    total_connections: int
    active_connections: int
    idle_connections: int
    slow_queries: int
    database_size_mb: float
    cache_hit_ratio: float


@dataclass
class RedisMetrics:
    """Redis metrics data class."""
    used_memory_mb: float
    total_keys: int
    hit_rate: float
    evicted_keys: int
    connected_clients: int


@dataclass
class SystemHealth:
    """System health status data class."""
    status: HealthStatus
    database: DatabaseMetrics
    cache: RedisMetrics
    timestamp: datetime
    message: str


# ============================================================================
# Prometheus Metrics
# ============================================================================

class MetricsCollector:
    """Centralized metrics collection following Single Responsibility."""
    
    def __init__(self):
        self.http_requests = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint']
        )
        
        self.concurrent_connections = Gauge(
            'http_concurrent_connections',
            'Current concurrent connections'
        )
        
        self.database_connections = Gauge(
            'database_connections',
            'Database connection pool status',
            ['state']
        )
        
        self.redis_memory = Gauge(
            'redis_memory_used_bytes',
            'Redis memory usage in bytes'
        )
    
    def record_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float
    ) -> None:
        """Record HTTP request metrics."""
        self.http_requests.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        self.request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def update_concurrent_connections(self, count: int) -> None:
        """Update concurrent connection count."""
        self.concurrent_connections.set(count)
    
    def update_database_metrics(self, metrics: DatabaseMetrics) -> None:
        """Update database metrics."""
        self.database_connections.labels(state='active').set(
            metrics.active_connections
        )
        self.database_connections.labels(state='idle').set(
            metrics.idle_connections
        )
    
    def update_redis_metrics(self, metrics: RedisMetrics) -> None:
        """Update Redis metrics."""
        self.redis_memory.set(metrics.used_memory_mb * 1024 * 1024)


# ============================================================================
# Database Health Monitor
# ============================================================================

class DatabaseHealthMonitor:
    """
    Database health monitoring following best practices.
    Single responsibility: Monitor and report database health.
    """
    
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> None:
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(
            self.connection_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("Database pool initialized")
    
    async def check_health(self) -> Tuple[HealthStatus, DatabaseMetrics]:
        """
        Check database health and return metrics.
        Clear, single-purpose method.
        """
        if not self.pool:
            raise RuntimeError("Pool not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                metrics = await self._collect_metrics(conn)
                status = self._determine_health_status(metrics)
                return status, metrics
        
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return HealthStatus.UNHEALTHY, self._get_empty_metrics()
    
    async def _collect_metrics(
        self,
        conn: asyncpg.Connection
    ) -> DatabaseMetrics:
        """Collect database metrics."""
        
        # Get connection stats
        conn_stats = await conn.fetch("""
            SELECT 
                count(*) FILTER (WHERE state = 'active') as active,
                count(*) FILTER (WHERE state = 'idle') as idle,
                count(*) as total
            FROM pg_stat_activity
            WHERE datname = current_database()
        """)
        
        # Get slow queries
        slow_queries = await conn.fetchval("""
            SELECT count(*)
            FROM pg_stat_statements
            WHERE mean_exec_time > 1000
        """)
        
        # Get database size
        db_size = await conn.fetchval("""
            SELECT pg_database_size(current_database()) / 1024.0 / 1024.0
        """)
        
        # Get cache hit ratio
        cache_hit = await conn.fetchval("""
            SELECT 
                sum(heap_blks_hit) / 
                NULLIF(sum(heap_blks_hit + heap_blks_read), 0)
            FROM pg_statio_user_tables
        """)
        
        return DatabaseMetrics(
            total_connections=conn_stats[0]['total'],
            active_connections=conn_stats[0]['active'],
            idle_connections=conn_stats[0]['idle'],
            slow_queries=slow_queries or 0,
            database_size_mb=float(db_size),
            cache_hit_ratio=float(cache_hit or 0)
        )
    
    def _determine_health_status(
        self,
        metrics: DatabaseMetrics
    ) -> HealthStatus:
        """Determine health status from metrics."""
        
        # Check connection pool usage
        pool_usage = metrics.active_connections / metrics.total_connections
        if pool_usage > 0.9:
            return HealthStatus.UNHEALTHY
        
        # Check cache hit ratio
        if metrics.cache_hit_ratio < 0.8:
            return HealthStatus.DEGRADED
        
        # Check slow queries
        if metrics.slow_queries > 100:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _get_empty_metrics(self) -> DatabaseMetrics:
        """Return empty metrics for error cases."""
        return DatabaseMetrics(
            total_connections=0,
            active_connections=0,
            idle_connections=0,
            slow_queries=0,
            database_size_mb=0.0,
            cache_hit_ratio=0.0
        )
    
    async def close(self) -> None:
        """Close database connections."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")


# ============================================================================
# Redis Health Monitor
# ============================================================================

class RedisHealthMonitor:
    """
    Redis health monitoring with clear separation of concerns.
    Single responsibility: Monitor and report Redis health.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        self.client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Redis client initialized")
    
    async def check_health(self) -> Tuple[HealthStatus, RedisMetrics]:
        """Check Redis health and return metrics."""
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        try:
            metrics = await self._collect_metrics()
            status = self._determine_health_status(metrics)
            return status, metrics
        
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return HealthStatus.UNHEALTHY, self._get_empty_metrics()
    
    async def _collect_metrics(self) -> RedisMetrics:
        """Collect Redis metrics."""
        
        info = await self.client.info()
        stats = await self.client.info('stats')
        
        used_memory = info.get('used_memory', 0)
        total_keys = sum([
            await self.client.dbsize()
            for _ in range(16)  # Default 16 databases
        ])
        
        keyspace_hits = stats.get('keyspace_hits', 0)
        keyspace_misses = stats.get('keyspace_misses', 0)
        hit_rate = (
            keyspace_hits / (keyspace_hits + keyspace_misses)
            if (keyspace_hits + keyspace_misses) > 0
            else 0.0
        )
        
        return RedisMetrics(
            used_memory_mb=used_memory / 1024 / 1024,
            total_keys=total_keys,
            hit_rate=hit_rate,
            evicted_keys=stats.get('evicted_keys', 0),
            connected_clients=info.get('connected_clients', 0)
        )
    
    def _determine_health_status(
        self,
        metrics: RedisMetrics
    ) -> HealthStatus:
        """Determine health status from metrics."""
        
        # Check memory usage (assuming 2GB max)
        if metrics.used_memory_mb > 1800:  # 90% of 2GB
            return HealthStatus.UNHEALTHY
        
        # Check hit rate
        if metrics.hit_rate < 0.7:
            return HealthStatus.DEGRADED
        
        # Check eviction rate
        if metrics.evicted_keys > 1000:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _get_empty_metrics(self) -> RedisMetrics:
        """Return empty metrics for error cases."""
        return RedisMetrics(
            used_memory_mb=0.0,
            total_keys=0,
            hit_rate=0.0,
            evicted_keys=0,
            connected_clients=0
        )
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis client closed")


# ============================================================================
# System Health Orchestrator
# ============================================================================

class SystemHealthOrchestrator:
    """
    Orchestrates health checks across all system components.
    Follows best practices of clear coordination.
    """
    
    def __init__(
        self,
        db_monitor: DatabaseHealthMonitor,
        redis_monitor: RedisHealthMonitor,
        metrics_collector: MetricsCollector
    ):
        self.db_monitor = db_monitor
        self.redis_monitor = redis_monitor
        self.metrics = metrics_collector
    
    async def perform_health_check(self) -> SystemHealth:
        """
        Perform comprehensive system health check.
        Single, clear purpose with descriptive return type.
        """
        
        # Check database
        db_status, db_metrics = await self.db_monitor.check_health()
        
        # Check Redis
        redis_status, redis_metrics = await self.redis_monitor.check_health()
        
        # Update Prometheus metrics
        self.metrics.update_database_metrics(db_metrics)
        self.metrics.update_redis_metrics(redis_metrics)
        
        # Determine overall status
        overall_status = self._determine_overall_status(
            db_status,
            redis_status
        )
        
        message = self._generate_status_message(
            overall_status,
            db_status,
            redis_status
        )
        
        return SystemHealth(
            status=overall_status,
            database=db_metrics,
            cache=redis_metrics,
            timestamp=datetime.utcnow(),
            message=message
        )
    
    def _determine_overall_status(
        self,
        db_status: HealthStatus,
        redis_status: HealthStatus
    ) -> HealthStatus:
        """Determine overall system health status."""
        
        if (db_status == HealthStatus.UNHEALTHY or
            redis_status == HealthStatus.UNHEALTHY):
            return HealthStatus.UNHEALTHY
        
        if (db_status == HealthStatus.DEGRADED or
            redis_status == HealthStatus.DEGRADED):
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _generate_status_message(
        self,
        overall: HealthStatus,
        db_status: HealthStatus,
        redis_status: HealthStatus
    ) -> str:
        """Generate human-readable status message."""
        
        if overall == HealthStatus.HEALTHY:
            return "All systems operational"
        
        issues = []
        if db_status != HealthStatus.HEALTHY:
            issues.append(f"Database: {db_status.value}")
        if redis_status != HealthStatus.HEALTHY:
            issues.append(f"Redis: {redis_status.value}")
        
        return f"System {overall.value}: {', '.join(issues)}"


# ============================================================================
# Performance Testing Utilities
# ============================================================================

class PerformanceTester:
    """
    Performance testing utilities following best practices.
    Single responsibility: Execute and report performance tests.
    """
    
    def __init__(self, base_url: str, target_rps: int = 1000):
        self.base_url = base_url
        self.target_rps = target_rps
        self.results: List[Dict] = []
    
    async def run_load_test(
        self,
        duration_seconds: int = 60
    ) -> Dict[str, float]:
        """
        Run load test with target RPS.
        Clear method name indicating its purpose.
        """
        
        logger.info(
            f"Starting load test: {self.target_rps} RPS "
            f"for {duration_seconds}s"
        )
        
        tasks = []
        for _ in range(duration_seconds * self.target_rps):
            tasks.append(self._make_request())
            
            # Rate limiting
            if len(tasks) >= self.target_rps:
                await asyncio.gather(*tasks)
                tasks = []
                await asyncio.sleep(1)
        
        # Wait for remaining requests
        if tasks:
            await asyncio.gather(*tasks)
        
        return self._calculate_statistics()
    
    async def _make_request(self) -> None:
        """Make single test request."""
        start_time = datetime.utcnow()
        
        try:
            # Simulate API call
            await asyncio.sleep(0.01)  # Replace with actual HTTP client
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            self.results.append({
                'duration': duration,
                'status': 200,
                'timestamp': start_time
            })
        
        except Exception as e:
            logger.error(f"Request failed: {e}")
            self.results.append({
                'duration': 0,
                'status': 500,
                'timestamp': start_time
            })
    
    def _calculate_statistics(self) -> Dict[str, float]:
        """Calculate performance statistics."""
        
        durations = [r['duration'] for r in self.results]
        successful = len([r for r in self.results if r['status'] == 200])
        
        durations.sort()
        
        return {
            'total_requests': len(self.results),
            'successful_requests': successful,
            'error_rate': 1 - (successful / len(self.results)),
            'mean_duration': sum(durations) / len(durations),
            'p50_duration': durations[int(len(durations) * 0.5)],
            'p95_duration': durations[int(len(durations) * 0.95)],
            'p99_duration': durations[int(len(durations) * 0.99)],
            'max_duration': max(durations)
        }


# ============================================================================
# Main Infrastructure Manager
# ============================================================================

class InfrastructureManager:
    """
    Main infrastructure management class.
    Coordinates all infrastructure components.
    """
    
    def __init__(
        self,
        database_url: str,
        redis_url: str,
        metrics_port: int = 9090
    ):
        self.db_monitor = DatabaseHealthMonitor(database_url)
        self.redis_monitor = RedisHealthMonitor(redis_url)
        self.metrics = MetricsCollector()
        self.orchestrator = SystemHealthOrchestrator(
            self.db_monitor,
            self.redis_monitor,
            self.metrics
        )
        self.metrics_port = metrics_port
    
    async def initialize(self) -> None:
        """Initialize all infrastructure components."""
        await self.db_monitor.initialize()
        await self.redis_monitor.initialize()
        start_http_server(self.metrics_port)
        logger.info("Infrastructure manager initialized")
    
    async def run_health_checks(self, interval_seconds: int = 30) -> None:
        """
        Run continuous health checks.
        Clear method purpose with appropriate parameters.
        """
        while True:
            try:
                health = await self.orchestrator.perform_health_check()
                
                logger.info(
                    f"Health check: {health.status.value} - "
                    f"{health.message}"
                )
                
                if health.status == HealthStatus.UNHEALTHY:
                    logger.error("System unhealthy - alerting required")
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all components."""
        await self.db_monitor.close()
        await self.redis_monitor.close()
        logger.info("Infrastructure manager shut down")


# ============================================================================
# CLI Entry Point
# ============================================================================

async def main() -> None:
    """Main entry point following best practices."""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = InfrastructureManager(
        database_url="postgresql://user:pass@localhost/bais",
        redis_url="redis://localhost:6379"
    )
    
    try:
        await manager.initialize()
        await manager.run_health_checks()
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
