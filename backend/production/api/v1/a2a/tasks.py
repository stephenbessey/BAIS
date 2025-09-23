from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, AsyncIterator
import asyncio

from ...core.a2a_integration import A2ATaskRequest, A2ATaskStatus, A2ATaskResult
from ...core.a2a_processor_manager import get_processor_manager, A2AProcessorManager
from ...core.protocol_configurations import A2A_CONFIG
from ...core.comprehensive_error_handler import (
    handle_a2a_error, ValidationError, BusinessLogicError, 
    NetworkError, ErrorContext
)

router = APIRouter(prefix="/a2a/v1")

def get_processor_manager_dependency() -> A2AProcessorManager:
	"""FastAPI dependency for getting processor manager"""
	return get_processor_manager()


@router.post("/tasks", response_model=A2ATaskStatus)
async def submit_task(
	request: A2ATaskRequest,
	http_request: Request,
	manager: A2AProcessorManager = Depends(get_processor_manager_dependency)
) -> A2ATaskStatus:
	"""Submit a new A2A task for processing"""
	context = ErrorContext(
		endpoint="/a2a/v1/tasks",
		method="POST",
		task_id=request.task_id
	)
	
	try:
		processor = await manager.get_processor()
		
		# Validate task timeout against configuration
		if request.timeout_seconds > A2A_CONFIG.MAX_TASK_TIMEOUT_SECONDS:
			error = ValidationError(
				message=f"Task timeout exceeds maximum allowed duration of {A2A_CONFIG.MAX_TASK_TIMEOUT_SECONDS} seconds",
				field="timeout_seconds",
				value=request.timeout_seconds,
				context=context
			)
			error_details = handle_a2a_error(error, context)
			raise HTTPException(status_code=400, detail=error_details.user_message)
		
		# Initialize task as pending
		status = A2ATaskStatus(task_id=request.task_id, status="pending")
		processor.active_tasks[request.task_id] = status
		
		# Fire-and-forget execution
		asyncio.create_task(_run_task(processor, request))
		return status
		
	except HTTPException:
		raise
	except Exception as e:
		error_details = handle_a2a_error(e, context)
		raise HTTPException(status_code=500, detail=error_details.user_message)


async def _run_task(processor, request: A2ATaskRequest) -> None:
	"""Execute task with proper error handling"""
	try:
		await processor.process_task(request)
	except Exception as e:
		# Update task status with error information
		processor.active_tasks[request.task_id] = A2ATaskStatus(
			task_id=request.task_id,
			status="failed",
			message=str(e),
		)


@router.get("/tasks/{task_id}/status", response_model=A2ATaskStatus)
async def get_task_status(
	task_id: str,
	manager: A2AProcessorManager = Depends(get_processor_manager_dependency)
) -> A2ATaskStatus:
	"""Get the current status of a task"""
	try:
		processor = await manager.get_processor()
		
		if task_id not in processor.active_tasks:
			raise HTTPException(status_code=404, detail="Task not found")
		
		return processor.active_tasks[task_id]
		
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.get("/tasks/{task_id}/result", response_model=A2ATaskResult)
async def get_task_result(
	task_id: str,
	manager: A2AProcessorManager = Depends(get_processor_manager_dependency)
) -> A2ATaskResult:
	"""Get the result of a completed task"""
	try:
		processor = await manager.get_processor()
		status = processor.active_tasks.get(task_id)
		
		if not status:
			raise HTTPException(status_code=404, detail="Task not found")
		
		# Return result envelope from status
		return A2ATaskResult(task_id=task_id, status=status.status)
		
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get task result: {str(e)}")


@router.get("/tasks/{task_id}/events")
async def stream_task_events(
	task_id: str,
	manager: A2AProcessorManager = Depends(get_processor_manager_dependency)
) -> StreamingResponse:
	"""Stream real-time task status updates using Server-Sent Events"""
	try:
		processor = await manager.get_processor()
		
		if task_id not in processor.active_tasks:
			raise HTTPException(status_code=404, detail="Task not found")
		
		return StreamingResponse(
			_sse_stream(task_id, processor), 
			media_type="text/event-stream",
			headers={
				"Cache-Control": "no-cache",
				"Connection": "keep-alive",
				"Access-Control-Allow-Origin": "*"
			}
		)
		
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to stream task events: {str(e)}")


async def _sse_stream(task_id: str, processor) -> AsyncIterator[str]:
	"""Enhanced SSE stream for task status updates with proper error handling"""
	last_status = None
	heartbeat_count = 0
	max_heartbeats = (A2A_CONFIG.MAX_STREAM_DURATION_HOURS * 3600) // A2A_CONFIG.HEARTBEAT_INTERVAL_SECONDS
	
	try:
		while heartbeat_count < max_heartbeats:
			status = processor.active_tasks.get(task_id)
			if not status:
				# Send final event and break
				yield "data: {\"event\": \"task_not_found\"}\n\n"
				break
			
			payload = {
				"task_id": status.task_id,
				"status": status.status,
				"progress": getattr(status, 'progress', 0),
				"message": getattr(status, 'message', ''),
				"timestamp": getattr(status, 'updated_at', '').isoformat() if hasattr(status, 'updated_at') else None
			}
			
			data = f"data: {payload}\n\n"
			
			# Send update if status changed
			if data != last_status:
				yield data
				last_status = data
			
			# Check if task is complete
			if status.status in ("completed", "failed", "cancelled"):
				yield "data: {\"event\": \"task_complete\"}\n\n"
				break
			
			# Send heartbeat periodically
			if heartbeat_count % (A2A_CONFIG.HEARTBEAT_INTERVAL_SECONDS // 1) == 0:
				yield "data: {\"event\": \"heartbeat\"}\n\n"
			
			heartbeat_count += 1
			await asyncio.sleep(1)
			
	except Exception as e:
		# Send error event
		yield f"data: {{\"event\": \"error\", \"message\": \"{str(e)}\"}}\n\n"
