"""
Performance Monitoring System
Real-time performance metrics collection and reporting
"""

import psutil
import time
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
import asyncio
from collections import deque

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int
    request_count: int
    avg_response_time: float
    error_rate: float


class PerformanceMonitor:
    """
    Real-time performance monitoring
    Tracks system resources and application metrics
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics_history: deque = deque(maxlen=window_size)
        self.request_times: deque = deque(maxlen=1000)
        self.error_count = 0
        self.request_count = 0
        self._start_time = time.time()
        
    def record_request(self, response_time: float, is_error: bool = False):
        """Record individual request metrics"""
        self.request_times.append(response_time)
        self.request_count += 1
        if is_error:
            self.error_count += 1
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()
        
        # Application metrics
        avg_response_time = (
            sum(self.request_times) / len(self.request_times)
            if self.request_times else 0
        )
        error_rate = (
            (self.error_count / self.request_count * 100)
            if self.request_count > 0 else 0
        )
        
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_mb=memory.used / (1024 * 1024),
            disk_io_read_mb=disk_io.read_bytes / (1024 * 1024),
            disk_io_write_mb=disk_io.write_bytes / (1024 * 1024),
            network_sent_mb=network_io.bytes_sent / (1024 * 1024),
            network_recv_mb=network_io.bytes_recv / (1024 * 1024),
            active_connections=len(psutil.net_connections()),
            request_count=self.request_count,
            avg_response_time=avg_response_time,
            error_rate=error_rate
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of recent metrics"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = list(self.metrics_history)
        
        return {
            "avg_cpu_percent": sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            "max_cpu_percent": max(m.cpu_percent for m in recent_metrics),
            "avg_memory_percent": sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            "max_memory_mb": max(m.memory_mb for m in recent_metrics),
            "total_requests": self.request_count,
            "avg_response_time_ms": recent_metrics[-1].avg_response_time * 1000,
            "error_rate_percent": recent_metrics[-1].error_rate,
            "uptime_seconds": time.time() - self._start_time
        }
    
    def check_thresholds(self) -> List[str]:
        """Check if performance thresholds are exceeded"""
        warnings = []
        metrics = self.get_current_metrics()
        
        if metrics.cpu_percent > 80:
            warnings.append(f"HIGH CPU: {metrics.cpu_percent}%")
        
        if metrics.memory_percent > 85:
            warnings.append(f"HIGH MEMORY: {metrics.memory_percent}%")
        
        if metrics.avg_response_time > 0.2:  # 200ms threshold
            warnings.append(f"SLOW RESPONSE: {metrics.avg_response_time*1000:.2f}ms")
        
        if metrics.error_rate > 1:  # 1% error rate threshold
            warnings.append(f"HIGH ERROR RATE: {metrics.error_rate:.2f}%")
        
        return warnings


# Singleton instance
_performance_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """Get singleton performance monitor"""
    return _performance_monitor
