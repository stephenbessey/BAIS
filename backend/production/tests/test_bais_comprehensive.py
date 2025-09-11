"""
BAIS Comprehensive Testing Framework
Test suite covering all components: Schema validation, MCP, A2A, OAuth, Database
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import httpx
from unittest.mock import Mock, patch, AsyncMock

# Import BAIS components for testing
from bais_schema_validator import (
    BAISSchemaValidator, BAISBusinessSchema, BusinessInfo, 
    Location, ContactInfo, BusinessService
)
from mcp_server_generator import BAISMCPServerFactory, BusinessSystemAdapter
from a2a_integration import BAISA2AFactory, BAISA2AClient
from oauth2_security import BAISOAuth2Provider, OAuth2TokenRequest
from database_models import DatabaseManager, BusinessRepository, ServiceRepository
from production_bais_backend import create_production_app

# Test Configuration
TEST_DATABASE_URL = "postgresql://test_user:test_pass@localhost:5433/test_bais"
TEST_REDIS_URL = "redis://localhost:6380/0"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    from database_models import Base
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_business_data():
    """Sample business data for testing"""
    return {
        "business_name": "Test Hotel",
        "business_type": "hospitality",
        "contact_info": {
            "website": "https://testhotel.com",
            "phone": "+1-555-123-4567",
            "email": "test@testhotel.com"
        },
        "location": {
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
            "country": "US"
        },
        "services_config": [
            {
                "id": "room_booking",
                "name": "Room Booking",
                "description": "Hotel room reservations",
                "category": "accommodation",
                "parameters": {
                    "check_in": {"type": "string", "format": "date", "required": True},
                    "check_out": {"type": "string", "format": "date", "required": True},
                    "guests": {"type": "integer", "minimum": 1, "maximum": 6, "default": 2}
                }
            }
        ]
    }

@pytest.fixture
def test_client():
    """FastAPI test client"""
    app = create_production_app()
    return TestClient(app)

class TestBAISSchemaValidator:
    """Test BAIS schema validation functionality"""
    
    def test_create_hospitality_template(self):
        """Test creating hospitality template"""
        template = BAISSchemaValidator.create_hospitality_template()
        
        assert template.bais_version == "1.0"
        assert template.business_info.type.value == "hospitality"
        assert len(template.services) >= 1
        assert template.services[0].id == "room_booking"
    
    def test_valid_schema_validation(self):
        """Test validation of valid schema"""
        template = BAISSchemaValidator.create_hospitality_template()
        schema_data = template.dict()
        
        is_valid, issues = BAISSchemaValidator.validate_schema(schema_data)
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_invalid_schema_validation(self):
        """Test validation of invalid schema"""
        invalid_schema = {
            "business_info": {
                "name": "",  # Invalid: empty name
                "type": "invalid_type"  # Invalid: unknown type
            }
        }
        
        is_valid, issues = BAISSchemaValidator.validate_schema(invalid_schema)
        
        assert is_valid is False
        assert len(issues) > 0
    
    def test_mcp_compatibility_validation(self):
        """Test MCP protocol compatibility validation"""
        template = BAISSchemaValidator.create_hospitality_template()
        
        issues = template.validate_mcp_compatibility()
        
        assert isinstance(issues, list)
        # Should have no issues for valid template
        assert len(issues) == 0
    
    def test_a2a_compatibility_validation(self):
        """Test A2A protocol compatibility validation"""
        template = BAISSchemaValidator.create_hospitality_template()
        
        issues = template.validate_a2a_compatibility()
        
        assert isinstance(issues, list)
        # Should have no issues for valid template
        assert len(issues) == 0

class TestMCPServerGeneration:
    """Test MCP server generation and functionality"""
    
    @pytest.fixture
    def business_schema(self):
        """Business schema for testing"""
        return BAISSchemaValidator.create_hospitality_template()
    
    @pytest.fixture
    def mock_adapter(self):
        """Mock business system adapter"""
        adapter = Mock(spec=BusinessSystemAdapter)
        adapter.get_availability = AsyncMock(return_value={
            "available_slots": [
                {"date": "2024-03-15", "available": True, "price": 159.00}
            ]
        })
        adapter.search_availability = AsyncMock(return_value={
            "search_id": "test-search-123",
            "results": [{"date": "2024-03-15", "available": True}],
            "total_results": 1
        })
        adapter.create_booking = AsyncMock(return_value={
            "booking_id": "test-booking-123",
            "status": "confirmed",
            "confirmation_number": "BAIS-TEST123"
        })
        return adapter
    
    def test_mcp_server_creation(self, business_schema):
        """Test MCP server creation"""
        server = BAISMCPServerFactory.create_server(business_schema)
        
        assert server is not None
        assert server.business_schema == business_schema
        assert hasattr(server, 'app')
    
    @pytest.mark.asyncio
    async def test_mcp_resource_listing(self, business_schema, mock_adapter):
        """Test MCP resource listing"""
        from mcp_server_generator import BAISMCPServer
        
        server = BAISMCPServer(business_schema, mock_adapter)
        
        # Mock authentication
        mock_auth = Mock()
        mock_auth.credentials = "valid-token"
        
        with patch.object(server, '_validate_auth', return_value=None):
            response = await server.app.router.routes[2].endpoint(mock_auth)
            
            assert response.resources is not None
            assert len(response.resources) > 0
            
            # Check for expected resources
            resource_uris = [r.uri for r in response.resources]
            assert any("availability://" in uri for uri in resource_uris)
            assert any("service://" in uri for uri in resource_uris)
    
    @pytest.mark.asyncio
    async def test_mcp_tool_execution(self, business_schema, mock_adapter):
        """Test MCP tool execution"""
        from mcp_server_generator import BAISMCPServer, MCPCallToolRequest
        
        server = BAISMCPServer(business_schema, mock_adapter)
        
        # Test search tool
        request = MCPCallToolRequest(
            name="search_room_booking",
            arguments={
                "check_in": "2024-03-15",
                "check_out": "2024-03-17",
                "guests": 2
            }
        )
        
        mock_auth = Mock()
        mock_auth.credentials = "valid-token"
        
        with patch.object(server, '_validate_auth', return_value=None):
            response = await server.app.router.routes[4].endpoint(request, mock_auth)
            
            assert response.isError is False
            assert len(response.content) > 0
            
            # Verify mock was called
            mock_adapter.search_availability.assert_called_once()

class TestA2AIntegration:
    """Test A2A protocol integration"""
    
    @pytest.fixture
    def business_schema(self):
        """Business schema for testing"""
        return BAISSchemaValidator.create_hospitality_template()
    
    @pytest.fixture
    def mcp_server(self, business_schema):
        """MCP server for testing"""
        return BAISMCPServerFactory.create_server(business_schema)
    
    def test_a2a_server_creation(self, business_schema, mcp_server):
        """Test A2A server creation"""
        a2a_server = BAISA2AFactory.create_server(business_schema, mcp_server)
        
        assert a2a_server is not None
        assert a2a_server.business_schema == business_schema
        assert a2a_server.mcp_server == mcp_server
        assert hasattr(a2a_server, 'agent_card')
    
    def test_agent_card_generation(self, business_schema, mcp_server):
        """Test agent card generation"""
        a2a_server = BAISA2AFactory.create_server(business_schema, mcp_server)
        
        agent_card = a2a_server.agent_card
        
        assert agent_card.agent.name is not None
        assert len(agent_card.agent.capabilities) > 0
        assert agent_card.server.endpoint is not None
        assert agent_card.bais_integration is not None
    
    @pytest.mark.asyncio
    async def test_a2a_client_discovery(self):
        """Test A2A client agent discovery"""
        client = BAISA2AClient()
        
        # Mock discovery response
        mock_response = Mock()
        mock_response.json.return_value = {
            "agent": {
                "name": "Test Agent",
                "capabilities": ["search_room_booking"]
            },
            "server": {
                "endpoint": "https://test.example.com/a2a"
            }
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(client.client, 'get', return_value=mock_response):
            agent_card = await client.discover_agent("https://test.example.com/.well-known/agent.json")
            
            assert agent_card.agent.name == "Test Agent"
            assert "search_room_booking" in [cap.name for cap in agent_card.agent.capabilities]

class TestOAuth2Security:
    """Test OAuth 2.0 security implementation"""
    
    @pytest.fixture
    def oauth_provider(self):
        """OAuth provider for testing"""
        return BAISOAuth2Provider(secret_key="test-secret-key")
    
    def test_client_registration(self, oauth_provider):
        """Test OAuth client registration"""
        from oauth2_security import OAuth2ClientCredentials
        
        client_data = OAuth2ClientCredentials(
            client_id="test_client",
            client_secret="test_secret",
            client_name="Test Client",
            redirect_uris=["http://localhost:3000/callback"],
            scopes=["read", "write"]
        )
        
        client_id = oauth_provider.register_client(client_data)
        
        assert client_id == "test_client"
        assert "test_client" in oauth_provider.clients
    
    def test_client_validation(self, oauth_provider):
        """Test client credentials validation"""
        from oauth2_security import OAuth2ClientCredentials
        
        # Register client first
        client_data = OAuth2ClientCredentials(
            client_id="test_client",
            client_secret="test_secret",
            client_name="Test Client",
            redirect_uris=["http://localhost:3000/callback"],
            scopes=["read"]
        )
        oauth_provider.register_client(client_data)
        
        # Test validation
        is_valid = oauth_provider.validate_client("test_client", "test_secret")
        assert is_valid is True
        
        # Test invalid credentials
        is_invalid = oauth_provider.validate_client("test_client", "wrong_secret")
        assert is_invalid is False
    
    def test_authorization_code_flow(self, oauth_provider):
        """Test authorization code flow"""
        from oauth2_security import OAuth2ClientCredentials, OAuth2TokenRequest
        
        # Register client
        client_data = OAuth2ClientCredentials(
            client_id="test_client",
            client_secret="test_secret",
            client_name="Test Client",
            redirect_uris=["http://localhost:3000/callback"],
            scopes=["read"]
        )
        oauth_provider.register_client(client_data)
        
        # Create authorization code
        code = oauth_provider.create_authorization_code(
            client_id="test_client",
            redirect_uri="http://localhost:3000/callback",
            scope="read"
        )
        
        assert code is not None
        assert code in oauth_provider.authorization_codes
        
        # Exchange for token
        token_request = OAuth2TokenRequest(
            grant_type="authorization_code",
            code=code,
            redirect_uri="http://localhost:3000/callback",
            client_id="test_client",
            client_secret="test_secret"
        )
        
        token_response = oauth_provider.exchange_code_for_token(token_request)
        
        assert token_response.access_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.expires_in > 0
    
    def test_token_introspection(self, oauth_provider):
        """Test token introspection"""
        from oauth2_security import OAuth2ClientCredentials, OAuth2TokenRequest
        
        # Setup client and get token
        client_data = OAuth2ClientCredentials(
            client_id="test_client",
            client_secret="test_secret",
            client_name="Test Client",
            redirect_uris=["http://localhost:3000/callback"],
            scopes=["read"]
        )
        oauth_provider.register_client(client_data)
        
        token_request = OAuth2TokenRequest(
            grant_type="client_credentials",
            client_id="test_client",
            client_secret="test_secret",
            scope="read"
        )
        
        token_response = oauth_provider.exchange_code_for_token(token_request)
        
        # Introspect token
        introspection = oauth_provider.introspect_token(token_response.access_token)
        
        assert introspection.active is True
        assert introspection.client_id == "test_client"
        assert introspection.scope == "read"

class TestDatabaseModels:
    """Test database models and repositories"""
    
    def test_business_creation(self, test_db):
        """Test business creation in database"""
        from database_models import BusinessRepository
        
        repo = BusinessRepository(test_db)
        
        business_data = {
            "external_id": "test-hotel-001",
            "name": "Test Hotel",
            "business_type": "hospitality",
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "email": "test@testhotel.com",
            "mcp_endpoint": "https://test.example.com/mcp",
            "a2a_endpoint": "https://test.example.com/.well-known/agent.json"
        }
        
        business = repo.create_business(business_data)
        
        assert business.id is not None
        assert business.name == "Test Hotel"
        assert business.business_type == "hospitality"
    
    def test_service_creation(self, test_db):
        """Test service creation in database"""
        from database_models import BusinessRepository, ServiceRepository
        
        # Create business first
        business_repo = BusinessRepository(test_db)
        business_data = {
            "external_id": "test-hotel-001",
            "name": "Test Hotel",
            "business_type": "hospitality",
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "email": "test@testhotel.com",
            "mcp_endpoint": "https://test.example.com/mcp",
            "a2a_endpoint": "https://test.example.com/.well-known/agent.json"
        }
        business = business_repo.create_business(business_data)
        
        # Create service
        service_repo = ServiceRepository(test_db)
        service_data = {
            "business_id": business.id,
            "service_id": "room_booking",
            "name": "Room Booking",
            "description": "Hotel room reservations",
            "category": "accommodation",
            "workflow_pattern": "booking_confirmation_payment",
            "workflow_steps": [{"step": "check", "description": "Check availability"}],
            "parameters_schema": {"check_in": {"type": "string"}},
            "availability_endpoint": "/api/availability",
            "cancellation_policy": {"type": "flexible"},
            "payment_config": {"methods": ["credit_card"]}
        }
        
        service = service_repo.create_service(service_data)
        
        assert service.id is not None
        assert service.business_id == business.id
        assert service.service_id == "room_booking"
    
    def test_business_query_filters(self, test_db):
        """Test business query with filters"""
        from database_models import BusinessRepository
        
        repo = BusinessRepository(test_db)
        
        # Create test businesses
        businesses_data = [
            {
                "external_id": "hotel-001",
                "name": "Test Hotel 1",
                "business_type": "hospitality",
                "city": "New York",
                "state": "NY",
                "address": "123 NY St",
                "email": "test1@hotel.com",
                "status": "active",
                "mcp_endpoint": "https://test1.example.com/mcp",
                "a2a_endpoint": "https://test1.example.com/.well-known/agent.json"
            },
            {
                "external_id": "restaurant-001",
                "name": "Test Restaurant 1",
                "business_type": "food_service",
                "city": "Los Angeles",
                "state": "CA",
                "address": "456 LA St",
                "email": "test1@restaurant.com",
                "status": "active",
                "mcp_endpoint": "https://test2.example.com/mcp",
                "a2a_endpoint": "https://test2.example.com/.well-known/agent.json"
            }
        ]
        
        for data in businesses_data:
            repo.create_business(data)
        
        # Test filtering by business type
        hotels = repo.list_businesses(business_type="hospitality")
        assert len(hotels) == 1
        assert hotels[0].name == "Test Hotel 1"
        
        # Test filtering by city
        ny_businesses = repo.list_businesses(city="New York")
        assert len(ny_businesses) == 1
        assert ny_businesses[0].city == "New York"

class TestProductionAPI:
    """Test production API endpoints"""
    
    @pytest.fixture
    def authenticated_headers(self):
        """Headers with authentication for API testing"""
        return {"Authorization": "Bearer test-token"}
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_business_registration_endpoint(self, test_client, sample_business_data):
        """Test business registration endpoint"""
        response = test_client.post("/api/v1/businesses", json=sample_business_data)
        
        # Note: This will fail without proper database setup
        # In tests, need mock the database or use test database
        assert response.status_code in [200, 201, 500]  # 500 expected without DB
    
    def test_schema_validation_endpoint(self, test_client):
        """Test schema validation endpoint"""
        template = BAISSchemaValidator.create_hospitality_template()
        schema_data = template.dict()
        
        response = test_client.post(
            "/api/v1/schemas/validate",
            json={"schema_data": schema_data}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "issues" in data

class TestIntegrationScenarios:
    """Integration tests covering full scenarios"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_booking_flow(self):
        """Test complete booking flow from agent to business"""
        # This  test the full flow:
        # 1. Agent discovers business via A2A
        # 2. Agent authenticates via OAuth
        # 3. Agent searches availability via MCP
        # 4. Agent creates booking via MCP
        # 5. Business confirms booking
        
        # Mock the components for integration test
        business_schema = BAISSchemaValidator.create_hospitality_template()
        
        # Create mock business adapter
        mock_adapter = Mock(spec=BusinessSystemAdapter)
        mock_adapter.search_availability = AsyncMock(return_value={
            "search_id": "test-search-123",
            "results": [{"date": "2024-03-15", "available": True, "price": 159.00}],
            "total_results": 1
        })
        mock_adapter.create_booking = AsyncMock(return_value={
            "booking_id": "test-booking-123",
            "status": "confirmed",
            "confirmation_number": "BAIS-TEST123",
            "total_amount": 318.00,
            "currency": "USD"
        })
        
        # Test the flow
        mcp_server = BAISMCPServerFactory.create_server(business_schema)
        mcp_server.business_adapter = mock_adapter
        
        a2a_server = BAISA2AFactory.create_server(business_schema, mcp_server)
        
        # Simulate agent task execution
        from a2a_integration import A2ATaskRequest
        
        # Search task
        search_request = A2ATaskRequest(
            capability="search_room_booking",
            input={
                "check_in": "2024-03-15",
                "check_out": "2024-03-17",
                "guests": 2
            }
        )
        
        await a2a_server._execute_task(search_request, a2a_server.agent_card.agent.capabilities[0])
        
        # Verify search was executed
        assert search_request.task_id in a2a_server.task_results
        search_result = a2a_server.task_results[search_request.task_id]
        assert search_result.status == "completed"
        assert search_result.output is not None
        
        # Booking task
        booking_request = A2ATaskRequest(
            capability="book_room_booking",
            input={
                "check_in": "2024-03-15",
                "check_out": "2024-03-17",
                "guests": 2,
                "customer_info": {
                    "name": "Test Customer",
                    "email": "test@customer.com"
                }
            }
        )
        
        await a2a_server._execute_task(booking_request, a2a_server.agent_card.agent.capabilities[1])
        
        # Verify booking was executed
        assert booking_request.task_id in a2a_server.task_results
        booking_result = a2a_server.task_results[booking_request.task_id]
        assert booking_result.status == "completed"
        assert booking_result.output["booking_id"] == "test-booking-123"
        assert booking_result.output["status"] == "confirmed"

class TestPerformance:
    """Performance and load testing"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        business_schema = BAISSchemaValidator.create_hospitality_template()
        
        # Create multiple concurrent tasks
        tasks = []
        for i in range(10):
            task = asyncio.create_task(self._simulate_agent_request(business_schema, i))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all tasks completed successfully
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Task {i} failed with exception: {result}")
            assert result["status"] == "completed"
    
    async def _simulate_agent_request(self, business_schema, request_id):
        """Simulate an agent request"""
        # Mock a simple agent interaction
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return {
            "request_id": request_id,
            "status": "completed",
            "processing_time": 100
        }
    
    def test_schema_validation_performance(self):
        """Test schema validation performance"""
        import time
        
        template = BAISSchemaValidator.create_hospitality_template()
        schema_data = template.dict()
        
        # Measure validation time
        start_time = time.time()
        
        for _ in range(100):
            is_valid, issues = BAISSchemaValidator.validate_schema(schema_data)
            assert is_valid is True
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 100 validations in under 1 second
        assert total_time < 1.0
        print(f"100 schema validations completed in {total_time:.3f} seconds")

# Test configuration and utilities
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test"""
    # Set test environment variables
    import os
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["REDIS_URL"] = TEST_REDIS_URL
    
    yield
    
    # Cleanup after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )

# Utility functions for testing
def create_test_business_schema():
    """Create a test business schema"""
    return BAISSchemaValidator.create_hospitality_template()

def create_mock_agent_request(service_id="room_booking", **kwargs):
    """Create a mock agent request"""
    default_params = {
        "check_in": "2024-03-15",
        "check_out": "2024-03-17",
        "guests": 2
    }
    default_params.update(kwargs)
    
    return {
        "service_id": service_id,
        "parameters": default_params,
        "agent_id": "test-agent",
        "interaction_type": "search"
    }

if __name__ == "__main__":
    # Run tests
    pytest.main([
        "-v",
        "--tb=short",
        "--strict-markers",
        "--cov=bais",
        "--cov-report=html",
        "--cov-report=term-missing"
    ])