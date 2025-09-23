"""
Integration Tests for A2A and AP2 Workflows
Comprehensive end-to-end testing of critical business workflows
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from ..core.payments.payment_coordinator import PaymentCoordinator
from ..core.payments.ap2_client import AP2Client, AP2ClientConfig
from ..core.a2a_integration import BAISA2AServer, A2ATaskRequest
from ..core.workflow_event_bus import WorkflowEventBus, WorkflowEventType
from ..core.secure_logging import LogContext
from ..api_models import BusinessRegistrationRequest
from ..services.business_registration_orchestrator import BusinessRegistrationOrchestrator
from ..monitoring.health_checks import HealthCheckManager, HealthStatus


@pytest.fixture
def mock_ap2_client():
    """Mock AP2 client for testing"""
    client = Mock(spec=AP2Client)
    client.create_intent_mandate = AsyncMock(return_value=Mock(id="intent_123"))
    client.create_cart_mandate = AsyncMock(return_value=Mock(id="cart_123"))
    client.execute_payment = AsyncMock(return_value=Mock(id="payment_123", status="completed"))
    return client


@pytest.fixture
def mock_business_repository():
    """Mock business repository for testing"""
    repo = Mock()
    repo.create_business = AsyncMock(return_value=Mock(id="business_123"))
    repo.get_business_by_id = AsyncMock(return_value=Mock(id="business_123", name="Test Hotel"))
    return repo


@pytest.fixture
def payment_coordinator(mock_ap2_client, mock_business_repository):
    """Payment coordinator with mocked dependencies"""
    return PaymentCoordinator(mock_ap2_client, mock_business_repository)


@pytest.fixture
def workflow_event_bus():
    """Workflow event bus for testing"""
    return WorkflowEventBus()


@pytest.fixture
def health_check_manager():
    """Health check manager for testing"""
    return HealthCheckManager()


class TestAP2PaymentWorkflow:
    """Integration tests for AP2 payment workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_payment_workflow_success(self, payment_coordinator):
        """Test complete payment workflow from intent to completion"""
        # Arrange
        request = Mock()
        request.user_id = "user_123"
        request.business_id = "business_123"
        request.intent_description = "Hotel booking"
        request.cart_items = [{"item": "room", "price": 100, "quantity": 1}]
        request.payment_method_id = "pm_123"
        request.currency = "USD"
        
        # Act
        workflow = await payment_coordinator.coordinate_payment_workflow(request)
        
        # Assert
        assert workflow.status == "completed"
        assert workflow.intent_mandate_id == "intent_123"
        assert workflow.cart_mandate_id == "cart_123"
        assert workflow.transaction_id == "payment_123"
    
    @pytest.mark.asyncio
    async def test_payment_workflow_with_failure(self, payment_coordinator):
        """Test payment workflow when AP2 client fails"""
        # Arrange
        request = Mock()
        request.user_id = "user_123"
        request.business_id = "business_123"
        request.intent_description = "Hotel booking"
        request.cart_items = [{"item": "room", "price": 100, "quantity": 1}]
        request.payment_method_id = "pm_123"
        request.currency = "USD"
        
        # Make AP2 client fail
        payment_coordinator._ap2_client.create_intent_mandate.side_effect = Exception("AP2 network error")
        
        # Act & Assert
        with pytest.raises(Exception):
            await payment_coordinator.coordinate_payment_workflow(request)
    
    @pytest.mark.asyncio
    async def test_payment_workflow_with_validation_error(self, payment_coordinator):
        """Test payment workflow with validation errors"""
        # Arrange
        request = Mock()
        request.user_id = None  # Invalid user ID
        request.business_id = "business_123"
        request.intent_description = "Hotel booking"
        request.cart_items = []
        request.payment_method_id = "pm_123"
        request.currency = "USD"
        
        # Act & Assert
        with pytest.raises(Exception):
            await payment_coordinator.coordinate_payment_workflow(request)


class TestA2AWorkflow:
    """Integration tests for A2A workflows"""
    
    @pytest.mark.asyncio
    async def test_a2a_task_processing_workflow(self):
        """Test complete A2A task processing workflow"""
        # Arrange
        mock_business_adapter = Mock()
        mock_business_adapter.search_availability = AsyncMock(return_value={
            "available": True,
            "slots": [{"time": "10:00", "available": True}]
        })
        
        a2a_server = BAISA2AServer(
            business_schema=Mock(),
            mcp_server=Mock(business_adapter=mock_business_adapter)
        )
        
        task_request = A2ATaskRequest(
            task_id="task_123",
            capability="search_availability",
            input={"service_id": "room_booking", "date": "2024-01-01"}
        )
        
        # Act
        result = await a2a_server.process_task(task_request)
        
        # Assert
        assert result["status"] == "completed"
        assert "available" in result["output"]
    
    @pytest.mark.asyncio
    async def test_a2a_task_with_booking_workflow(self):
        """Test A2A task that includes booking creation"""
        # Arrange
        mock_business_adapter = Mock()
        mock_business_adapter.create_booking = AsyncMock(return_value={
            "booking_id": "booking_123",
            "status": "confirmed",
            "confirmation_number": "ABC123"
        })
        
        a2a_server = BAISA2AServer(
            business_schema=Mock(),
            mcp_server=Mock(business_adapter=mock_business_adapter)
        )
        
        task_request = A2ATaskRequest(
            task_id="task_456",
            capability="book_room",
            input={"service_id": "room_booking", "date": "2024-01-01", "guest_count": 2}
        )
        
        # Act
        result = await a2a_server.process_task(task_request)
        
        # Assert
        assert result["status"] == "completed"
        assert result["output"]["booking_id"] == "booking_123"
        assert result["output"]["status"] == "confirmed"


class TestWorkflowEventBus:
    """Integration tests for workflow event bus"""
    
    @pytest.mark.asyncio
    async def test_event_publishing_and_subscription(self, workflow_event_bus):
        """Test event publishing and listener subscription"""
        # Arrange
        events_received = []
        
        class TestListener:
            async def handle_event(self, event):
                events_received.append(event)
            
            def get_supported_events(self):
                return [WorkflowEventType.PAYMENT_COMPLETED]
        
        listener = TestListener()
        workflow_event_bus.subscribe(WorkflowEventType.PAYMENT_COMPLETED, listener)
        
        # Act
        from ..core.workflow_event_bus import WorkflowEvent
        event = WorkflowEvent(
            event_type=WorkflowEventType.PAYMENT_COMPLETED,
            workflow_id="workflow_123",
            business_id="business_123",
            user_id="user_123"
        )
        
        await workflow_event_bus.publish(event)
        
        # Assert
        assert len(events_received) == 1
        assert events_received[0].workflow_id == "workflow_123"
        assert events_received[0].event_type == WorkflowEventType.PAYMENT_COMPLETED
    
    @pytest.mark.asyncio
    async def test_event_history_tracking(self, workflow_event_bus):
        """Test that events are tracked in history"""
        # Arrange
        from ..core.workflow_event_bus import WorkflowEvent
        
        events = [
            WorkflowEvent(
                event_type=WorkflowEventType.PAYMENT_INITIATED,
                workflow_id="workflow_1",
                business_id="business_123"
            ),
            WorkflowEvent(
                event_type=WorkflowEventType.PAYMENT_COMPLETED,
                workflow_id="workflow_1",
                business_id="business_123"
            ),
            WorkflowEvent(
                event_type=WorkflowEventType.A2A_TASK_STARTED,
                workflow_id="workflow_2",
                business_id="business_456"
            )
        ]
        
        # Act
        for event in events:
            await workflow_event_bus.publish(event)
        
        # Assert
        history = workflow_event_bus.get_event_history()
        assert len(history) == 3
        
        payment_events = workflow_event_bus.get_event_history(WorkflowEventType.PAYMENT_COMPLETED)
        assert len(payment_events) == 1
        assert payment_events[0].workflow_id == "workflow_1"


class TestBusinessRegistrationWorkflow:
    """Integration tests for business registration workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_business_registration_workflow(self, mock_business_repository):
        """Test complete business registration workflow"""
        # Arrange
        mock_validator = Mock()
        mock_validator.validate_registration_request = AsyncMock()
        
        mock_server_orchestrator = Mock()
        mock_server_orchestrator.setup_business_servers = AsyncMock()
        
        orchestrator = BusinessRegistrationOrchestrator(
            validator=mock_validator,
            repository=mock_business_repository,
            server_orchestrator=mock_server_orchestrator,
            background_tasks=Mock()
        )
        
        request = BusinessRegistrationRequest(
            business_name="Test Hotel",
            business_type="hospitality",
            business_schema={
                "business_info": {
                    "name": "Test Hotel",
                    "type": "hospitality"
                }
            }
        )
        
        # Act
        result = await orchestrator.register_business(request)
        
        # Assert
        assert result.business_id is not None
        assert result.status == "registered"
        assert result.mcp_endpoint is not None
        assert result.a2a_endpoint is not None
        mock_validator.validate_registration_request.assert_called_once()
        mock_business_repository.create_business.assert_called_once()
        mock_server_orchestrator.setup_business_servers.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_business_registration_with_validation_failure(self, mock_business_repository):
        """Test business registration with validation failure"""
        # Arrange
        mock_validator = Mock()
        mock_validator.validate_registration_request = AsyncMock(
            side_effect=Exception("Validation failed")
        )
        
        orchestrator = BusinessRegistrationOrchestrator(
            validator=mock_validator,
            repository=mock_business_repository,
            server_orchestrator=Mock(),
            background_tasks=Mock()
        )
        
        request = BusinessRegistrationRequest(
            business_name="",  # Invalid empty name
            business_type="hospitality",
            business_schema={}
        )
        
        # Act & Assert
        with pytest.raises(Exception, match="Validation failed"):
            await orchestrator.register_business(request)


class TestHealthChecks:
    """Integration tests for health check system"""
    
    @pytest.mark.asyncio
    async def test_health_check_manager_initialization(self, health_check_manager):
        """Test health check manager initialization and service registration"""
        # Arrange
        from ..monitoring.health_checks import ServiceHealthConfig
        
        config = ServiceHealthConfig(
            service_name="test_service",
            endpoint="http://localhost:8080/health",
            timeout_seconds=5
        )
        
        # Act
        health_check_manager.register_service(config, "http")
        
        # Assert
        assert "test_service" in health_check_manager.checkers
        assert health_check_manager.get_overall_health() in [
            HealthStatus.HEALTHY, 
            HealthStatus.DEGRADED, 
            HealthStatus.UNHEALTHY, 
            HealthStatus.UNKNOWN
        ]
    
    @pytest.mark.asyncio
    async def test_health_check_execution(self, health_check_manager):
        """Test health check execution for registered services"""
        # Arrange
        from ..monitoring.health_checks import ServiceHealthConfig
        
        config = ServiceHealthConfig(
            service_name="test_service",
            endpoint="http://httpbin.org/status/200",  # Reliable test endpoint
            timeout_seconds=10
        )
        
        health_check_manager.register_service(config, "http")
        
        # Act
        results = await health_check_manager.check_all_services()
        
        # Assert
        assert len(results) >= 1
        test_service_result = next(
            (r for r in results if r.service_name == "test_service"), 
            None
        )
        assert test_service_result is not None
        assert test_service_result.response_time_ms is not None


class TestEndToEndWorkflows:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_complete_booking_workflow_with_payment(self, payment_coordinator, workflow_event_bus):
        """Test complete workflow from A2A booking to AP2 payment"""
        # This would be a comprehensive test that:
        # 1. Registers a business
        # 2. Processes an A2A booking request
        # 3. Coordinates AP2 payment
        # 4. Verifies event publishing
        # 5. Checks health status
        
        # For now, this is a placeholder for the complete workflow
        # In a real implementation, this would orchestrate all components
        
        # Arrange
        business_id = "business_123"
        user_id = "user_123"
        
        # Act - Simulate the complete workflow
        booking_request = Mock()
        booking_request.user_id = user_id
        booking_request.business_id = business_id
        booking_request.intent_description = "Hotel booking for 2 nights"
        booking_request.cart_items = [{"item": "deluxe_room", "price": 200, "quantity": 2}]
        booking_request.payment_method_id = "pm_123"
        booking_request.currency = "USD"
        
        # Process payment workflow
        workflow = await payment_coordinator.coordinate_payment_workflow(booking_request)
        
        # Assert
        assert workflow.status == "completed"
        assert workflow.business_id == business_id
        assert workflow.user_id == user_id
        
        # Verify events were published (this would be verified through event bus)
        # In a real implementation, you'd check the event history


@pytest.mark.asyncio
async def test_concurrent_workflow_execution():
    """Test concurrent execution of multiple workflows"""
    # Arrange
    mock_ap2_client = Mock(spec=AP2Client)
    mock_ap2_client.create_intent_mandate = AsyncMock(return_value=Mock(id="intent_123"))
    mock_ap2_client.create_cart_mandate = AsyncMock(return_value=Mock(id="cart_123"))
    mock_ap2_client.execute_payment = AsyncMock(return_value=Mock(id="payment_123", status="completed"))
    
    mock_business_repository = Mock()
    coordinator = PaymentCoordinator(mock_ap2_client, mock_business_repository)
    
    # Create multiple concurrent requests
    requests = []
    for i in range(5):
        request = Mock()
        request.user_id = f"user_{i}"
        request.business_id = f"business_{i}"
        request.intent_description = f"Booking {i}"
        request.cart_items = [{"item": "room", "price": 100, "quantity": 1}]
        request.payment_method_id = f"pm_{i}"
        request.currency = "USD"
        requests.append(request)
    
    # Act - Execute all workflows concurrently
    tasks = [coordinator.coordinate_payment_workflow(req) for req in requests]
    workflows = await asyncio.gather(*tasks)
    
    # Assert
    assert len(workflows) == 5
    for workflow in workflows:
        assert workflow.status == "completed"
        assert workflow.intent_mandate_id == "intent_123"
        assert workflow.cart_mandate_id == "cart_123"
        assert workflow.transaction_id == "payment_123"


# Performance and load testing
@pytest.mark.asyncio
async def test_workflow_performance_under_load():
    """Test workflow performance under load"""
    # Arrange
    mock_ap2_client = Mock(spec=AP2Client)
    mock_ap2_client.create_intent_mandate = AsyncMock(return_value=Mock(id="intent_123"))
    mock_ap2_client.create_cart_mandate = AsyncMock(return_value=Mock(id="cart_123"))
    mock_ap2_client.execute_payment = AsyncMock(return_value=Mock(id="payment_123", status="completed"))
    
    mock_business_repository = Mock()
    coordinator = PaymentCoordinator(mock_ap2_client, mock_business_repository)
    
    # Act - Execute many workflows concurrently
    start_time = datetime.utcnow()
    
    tasks = []
    for i in range(100):  # Simulate 100 concurrent workflows
        request = Mock()
        request.user_id = f"user_{i}"
        request.business_id = f"business_{i}"
        request.intent_description = f"Booking {i}"
        request.cart_items = [{"item": "room", "price": 100, "quantity": 1}]
        request.payment_method_id = f"pm_{i}"
        request.currency = "USD"
        tasks.append(coordinator.coordinate_payment_workflow(request))
    
    workflows = await asyncio.gather(*tasks)
    
    end_time = datetime.utcnow()
    execution_time = (end_time - start_time).total_seconds()
    
    # Assert
    assert len(workflows) == 100
    assert execution_time < 10  # Should complete within 10 seconds
    assert all(workflow.status == "completed" for workflow in workflows)
    
    # Performance metrics
    workflows_per_second = len(workflows) / execution_time
    assert workflows_per_second > 10  # Should handle at least 10 workflows per second
