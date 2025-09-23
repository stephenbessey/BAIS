"""
Circuit Breaker Monitoring API
Provides endpoints for monitoring circuit breaker states and health
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel

from ...core.circuit_breaker import get_circuit_breaker_manager, CircuitBreakerManager

router = APIRouter(prefix="/monitoring", tags=["Circuit Breaker Monitoring"])


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status response"""
    name: str
    state: str
    failure_count: int
    success_count: int
    last_failure_time: str = None
    last_success_time: str = None
    config: Dict[str, Any]


class CircuitBreakerSummary(BaseModel):
    """Summary of all circuit breakers"""
    total_circuits: int
    open_circuits: int
    half_open_circuits: int
    closed_circuits: int
    circuits: List[CircuitBreakerStatus]


@router.get("/circuit-breakers", response_model=CircuitBreakerSummary)
async def get_circuit_breaker_status(
    manager: CircuitBreakerManager = Depends(get_circuit_breaker_manager)
) -> CircuitBreakerSummary:
    """
    Get status of all circuit breakers in the system.
    
    Returns comprehensive information about circuit breaker states,
    failure counts, and configuration for monitoring purposes.
    """
    try:
        all_states = manager.get_all_states()
        
        circuits = []
        open_count = 0
        half_open_count = 0
        closed_count = 0
        
        for name, state in all_states.items():
            circuit_status = CircuitBreakerStatus(
                name=state["name"],
                state=state["state"],
                failure_count=state["failure_count"],
                success_count=state["success_count"],
                last_failure_time=state["last_failure_time"],
                last_success_time=state["last_success_time"],
                config=state["config"]
            )
            circuits.append(circuit_status)
            
            # Count states
            if state["state"] == "open":
                open_count += 1
            elif state["state"] == "half_open":
                half_open_count += 1
            elif state["state"] == "closed":
                closed_count += 1
        
        return CircuitBreakerSummary(
            total_circuits=len(circuits),
            open_circuits=open_count,
            half_open_circuits=half_open_count,
            closed_circuits=closed_count,
            circuits=circuits
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve circuit breaker status: {str(e)}"
        )


@router.get("/circuit-breakers/{circuit_name}", response_model=CircuitBreakerStatus)
async def get_circuit_breaker_detail(
    circuit_name: str,
    manager: CircuitBreakerManager = Depends(get_circuit_breaker_manager)
) -> CircuitBreakerStatus:
    """
    Get detailed status of a specific circuit breaker.
    
    Args:
        circuit_name: Name of the circuit breaker to retrieve
        
    Returns:
        Detailed status information for the specified circuit breaker
    """
    try:
        circuit = manager.get_circuit(circuit_name)
        if not circuit:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker '{circuit_name}' not found"
            )
        
        state = circuit.get_state()
        return CircuitBreakerStatus(
            name=state["name"],
            state=state["state"],
            failure_count=state["failure_count"],
            success_count=state["success_count"],
            last_failure_time=state["last_failure_time"],
            last_success_time=state["last_success_time"],
            config=state["config"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve circuit breaker '{circuit_name}': {str(e)}"
        )


@router.post("/circuit-breakers/{circuit_name}/reset")
async def reset_circuit_breaker(
    circuit_name: str,
    manager: CircuitBreakerManager = Depends(get_circuit_breaker_manager)
) -> Dict[str, str]:
    """
    Manually reset a specific circuit breaker to CLOSED state.
    
    This endpoint allows administrators to manually reset circuit breakers
    that may be stuck in OPEN state due to temporary issues.
    
    Args:
        circuit_name: Name of the circuit breaker to reset
        
    Returns:
        Success message confirming the reset
    """
    try:
        circuit = manager.get_circuit(circuit_name)
        if not circuit:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker '{circuit_name}' not found"
            )
        
        circuit.reset()
        
        return {
            "message": f"Circuit breaker '{circuit_name}' has been reset to CLOSED state",
            "circuit_name": circuit_name,
            "status": "reset"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset circuit breaker '{circuit_name}': {str(e)}"
        )


@router.post("/circuit-breakers/reset-all")
async def reset_all_circuit_breakers(
    manager: CircuitBreakerManager = Depends(get_circuit_breaker_manager)
) -> Dict[str, str]:
    """
    Reset all circuit breakers to CLOSED state.
    
    This endpoint allows administrators to reset all circuit breakers
    in the system, useful for recovery after system-wide issues.
    
    Returns:
        Success message confirming all resets
    """
    try:
        manager.reset_all()
        
        all_states = manager.get_all_states()
        circuit_count = len(all_states)
        
        return {
            "message": f"All {circuit_count} circuit breakers have been reset to CLOSED state",
            "circuits_reset": circuit_count,
            "status": "reset_all"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset all circuit breakers: {str(e)}"
        )


@router.get("/health")
async def get_system_health(
    manager: CircuitBreakerManager = Depends(get_circuit_breaker_manager)
) -> Dict[str, Any]:
    """
    Get overall system health based on circuit breaker states.
    
    Returns a health status that indicates if critical services
    are available or if there are any circuit breaker issues.
    """
    try:
        all_states = manager.get_all_states()
        
        # Analyze circuit breaker states
        critical_circuits = ["ap2_payment_execution", "ap2_mandate_operations", "a2a_discovery"]
        critical_issues = []
        warnings = []
        
        for name, state in all_states.items():
            if state["state"] == "open":
                if name in critical_circuits:
                    critical_issues.append(f"Critical circuit '{name}' is OPEN")
                else:
                    warnings.append(f"Circuit '{name}' is OPEN")
            elif state["state"] == "half_open":
                warnings.append(f"Circuit '{name}' is HALF_OPEN (testing recovery)")
        
        # Determine overall health status
        if critical_issues:
            health_status = "unhealthy"
            status_code = 503
        elif warnings:
            health_status = "degraded"
            status_code = 200
        else:
            health_status = "healthy"
            status_code = 200
        
        return {
            "status": health_status,
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "critical_issues": critical_issues,
            "warnings": warnings,
            "circuit_breaker_summary": {
                "total_circuits": len(all_states),
                "open_circuits": sum(1 for s in all_states.values() if s["state"] == "open"),
                "half_open_circuits": sum(1 for s in all_states.values() if s["state"] == "half_open"),
                "closed_circuits": sum(1 for s in all_states.values() if s["state"] == "closed")
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to determine system health: {str(e)}"
        )
