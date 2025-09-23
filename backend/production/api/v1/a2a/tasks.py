from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, AsyncIterator
import asyncio

from ...core.a2a_integration import A2ATaskRequest, A2ATaskStatus, A2ATaskResult
from ...core.a2a_task_processor import A2ATaskProcessor

router = APIRouter(prefix="/a2a/v1")

# In-memory processor placeholder; in real app inject via dependency
_processor: A2ATaskProcessor | None = None

def get_processor() -> A2ATaskProcessor:
	global _processor
	if _processor is None:
		# Lazy import to avoid circular deps; integrate a real adapter in app wiring
		from ...core.mcp_server_generator import BusinessSystemAdapter
		from ...core.payments.payment_coordinator import PaymentCoordinator
		from ...core.payments.ap2_client import AP2Client, AP2ClientConfig
		from ...config.ap2_settings import get_ap2_client_config
		adapter = BusinessSystemAdapter({})
		ap2 = AP2Client(AP2ClientConfig(**get_ap2_client_config()))
		coordinator = PaymentCoordinator(ap2, None)  # Inject real repo in app wiring
		_processor = A2ATaskProcessor(adapter, coordinator)
	return _processor


@router.post("/tasks", response_model=A2ATaskStatus)
async def submit_task(request: A2ATaskRequest) -> A2ATaskStatus:
	processor = get_processor()
	# Initialize task as pending
	status = A2ATaskStatus(task_id=request.task_id, status="pending")
	processor.active_tasks[request.task_id] = status
	# Fire-and-forget execution
	asyncio.create_task(_run_task(processor, request))
	return status


async def _run_task(processor: A2ATaskProcessor, request: A2ATaskRequest) -> None:
	try:
		await processor.process_task(request)
	except Exception as e:
		processor.active_tasks[request.task_id] = A2ATaskStatus(
			task_id=request.task_id,
			status="failed",
			message=str(e),
		)


@router.get("/tasks/{task_id}/status", response_model=A2ATaskStatus)
async def get_task_status(task_id: str) -> A2ATaskStatus:
	processor = get_processor()
	if task_id not in processor.active_tasks:
		raise HTTPException(status_code=404, detail="Task not found")
	return processor.active_tasks[task_id]


@router.get("/tasks/{task_id}/result", response_model=A2ATaskResult)
async def get_task_result(task_id: str) -> A2ATaskResult:
	processor = get_processor()
	status = processor.active_tasks.get(task_id)
	if not status:
		raise HTTPException(status_code=404, detail="Task not found")
	# Minimal result envelope from status for now
	return A2ATaskResult(task_id=task_id, status=status.status)


@router.get("/tasks/{task_id}/events")
async def stream_task_events(task_id: str) -> StreamingResponse:
	processor = get_processor()
	if task_id not in processor.active_tasks:
		raise HTTPException(status_code=404, detail="Task not found")
	return StreamingResponse(_sse_stream(task_id, processor), media_type="text/event-stream")


async def _sse_stream(task_id: str, processor: A2ATaskProcessor) -> AsyncIterator[str]:
	"""Simple SSE stream for task status updates"""
	last_status = None
	while True:
		status = processor.active_tasks.get(task_id)
		if not status:
			break
		payload = {
			"task_id": status.task_id,
			"status": status.status,
			"progress": status.progress,
			"message": status.message,
		}
		data = f"data: {payload}\n\n"
		if data != last_status:
			yield data
			last_status = data
		if status.status in ("completed", "failed", "cancelled"):
			break
		await asyncio.sleep(1)
