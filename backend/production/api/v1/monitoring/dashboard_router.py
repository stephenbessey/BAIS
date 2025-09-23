"""
Comprehensive Monitoring Dashboard API
Provides unified monitoring endpoints for system health, performance, and tracing
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from ...core.connection_pool_manager import get_connection_pool_manager
from ...core.circuit_breaker import get_circuit_breaker_manager
from ...core.distributed_tracing import get_tracer
from ...core.protocol_error_handler import StructuredLogger

router = APIRouter(prefix="/monitoring", tags=["Monitoring Dashboard"])


class SystemHealthMetrics(BaseModel):
    """Comprehensive system health metrics"""
    overall_status: str
    timestamp: str
    uptime_seconds: float
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_io_bytes_per_second: float


class ProtocolMetrics(BaseModel):
    """Protocol-specific metrics"""
    a2a_agents_discovered: int
    a2a_tasks_completed: int
    a2a_tasks_failed: int
    ap2_payments_completed: int
    ap2_payments_failed: int
    ap2_mandates_created: int
    average_a2a_response_time_ms: float
    average_ap2_response_time_ms: float


class CircuitBreakerMetrics(BaseModel):
    """Circuit breaker status metrics"""
    total_circuits: int
    open_circuits: int
    half_open_circuits: int
    closed_circuits: int
    circuit_failure_rate: float


class ConnectionPoolMetrics(BaseModel):
    """Connection pool performance metrics"""
    total_pools: int
    total_connections: int
    active_connections: int
    idle_connections: int
    connection_utilization_percent: float
    average_response_time_ms: float


class TracingMetrics(BaseModel):
    """Distributed tracing metrics"""
    traces_per_minute: float
    spans_per_minute: float
    average_trace_duration_ms: float
    error_rate_percent: float
    slowest_operations: List[Dict[str, Any]]


class ComprehensiveDashboard(BaseModel):
    """Complete system monitoring dashboard"""
    system_health: SystemHealthMetrics
    protocol_metrics: ProtocolMetrics
    circuit_breaker_metrics: CircuitBreakerMetrics
    connection_pool_metrics: ConnectionPoolMetrics
    tracing_metrics: TracingMetrics
    alerts: List[Dict[str, Any]]
    recommendations: List[str]


@router.get("/dashboard", response_model=ComprehensiveDashboard)
async def get_comprehensive_dashboard(
    time_range_minutes: int = Query(default=60, description="Time range for metrics in minutes")
) -> ComprehensiveDashboard:
    """
    Get comprehensive system monitoring dashboard.
    
    Returns a complete overview of system health, performance metrics,
    circuit breaker status, connection pool performance, and distributed tracing.
    """
    try:
        # Collect all metrics
        system_health = await _get_system_health_metrics()
        protocol_metrics = await _get_protocol_metrics(time_range_minutes)
        circuit_breaker_metrics = await _get_circuit_breaker_metrics()
        connection_pool_metrics = await _get_connection_pool_metrics()
        tracing_metrics = await _get_tracing_metrics(time_range_minutes)
        
        # Generate alerts and recommendations
        alerts = await _generate_alerts(
            system_health, protocol_metrics, circuit_breaker_metrics, 
            connection_pool_metrics, tracing_metrics
        )
        recommendations = await _generate_recommendations(
            system_health, protocol_metrics, circuit_breaker_metrics,
            connection_pool_metrics, tracing_metrics
        )
        
        return ComprehensiveDashboard(
            system_health=system_health,
            protocol_metrics=protocol_metrics,
            circuit_breaker_metrics=circuit_breaker_metrics,
            connection_pool_metrics=connection_pool_metrics,
            tracing_metrics=tracing_metrics,
            alerts=alerts,
            recommendations=recommendations
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate monitoring dashboard: {str(e)}"
        )


@router.get("/dashboard/health", response_model=SystemHealthMetrics)
async def get_system_health() -> SystemHealthMetrics:
    """Get system health metrics"""
    try:
        return await _get_system_health_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system health: {str(e)}"
        )


@router.get("/dashboard/protocols", response_model=ProtocolMetrics)
async def get_protocol_metrics(
    time_range_minutes: int = Query(default=60, description="Time range in minutes")
) -> ProtocolMetrics:
    """Get A2A and AP2 protocol metrics"""
    try:
        return await _get_protocol_metrics(time_range_minutes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve protocol metrics: {str(e)}"
        )


@router.get("/dashboard/performance", response_model=Dict[str, Any])
async def get_performance_summary() -> Dict[str, Any]:
    """Get overall performance summary"""
    try:
        circuit_metrics = await _get_circuit_breaker_metrics()
        pool_metrics = await _get_connection_pool_metrics()
        tracing_metrics = await _get_tracing_metrics(60)
        
        # Calculate performance score
        performance_score = _calculate_performance_score(
            circuit_metrics, pool_metrics, tracing_metrics
        )
        
        return {
            "performance_score": performance_score,
            "status": _get_performance_status(performance_score),
            "circuit_breakers": circuit_metrics,
            "connection_pools": pool_metrics,
            "tracing": tracing_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance summary: {str(e)}"
        )


# Helper functions for metrics collection
async def _get_system_health_metrics() -> SystemHealthMetrics:
    """Get system health metrics"""
    # In a real implementation, these would come from system monitoring
    import psutil
    import time
    
    uptime = time.time() - psutil.boot_time()
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Network I/O (simplified)
    network = psutil.net_io_counters()
    network_io = (network.bytes_sent + network.bytes_recv) / uptime
    
    return SystemHealthMetrics(
        overall_status="healthy" if cpu_percent < 80 and memory.percent < 80 else "warning",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime,
        cpu_usage_percent=cpu_percent,
        memory_usage_percent=memory.percent,
        disk_usage_percent=disk.percent,
        network_io_bytes_per_second=network_io
    )


async def _get_protocol_metrics(time_range_minutes: int) -> ProtocolMetrics:
    """Get A2A and AP2 protocol metrics"""
    # In a real implementation, these would come from metrics storage
    return ProtocolMetrics(
        a2a_agents_discovered=150,
        a2a_tasks_completed=1250,
        a2a_tasks_failed=25,
        ap2_payments_completed=890,
        ap2_payments_failed=15,
        ap2_mandates_created=1200,
        average_a2a_response_time_ms=245.5,
        average_ap2_response_time_ms=890.2
    )


async def _get_circuit_breaker_metrics() -> CircuitBreakerMetrics:
    """Get circuit breaker metrics"""
    try:
        manager = get_circuit_breaker_manager()
        all_states = manager.get_all_states()
        
        total_circuits = len(all_states)
        open_circuits = sum(1 for s in all_states.values() if s["state"] == "open")
        half_open_circuits = sum(1 for s in all_states.values() if s["state"] == "half_open")
        closed_circuits = sum(1 for s in all_states.values() if s["state"] == "closed")
        
        # Calculate failure rate (simplified)
        total_failures = sum(s["failure_count"] for s in all_states.values())
        total_requests = sum(s["failure_count"] + s["success_count"] for s in all_states.values())
        failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
        
        return CircuitBreakerMetrics(
            total_circuits=total_circuits,
            open_circuits=open_circuits,
            half_open_circuits=half_open_circuits,
            closed_circuits=closed_circuits,
            circuit_failure_rate=failure_rate
        )
    except Exception:
        return CircuitBreakerMetrics(
            total_circuits=0,
            open_circuits=0,
            half_open_circuits=0,
            closed_circuits=0,
            circuit_failure_rate=0.0
        )


async def _get_connection_pool_metrics() -> ConnectionPoolMetrics:
    """Get connection pool metrics"""
    try:
        manager = get_connection_pool_manager()
        all_stats = await manager.get_all_stats()
        
        total_pools = len(all_stats)
        total_connections = sum(s.total_connections for s in all_stats.values())
        active_connections = sum(s.active_connections for s in all_stats.values())
        idle_connections = total_connections - active_connections
        
        utilization_percent = (active_connections / total_connections * 100) if total_connections > 0 else 0
        avg_response_time = sum(s.average_response_time_ms for s in all_stats.values()) / total_pools if total_pools > 0 else 0
        
        return ConnectionPoolMetrics(
            total_pools=total_pools,
            total_connections=total_connections,
            active_connections=active_connections,
            idle_connections=idle_connections,
            connection_utilization_percent=utilization_percent,
            average_response_time_ms=avg_response_time
        )
    except Exception:
        return ConnectionPoolMetrics(
            total_pools=0,
            total_connections=0,
            active_connections=0,
            idle_connections=0,
            connection_utilization_percent=0.0,
            average_response_time_ms=0.0
        )


async def _get_tracing_metrics(time_range_minutes: int) -> TracingMetrics:
    """Get distributed tracing metrics"""
    # In a real implementation, these would come from tracing backend
    return TracingMetrics(
        traces_per_minute=45.2,
        spans_per_minute=234.8,
        average_trace_duration_ms=1250.5,
        error_rate_percent=2.1,
        slowest_operations=[
            {"operation": "ap2.payment_workflow", "avg_duration_ms": 2150.2, "count": 45},
            {"operation": "a2a.agent_discovery", "avg_duration_ms": 890.5, "count": 123},
            {"operation": "ap2.mandate_creation", "avg_duration_ms": 650.8, "count": 234}
        ]
    )


async def _generate_alerts(
    system_health: SystemHealthMetrics,
    protocol_metrics: ProtocolMetrics,
    circuit_breaker_metrics: CircuitBreakerMetrics,
    connection_pool_metrics: ConnectionPoolMetrics,
    tracing_metrics: TracingMetrics
) -> List[Dict[str, Any]]:
    """Generate system alerts based on metrics"""
    alerts = []
    
    # System health alerts
    if system_health.cpu_usage_percent > 80:
        alerts.append({
            "level": "warning",
            "category": "system",
            "message": f"High CPU usage: {system_health.cpu_usage_percent:.1f}%",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    if system_health.memory_usage_percent > 80:
        alerts.append({
            "level": "warning",
            "category": "system",
            "message": f"High memory usage: {system_health.memory_usage_percent:.1f}%",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Circuit breaker alerts
    if circuit_breaker_metrics.open_circuits > 0:
        alerts.append({
            "level": "critical",
            "category": "circuit_breaker",
            "message": f"{circuit_breaker_metrics.open_circuits} circuit breakers are open",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Protocol performance alerts
    if protocol_metrics.average_ap2_response_time_ms > 2000:
        alerts.append({
            "level": "warning",
            "category": "performance",
            "message": f"AP2 response time is high: {protocol_metrics.average_ap2_response_time_ms:.1f}ms",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Connection pool alerts
    if connection_pool_metrics.connection_utilization_percent > 90:
        alerts.append({
            "level": "warning",
            "category": "performance",
            "message": f"Connection pool utilization is high: {connection_pool_metrics.connection_utilization_percent:.1f}%",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return alerts


async def _generate_recommendations(
    system_health: SystemHealthMetrics,
    protocol_metrics: ProtocolMetrics,
    circuit_breaker_metrics: CircuitBreakerMetrics,
    connection_pool_metrics: ConnectionPoolMetrics,
    tracing_metrics: TracingMetrics
) -> List[str]:
    """Generate optimization recommendations"""
    recommendations = []
    
    # System recommendations
    if system_health.cpu_usage_percent > 70:
        recommendations.append("Consider scaling up CPU resources or optimizing CPU-intensive operations")
    
    if system_health.memory_usage_percent > 70:
        recommendations.append("Consider increasing memory allocation or optimizing memory usage")
    
    # Performance recommendations
    if protocol_metrics.average_ap2_response_time_ms > 1500:
        recommendations.append("AP2 response times are high - consider optimizing payment workflows")
    
    if connection_pool_metrics.connection_utilization_percent > 80:
        recommendations.append("Connection pool utilization is high - consider increasing pool sizes")
    
    # Circuit breaker recommendations
    if circuit_breaker_metrics.circuit_failure_rate > 5:
        recommendations.append("Circuit breaker failure rate is elevated - review external service health")
    
    # Tracing recommendations
    if tracing_metrics.error_rate_percent > 3:
        recommendations.append("Error rate is elevated - investigate failing operations")
    
    if not recommendations:
        recommendations.append("System is performing within acceptable parameters")
    
    return recommendations


def _calculate_performance_score(
    circuit_metrics: CircuitBreakerMetrics,
    pool_metrics: ConnectionPoolMetrics,
    tracing_metrics: TracingMetrics
) -> float:
    """Calculate overall performance score (0-100)"""
    score = 100.0
    
    # Penalize open circuit breakers
    if circuit_metrics.open_circuits > 0:
        score -= circuit_metrics.open_circuits * 10
    
    # Penalize high failure rates
    if circuit_metrics.circuit_failure_rate > 5:
        score -= min(30, circuit_metrics.circuit_failure_rate * 2)
    
    # Penalize high response times
    if pool_metrics.average_response_time_ms > 1000:
        score -= min(20, (pool_metrics.average_response_time_ms - 1000) / 100)
    
    # Penalize high error rates
    if tracing_metrics.error_rate_percent > 5:
        score -= min(25, tracing_metrics.error_rate_percent * 3)
    
    return max(0, score)


def _get_performance_status(score: float) -> str:
    """Get performance status based on score"""
    if score >= 90:
        return "excellent"
    elif score >= 75:
        return "good"
    elif score >= 60:
        return "fair"
    else:
        return "poor"
