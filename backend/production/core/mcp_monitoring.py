"""
MCP Monitoring and Observability - Implementation
Comprehensive monitoring, metrics, and observability for MCP server
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json
import psutil
import threading
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics supported"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class HealthCheck:
    """Health check result"""
    name: str
    status: str  # "healthy", "unhealthy", "degraded"
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    request_count: int = 0
    error_count: int = 0
    average_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    throughput_rps: float = 0.0
    active_connections: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """Metrics collection following best practices"""
    
    def __init__(self, max_metrics_history: int = 1000):
        self._max_metrics_history = max_metrics_history
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics_history))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._make_key(name, labels or {})
            self._counters[key] += value
            self._record_metric(name, self._counters[key], labels or {}, MetricType.COUNTER)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        with self._lock:
            key = self._make_key(name, labels or {})
            self._gauges[key] = value
            self._record_metric(name, value, labels or {}, MetricType.GAUGE)
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram observation"""
        with self._lock:
            key = self._make_key(name, labels or {})
            self._histograms[key].append(value)
            # Keep only recent values for memory efficiency
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-500:]
            self._record_metric(name, value, labels or {}, MetricType.HISTOGRAM)
    
    def _record_metric(self, name: str, value: float, labels: Dict[str, str], metric_type: MetricType):
        """Record a metric data point"""
        metric = MetricPoint(
            name=name,
            value=value,
            labels=labels,
            timestamp=datetime.now(),
            metric_type=metric_type
        )
        self._metrics[name].append(metric)
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create a unique key for metric with labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"
    
    def get_counter(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get counter value"""
        with self._lock:
            key = self._make_key(name, labels or {})
            return self._counters.get(key, 0.0)
    
    def get_gauge(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get gauge value"""
        with self._lock:
            key = self._make_key(name, labels or {})
            return self._gauges.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get histogram statistics"""
        with self._lock:
            key = self._make_key(name, labels or {})
            values = self._histograms.get(key, [])
            
            if not values:
                return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0, "p99": 0.0}
            
            values_sorted = sorted(values)
            count = len(values)
            total = sum(values)
            avg = total / count
            
            return {
                "count": count,
                "sum": total,
                "avg": avg,
                "min": min(values),
                "max": max(values),
                "p95": self._percentile(values_sorted, 0.95),
                "p99": self._percentile(values_sorted, 0.99)
            }
    
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not sorted_values:
            return 0.0
        
        index = int(len(sorted_values) * percentile)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        with self._lock:
            summary = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {name: self.get_histogram_stats(name) for name in self._histograms.keys()},
                "timestamp": datetime.now().isoformat()
            }
            return summary


class HealthChecker:
    """Health check system following best practices"""
    
    def __init__(self):
        self._health_checks: Dict[str, Callable] = {}
        self._results: Dict[str, HealthCheck] = {}
        self._lock = threading.Lock()
    
    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self._health_checks[name] = check_func
    
    async def run_health_check(self, name: str) -> HealthCheck:
        """Run a specific health check"""
        if name not in self._health_checks:
            return HealthCheck(
                name=name,
                status="unhealthy",
                message=f"Health check '{name}' not found"
            )
        
        start_time = time.time()
        try:
            check_func = self._health_checks[name]
            result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
            
            response_time = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheck):
                result.response_time_ms = response_time
                return result
            elif isinstance(result, bool):
                return HealthCheck(
                    name=name,
                    status="healthy" if result else "unhealthy",
                    message="Health check completed",
                    response_time_ms=response_time
                )
            else:
                return HealthCheck(
                    name=name,
                    status="healthy",
                    message=str(result),
                    response_time_ms=response_time
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name=name,
                status="unhealthy",
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def run_all_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks"""
        tasks = [self.run_health_check(name) for name in self._health_checks.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        with self._lock:
            for i, result in enumerate(results):
                name = list(self._health_checks.keys())[i]
                if isinstance(result, Exception):
                    self._results[name] = HealthCheck(
                        name=name,
                        status="unhealthy",
                        message=f"Health check exception: {str(result)}"
                    )
                else:
                    self._results[name] = result
        
        return dict(self._results)
    
    def get_overall_health(self) -> str:
        """Get overall health status"""
        with self._lock:
            if not self._results:
                return "unknown"
            
            statuses = [result.status for result in self._results.values()]
            
            if all(status == "healthy" for status in statuses):
                return "healthy"
            elif any(status == "unhealthy" for status in statuses):
                return "unhealthy"
            else:
                return "degraded"


class SystemMetricsCollector:
    """System metrics collection following best practices"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics = metrics_collector
        self._last_cpu_times = None
    
    def collect_system_metrics(self):
        """Collect system-level metrics"""
        # Memory metrics
        memory = psutil.virtual_memory()
        self._metrics.set_gauge("system_memory_usage_percent", memory.percent)
        self._metrics.set_gauge("system_memory_usage_mb", memory.used / (1024 * 1024))
        self._metrics.set_gauge("system_memory_available_mb", memory.available / (1024 * 1024))
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        self._metrics.set_gauge("system_cpu_usage_percent", cpu_percent)
        
        # CPU times (for more detailed CPU metrics)
        cpu_times = psutil.cpu_times()
        if self._last_cpu_times is not None:
            cpu_time_delta = cpu_times.user - self._last_cpu_times.user + \
                           cpu_times.system - self._last_cpu_times.system
            total_time_delta = cpu_time_delta + (cpu_times.idle - self._last_cpu_times.idle)
            
            if total_time_delta > 0:
                cpu_usage = (cpu_time_delta / total_time_delta) * 100
                self._metrics.set_gauge("system_cpu_usage_detailed_percent", cpu_usage)
        
        self._last_cpu_times = cpu_times
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        self._metrics.set_gauge("system_disk_usage_percent", (disk.used / disk.total) * 100)
        self._metrics.set_gauge("system_disk_usage_gb", disk.used / (1024**3))
        self._metrics.set_gauge("system_disk_free_gb", disk.free / (1024**3))
        
        # Network metrics
        network = psutil.net_io_counters()
        self._metrics.set_gauge("system_network_bytes_sent", network.bytes_sent)
        self._metrics.set_gauge("system_network_bytes_recv", network.bytes_recv)
        self._metrics.set_gauge("system_network_packets_sent", network.packets_sent)
        self._metrics.set_gauge("system_network_packets_recv", network.packets_recv)


class MCPMetricsCollector:
    """MCP-specific metrics collection following best practices"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics = metrics_collector
        self._request_times: deque = deque(maxlen=1000)
        self._start_time = time.time()
    
    def record_request(self, method: str, endpoint: str, status_code: int, response_time_ms: float):
        """Record HTTP request metrics"""
        labels = {
            "method": method,
            "endpoint": endpoint,
            "status_code": str(status_code)
        }
        
        # Request count
        self._metrics.increment_counter("mcp_requests_total", labels=labels)
        
        # Response time histogram
        self._metrics.observe_histogram("mcp_request_duration_ms", response_time_ms, labels=labels)
        
        # Store for throughput calculation
        self._request_times.append(time.time())
        
        # Error count
        if status_code >= 400:
            self._metrics.increment_counter("mcp_errors_total", labels=labels)
    
    def record_tool_execution(self, tool_name: str, success: bool, execution_time_ms: float):
        """Record tool execution metrics"""
        labels = {
            "tool_name": tool_name,
            "success": str(success).lower()
        }
        
        self._metrics.increment_counter("mcp_tools_executed_total", labels=labels)
        self._metrics.observe_histogram("mcp_tool_execution_duration_ms", execution_time_ms, labels=labels)
    
    def record_resource_access(self, resource_uri: str, success: bool, access_time_ms: float):
        """Record resource access metrics"""
        labels = {
            "resource_uri": resource_uri,
            "success": str(success).lower()
        }
        
        self._metrics.increment_counter("mcp_resources_accessed_total", labels=labels)
        self._metrics.observe_histogram("mcp_resource_access_duration_ms", access_time_ms, labels=labels)
    
    def record_auth_attempt(self, success: bool, auth_method: str = "oauth"):
        """Record authentication attempt metrics"""
        labels = {
            "success": str(success).lower(),
            "auth_method": auth_method
        }
        
        self._metrics.increment_counter("mcp_auth_attempts_total", labels=labels)
    
    def record_rate_limit_hit(self, endpoint: str, client_id: str):
        """Record rate limit hit"""
        labels = {
            "endpoint": endpoint,
            "client_id": client_id
        }
        
        self._metrics.increment_counter("mcp_rate_limit_hits_total", labels=labels)
    
    def get_throughput_rps(self, window_seconds: int = 60) -> float:
        """Calculate requests per second over a time window"""
        cutoff_time = time.time() - window_seconds
        recent_requests = [t for t in self._request_times if t > cutoff_time]
        return len(recent_requests) / window_seconds
    
    def get_uptime_seconds(self) -> float:
        """Get server uptime in seconds"""
        return time.time() - self._start_time


class PerformanceMonitor:
    """Performance monitoring following best practices"""
    
    def __init__(self, metrics_collector: MetricsCollector, mcp_metrics: MCPMetricsCollector):
        self._metrics = metrics_collector
        self._mcp_metrics = mcp_metrics
        self._performance_data: deque = deque(maxlen=100)
    
    def collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect comprehensive performance metrics"""
        # Request metrics
        request_count = self._metrics.get_counter("mcp_requests_total")
        error_count = self._metrics.get_counter("mcp_errors_total")
        
        # Response time metrics
        response_time_stats = self._metrics.get_histogram_stats("mcp_request_duration_ms")
        avg_response_time = response_time_stats.get("avg", 0.0)
        p95_response_time = response_time_stats.get("p95", 0.0)
        p99_response_time = response_time_stats.get("p99", 0.0)
        
        # Throughput
        throughput_rps = self._mcp_metrics.get_throughput_rps()
        
        # System metrics
        memory_usage = self._metrics.get_gauge("system_memory_usage_mb")
        cpu_usage = self._metrics.get_gauge("system_cpu_usage_percent")
        
        # Active connections (placeholder - would need actual connection tracking)
        active_connections = self._metrics.get_gauge("mcp_active_connections", default=0.0)
        
        performance = PerformanceMetrics(
            request_count=int(request_count),
            error_count=int(error_count),
            average_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            throughput_rps=throughput_rps,
            active_connections=int(active_connections),
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage
        )
        
        self._performance_data.append(performance)
        return performance
    
    def get_performance_trend(self, window_minutes: int = 60) -> List[PerformanceMetrics]:
        """Get performance trend over time window"""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        return [p for p in self._performance_data if p.timestamp > cutoff_time]
    
    def detect_performance_issues(self) -> List[str]:
        """Detect potential performance issues"""
        issues = []
        
        if not self._performance_data:
            return issues
        
        latest = self._performance_data[-1]
        
        # High error rate
        if latest.request_count > 0 and (latest.error_count / latest.request_count) > 0.05:
            issues.append("High error rate detected (>5%)")
        
        # High response time
        if latest.p95_response_time_ms > 1000:
            issues.append("High response time detected (P95 > 1s)")
        
        # High memory usage
        if latest.memory_usage_mb > 1000:  # 1GB
            issues.append("High memory usage detected (>1GB)")
        
        # High CPU usage
        if latest.cpu_usage_percent > 80:
            issues.append("High CPU usage detected (>80%)")
        
        # Low throughput
        if latest.throughput_rps < 1:
            issues.append("Low throughput detected (<1 RPS)")
        
        return issues


class MonitoringService:
    """Central monitoring service following best practices"""
    
    def __init__(self, config: Any = None):  # MCPServerConfig
        self._config = config
        self._metrics = MetricsCollector()
        self._health_checker = HealthChecker()
        self._system_metrics = SystemMetricsCollector(self._metrics)
        self._mcp_metrics = MCPMetricsCollector(self._metrics)
        self._performance_monitor = PerformanceMonitor(self._metrics, self._mcp_metrics)
        self._monitoring_active = False
        self._monitoring_task = None
    
    async def start_monitoring(self):
        """Start monitoring service"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Register default health checks
        self._register_default_health_checks()
        
        logger.info("Monitoring service started")
    
    async def stop_monitoring(self):
        """Stop monitoring service"""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                # Collect system metrics
                self._system_metrics.collect_system_metrics()
                
                # Collect performance metrics
                self._performance_monitor.collect_performance_metrics()
                
                # Run health checks
                await self._health_checker.run_all_health_checks()
                
                # Sleep for monitoring interval
                await asyncio.sleep(60)  # 1 minute interval
            
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    def _register_default_health_checks(self):
        """Register default health checks"""
        
        async def database_health_check():
            """Check database connectivity"""
            try:
                # This would be implemented based on your database setup
                return HealthCheck(
                    name="database",
                    status="healthy",
                    message="Database connection successful"
                )
            except Exception as e:
                return HealthCheck(
                    name="database",
                    status="unhealthy",
                    message=f"Database connection failed: {e}"
                )
        
        async def redis_health_check():
            """Check Redis connectivity"""
            try:
                # This would be implemented based on your Redis setup
                return HealthCheck(
                    name="redis",
                    status="healthy",
                    message="Redis connection successful"
                )
            except Exception as e:
                return HealthCheck(
                    name="redis",
                    status="unhealthy",
                    message=f"Redis connection failed: {e}"
                )
        
        async def ap2_health_check():
            """Check AP2 service connectivity"""
            try:
                # This would be implemented based on your AP2 setup
                return HealthCheck(
                    name="ap2",
                    status="healthy",
                    message="AP2 service accessible"
                )
            except Exception as e:
                return HealthCheck(
                    name="ap2",
                    status="unhealthy",
                    message=f"AP2 service unavailable: {e}"
                )
        
        self._health_checker.register_health_check("database", database_health_check)
        self._health_checker.register_health_check("redis", redis_health_check)
        self._health_checker.register_health_check("ap2", ap2_health_check)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return self._metrics.get_metrics_summary()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status"""
        health_checks = await self._health_checker.run_all_health_checks()
        overall_health = self._health_checker.get_overall_health()
        
        return {
            "status": overall_health,
            "checks": {name: {
                "status": check.status,
                "message": check.message,
                "response_time_ms": check.response_time_ms,
                "timestamp": check.timestamp.isoformat()
            } for name, check in health_checks.items()},
            "timestamp": datetime.now().isoformat()
        }
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        return self._performance_monitor.collect_performance_metrics()
    
    def get_performance_issues(self) -> List[str]:
        """Get detected performance issues"""
        return self._performance_monitor.detect_performance_issues()
    
    # Metrics recording methods
    def record_request(self, method: str, endpoint: str, status_code: int, response_time_ms: float):
        """Record HTTP request metrics"""
        self._mcp_metrics.record_request(method, endpoint, status_code, response_time_ms)
    
    def record_tool_execution(self, tool_name: str, success: bool, execution_time_ms: float):
        """Record tool execution metrics"""
        self._mcp_metrics.record_tool_execution(tool_name, success, execution_time_ms)
    
    def record_resource_access(self, resource_uri: str, success: bool, access_time_ms: float):
        """Record resource access metrics"""
        self._mcp_metrics.record_resource_access(resource_uri, success, access_time_ms)
    
    def record_auth_attempt(self, success: bool, auth_method: str = "oauth"):
        """Record authentication attempt metrics"""
        self._mcp_metrics.record_auth_attempt(success, auth_method)
    
    def record_rate_limit_hit(self, endpoint: str, client_id: str):
        """Record rate limit hit"""
        self._mcp_metrics.record_rate_limit_hit(endpoint, client_id)


# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service(config: Any = None) -> MonitoringService:
    """Get global monitoring service instance"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService(config)
    return _monitoring_service


# Context manager for request timing
@asynccontextmanager
async def time_request(method: str, endpoint: str):
    """Context manager for timing HTTP requests"""
    start_time = time.time()
    status_code = 200
    
    try:
        yield
    except Exception as e:
        status_code = 500
        raise
    finally:
        response_time = (time.time() - start_time) * 1000
        monitoring = get_monitoring_service()
        monitoring.record_request(method, endpoint, status_code, response_time)


@asynccontextmanager
async def time_tool_execution(tool_name: str):
    """Context manager for timing tool execution"""
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        execution_time = (time.time() - start_time) * 1000
        monitoring = get_monitoring_service()
        monitoring.record_tool_execution(tool_name, success, execution_time)


@asynccontextmanager
async def time_resource_access(resource_uri: str):
    """Context manager for timing resource access"""
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        access_time = (time.time() - start_time) * 1000
        monitoring = get_monitoring_service()
        monitoring.record_resource_access(resource_uri, success, access_time)


if __name__ == "__main__":
    # Example usage
    async def main():
        monitoring = get_monitoring_service()
        await monitoring.start_monitoring()
        
        # Record some metrics
        monitoring.record_request("GET", "/health", 200, 50.0)
        monitoring.record_tool_execution("search_availability", True, 100.0)
        
        # Get metrics summary
        metrics = monitoring.get_metrics_summary()
        print("Metrics Summary:")
        print(json.dumps(metrics, indent=2))
        
        # Get health status
        health = await monitoring.get_health_status()
        print("\nHealth Status:")
        print(json.dumps(health, indent=2))
        
        await monitoring.stop_monitoring()
    
    asyncio.run(main())
