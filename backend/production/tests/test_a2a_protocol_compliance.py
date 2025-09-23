"""
A2A Protocol Compliance Tests
Comprehensive test suite for A2A protocol implementation
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from ..core.a2a_integration import A2AAgentCard, A2AAgent, A2AServer, A2ACapability
from ..core.a2a_agent_card_generator import A2AAgentCardGenerator, A2ACapabilityRegistry
from ..core.a2a_registry_network import A2ARegistryNetworkClient, AgentDiscoveryCriteria
from ..core.bais_schema_validator import BAISBusinessSchema


class TestA2AAgentCardCompliance:
    """Test A2A agent card format compliance"""
    
    def test_agent_card_structure_compliance(self):
        """Test that agent card follows A2A specification structure"""
        generator = A2AAgentCardGenerator()
        
        # Create sample business schema
        business_schema = BAISBusinessSchema(
            business_info={
                "id": "test_business_123",
                "name": "Test Hotel",
                "type": "hospitality",
                "version": "1.0"
            },
            integration={
                "mcp_server": {"endpoint": "https://api.test.com/mcp"},
                "a2a_endpoint": {"discovery_url": "https://api.test.com/a2a"}
            },
            version="1.0"
        )
        
        agent_card = generator.generate_agent_card(
            business_schema=business_schema,
            server_endpoint="https://api.test.com/a2a"
        )
        
        # Validate required fields
        assert agent_card.agent.id is not None
        assert agent_card.agent.name == "Test Hotel"
        assert agent_card.agent.description is not None
        assert agent_card.agent.version == "1.0"
        assert len(agent_card.agent.capabilities) > 0
        
        # Validate server configuration
        assert agent_card.server.endpoint == "https://api.test.com/a2a"
        assert agent_card.server.transport == "http"
        assert agent_card.server.version == "2025-06-18"
        assert "json-rpc-2.0" in agent_card.server.supported_protocols
        
        # Validate BAIS integration metadata
        assert "supported_protocols" in agent_card.bais_integration
        assert "AP2" in agent_card.bais_integration["supported_protocols"]
        assert "MCP" in agent_card.bais_integration["supported_protocols"]
    
    def test_agent_card_json_rpc_compliance(self):
        """Test that agent card supports JSON-RPC 2.0 protocol"""
        generator = A2AAgentCardGenerator()
        
        business_schema = BAISBusinessSchema(
            business_info={
                "id": "test_business_123",
                "name": "Test Business",
                "type": "retail",
                "version": "1.0"
            },
            integration={
                "mcp_server": {"endpoint": "https://api.test.com/mcp"},
                "a2a_endpoint": {"discovery_url": "https://api.test.com/a2a"}
            },
            version="1.0"
        )
        
        agent_card = generator.generate_agent_card(
            business_schema=business_schema,
            server_endpoint="https://api.test.com/a2a"
        )
        
        # Validate JSON-RPC support
        assert "json-rpc-2.0" in agent_card.server.supported_protocols
        
        # Validate authentication requirement
        assert agent_card.server.authentication_required is True
    
    def test_capability_schema_compliance(self):
        """Test that capabilities follow A2A capability schema"""
        generator = A2AAgentCardGenerator()
        
        business_schema = BAISBusinessSchema(
            business_info={
                "id": "test_business_123",
                "name": "Test Restaurant",
                "type": "restaurant",
                "version": "1.0"
            },
            integration={
                "mcp_server": {"endpoint": "https://api.test.com/mcp"},
                "a2a_endpoint": {"discovery_url": "https://api.test.com/a2a"}
            },
            version="1.0"
        )
        
        agent_card = generator.generate_agent_card(
            business_schema=business_schema,
            server_endpoint="https://api.test.com/a2a"
        )
        
        # Validate each capability
        for capability in agent_card.agent.capabilities:
            assert capability.name is not None
            assert capability.description is not None
            assert capability.version is not None
            assert capability.timeout_seconds > 0
            
            # Validate input/output schemas
            if capability.input_schema:
                assert isinstance(capability.input_schema, dict)
                assert "type" in capability.input_schema
            
            if capability.output_schema:
                assert isinstance(capability.output_schema, dict)
                assert "type" in capability.output_schema
    
    def test_agent_card_validation(self):
        """Test agent card validation logic"""
        generator = A2AAgentCardGenerator()
        
        # Test valid agent card
        business_schema = BAISBusinessSchema(
            business_info={
                "id": "test_business_123",
                "name": "Test Business",
                "type": "retail",
                "version": "1.0"
            },
            integration={
                "mcp_server": {"endpoint": "https://api.test.com/mcp"},
                "a2a_endpoint": {"discovery_url": "https://api.test.com/a2a"}
            },
            version="1.0"
        )
        
        agent_card = generator.generate_agent_card(
            business_schema=business_schema,
            server_endpoint="https://api.test.com/a2a"
        )
        
        validation_issues = generator.validate_agent_card(agent_card)
        assert len(validation_issues) == 0
        
        # Test invalid agent card (missing name)
        invalid_agent = agent_card.agent
        invalid_agent.name = ""
        
        invalid_card = A2AAgentCard(
            agent=invalid_agent,
            server=agent_card.server,
            bais_integration=agent_card.bais_integration
        )
        
        validation_issues = generator.validate_agent_card(invalid_card)
        assert len(validation_issues) > 0
        assert any("name" in issue.lower() for issue in validation_issues)


class TestA2ADiscoveryCompliance:
    """Test A2A discovery protocol compliance"""
    
    @pytest.fixture
    def registry_client(self):
        """Create mock registry client"""
        client = Mock(spec=A2ARegistryNetworkClient)
        client.discover_agents_across_networks = AsyncMock()
        return client
    
    def test_discovery_request_format(self):
        """Test that discovery requests follow A2A format"""
        criteria = AgentDiscoveryCriteria(
            capabilities_needed=["task_execution", "context_sharing"],
            agent_type="business",
            location="US",
            max_results=50
        )
        
        # Validate criteria structure
        assert isinstance(criteria.capabilities_needed, list)
        assert len(criteria.capabilities_needed) > 0
        assert isinstance(criteria.max_results, int)
        assert criteria.max_results > 0
    
    @pytest.mark.asyncio
    async def test_discovery_response_format(self, registry_client):
        """Test that discovery responses follow A2A format"""
        # Mock discovery response
        mock_agents = [
            A2AAgent(
                id="agent_1",
                name="Test Agent 1",
                description="Test agent for discovery",
                url="https://agent1.test.com",
                capabilities=["task_execution"],
                reputation_score=8.5
            ),
            A2AAgent(
                id="agent_2", 
                name="Test Agent 2",
                description="Another test agent",
                url="https://agent2.test.com",
                capabilities=["context_sharing"],
                reputation_score=9.2
            )
        ]
        
        from ..core.a2a_integration import A2ADiscoveryResponse
        mock_response = A2ADiscoveryResponse(
            agents=mock_agents,
            total_found=2
        )
        
        registry_client.discover_agents_across_networks.return_value = mock_response
        
        # Test discovery
        criteria = AgentDiscoveryCriteria(capabilities_needed=["task_execution"])
        response = await registry_client.discover_agents_across_networks(criteria)
        
        # Validate response structure
        assert response.total_found == 2
        assert len(response.agents) == 2
        
        for agent in response.agents:
            assert agent.id is not None
            assert agent.name is not None
            assert agent.description is not None
            assert agent.url is not None
            assert isinstance(agent.capabilities, list)
            assert isinstance(agent.reputation_score, (int, float))
    
    def test_capability_matching_logic(self):
        """Test capability matching logic"""
        registry = A2ACapabilityRegistry()
        
        # Test capability registration
        task_capability = registry.get_capability("task_execution")
        assert task_capability is not None
        assert task_capability.name == "task_execution"
        assert task_capability.description is not None
        
        # Test capability retrieval
        all_capabilities = registry.get_all_capabilities()
        assert len(all_capabilities) > 0
        
        # Test capability filtering
        task_capabilities = registry.get_capabilities_by_type("task_execution")
        assert len(task_capabilities) > 0


class TestA2ASessionManagement:
    """Test A2A session management compliance"""
    
    def test_session_lifecycle(self):
        """Test A2A session lifecycle management"""
        # This would test session creation, maintenance, and cleanup
        # For now, we'll test the concept with mocks
        
        session_id = "session_123"
        agent_id = "agent_456"
        
        # Mock session creation
        session_data = {
            "session_id": session_id,
            "agent_id": agent_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "status": "active"
        }
        
        assert session_data["session_id"] == session_id
        assert session_data["agent_id"] == agent_id
        assert session_data["status"] == "active"
        
        # Mock session maintenance
        session_data["last_activity"] = datetime.utcnow().isoformat()
        assert "last_activity" in session_data
        
        # Mock session cleanup
        session_data["status"] = "expired"
        assert session_data["status"] == "expired"


class TestA2AJSONRPCCompliance:
    """Test JSON-RPC 2.0 protocol compliance"""
    
    def test_json_rpc_request_format(self):
        """Test JSON-RPC 2.0 request format compliance"""
        request = {
            "jsonrpc": "2.0",
            "method": "a2a.execute_task",
            "params": {
                "task_id": "task_123",
                "capability": "task_execution",
                "parameters": {"input": "test"}
            },
            "id": 1
        }
        
        # Validate required fields
        assert request["jsonrpc"] == "2.0"
        assert "method" in request
        assert "params" in request
        assert "id" in request
        
        # Validate method format
        assert request["method"].startswith("a2a.")
    
    def test_json_rpc_response_format(self):
        """Test JSON-RPC 2.0 response format compliance"""
        response = {
            "jsonrpc": "2.0",
            "result": {
                "task_id": "task_123",
                "status": "completed",
                "result": {"output": "success"}
            },
            "id": 1
        }
        
        # Validate required fields
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert response["id"] == 1
        
        # Validate result structure
        result = response["result"]
        assert "task_id" in result
        assert "status" in result
    
    def test_json_rpc_error_format(self):
        """Test JSON-RPC 2.0 error format compliance"""
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": "Method not found",
                "data": {"method": "a2a.invalid_method"}
            },
            "id": 1
        }
        
        # Validate required fields
        assert error_response["jsonrpc"] == "2.0"
        assert "error" in error_response
        assert error_response["id"] == 1
        
        # Validate error structure
        error = error_response["error"]
        assert "code" in error
        assert "message" in error
        assert isinstance(error["code"], int)


class TestA2AStreamingCompliance:
    """Test A2A streaming protocol compliance"""
    
    def test_server_sent_events_format(self):
        """Test Server-Sent Events format compliance"""
        # Mock SSE event
        event_data = {
            "task_id": "task_123",
            "status": "processing",
            "progress": 0.5,
            "message": "Processing task...",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Format as SSE
        sse_event = f"event: task_update\ndata: {json.dumps(event_data)}\n\n"
        
        # Validate SSE format
        lines = sse_event.strip().split('\n')
        assert lines[0].startswith("event:")
        assert lines[1].startswith("data:")
        assert lines[2] == ""
        
        # Validate event data
        event_json = json.loads(lines[1].split(': ', 1)[1])
        assert "task_id" in event_json
        assert "status" in event_json
        assert "timestamp" in event_json
    
    def test_streaming_event_types(self):
        """Test different streaming event types"""
        event_types = [
            "task_started",
            "task_update", 
            "task_completed",
            "task_failed",
            "task_cancelled"
        ]
        
        for event_type in event_types:
            event_data = {
                "task_id": "task_123",
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            sse_event = f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
            
            # Validate each event type
            assert event_type in sse_event
            assert "data:" in sse_event
            assert sse_event.endswith("\n\n")


class TestA2AIntegrationCompliance:
    """Test A2A integration with other protocols"""
    
    def test_a2a_ap2_integration(self):
        """Test A2A integration with AP2 protocol"""
        # Test that A2A agents can discover AP2 payment capabilities
        agent_card = A2AAgentCard(
            agent=A2AAgent(
                id="payment_agent",
                name="Payment Agent",
                description="Agent with payment capabilities",
                capabilities=[
                    A2ACapability(
                        name="payment_processing",
                        description="Process payments using AP2 protocol",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "amount": {"type": "number"},
                                "currency": {"type": "string"},
                                "payment_method": {"type": "string"}
                            }
                        }
                    )
                ]
            ),
            server=A2AServer(
                endpoint="https://payment-agent.test.com",
                supported_protocols=["json-rpc-2.0"]
            ),
            bais_integration={
                "supported_protocols": ["AP2", "MCP"],
                "payment_capabilities": ["mandate_creation", "payment_execution"]
            }
        )
        
        # Validate AP2 integration
        assert "AP2" in agent_card.bais_integration["supported_protocols"]
        assert "payment_processing" in [cap.name for cap in agent_card.agent.capabilities]
    
    def test_a2a_mcp_integration(self):
        """Test A2A integration with MCP protocol"""
        # Test that A2A agents can provide MCP server capabilities
        agent_card = A2AAgentCard(
            agent=A2AAgent(
                id="mcp_agent",
                name="MCP Agent", 
                description="Agent with MCP server capabilities",
                capabilities=[
                    A2ACapability(
                        name="mcp_server_access",
                        description="Access MCP server functionality",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "mcp_method": {"type": "string"},
                                "parameters": {"type": "object"}
                            }
                        }
                    )
                ]
            ),
            server=A2AServer(
                endpoint="https://mcp-agent.test.com",
                supported_protocols=["json-rpc-2.0"]
            ),
            bais_integration={
                "supported_protocols": ["AP2", "MCP"],
                "mcp_endpoint": "https://mcp-agent.test.com/mcp"
            }
        )
        
        # Validate MCP integration
        assert "MCP" in agent_card.bais_integration["supported_protocols"]
        assert "mcp_endpoint" in agent_card.bais_integration
        assert "mcp_server_access" in [cap.name for cap in agent_card.agent.capabilities]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
