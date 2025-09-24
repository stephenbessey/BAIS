"""
A2A SSE Router - Clean Code Implementation
FastAPI router for A2A Server-Sent Events endpoints for real-time task streaming
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
import asyncio
import uuid
from enum import Enum

from ...core.mcp_sse_transport import (
    MCPSSETransportManager, 
    MCPSSEEvent, 
    get_sse_transport_manager
)
from ...core.a2a_integration import A2ATaskStatus, A2ATaskResult
from ...core.mcp_error_handler import MCPErrorHandler, ValidationError

router = APIRouter(prefix="/a2a/sse", tags=["A2A SSE"])


class A2ATaskEventType(Enum):
    """A2A task event types for SSE streaming"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    AGENT_DISCOVERED = "agent_discovered"
    COORDINATION_UPDATE = "coordination_update"


class A2ATaskStreamRequest(BaseModel):
    """Request model for A2A task streaming"""
    task_ids: Optional[List[str]] = Field(None, description="Specific task IDs to stream")
    agent_ids: Optional[List[str]] = Field(None, description="Agent IDs to monitor")
    event_types: Optional[List[str]] = Field(None, description="Specific event types to stream")
    include_agent_discovery: bool = Field(True, description="Include agent discovery events")


class A2ATaskStreamResponse(BaseModel):
    """Response model for A2A task streaming events"""
    event_type: str = Field(..., description="Type of A2A event")
    task_id: Optional[str] = Field(None, description="Task ID if applicable")
    agent_id: Optional[str] = Field(None, description="Agent ID if applicable")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


class A2ASSEConnectionManager:
    """Manages A2A SSE connections and task streaming following Clean Code principles"""
    
    def __init__(self, sse_transport_manager: MCPSSETransportManager):
        self._sse_manager = sse_transport_manager
        self._task_subscribers: Dict[str, List[str]] = {}  # task_id -> [client_ids]
        self._agent_subscribers: Dict[str, List[str]] = {}  # agent_id -> [client_ids]
        self._client_filters: Dict[str, Dict[str, Any]] = {}  # client_id -> filters
        self._active_tasks: Dict[str, A2ATaskStatus] = {}
        self._task_results: Dict[str, A2ATaskResult] = {}
    
    async def connect_client(self, client_id: str, filters: Dict[str, Any]) -> str:
        """Connect a new A2A SSE client with filters"""
        try:
            # Store client filters
            self._client_filters[client_id] = filters
            
            # Subscribe to specific tasks if specified
            if filters.get("task_ids"):
                for task_id in filters["task_ids"]:
                    if task_id not in self._task_subscribers:
                        self._task_subscribers[task_id] = []
                    self._task_subscribers[task_id].append(client_id)
            
            # Subscribe to specific agents if specified
            if filters.get("agent_ids"):
                for agent_id in filters["agent_ids"]:
                    if agent_id not in self._agent_subscribers:
                        self._agent_subscribers[agent_id] = []
                    self._agent_subscribers[agent_id].append(client_id)
            
            # Create SSE connection
            client_info = {
                "type": "a2a_task_stream",
                "filters": filters,
                "connected_at": datetime.now().isoformat()
            }
            
            queue = await self._sse_manager.connect_client(client_id, client_info)
            
            # Send connection confirmation
            await self._sse_manager.send_to_client(client_id, MCPSSEEvent(
                event_type="a2a_connected",
                data={
                    "client_id": client_id,
                    "message": "Connected to A2A task stream",
                    "filters": filters,
                    "timestamp": datetime.now().isoformat()
                },
                id=str(uuid.uuid4())
            ))
            
            return client_id
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect A2A SSE client: {str(e)}")
    
    async def disconnect_client(self, client_id: str):
        """Disconnect an A2A SSE client"""
        try:
            # Remove from all subscriptions
            for task_id, subscribers in self._task_subscribers.items():
                if client_id in subscribers:
                    subscribers.remove(client_id)
            
            for agent_id, subscribers in self._agent_subscribers.items():
                if client_id in subscribers:
                    subscribers.remove(client_id)
            
            # Remove client filters
            if client_id in self._client_filters:
                del self._client_filters[client_id]
            
            # Disconnect from SSE manager
            await self._sse_manager.disconnect_client(client_id)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to disconnect A2A SSE client: {str(e)}")
    
    async def broadcast_task_event(
        self, 
        event_type: A2ATaskEventType, 
        task_id: str, 
        agent_id: str, 
        data: Dict[str, Any]
    ):
        """Broadcast A2A task event to subscribed clients"""
        try:
            # Create A2A-specific event
            event_data = {
                "event_type": event_type.value,
                "task_id": task_id,
                "agent_id": agent_id,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Create SSE event
            sse_event = MCPSSEEvent(
                event_type="a2a_task_event",
                data=event_data,
                id=str(uuid.uuid4())
            )
            
            # Broadcast to task subscribers
            if task_id in self._task_subscribers:
                for client_id in self._task_subscribers[task_id]:
                    await self._sse_manager.send_to_client(client_id, sse_event)
            
            # Broadcast to agent subscribers
            if agent_id in self._agent_subscribers:
                for client_id in self._agent_subscribers[agent_id]:
                    await self._sse_manager.send_to_client(client_id, sse_event)
            
            # Broadcast to general A2A subscribers
            await self._sse_manager.broadcast_event(sse_event, "a2a_tasks")
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to broadcast A2A task event: {str(e)}")
    
    async def update_task_status(self, task_id: str, status: A2ATaskStatus):
        """Update task status and broadcast to subscribers"""
        try:
            # Update local status
            self._active_tasks[task_id] = status
            
            # Determine event type based on status
            if status.status == "pending":
                event_type = A2ATaskEventType.TASK_CREATED
            elif status.status == "running":
                event_type = A2ATaskEventType.TASK_STARTED
            elif status.status == "completed":
                event_type = A2ATaskEventType.TASK_COMPLETED
            elif status.status == "failed":
                event_type = A2ATaskEventType.TASK_FAILED
            elif status.status == "cancelled":
                event_type = A2ATaskEventType.TASK_CANCELLED
            else:
                event_type = A2ATaskEventType.TASK_PROGRESS
            
            # Broadcast event
            await self.broadcast_task_event(
                event_type=event_type,
                task_id=task_id,
                agent_id=getattr(status, 'agent_id', 'unknown'),
                data={
                    "status": status.status,
                    "message": status.message,
                    "progress": getattr(status, 'progress', None),
                    "metadata": getattr(status, 'metadata', {})
                }
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update task status: {str(e)}")
    
    async def update_task_result(self, task_id: str, result: A2ATaskResult):
        """Update task result and broadcast to subscribers"""
        try:
            # Update local result
            self._task_results[task_id] = result
            
            # Broadcast completion event
            await self.broadcast_task_event(
                event_type=A2ATaskEventType.TASK_COMPLETED,
                task_id=task_id,
                agent_id=getattr(result, 'agent_id', 'unknown'),
                data={
                    "result": result.result if hasattr(result, 'result') else result.dict(),
                    "execution_time": getattr(result, 'execution_time', None),
                    "metadata": getattr(result, 'metadata', {})
                }
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update task result: {str(e)}")
    
    def get_active_tasks(self) -> Dict[str, A2ATaskStatus]:
        """Get all active tasks"""
        return self._active_tasks.copy()
    
    def get_task_result(self, task_id: str) -> Optional[A2ATaskResult]:
        """Get task result by ID"""
        return self._task_results.get(task_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_clients": len(self._client_filters),
            "task_subscriptions": {task_id: len(subs) for task_id, subs in self._task_subscribers.items()},
            "agent_subscriptions": {agent_id: len(subs) for agent_id, subs in self._agent_subscribers.items()},
            "active_tasks": len(self._active_tasks),
            "completed_tasks": len(self._task_results)
        }


# Global A2A SSE connection manager
_a2a_sse_manager: Optional[A2ASSEConnectionManager] = None


def get_a2a_sse_manager() -> A2ASSEConnectionManager:
    """Get global A2A SSE connection manager"""
    global _a2a_sse_manager
    if _a2a_sse_manager is None:
        sse_transport = get_sse_transport_manager()
        _a2a_sse_manager = A2ASSEConnectionManager(sse_transport)
    return _a2a_sse_manager


@router.get("/connect")
async def connect_a2a_stream(
    request: Request,
    task_ids: Optional[str] = Query(None, description="Comma-separated task IDs to monitor"),
    agent_ids: Optional[str] = Query(None, description="Comma-separated agent IDs to monitor"),
    event_types: Optional[str] = Query(None, description="Comma-separated event types to stream"),
    include_agent_discovery: bool = Query(True, description="Include agent discovery events"),
    sse_manager: MCPSSETransportManager = Depends(get_sse_transport_manager)
):
    """
    Connect to A2A task streaming via Server-Sent Events
    
    This endpoint establishes a persistent SSE connection for real-time A2A task updates.
    Clients can subscribe to specific tasks, agents, or event types for targeted monitoring.
    
    Event Types:
    - task_created: New task created
    - task_started: Task execution started
    - task_progress: Task progress updates
    - task_completed: Task completed successfully
    - task_failed: Task failed with error
    - task_cancelled: Task was cancelled
    - agent_discovered: New agent discovered
    - coordination_update: Multi-agent coordination updates
    """
    try:
        # Parse filter parameters
        task_id_list = []
        if task_ids:
            task_id_list = [tid.strip() for tid in task_ids.split(",") if tid.strip()]
        
        agent_id_list = []
        if agent_ids:
            agent_id_list = [aid.strip() for aid in agent_ids.split(",") if aid.strip()]
        
        event_type_list = []
        if event_types:
            event_type_list = [et.strip() for et in event_types.split(",") if et.strip()]
        
        # Validate event types
        valid_event_types = [et.value for et in A2ATaskEventType]
        for event_type in event_type_list:
            if event_type not in valid_event_types:
                raise ValidationError(
                    f"Invalid event type: {event_type}",
                    field="event_types",
                    details={"valid_types": valid_event_types}
                )
        
        # Create filters
        filters = {
            "task_ids": task_id_list,
            "agent_ids": agent_id_list,
            "event_types": event_type_list,
            "include_agent_discovery": include_agent_discovery
        }
        
        # Generate client ID
        client_id = str(uuid.uuid4())
        
        # Connect to A2A SSE manager
        a2a_manager = get_a2a_sse_manager()
        await a2a_manager.connect_client(client_id, filters)
        
        # Get SSE connection from transport manager
        queue = await sse_manager.connect_client(client_id, {
            "type": "a2a_task_stream",
            "filters": filters,
            "connected_at": datetime.now().isoformat()
        })
        
        # Create SSE response
        async def event_generator():
            """Generate SSE events for A2A task streaming"""
            try:
                # Send initial connection event
                yield MCPSSEEvent(
                    event_type="a2a_connected",
                    data={
                        "client_id": client_id,
                        "message": "Connected to A2A task stream",
                        "filters": filters,
                        "timestamp": datetime.now().isoformat()
                    },
                    id=str(uuid.uuid4())
                ).to_sse_format()
                
                # Process events from queue
                while True:
                    try:
                        # Wait for event with timeout
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        
                        # None indicates connection should close
                        if event is None:
                            break
                        
                        yield event.to_sse_format()
                        
                        # Mark task as done
                        queue.task_done()
                        
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        yield MCPSSEEvent(
                            event_type="ping",
                            data={"timestamp": datetime.now().isoformat()},
                            id=str(uuid.uuid4())
                        ).to_sse_format()
                        
                    except Exception as e:
                        yield MCPSSEEvent(
                            event_type="error",
                            data={"error": str(e)},
                            id=str(uuid.uuid4())
                        ).to_sse_format()
                        break
            
            finally:
                # Cleanup on disconnect
                await a2a_manager.disconnect_client(client_id)
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to A2A stream: {str(e)}")


@router.get("/tasks/active")
async def get_active_tasks(
    a2a_manager: A2ASSEConnectionManager = Depends(get_a2a_sse_manager)
):
    """
    Get list of currently active A2A tasks
    
    Returns information about all currently active tasks for monitoring purposes.
    """
    try:
        active_tasks = a2a_manager.get_active_tasks()
        
        return {
            "active_tasks": [
                {
                    "task_id": task_id,
                    "status": task.status,
                    "message": task.message,
                    "agent_id": getattr(task, 'agent_id', None),
                    "created_at": getattr(task, 'created_at', None),
                    "progress": getattr(task, 'progress', None)
                }
                for task_id, task in active_tasks.items()
            ],
            "total_count": len(active_tasks),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active tasks: {str(e)}")


@router.get("/tasks/{task_id}/result")
async def get_task_result(
    task_id: str,
    a2a_manager: A2ASSEConnectionManager = Depends(get_a2a_sse_manager)
):
    """
    Get result for a specific A2A task
    
    Returns the result of a completed task for retrieval purposes.
    """
    try:
        result = a2a_manager.get_task_result(task_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Task result not found: {task_id}")
        
        return {
            "task_id": task_id,
            "result": result.result if hasattr(result, 'result') else result.dict(),
            "execution_time": getattr(result, 'execution_time', None),
            "metadata": getattr(result, 'metadata', {}),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task result: {str(e)}")


@router.get("/stats")
async def get_a2a_stream_stats(
    a2a_manager: A2ASSEConnectionManager = Depends(get_a2a_sse_manager)
):
    """
    Get A2A streaming statistics
    
    Returns connection and task statistics for monitoring and debugging.
    """
    try:
        stats = a2a_manager.get_connection_stats()
        
        return {
            "connection_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get A2A stream stats: {str(e)}")


@router.post("/tasks/{task_id}/subscribe")
async def subscribe_to_task(
    task_id: str,
    client_id: str,
    a2a_manager: A2ASSEConnectionManager = Depends(get_a2a_sse_manager)
):
    """
    Subscribe to updates for a specific task
    
    Allows clients to subscribe to updates for a specific task ID.
    """
    try:
        # Add task subscription
        if task_id not in a2a_manager._task_subscribers:
            a2a_manager._task_subscribers[task_id] = []
        
        if client_id not in a2a_manager._task_subscribers[task_id]:
            a2a_manager._task_subscribers[task_id].append(client_id)
        
        return {
            "success": True,
            "message": f"Subscribed to task {task_id}",
            "task_id": task_id,
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe to task: {str(e)}")


@router.delete("/tasks/{task_id}/subscribe")
async def unsubscribe_from_task(
    task_id: str,
    client_id: str,
    a2a_manager: A2ASSEConnectionManager = Depends(get_a2a_sse_manager)
):
    """
    Unsubscribe from updates for a specific task
    
    Allows clients to unsubscribe from updates for a specific task ID.
    """
    try:
        # Remove task subscription
        if task_id in a2a_manager._task_subscribers:
            if client_id in a2a_manager._task_subscribers[task_id]:
                a2a_manager._task_subscribers[task_id].remove(client_id)
        
        return {
            "success": True,
            "message": f"Unsubscribed from task {task_id}",
            "task_id": task_id,
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe from task: {str(e)}")


@router.get("/health")
async def a2a_sse_health_check():
    """
    Health check endpoint for A2A SSE service
    
    Returns the health status of the A2A SSE streaming service.
    """
    try:
        a2a_manager = get_a2a_sse_manager()
        stats = a2a_manager.get_connection_stats()
        
        return {
            "status": "healthy",
            "service": "a2a-sse",
            "active_connections": stats["total_clients"],
            "active_tasks": stats["active_tasks"],
            "completed_tasks": stats["completed_tasks"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "a2a-sse",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
