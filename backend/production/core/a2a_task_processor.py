import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

from .a2a_integration import A2ATaskRequest, A2ATaskResult, A2ATaskStatus


class TaskExecutionStrategy(Enum):
	IMMEDIATE = "immediate"
	QUEUED = "queued"
	SCHEDULED = "scheduled"
	COORDINATED = "coordinated"


class A2ATaskProcessor:
	"""Processes A2A tasks with capability routing and robust error handling"""

	def __init__(self, business_adapter: 'BusinessSystemAdapter', payment_coordinator: 'PaymentCoordinator'):
		self.business_adapter = business_adapter
		self.payment_coordinator = payment_coordinator
		self.task_handlers = self._initialize_task_handlers()
		self.active_tasks: Dict[str, A2ATaskStatus] = {}

	def _initialize_task_handlers(self) -> Dict[str, Callable[[Dict[str, Any]], Any]]:
		return {
			"business_search": self._handle_business_search,
			"create_booking": self._handle_booking_creation,
			"coordinate_workflow": self._handle_workflow_coordination,
		}

	async def process_task(self, task_request: A2ATaskRequest) -> A2ATaskResult:
		self._validate_task_request(task_request)
		await self._update_task_status(task_request.task_id, "running", 10.0)

		try:
			result = await self._execute_task(task_request)
			await self._update_task_status(task_request.task_id, "completed", 100.0)
			return A2ATaskResult(
				task_id=task_request.task_id,
				status="completed",
				output=result,
				completed_at=datetime.utcnow(),
			)
		except Exception as e:
			await self._update_task_status(task_request.task_id, "failed", 0.0, str(e))
			raise

	def _validate_task_request(self, task_request: A2ATaskRequest) -> None:
		if task_request.capability not in self.task_handlers:
			raise ValueError(f"Unsupported capability: {task_request.capability}")
		if task_request.timeout_seconds > 300:
			raise ValueError("Task timeout exceeds maximum allowed duration")

	async def _execute_task(self, task_request: A2ATaskRequest) -> Dict[str, Any]:
		handler = self.task_handlers[task_request.capability]
		return await asyncio.wait_for(handler(task_request.input), timeout=task_request.timeout_seconds)

	async def _handle_business_search(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
		criteria = {
			"service_type": input_data.get("service_type"),
			"location": input_data.get("location"),
			"dates": input_data.get("dates", {}),
			"guests": input_data.get("guests", 1),
		}
		businesses = await self.business_adapter.search_businesses(criteria)
		results: List[Dict[str, Any]] = []
		for b in businesses:
			availability = await self.business_adapter.check_availability(b.id, criteria.get("dates", {}))
			results.append({
				"business_id": str(b.id),
				"name": b.name,
				"available": availability.get("available", False),
				"pricing": availability.get("pricing", {}),
			})
		return {"results": results}

	async def _handle_booking_creation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
		business_id = input_data["business_id"]
		service_id = input_data["service_id"]
		booking_details = input_data["booking_details"]
		customer_info = input_data["customer_info"]
		payment_mandate_id = input_data.get("payment_mandate_id")

		booking = await self.business_adapter.create_booking(
			business_id=business_id,
			service_id=service_id,
			booking_details=booking_details,
			customer_info=customer_info,
		)

		payment_status = "pending"
		if payment_mandate_id:
			payment_result = await self.payment_coordinator.process_payment(
				mandate_id=payment_mandate_id,
				booking_id=str(booking.id),
				amount=booking.total_amount,
			)
			payment_status = payment_result.status
			if payment_status != "completed":
				await self.business_adapter.cancel_booking(booking.id)
				raise ValueError(f"Payment failed: {payment_result.message}")

		return {
			"booking_id": str(booking.id),
			"status": booking.status,
			"confirmation_code": booking.confirmation_code,
			"payment_status": payment_status,
		}

	async def _handle_workflow_coordination(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
		workflow_id = f"workflow_{datetime.utcnow().timestamp()}"
		return {"workflow_id": workflow_id, "status": "planned"}

	async def _update_task_status(self, task_id: str, status: str, progress: float, message: Optional[str] = None) -> None:
		self.active_tasks[task_id] = A2ATaskStatus(
			task_id=task_id,
			status=status,
			progress=progress,
			message=message,
			updated_at=datetime.utcnow(),
		)
