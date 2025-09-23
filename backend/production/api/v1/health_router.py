"""
Health Check API Router
Provides endpoints for monitoring system health and external dependencies
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime

from ...monitoring.health_checks import (
    get_health_manager, 
    get_health_status, 
    get_service_health,
    initialize_health_checks,
    HealthStatus
)

router = APIRouter(prefix="/health", tags=["Health Checks"])


@router.get("/", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint
    
    Returns the overall health status of the system and all external dependencies.
    This endpoint is used by load balancers, monitoring systems, and DevOps tools.
    """
    try:
        return await get_health_status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/status", response_model=Dict[str, Any])
async def health_status() -> Dict[str, Any]:
    """
    Quick health status endpoint
    
    Returns a simplified health status for basic monitoring.
    Faster than the full health check endpoint.
    """
    try:
        manager = get_health_manager()
        summary = manager.get_health_summary()
        
        # Return appropriate HTTP status code based on health
        overall_status = summary["overall_status"]
        if overall_status == HealthStatus.HEALTHY.value:
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        elif overall_status == HealthStatus.DEGRADED.value:
            raise HTTPException(
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                detail="System is degraded - some services are experiencing issues"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="System is unhealthy - critical services are down"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health status check failed: {str(e)}"
        )


@router.get("/services", response_model=Dict[str, Any])
async def list_services() -> Dict[str, Any]:
    """
    List all monitored services and their current status
    
    Returns a list of all services being monitored by the health check system.
    """
    try:
        manager = get_health_manager()
        summary = manager.get_health_summary()
        
        return {
            "services": summary["services"],
            "total_services": summary["total_services"],
            "healthy_services": summary["healthy_services"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list services: {str(e)}"
        )


@router.get("/services/{service_name}", response_model=Dict[str, Any])
async def service_health_check(service_name: str) -> Dict[str, Any]:
    """
    Get detailed health information for a specific service
    
    Args:
        service_name: Name of the service to check
        
    Returns detailed health information including response times, errors, and last successful check.
    """
    try:
        result = await get_service_health(service_name)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        # Return appropriate HTTP status code based on service health
        service_status = result["status"]
        if service_status == HealthStatus.HEALTHY.value:
            return result
        elif service_status == HealthStatus.DEGRADED.value:
            raise HTTPException(
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                detail=f"Service '{service_name}' is degraded",
                headers={"X-Service-Status": service_status}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service '{service_name}' is unhealthy",
                headers={"X-Service-Status": service_status}
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check service health: {str(e)}"
        )


@router.post("/services/{service_name}/check")
async def trigger_service_check(service_name: str) -> Dict[str, Any]:
    """
    Manually trigger a health check for a specific service
    
    Args:
        service_name: Name of the service to check
        
    This endpoint allows manual triggering of health checks for testing or debugging.
    """
    try:
        result = await get_service_health(service_name)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "message": f"Health check triggered for service '{service_name}'",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger service check: {str(e)}"
        )


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness probe endpoint
    
    Used by Kubernetes and other orchestration systems to determine if the service
    is ready to receive traffic. Only checks critical dependencies.
    """
    try:
        manager = get_health_manager()
        
        # Check only critical services for readiness
        critical_services = ["postgresql_database", "redis_cache"]
        critical_statuses = {}
        
        for service_name in critical_services:
            status = manager.get_service_status(service_name)
            critical_statuses[service_name] = status
        
        # All critical services must be healthy for readiness
        all_critical_healthy = all(
            status == HealthStatus.HEALTHY
            for status in critical_statuses.values()
        )
        
        if all_critical_healthy:
            return {
                "status": "ready",
                "critical_services": {name: status.value for name, status in critical_statuses.items()},
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service is not ready - critical dependencies are unhealthy",
                headers={"X-Critical-Services": str(critical_statuses)}
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Readiness check failed: {str(e)}"
        )


@router.get("/live", response_model=Dict[str, Any])
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe endpoint
    
    Used by Kubernetes and other orchestration systems to determine if the service
    is alive and should not be restarted. This is a simple check that doesn't depend
    on external services.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "running"  # In a real implementation, you'd calculate actual uptime
    }


# Initialize health checks when the module is imported
initialize_health_checks()
