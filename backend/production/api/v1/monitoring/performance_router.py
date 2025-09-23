"""
Performance Monitoring API
Provides endpoints for monitoring connection pool performance and system metrics
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

from ...core.connection_pool_manager import (
    get_connection_pool_manager, 
    ConnectionPoolManager,
    PoolStats
)

router = APIRouter(prefix="/monitoring", tags=["Performance Monitoring"])


class PoolPerformanceMetrics(BaseModel):
    """Performance metrics for a connection pool"""
    pool_name: str
    total_connections: int
    active_connections: int
    idle_connections: int
    requests_per_second: float
    average_response_time_ms: float
    error_rate: float
    last_updated: str
    optimization_score: float


class SystemPerformanceSummary(BaseModel):
    """Overall system performance summary"""
    total_pools: int
    total_connections: int
    total_active_connections: int
    average_response_time_ms: float
    system_error_rate: float
    overall_optimization_score: float
    pools: List[PoolPerformanceMetrics]


@router.get("/performance/pools", response_model=SystemPerformanceSummary)
async def get_system_performance(
    manager: ConnectionPoolManager = Depends(get_connection_pool_manager)
) -> SystemPerformanceSummary:
    """
    Get comprehensive performance metrics for all connection pools.
    
    Returns detailed performance statistics including connection usage,
    response times, error rates, and optimization scores.
    """
    try:
        all_stats = await manager.get_all_stats()
        
        pools = []
        total_connections = 0
        total_active_connections = 0
        total_response_times = []
        total_errors = 0
        total_requests = 0
        
        for pool_name, stats in all_stats.items():
            # Calculate optimization score
            optimization_score = await manager.optimize_pool(pool_name)
            score = optimization_score.get("optimization_score", 0.0)
            
            pool_metrics = PoolPerformanceMetrics(
                pool_name=pool_name,
                total_connections=stats.total_connections,
                active_connections=stats.active_connections,
                idle_connections=stats.idle_connections,
                requests_per_second=stats.requests_per_second,
                average_response_time_ms=stats.average_response_time_ms,
                error_rate=stats.error_rate,
                last_updated=stats.last_updated.isoformat(),
                optimization_score=score
            )
            pools.append(pool_metrics)
            
            # Aggregate system metrics
            total_connections += stats.total_connections
            total_active_connections += stats.active_connections
            
            if stats.average_response_time_ms > 0:
                total_response_times.append(stats.average_response_time_ms)
            
            # Calculate total error rate
            pool_requests = stats.requests_per_second * 60  # Rough estimate
            total_requests += pool_requests
            total_errors += (stats.error_rate / 100) * pool_requests
        
        # Calculate system-wide metrics
        avg_response_time = sum(total_response_times) / len(total_response_times) if total_response_times else 0
        system_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        overall_optimization_score = sum(p.optimization_score for p in pools) / len(pools) if pools else 0
        
        return SystemPerformanceSummary(
            total_pools=len(pools),
            total_connections=total_connections,
            total_active_connections=total_active_connections,
            average_response_time_ms=avg_response_time,
            system_error_rate=system_error_rate,
            overall_optimization_score=overall_optimization_score,
            pools=pools
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance metrics: {str(e)}"
        )


@router.get("/performance/pools/{pool_name}", response_model=PoolPerformanceMetrics)
async def get_pool_performance(
    pool_name: str,
    manager: ConnectionPoolManager = Depends(get_connection_pool_manager)
) -> PoolPerformanceMetrics:
    """
    Get detailed performance metrics for a specific connection pool.
    
    Args:
        pool_name: Name of the connection pool to retrieve metrics for
        
    Returns:
        Detailed performance metrics for the specified pool
    """
    try:
        stats = await manager.get_pool_stats(pool_name)
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"Connection pool '{pool_name}' not found"
            )
        
        # Get optimization analysis
        optimization = await manager.optimize_pool(pool_name)
        optimization_score = optimization.get("optimization_score", 0.0)
        
        return PoolPerformanceMetrics(
            pool_name=pool_name,
            total_connections=stats.total_connections,
            active_connections=stats.active_connections,
            idle_connections=stats.idle_connections,
            requests_per_second=stats.requests_per_second,
            average_response_time_ms=stats.average_response_time_ms,
            error_rate=stats.error_rate,
            last_updated=stats.last_updated.isoformat(),
            optimization_score=optimization_score
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance metrics for pool '{pool_name}': {str(e)}"
        )


@router.get("/performance/optimizations/{pool_name}")
async def get_pool_optimizations(
    pool_name: str,
    manager: ConnectionPoolManager = Depends(get_connection_pool_manager)
) -> Dict[str, Any]:
    """
    Get optimization recommendations for a specific connection pool.
    
    Args:
        pool_name: Name of the connection pool to analyze
        
    Returns:
        Detailed optimization analysis and recommendations
    """
    try:
        optimization = await manager.optimize_pool(pool_name)
        
        if "error" in optimization:
            raise HTTPException(
                status_code=404,
                detail=optimization["error"]
            )
        
        return optimization
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze pool '{pool_name}': {str(e)}"
        )


@router.get("/performance/health")
async def get_performance_health(
    manager: ConnectionPoolManager = Depends(get_connection_pool_manager)
) -> Dict[str, Any]:
    """
    Get overall performance health status.
    
    Returns a health assessment based on connection pool performance
    metrics and optimization scores.
    """
    try:
        all_stats = await manager.get_all_stats()
        
        if not all_stats:
            return {
                "status": "no_data",
                "message": "No connection pools available",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Analyze performance health
        critical_issues = []
        warnings = []
        
        for pool_name, stats in all_stats.items():
            # Check response times
            if stats.average_response_time_ms > 2000:  # 2 seconds
                critical_issues.append(f"Pool '{pool_name}' has high response time: {stats.average_response_time_ms:.1f}ms")
            elif stats.average_response_time_ms > 1000:  # 1 second
                warnings.append(f"Pool '{pool_name}' has elevated response time: {stats.average_response_time_ms:.1f}ms")
            
            # Check error rates
            if stats.error_rate > 10:  # 10%
                critical_issues.append(f"Pool '{pool_name}' has high error rate: {stats.error_rate:.1f}%")
            elif stats.error_rate > 5:  # 5%
                warnings.append(f"Pool '{pool_name}' has elevated error rate: {stats.error_rate:.1f}%")
            
            # Check connection utilization
            if stats.total_connections > 0:
                utilization = (stats.active_connections / stats.total_connections) * 100
                if utilization > 90:
                    critical_issues.append(f"Pool '{pool_name}' is over-utilized: {utilization:.1f}%")
                elif utilization > 80:
                    warnings.append(f"Pool '{pool_name}' is highly utilized: {utilization:.1f}%")
        
        # Determine overall health status
        if critical_issues:
            health_status = "critical"
            status_code = 503
        elif warnings:
            health_status = "warning"
            status_code = 200
        else:
            health_status = "healthy"
            status_code = 200
        
        # Calculate overall metrics
        total_pools = len(all_stats)
        avg_response_time = sum(s.average_response_time_ms for s in all_stats.values()) / total_pools
        avg_error_rate = sum(s.error_rate for s in all_stats.values()) / total_pools
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "critical_issues": critical_issues,
            "warnings": warnings,
            "performance_summary": {
                "total_pools": total_pools,
                "average_response_time_ms": avg_response_time,
                "average_error_rate": avg_error_rate
            },
            "recommendations": _generate_performance_recommendations(critical_issues, warnings)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to determine performance health: {str(e)}"
        )


def _generate_performance_recommendations(critical_issues: List[str], warnings: List[str]) -> List[str]:
    """Generate performance optimization recommendations"""
    recommendations = []
    
    if any("response time" in issue.lower() for issue in critical_issues + warnings):
        recommendations.append("Consider increasing connection pool size or timeout settings")
    
    if any("error rate" in issue.lower() for issue in critical_issues + warnings):
        recommendations.append("Review error handling and retry logic")
        recommendations.append("Check network connectivity and service health")
    
    if any("utilized" in issue.lower() for issue in critical_issues + warnings):
        recommendations.append("Scale up connection pools or add more instances")
    
    if not recommendations:
        recommendations.append("Performance is within acceptable ranges")
    
    return recommendations
