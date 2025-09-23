"""
Workflow State Manager - Clean Code Solution
Eliminates global state violations using proper dependency injection and storage abstraction
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from .payments.models import PaymentWorkflow, PaymentStatus
from .exceptions import ValidationError, NotFoundError


class WorkflowStorage(ABC):
    """Abstract interface for workflow storage - follows Dependency Inversion Principle"""
    
    @abstractmethod
    async def store_workflow(self, workflow: PaymentWorkflow) -> None:
        """Store a payment workflow"""
        pass
    
    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> Optional[PaymentWorkflow]:
        """Retrieve a payment workflow by ID"""
        pass
    
    @abstractmethod
    async def update_workflow(self, workflow: PaymentWorkflow) -> None:
        """Update an existing workflow"""
        pass
    
    @abstractmethod
    async def delete_workflow(self, workflow_id: str) -> None:
        """Delete a workflow"""
        pass
    
    @abstractmethod
    async def list_workflows(self, 
                           business_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           status: Optional[PaymentStatus] = None,
                           limit: int = 100,
                           offset: int = 0) -> List[PaymentWorkflow]:
        """List workflows with filtering"""
        pass


class InMemoryWorkflowStorage(WorkflowStorage):
    """In-memory workflow storage implementation for development/testing"""
    
    def __init__(self):
        self._workflows: Dict[str, PaymentWorkflow] = {}
        self._lock = asyncio.Lock()
    
    async def store_workflow(self, workflow: PaymentWorkflow) -> None:
        """Store workflow in memory"""
        async with self._lock:
            self._workflows[workflow.id] = workflow
    
    async def get_workflow(self, workflow_id: str) -> Optional[PaymentWorkflow]:
        """Retrieve workflow from memory"""
        async with self._lock:
            return self._workflows.get(workflow_id)
    
    async def update_workflow(self, workflow: PaymentWorkflow) -> None:
        """Update workflow in memory"""
        async with self._lock:
            if workflow.id in self._workflows:
                self._workflows[workflow.id] = workflow
            else:
                raise NotFoundError(f"Workflow {workflow.id} not found")
    
    async def delete_workflow(self, workflow_id: str) -> None:
        """Delete workflow from memory"""
        async with self._lock:
            if workflow_id in self._workflows:
                del self._workflows[workflow_id]
            else:
                raise NotFoundError(f"Workflow {workflow_id} not found")
    
    async def list_workflows(self, 
                           business_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           status: Optional[PaymentStatus] = None,
                           limit: int = 100,
                           offset: int = 0) -> List[PaymentWorkflow]:
        """List workflows with filtering"""
        async with self._lock:
            workflows = list(self._workflows.values())
            
            # Apply filters
            if business_id:
                workflows = [w for w in workflows if w.business_id == business_id]
            if user_id:
                workflows = [w for w in workflows if w.user_id == user_id]
            if status:
                workflows = [w for w in workflows if w.status == status]
            
            # Apply pagination
            return workflows[offset:offset + limit]


class DatabaseWorkflowStorage(WorkflowStorage):
    """Database workflow storage implementation for production"""
    
    def __init__(self, db_manager):
        self._db_manager = db_manager
    
    async def store_workflow(self, workflow: PaymentWorkflow) -> None:
        """Store workflow in database"""
        # Implementation would use SQLAlchemy or similar ORM
        # For now, placeholder implementation
        pass
    
    async def get_workflow(self, workflow_id: str) -> Optional[PaymentWorkflow]:
        """Retrieve workflow from database"""
        # Implementation would query database
        # For now, placeholder implementation
        return None
    
    async def update_workflow(self, workflow: PaymentWorkflow) -> None:
        """Update workflow in database"""
        # Implementation would update database record
        pass
    
    async def delete_workflow(self, workflow_id: str) -> None:
        """Delete workflow from database"""
        # Implementation would delete database record
        pass
    
    async def list_workflows(self, 
                           business_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           status: Optional[PaymentStatus] = None,
                           limit: int = 100,
                           offset: int = 0) -> List[PaymentWorkflow]:
        """List workflows with filtering from database"""
        # Implementation would query database with filters
        return []


@dataclass
class WorkflowStateManagerConfig:
    """Configuration for workflow state manager"""
    cleanup_interval_minutes: int = 60
    max_workflow_age_hours: int = 24
    enable_cleanup: bool = True


class WorkflowStateManager:
    """
    Manages payment workflow state with proper dependency injection.
    Eliminates global state violations by using storage abstraction.
    """
    
    def __init__(self, storage: WorkflowStorage, config: WorkflowStateManagerConfig = None):
        self._storage = storage
        self._config = config or WorkflowStateManagerConfig()
        self._cleanup_task: Optional[asyncio.Task] = None
        
        if self._config.enable_cleanup:
            self._start_cleanup_task()
    
    async def create_workflow(self, workflow: PaymentWorkflow) -> PaymentWorkflow:
        """Create and store a new workflow"""
        if not workflow.id:
            raise ValidationError("Workflow must have an ID")
        
        # Validate workflow state
        if workflow.status not in [PaymentStatus.INITIALIZING, PaymentStatus.PENDING]:
            raise ValidationError("New workflow must be in INITIALIZING or PENDING state")
        
        await self._storage.store_workflow(workflow)
        return workflow
    
    async def get_workflow(self, workflow_id: str) -> PaymentWorkflow:
        """Retrieve a workflow by ID"""
        workflow = await self._storage.get_workflow(workflow_id)
        if not workflow:
            raise NotFoundError(f"Workflow {workflow_id} not found")
        return workflow
    
    async def update_workflow(self, workflow: PaymentWorkflow) -> PaymentWorkflow:
        """Update an existing workflow"""
        # Validate workflow exists
        existing = await self._storage.get_workflow(workflow.id)
        if not existing:
            raise NotFoundError(f"Workflow {workflow.id} not found")
        
        await self._storage.update_workflow(workflow)
        return workflow
    
    async def update_workflow_status(self, 
                                   workflow_id: str, 
                                   status: PaymentStatus,
                                   error_message: Optional[str] = None) -> PaymentWorkflow:
        """Update workflow status with validation"""
        workflow = await self.get_workflow(workflow_id)
        
        # Validate status transition
        if not self._is_valid_status_transition(workflow.status, status):
            raise ValidationError(
                f"Invalid status transition from {workflow.status} to {status}"
            )
        
        workflow.status = status
        workflow.updated_at = datetime.utcnow()
        
        if error_message:
            workflow.error_message = error_message
        
        return await self.update_workflow(workflow)
    
    async def delete_workflow(self, workflow_id: str) -> None:
        """Delete a workflow"""
        await self._storage.delete_workflow(workflow_id)
    
    async def list_workflows(self, 
                           business_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           status: Optional[PaymentStatus] = None,
                           limit: int = 100,
                           offset: int = 0) -> List[PaymentWorkflow]:
        """List workflows with filtering and pagination"""
        return await self._storage.list_workflows(
            business_id=business_id,
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
    
    async def get_workflow_metrics(self) -> Dict[str, Any]:
        """Get workflow metrics for monitoring"""
        all_workflows = await self._storage.list_workflows(limit=10000)
        
        total_workflows = len(all_workflows)
        status_counts = {}
        for workflow in all_workflows:
            status_counts[workflow.status.value] = status_counts.get(workflow.status.value, 0) + 1
        
        # Calculate completion rate
        completed = status_counts.get(PaymentStatus.COMPLETED.value, 0)
        failed = status_counts.get(PaymentStatus.FAILED.value, 0)
        completion_rate = (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0
        
        return {
            "total_workflows": total_workflows,
            "status_distribution": status_counts,
            "completion_rate": completion_rate,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _is_valid_status_transition(self, current_status: PaymentStatus, new_status: PaymentStatus) -> bool:
        """Validate status transition"""
        valid_transitions = {
            PaymentStatus.INITIALIZING: [PaymentStatus.PENDING, PaymentStatus.FAILED],
            PaymentStatus.PENDING: [PaymentStatus.INTENT_AUTHORIZED, PaymentStatus.FAILED],
            PaymentStatus.INTENT_AUTHORIZED: [PaymentStatus.CART_CONFIRMED, PaymentStatus.FAILED],
            PaymentStatus.CART_CONFIRMED: [PaymentStatus.PAYMENT_PROCESSING, PaymentStatus.FAILED],
            PaymentStatus.PAYMENT_PROCESSING: [PaymentStatus.COMPLETED, PaymentStatus.FAILED],
            PaymentStatus.COMPLETED: [],  # Terminal state
            PaymentStatus.FAILED: []      # Terminal state
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_expired_workflows():
            while True:
                try:
                    await asyncio.sleep(self._config.cleanup_interval_minutes * 60)
                    await self._cleanup_expired_workflows()
                except Exception as e:
                    # Log error but don't crash the cleanup task
                    print(f"Error in workflow cleanup: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_expired_workflows())
    
    async def _cleanup_expired_workflows(self):
        """Clean up expired workflows"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self._config.max_workflow_age_hours)
        
        # Get workflows older than cutoff time
        all_workflows = await self._storage.list_workflows(limit=10000)
        expired_workflows = [
            w for w in all_workflows 
            if w.created_at < cutoff_time and w.status in [PaymentStatus.COMPLETED, PaymentStatus.FAILED]
        ]
        
        # Delete expired workflows
        for workflow in expired_workflows:
            try:
                await self.delete_workflow(workflow.id)
            except Exception as e:
                print(f"Failed to delete expired workflow {workflow.id}: {e}")
    
    async def close(self):
        """Clean up resources"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


# Factory for creating workflow state managers
class WorkflowStateManagerFactory:
    """Factory for creating workflow state managers with proper configuration"""
    
    @staticmethod
    def create_in_memory_manager(config: WorkflowStateManagerConfig = None) -> WorkflowStateManager:
        """Create in-memory workflow state manager for development"""
        storage = InMemoryWorkflowStorage()
        return WorkflowStateManager(storage, config)
    
    @staticmethod
    def create_database_manager(db_manager, config: WorkflowStateManagerConfig = None) -> WorkflowStateManager:
        """Create database-backed workflow state manager for production"""
        storage = DatabaseWorkflowStorage(db_manager)
        return WorkflowStateManager(storage, config)
