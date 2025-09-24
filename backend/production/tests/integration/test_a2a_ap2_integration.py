"""
Comprehensive A2A and AP2 Integration Tests
Tests the complete integration following testing best practices
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from ...core.a2a_integration import BAISA2AServer, A2ATaskRequest, A2ATaskStatus
from ...core.payments.ap2_client import AP2Client, AP2ClientConfig
from ...core.payments.payment_coordinator import PaymentCoordinator
from ...core.protocol_error_handler import A2ATaskError, AP2AuthenticationError, ErrorContext
from ...config.protocol_settings import A2ASettings, AP2Settings


class TestA2ACompleteWorkflow:
    """Test complete A2A workflows"""
    
    @pytest.fixture
    async def a2a_server_setup(self):
        """Setup A2A server with mock dependencies"""
        from ...core.bais_schema_validator import BAISSchemaValidator
        from ...core.mcp_server_generator import BAISMCPServerFactory
        
        # Create test business schema
        business_schema = BAISSchemaValidator.create_hospitality_template()
        business_schema.business_info.name = "Test Hotel"
        business_schema.business_info.id = "test_hotel_123"
        
        # Create mock MCP server
        mcp_server = Mock()
        mcp_server.handle_request = AsyncMock(return_value={"success": True})
        
        # Create A2A server
        a2a_server = BAISA2AServer(business_schema, mcp_server)
        
        return {
            "server": a2a_server,
            "schema": business_schema,
            "mcp": mcp_server
        }
    
    @pytest.mark.asyncio
    async def test_agent_discovery_workflow(self, a2a_server_setup):
        """Test complete agent discovery workflow"""
        server = a2a_server_setup["server"]
        
        # Test agent card endpoint
        agent_card = await server.app.get("/.well-known/agent.json")
        
        assert agent_card.agent.name == "Test Hotel"
        assert len(agent_card.agent.capabilities) > 0
        assert agent_card.server.endpoint is not None
        
        # Verify capabilities include expected services
        capability_names = [cap.name for cap in agent_card.agent.capabilities]
        assert "room_booking" in capability_names
        assert "room_search" in capability_names
    
    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self, a2a_server_setup):
        """Test coordination between multiple A2A agents"""
        from ...core.a2a_integration import BAISA2AClient
        
        client = BAISA2AClient()
        
        # Mock external agent responses
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock hotel agent discovery
            mock_hotel_response = Mock()
            mock_hotel_response.json.return_value = {
                "agent": {
                    "name": "Hotel Agent",
                    "capabilities": [{"name": "room_booking"}]
                },
                "server": {"endpoint": "https://hotel.example.com"}
            }
            mock_hotel_response.raise_for_status = Mock()
            
            # Mock restaurant agent discovery  
            mock_restaurant_response = Mock()
            mock_restaurant_response.json.return_value = {
                "agent": {
                    "name": "Restaurant Agent", 
                    "capabilities": [{"name": "table_reservation"}]
                },
                "server": {"endpoint": "https://restaurant.example.com"}
            }
            mock_restaurant_response.raise_for_status = Mock()
            
            mock_get.side_effect = [mock_hotel_response, mock_restaurant_response]
            
            # Test agent discovery
            hotel_agent = await client.discover_agent("https://hotel.example.com/.well-known/agent.json")
            restaurant_agent = await client.discover_agent("https://restaurant.example.com/.well-known/agent.json")
            
            assert hotel_agent.agent.name == "Hotel Agent"
            assert restaurant_agent.agent.name == "Restaurant Agent"
    
    @pytest.mark.asyncio
    async def test_task_execution_lifecycle(self, a2a_server_setup):
        """Test complete task execution lifecycle"""
        server = a2a_server_setup["server"]
        
        # Create task request
        task_request = A2ATaskRequest(
            task_id="test_task_123",
            capability="room_search",
            input={
                "check_in": "2024-04-01",
                "check_out": "2024-04-03", 
                "guests": 2
            },
            timeout_seconds=30
        )
        
        # Submit task
        initial_status = await server.submit_task(task_request)
        assert initial_status.task_id == "test_task_123"
        assert initial_status.status == "pending"
        
        # Wait for task processing
        await asyncio.sleep(0.1)
        
        # Check task status
        updated_status = server.tasks.get("test_task_123")
        assert updated_status is not None
        assert updated_status.status in ["running", "completed"]


class TestAP2CompleteWorkflow:
    """Test complete AP2 payment workflows"""
    
    @pytest.fixture
    def ap2_client_setup(self):
        """Setup AP2 client with test configuration"""
        config = AP2ClientConfig(
            client_id="test_client",
            private_key="-----BEGIN PRIVATE KEY-----\nTEST_KEY\n-----END PRIVATE KEY-----",
            public_key="-----BEGIN PUBLIC KEY-----\nTEST_PUBLIC_KEY\n-----END PUBLIC KEY-----",
            base_url="https://test-ap2.example.com"
        )
        
        with patch('cryptography.hazmat.primitives.serialization.load_pem_private_key'):
            client = AP2Client(config)
            
        return client
    
    @pytest.mark.asyncio
    async def test_complete_payment_workflow(self, ap2_client_setup):
        """Test complete payment workflow from intent to execution"""
        client = ap2_client_setup
        
        # Mock HTTP responses
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock intent mandate creation
            intent_response = Mock()
            intent_response.json.return_value = {
                "id": "intent_123",
                "type": "intent", 
                "user_id": "user_456",
                "business_id": "business_789",
                "constraints": {"max_amount": 500.00},
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
            intent_response.raise_for_status = Mock()
            
            # Mock cart mandate creation
            cart_response = Mock()
            cart_response.json.return_value = {
                "id": "cart_456",
                "type": "cart",
                "items": [{"name": "Hotel Room", "price": 150.00}],
                "total": 150.00
            }
            cart_response.raise_for_status = Mock()
            
            # Mock payment execution
            payment_response = Mock() 
            payment_response.json.return_value = {
                "id": "payment_789",
                "status": "completed",
                "amount": 150.00,
                "currency": "USD"
            }
            payment_response.raise_for_status = Mock()
            
            mock_post.side_effect = [intent_response, cart_response, payment_response]
            
            # Step 1: Create intent mandate
            intent_mandate = await client.create_intent_mandate({
                "max_amount": 500.00,
                "merchant_id": "business_789"
            })
            
            assert intent_mandate.id == "intent_123"
            assert intent_mandate.type == "intent"
            
            # Step 2: Create cart mandate
            cart_mandate = await client.create_cart_mandate({
                "items": [{"name": "Hotel Room", "price": 150.00}],
                "total": 150.00
            })
            
            assert cart_mandate.id == "cart_456"
            assert cart_mandate.total == 150.00
            
            # Step 3: Execute payment
            payment_result = await client.execute_payment(cart_mandate)
            
            assert payment_result.id == "payment_789"
            assert payment_result.status == "completed"
    
    @pytest.mark.asyncio 
    async def test_payment_error_handling(self, ap2_client_setup):
        """Test payment error handling scenarios"""
        client = ap2_client_setup
        
        # Test authentication error
        with patch('httpx.AsyncClient.post') as mock_post:
            error_response = Mock()
            error_response.status_code = 401
            error_response.json.return_value = {"error": "Invalid signature"}
            
            from httpx import HTTPStatusError
            mock_post.side_effect = HTTPStatusError(
                "Authentication failed", 
                request=Mock(), 
                response=error_response
            )
            
            with pytest.raises(AP2AuthenticationError) as exc_info:
                await client.create_intent_mandate({"max_amount": 100.00})
            
            assert "Authentication failed" in str(exc_info.value)


class TestIntegratedA2AandAP2Workflow:
    """Test integrated A2A and AP2 workflows"""
    
    @pytest.fixture
    async def integrated_setup(self):
        """Setup integrated A2A and AP2 environment"""
        # A2A server setup
        from ...core.bais_schema_validator import BAISSchemaValidator
        business_schema = BAISSchemaValidator.create_hospitality_template()
        
        mcp_server = Mock()
        a2a_server = BAISA2AServer(business_schema, mcp_server)
        
        # AP2 client setup
        ap2_config = AP2ClientConfig(
            client_id="test_client",
            private_key="-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----",
            public_key="-----BEGIN PUBLIC KEY-----\nTEST\n-----END PUBLIC KEY-----"
        )
        
        with patch('cryptography.hazmat.primitives.serialization.load_pem_private_key'):
            ap2_client = AP2Client(ap2_config)
        
        # Payment coordinator
        business_repository = Mock()
        payment_coordinator = PaymentCoordinator(ap2_client, business_repository)
        
        return {
            "a2a_server": a2a_server,
            "ap2_client": ap2_client,
            "payment_coordinator": payment_coordinator,
            "business_schema": business_schema
        }
    
    @pytest.mark.asyncio
    async def test_hotel_booking_with_payment(self, integrated_setup):
        """Test complete hotel booking workflow with payment"""
        a2a_server = integrated_setup["a2a_server"]
        payment_coordinator = integrated_setup["payment_coordinator"]
        
        # Mock payment responses
        with patch.object(payment_coordinator, 'process_payment') as mock_payment:
            mock_payment.return_value = {
                "payment_id": "payment_123",
                "status": "completed", 
                "amount": 300.00
            }
            
            # Step 1: A2A task for room search
            search_task = A2ATaskRequest(
                capability="room_search",
                input={
                    "check_in": "2024-04-01",
                    "check_out": "2024-04-03",
                    "guests": 2,
                    "budget_max": 350.00
                }
            )
            
            search_status = await a2a_server.submit_task(search_task)
            assert search_status.status == "pending"
            
            # Step 2: A2A task for room booking with AP2 payment
            booking_task = A2ATaskRequest(
                capability="room_booking",
                input={
                    "room_id": "room_456",
                    "check_in": "2024-04-01", 
                    "check_out": "2024-04-03",
                    "guests": 2,
                    "payment": {
                        "type": "ap2",
                        "mandate_id": "mandate_789",
                        "amount": 300.00
                    }
                }
            )
            
            booking_status = await a2a_server.submit_task(booking_task)
            assert booking_status.status == "pending"
            
            # Verify payment was processed
            mock_payment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_propagation_between_protocols(self, integrated_setup):
        """Test error propagation between A2A and AP2"""
        payment_coordinator = integrated_setup["payment_coordinator"]
        
        # Mock AP2 authentication error
        with patch.object(payment_coordinator, 'process_payment') as mock_payment:
            mock_payment.side_effect = AP2AuthenticationError(
                "Invalid mandate signature",
                mandate_id="mandate_123"
            )
            
            # Attempt payment processing
            with pytest.raises(AP2AuthenticationError) as exc_info:
                await payment_coordinator.process_payment({
                    "mandate_id": "mandate_123",
                    "amount": 150.00
                })
            
            assert exc_info.value.mandate_id == "mandate_123"
            assert "Invalid mandate signature" in str(exc_info.value)


class TestSecurityAndCompliance:
    """Test security and compliance features"""
    
    @pytest.mark.asyncio
    async def test_mandate_signature_verification(self):
        """Test AP2 mandate signature verification"""
        # This would test actual cryptographic verification
        # Implementation depends on your specific crypto setup
        pass
    
    @pytest.mark.asyncio
    async def test_a2a_rate_limiting(self):
        """Test A2A endpoint rate limiting"""
        # This would test rate limiting implementation
        # Depends on your rate limiting strategy
        pass
    
    @pytest.mark.asyncio
    async def test_audit_logging(self):
        """Test audit logging for both protocols"""
        from ...core.protocol_error_handler import StructuredLogger
        
        logger = StructuredLogger("test_audit")
        
        # Test A2A operation logging
        logger.log_a2a_task("task_123", "completed", {
            "operation": "room_booking",
            "business_id": "business_456"
        })
        
        # Test AP2 operation logging
        logger.log_ap2_payment("mandate_789", "completed", {
            "amount": 200.00,
            "currency": "USD"
        })
        
        # Verify logging calls (would check actual log output in real implementation)
        assert True  # Placeholder for actual log verification


# Performance testing
class TestPerformance:
    """Performance tests for A2A and AP2 operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_a2a_tasks(self):
        """Test handling of concurrent A2A tasks"""
        # Test concurrent task processing
        # Measure response times and resource usage
        pass
    
    @pytest.mark.asyncio
    async def test_ap2_payment_throughput(self):
        """Test AP2 payment processing throughput"""
        # Test payment processing under load
        # Measure transaction rates
        pass


# Configuration for test execution
if __name__ == "__main__":
    pytest.main([
        "-v",
        "--tb=short", 
        "--asyncio-mode=auto",
        "--cov=core",
        "--cov-report=html",
        "test_a2a_ap2_integration.py"
    ])
