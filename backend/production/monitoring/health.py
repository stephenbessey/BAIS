"""
Enhanced Health Check System with AP2 Integration Status
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx
from sqlalchemy.orm import Session

from ..core.database_models import DatabaseManager
from ..config.ap2_settings import get_ap2_settings
from ..core.payments.ap2_client import AP2Client


class HealthCheckResult:
    """Represents the result of a health check"""
    
    def __init__(self, name: str, status: str, details: Dict[str, Any] = None):
        self.name = name
        self.status = status  # "healthy", "degraded", "unhealthy"
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class AP2HealthChecker:
    """Health checker for AP2 integration components"""
    
    def __init__(self):
        self.ap2_settings = get_ap2_settings()
        self.timeout = 10
    
    async def check_ap2_connectivity(self) -> HealthCheckResult:
        """Check connectivity to AP2 network"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test basic connectivity to AP2 network
                response = await client.get(f"{self.ap2_settings.ap2_network_url}/health")
                
                if response.status_code == 200:
                    return HealthCheckResult(
                        name="ap2_connectivity",
                        status="healthy",
                        details={
                            "network_url": self.ap2_settings.ap2_network_url,
                            "response_time_ms": response.elapsed.total_seconds() * 1000
                        }
                    )
                else:
                    return HealthCheckResult(
                        name="ap2_connectivity",
                        status="degraded",
                        details={
                            "network_url": self.ap2_settings.ap2_network_url,
                            "status_code": response.status_code
                        }
                    )
                    
        except httpx.TimeoutException:
            return HealthCheckResult(
                name="ap2_connectivity",
                status="unhealthy",
                details={"error": "Connection timeout"}
            )
        except Exception as e:
            return HealthCheckResult(
                name="ap2_connectivity",
                status="unhealthy",
                details={"error": str(e)}
            )
    
    async def check_ap2_keys(self) -> HealthCheckResult:
        """Check AP2 cryptographic keys"""
        try:
            # Verify private key can be loaded
            with open(self.ap2_settings.ap2_private_key_path, 'r') as f:
                private_key_content = f.read()
            
            # Verify public key can be loaded
            with open(self.ap2_settings.ap2_public_key_path, 'r') as f:
                public_key_content = f.read()
            
            # Basic validation
            if "BEGIN PRIVATE KEY" in private_key_content and "BEGIN PUBLIC KEY" in public_key_content:
                return HealthCheckResult(
                    name="ap2_keys",
                    status="healthy",
                    details={
                        "private_key_path": self.ap2_settings.ap2_private_key_path,
                        "public_key_path": self.ap2_settings.ap2_public_key_path
                    }
                )
            else:
                return HealthCheckResult(
                    name="ap2_keys",
                    status="unhealthy",
                    details={"error": "Invalid key format"}
                )
                
        except FileNotFoundError as e:
            return HealthCheckResult(
                name="ap2_keys",
                status="unhealthy",
                details={"error": f"Key file not found: {str(e)}"}
            )
        except Exception as e:
            return HealthCheckResult(
                name="ap2_keys",
                status="unhealthy",
                details={"error": str(e)}
            )


class DatabaseHealthChecker:
    """Health checker for database components"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def check_database_connection(self) -> HealthCheckResult:
        """Check database connectivity"""
        try:
            with self.db_manager.get_session() as session:
                # Simple query to test connection
                result = session.execute("SELECT 1").fetchone()
                
                if result and result[0] == 1:
                    return HealthCheckResult(
                        name="database",
                        status="healthy",
                        details={"connection": "successful"}
                    )
                else:
                    return HealthCheckResult(
                        name="database",
                        status="unhealthy",
                        details={"error": "Invalid query result"}
                    )
                    
        except Exception as e:
            return HealthCheckResult(
                name="database",
                status="unhealthy",
                details={"error": str(e)}
            )
    
    async def check_payment_tables(self) -> HealthCheckResult:
        """Check AP2 payment tables exist and are accessible"""
        try:
            with self.db_manager.get_session() as session:
                # Check payment_workflow_logs table
                result = session.execute(
                    "SELECT COUNT(*) FROM payment_workflow_logs WHERE created_at > %s",
                    (datetime.utcnow() - timedelta(days=1),)
                ).fetchone()
                
                recent_workflows = result[0] if result else 0
                
                return HealthCheckResult(
                    name="payment_tables",
                    status="healthy",
                    details={
                        "recent_workflows_24h": recent_workflows,
                        "table_accessible": True
                    }
                )
                
        except Exception as e:
            return HealthCheckResult(
                name="payment_tables",
                status="unhealthy",
                details={"error": str(e)}
            )


class ComprehensiveHealthChecker:
    """Comprehensive health checker for BAIS with AP2 integration"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.ap2_checker = AP2HealthChecker()
        self.db_checker = DatabaseHealthChecker(db_manager)
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status"""
        checks = await asyncio.gather(
            self.ap2_checker.check_ap2_connectivity(),
            self.ap2_checker.check_ap2_keys(),
            self.db_checker.check_database_connection(),
            self.db_checker.check_payment_tables(),
            return_exceptions=True
        )
        
        # Process results
        results = {}
        overall_status = "healthy"
        
        for check in checks:
            if isinstance(check, Exception):
                results["internal_error"] = {
                    "status": "unhealthy",
                    "error": str(check)
                }
                overall_status = "unhealthy"
                continue
            
            results[check.name] = {
                "status": check.status,
                "details": check.details,
                "timestamp": check.timestamp.isoformat()
            }
            
            # Update overall status
            if check.status == "unhealthy":
                overall_status = "unhealthy"
            elif check.status == "degraded" and overall_status == "healthy":
                overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results,
            "summary": {
                "total_checks": len([c for c in checks if not isinstance(c, Exception)]),
                "healthy_checks": len([c for c in checks if not isinstance(c, Exception) and c.status == "healthy"]),
                "degraded_checks": len([c for c in checks if not isinstance(c, Exception) and c.status == "degraded"]),
                "unhealthy_checks": len([c for c in checks if not isinstance(c, Exception) and c.status == "unhealthy"])
            }
        }
