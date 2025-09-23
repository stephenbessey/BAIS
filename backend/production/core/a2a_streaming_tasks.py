"""
A2A Streaming Task Management
Implements Server-Sent Events for real-time A2A task updates

This module addresses the critical gap in A2A task coordination by implementing
proper streaming task management with Server-Sent Events (SSE).
"""

from typing import Dict, Any, Optional, AsyncGenerator, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .a2a_integration import A2ATaskStatus, A2ATaskResult, A2ATaskRequest


class TaskStreamEventType(Enum):
    """Types of task stream events"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    HEARTBEAT = "heartbeat"


@dataclass
class TaskStreamEvent:
    """Represents a task stream event"""
    event_type: TaskStreamEventType
    task_id: str
    timestamp: datetime
    data: Dict[str, Any]
    message: Optional[str] = None
    
    def to_sse_format(self) -> str:
        """Convert to Server-Sent Events format"""
        event_data = {
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "message": self.message
        }
        
        return f"data: {json.dumps(event_data)}\n\n"


@dataclass
class TaskProgress:
    """Represents task progress information"""
    current_step: str
    total_steps: int
    completed_steps: int
    progress_percentage: float
    estimated_completion: Optional[datetime] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class A2ATaskStreamManager:
    """
    Manages streaming task updates for A2A protocol
    
    Implements Server-Sent Events for real-time task coordination
    and progress updates.
    """
    
    def __init__(self):
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.task_progress: Dict[str, TaskProgress] = {}
        self.task_metadata: Dict[str, Dict[str, Any]] = {}
        self.heartbeat_interval = timedelta(seconds=30)
        self.max_stream_duration = timedelta(hours=1)
    
    def create_task_stream(self, task_id: str, task_request: A2ATaskRequest) -> str:
        """
        Create a new task stream
        
        Args:
            task_id: Unique task identifier
            task_request: Original task request
            
        Returns:
            Stream identifier
        """
        stream_id = str(uuid.uuid4())
        
        # Create stream queue
        self.active_streams[stream_id] = asyncio.Queue()
        
        # Initialize task metadata
        self.task_metadata[task_id] = {
            "task_request": asdict(task_request),
            "created_at": datetime.utcnow(),
            "stream_id": stream_id,
            "subscribers": set()
        }
        
        # Initialize task progress
        self.task_progress[task_id] = TaskProgress(
            current_step="initializing",
            total_steps=1,
            completed_steps=0,
            progress_percentage=0.0
        )
        
        # Send initial event
        asyncio.create_task(self._send_task_event(
            stream_id,
            TaskStreamEvent(
                event_type=TaskStreamEventType.TASK_CREATED,
                task_id=task_id,
                timestamp=datetime.utcnow(),
                data={"task_request": asdict(task_request)},
                message=f"Task {task_id} created successfully"
            )
        ))
        
        return stream_id
    
    async def update_task_progress(
        self, 
        task_id: str, 
        current_step: str,
        completed_steps: int = None,
        total_steps: int = None,
        details: Dict[str, Any] = None
    ) -> None:
        """Update task progress and notify subscribers"""
        if task_id not in self.task_progress:
            return
        
        progress = self.task_progress[task_id]
        progress.current_step = current_step
        
        if completed_steps is not None:
            progress.completed_steps = completed_steps
        
        if total_steps is not None:
            progress.total_steps = total_steps
        
        if details is not None:
            progress.details.update(details)
        
        # Calculate progress percentage
        if progress.total_steps > 0:
            progress.progress_percentage = (progress.completed_steps / progress.total_steps) * 100
        
        # Estimate completion time
        if progress.completed_steps > 0:
            elapsed = datetime.utcnow() - self.task_metadata[task_id]["created_at"]
            estimated_total = elapsed * (progress.total_steps / progress.completed_steps)
            progress.estimated_completion = self.task_metadata[task_id]["created_at"] + estimated_total
        
        # Send progress event
        stream_id = self.task_metadata[task_id]["stream_id"]
        await self._send_task_event(
            stream_id,
            TaskStreamEvent(
                event_type=TaskStreamEventType.TASK_PROGRESS,
                task_id=task_id,
                timestamp=datetime.utcnow(),
                data=asdict(progress),
                message=f"Task progress: {current_step}"
            )
        )
    
    async def complete_task(
        self, 
        task_id: str, 
        result: A2ATaskResult,
        success: bool = True
    ) -> None:
        """Mark task as completed and send final event"""
        if task_id not in self.task_metadata:
            return
        
        # Update final progress
        progress = self.task_progress[task_id]
        progress.current_step = "completed"
        progress.completed_steps = progress.total_steps
        progress.progress_percentage = 100.0
        progress.estimated_completion = datetime.utcnow()
        
        # Send completion event
        stream_id = self.task_metadata[task_id]["stream_id"]
        event_type = TaskStreamEventType.TASK_COMPLETED if success else TaskStreamEventType.TASK_FAILED
        
        await self._send_task_event(
            stream_id,
            TaskStreamEvent(
                event_type=event_type,
                task_id=task_id,
                timestamp=datetime.utcnow(),
                data={
                    "result": asdict(result),
                    "progress": asdict(progress)
                },
                message=f"Task {'completed' if success else 'failed'}"
            )
        )
        
        # Clean up after delay
        asyncio.create_task(self._cleanup_task_stream(task_id, delay_seconds=60))
    
    async def cancel_task(self, task_id: str, reason: str = "user_requested") -> None:
        """Cancel task and notify subscribers"""
        if task_id not in self.task_metadata:
            return
        
        stream_id = self.task_metadata[task_id]["stream_id"]
        await self._send_task_event(
            stream_id,
            TaskStreamEvent(
                event_type=TaskStreamEventType.TASK_CANCELLED,
                task_id=task_id,
                timestamp=datetime.utcnow(),
                data={"reason": reason},
                message=f"Task cancelled: {reason}"
            )
        )
        
        # Clean up immediately
        await self._cleanup_task_stream(task_id, delay_seconds=0)
    
    async def get_task_stream(self, task_id: str) -> AsyncGenerator[str, None]:
        """
        Get streaming response for task updates
        
        Args:
            task_id: Task identifier
            
        Yields:
            Server-Sent Events formatted strings
        """
        if task_id not in self.task_metadata:
            raise HTTPException(status_code=404, detail="Task not found")
        
        stream_id = self.task_metadata[task_id]["stream_id"]
        stream_queue = self.active_streams[stream_id]
        
        # Add subscriber
        self.task_metadata[task_id]["subscribers"].add(stream_id)
        
        try:
            # Send initial heartbeat
            yield self._create_heartbeat_event(task_id).to_sse_format()
            
            # Stream events
            while True:
                try:
                    # Wait for event with timeout for heartbeat
                    event = await asyncio.wait_for(
                        stream_queue.get(), 
                        timeout=self.heartbeat_interval.total_seconds()
                    )
                    
                    yield event.to_sse_format()
                    
                    # Check if task is complete
                    if event.event_type in [
                        TaskStreamEventType.TASK_COMPLETED,
                        TaskStreamEventType.TASK_FAILED,
                        TaskStreamEventType.TASK_CANCELLED
                    ]:
                        break
                        
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield self._create_heartbeat_event(task_id).to_sse_format()
                    
                except Exception as e:
                    print(f"Error in task stream {task_id}: {e}")
                    break
                    
        finally:
            # Remove subscriber
            self.task_metadata[task_id]["subscribers"].discard(stream_id)
    
    async def _send_task_event(self, stream_id: str, event: TaskStreamEvent) -> None:
        """Send event to task stream"""
        if stream_id in self.active_streams:
            try:
                await self.active_streams[stream_id].put(event)
            except Exception as e:
                print(f"Failed to send event to stream {stream_id}: {e}")
    
    def _create_heartbeat_event(self, task_id: str) -> TaskStreamEvent:
        """Create heartbeat event"""
        return TaskStreamEvent(
            event_type=TaskStreamEventType.HEARTBEAT,
            task_id=task_id,
            timestamp=datetime.utcnow(),
            data={"status": "alive"},
            message="Heartbeat"
        )
    
    async def _cleanup_task_stream(self, task_id: str, delay_seconds: int = 60) -> None:
        """Clean up task stream after delay"""
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        
        if task_id in self.task_metadata:
            stream_id = self.task_metadata[task_id]["stream_id"]
            
            # Close stream queue
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            
            # Clean up metadata
            del self.task_metadata[task_id]
            
            # Clean up progress
            if task_id in self.task_progress:
                del self.task_progress[task_id]
    
    async def cleanup_expired_streams(self) -> int:
        """Clean up expired streams"""
        current_time = datetime.utcnow()
        expired_tasks = []
        
        for task_id, metadata in self.task_metadata.items():
            created_at = metadata["created_at"]
            if current_time - created_at > self.max_stream_duration:
                expired_tasks.append(task_id)
        
        for task_id in expired_tasks:
            await self._cleanup_task_stream(task_id, delay_seconds=0)
        
        return len(expired_tasks)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task status"""
        if task_id not in self.task_metadata:
            return None
        
        return {
            "task_id": task_id,
            "progress": asdict(self.task_progress[task_id]) if task_id in self.task_progress else None,
            "metadata": self.task_metadata[task_id],
            "has_active_stream": self.task_metadata[task_id]["stream_id"] in self.active_streams
        }


class A2AStreamingTaskServer:
    """
    FastAPI server for A2A streaming task management
    
    Provides HTTP endpoints for task streaming using Server-Sent Events.
    """
    
    def __init__(self, task_manager: A2ATaskStreamManager):
        self.task_manager = task_manager
        self.app = FastAPI(title="A2A Streaming Task Server")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes for task streaming"""
        
        @self.app.get("/a2a/tasks/{task_id}/stream")
        async def stream_task_updates(task_id: str):
            """
            Stream task updates using Server-Sent Events
            
            This endpoint provides real-time task updates for A2A coordination.
            """
            try:
                return StreamingResponse(
                    self.task_manager.get_task_stream(task_id),
                    media_type="text/plain",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Cache-Control"
                    }
                )
            except HTTPException as e:
                raise e
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Stream error: {str(e)}")
        
        @self.app.get("/a2a/tasks/{task_id}/status")
        async def get_task_status(task_id: str):
            """Get current task status"""
            status = self.task_manager.get_task_status(task_id)
            if not status:
                raise HTTPException(status_code=404, detail="Task not found")
            return status
        
        @self.app.post("/a2a/tasks/{task_id}/progress")
        async def update_task_progress(
            task_id: str,
            current_step: str,
            completed_steps: int = None,
            total_steps: int = None,
            details: Dict[str, Any] = None
        ):
            """Update task progress"""
            await self.task_manager.update_task_progress(
                task_id, current_step, completed_steps, total_steps, details
            )
            return {"status": "updated"}
        
        @self.app.post("/a2a/tasks/{task_id}/complete")
        async def complete_task(task_id: str, result: A2ATaskResult, success: bool = True):
            """Mark task as completed"""
            await self.task_manager.complete_task(task_id, result, success)
            return {"status": "completed"}
        
        @self.app.post("/a2a/tasks/{task_id}/cancel")
        async def cancel_task(task_id: str, reason: str = "user_requested"):
            """Cancel task"""
            await self.task_manager.cancel_task(task_id, reason)
            return {"status": "cancelled"}
        
        @self.app.get("/a2a/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "active_streams": len(self.task_manager.active_streams),
                "active_tasks": len(self.task_manager.task_metadata),
                "timestamp": datetime.utcnow().isoformat()
            }


# Integration with existing A2A server
def integrate_streaming_with_a2a_server(
    a2a_server: 'BAISA2AServer',
    task_manager: A2ATaskStreamManager
) -> None:
    """
    Integrate streaming task management with existing A2A server
    
    This function modifies the existing A2A server to use streaming task updates.
    """
    
    # Store original task execution method
    original_execute_task = a2a_server._execute_task
    
    async def streaming_execute_task(task_request: A2ATaskRequest, capability: A2ACapability):
        """Enhanced task execution with streaming updates"""
        task_id = task_request.task_id
        
        # Create task stream
        stream_id = task_manager.create_task_stream(task_id, task_request)
        
        try:
            # Update progress: task started
            await task_manager.update_task_progress(
                task_id, 
                "executing",
                completed_steps=0,
                total_steps=3
            )
            
            # Execute original task logic
            result = await original_execute_task(task_request, capability)
            
            # Update progress: task completed
            await task_manager.update_task_progress(
                task_id,
                "completed",
                completed_steps=3,
                total_steps=3
            )
            
            # Complete task
            await task_manager.complete_task(task_id, result, success=True)
            
            return result
            
        except Exception as e:
            # Update progress: task failed
            await task_manager.update_task_progress(
                task_id,
                "failed",
                details={"error": str(e)}
            )
            
            # Create error result
            error_result = A2ATaskResult(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                completed_at=datetime.utcnow()
            )
            
            await task_manager.complete_task(task_id, error_result, success=False)
            raise
    
    # Replace the original method
    a2a_server._execute_task = streaming_execute_task
    
    # Add streaming endpoints to existing app
    streaming_server = A2AStreamingTaskServer(task_manager)
    
    # Mount streaming routes
    a2a_server.app.mount("/streaming", streaming_server.app)


# Factory for creating streaming components
class A2AStreamingFactory:
    """Factory for creating A2A streaming components"""
    
    @staticmethod
    def create_task_manager() -> A2ATaskStreamManager:
        """Create task stream manager"""
        return A2ATaskStreamManager()
    
    @staticmethod
    def create_streaming_server(task_manager: A2ATaskStreamManager) -> A2AStreamingTaskServer:
        """Create streaming task server"""
        return A2AStreamingTaskServer(task_manager)
    
    @staticmethod
    def create_integrated_server(
        a2a_server: 'BAISA2AServer',
        task_manager: Optional[A2ATaskStreamManager] = None
    ) -> A2ATaskStreamManager:
        """Create integrated streaming A2A server"""
        if task_manager is None:
            task_manager = A2ATaskStreamManager()
        
        integrate_streaming_with_a2a_server(a2a_server, task_manager)
        return task_manager
