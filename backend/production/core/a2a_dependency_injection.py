"""
A2A Dependency Injection Solution
Eliminates global state violation using proper DI patterns
"""

from typing import Optional
from fastapi import Depends
from .a2a_processor_manager import A2AProcessorManager, A2AConfiguration
from .payments.ap2_client import AP2ClientConfig
from ..config.settings import get_settings


class A2AProcessorManagerFactory:
    """Factory for creating A2A processor managers with proper DI"""
    
    _instance: Optional[A2AProcessorManager] = None
    _config: Optional[A2AConfiguration] = None
    
    @classmethod
    def create_manager(cls, 
                      config: A2AConfiguration,
                      business_config: dict,
                      ap2_config: Optional[AP2ClientConfig] = None) -> A2AProcessorManager:
        """Create processor manager with configuration"""
        return A2AProcessorManager(config, business_config, ap2_config)
    
    @classmethod 
    def get_or_create_manager(cls) -> A2AProcessorManager:
        """Get existing manager or create new one"""
        if cls._instance is None:
            settings = get_settings()
            config = A2AConfiguration()
            business_config = settings.business.dict()
            ap2_config = settings.ap2 if settings.ap2.enabled else None
            
            cls._instance = cls.create_manager(config, business_config, ap2_config)
        
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset for testing"""
        cls._instance = None


# FastAPI dependency
def get_processor_manager() -> A2AProcessorManager:
    """FastAPI dependency for A2A processor manager"""
    return A2AProcessorManagerFactory.get_or_create_manager()


# Updated route with proper DI
# backend/production/api/v1/a2a/tasks.py
@router.post("/tasks", response_model=A2ATaskStatus)
async def submit_task(
    request: A2ATaskRequest,
    manager: A2AProcessorManager = Depends(get_processor_manager)  # ✅ Clean DI
) -> A2ATaskStatus:
    """Submit A2A task with proper dependency injection"""
    try:
        processor = await manager.get_processor()
        
        # Validate against configuration
        if request.timeout_seconds > manager.config.MAX_TASK_TIMEOUT_SECONDS:
            raise ValidationError(f"Timeout exceeds maximum of {manager.config.MAX_TASK_TIMEOUT_SECONDS}s")
        
        # Process task
        status = A2ATaskStatus(task_id=request.task_id, status="pending")
        processor.active_tasks[request.task_id] = status
        
        # Execute asynchronously
        asyncio.create_task(_execute_task(processor, request))
        return status
        
    except Exception as e:
        # Proper error handling
        raise HTTPException(status_code=500, detail=str(e))
