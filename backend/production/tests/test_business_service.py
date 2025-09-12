"""
Unit Tests for Business Service
Comprehensive test coverage for business registration and status management
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4

from ..services.business_service import (
    BusinessService,
    BusinessRegistrationError,
    BusinessNotFoundError,
    SchemaValidationError
)
from ..api_models import BusinessRegistrationRequest, BusinessRegistrationResponse
from ..core.database_models import DatabaseManager, BusinessRepository
from ..core.parameter_objects import BusinessSearchCriteria


class TestBusinessService:
    """Test suite for BusinessService"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager"""
        return Mock(spec=DatabaseManager)
    
    @pytest.fixture
    def mock_background_tasks(self):
        """Mock background tasks"""
        return Mock()
    
    @pytest.fixture
    def mock_business_repository(self):
        """Mock business repository"""
        return Mock(spec=BusinessRepository)
    
    @pytest.fixture
    def business_service(self, mock_db_manager, mock_background_tasks, mock_business_repository):
        """Create business service with mocked dependencies"""
        service = BusinessService(mock_db_manager, mock_background_tasks)
        service._business_repository = mock_business_repository
        return service
    
    @pytest.fixture
    def valid_registration_request(self):
        """Valid business registration request"""
        return BusinessRegistrationRequest(
            name="Test Hotel",
            business_type="hospitality",
            description="A test hotel for unit testing",
            contact_info={
                "email": "test@hotel.com",
                "phone": "+1-555-0123",
                "website": "https://testhotel.com"
            },
            location={
                "address": "123 Test Street",
                "city": "Test City",
                "state": "TS",
                "postal_code": "12345",
                "country": "US"
            },
            services_config=[
                {
                    "service_id": "room_booking",
                    "name": "Room Booking",
                    "description": "Book hotel rooms",
                    "category": "accommodation",
                    "workflow_pattern": "booking",
                    "workflow_steps": [
                        {"step": "check_availability", "endpoint": "/availability"},
                        {"step": "create_booking", "endpoint": "/bookings"}
                    ],
                    "parameters_schema": {
                        "check_in_date": {"type": "date", "required": True},
                        "check_out_date": {"type": "date", "required": True},
                        "guests": {"type": "integer", "required": True}
                    },
                    "availability_endpoint": "https://api.testhotel.com/availability"
                }
            ],
            integration_config={
                "mcp_server": {
                    "endpoint": "https://api.testhotel.com/mcp",
                    "version": "1.0"
                },
                "a2a_endpoint": {
                    "discovery_url": "https://api.testhotel.com/a2a/discover",
                    "version": "1.0"
                }
            }
        )
    
    @pytest.mark.asyncio
    async def test_register_business_success(self, business_service, valid_registration_request):
        """Test successful business registration"""
        # Mock the schema creation and validation
        mock_schema = Mock()
        mock_schema.business_info.id = str(uuid4())
        mock_schema.integration.mcp_server.endpoint = "https://api.testhotel.com/mcp"
        mock_schema.integration.a2a_endpoint.discovery_url = "https://api.testhotel.com/a2a/discover"
        
        with patch.object(business_service, '_create_business_schema', return_value=mock_schema), \
             patch.object(business_service, '_validate_business_schema'), \
             patch.object(business_service, '_generate_secure_api_key', return_value="test_api_key"), \
             patch.object(business_service, '_persist_business_data', new_callable=AsyncMock), \
             patch.object(business_service, '_schedule_server_setup'), \
             patch.object(business_service, '_build_registration_response') as mock_build_response:
            
            expected_response = BusinessRegistrationResponse(
                business_id=mock_schema.business_info.id,
                status="registered",
                mcp_endpoint=mock_schema.integration.mcp_server.endpoint,
                a2a_endpoint=mock_schema.integration.a2a_endpoint.discovery_url,
                api_keys={"primary": "test_api_key"},
                setup_complete=False
            )
            mock_build_response.return_value = expected_response
            
            result = await business_service.register_business(valid_registration_request)
            
            assert result == expected_response
            business_service._create_business_schema.assert_called_once_with(valid_registration_request)
            business_service._validate_business_schema.assert_called_once_with(mock_schema)
            business_service._generate_secure_api_key.assert_called_once_with(mock_schema.business_info.id)
            business_service._persist_business_data.assert_called_once_with(mock_schema, "test_api_key")
            business_service._schedule_server_setup.assert_called_once_with(mock_schema)
    
    @pytest.mark.asyncio
    async def test_register_business_schema_validation_failure(self, business_service, valid_registration_request):
        """Test business registration with schema validation failure"""
        mock_schema = Mock()
        
        with patch.object(business_service, '_create_business_schema', return_value=mock_schema), \
             patch.object(business_service, '_validate_business_schema', 
                         side_effect=SchemaValidationError("Invalid schema")):
            
            with pytest.raises(SchemaValidationError):
                await business_service.register_business(valid_registration_request)
    
    @pytest.mark.asyncio
    async def test_register_business_general_error(self, business_service, valid_registration_request):
        """Test business registration with general error"""
        with patch.object(business_service, '_create_business_schema', 
                         side_effect=Exception("Database connection failed")):
            
            with pytest.raises(Exception) as exc_info:
                await business_service.register_business(valid_registration_request)
            
            assert "Database connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_business_status_success(self, business_service):
        """Test successful business status retrieval"""
        business_id = str(uuid4())
        mock_business_data = Mock()
        mock_business_data.name = "Test Hotel"
        mock_business_data.status = "active"
        mock_business_data.services = [Mock(), Mock()]  # 2 services
        mock_business_data.mcp_server_active = True
        mock_business_data.a2a_server_active = True
        
        business_service._business_repository.get_business_by_id = AsyncMock(return_value=mock_business_data)
        business_service._gather_business_metrics = AsyncMock(return_value={
            "total_interactions": 100,
            "successful_bookings": 25,
            "revenue_today": 1500.00,
            "avg_response_time_ms": 120
        })
        
        result = await business_service.get_business_status(business_id)
        
        assert result.business_id == business_id
        assert result.name == "Test Hotel"
        assert result.status == "active"
        assert result.services_enabled == 2
        assert result.mcp_server_active is True
        assert result.a2a_server_active is True
        assert result.metrics["total_interactions"] == 100
    
    @pytest.mark.asyncio
    async def test_get_business_status_not_found(self, business_service):
        """Test business status retrieval when business not found"""
        business_id = str(uuid4())
        business_service._business_repository.get_business_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(BusinessNotFoundError) as exc_info:
            await business_service.get_business_status(business_id)
        
        assert f"Business {business_id} not found" in str(exc_info.value)
    
    def test_generate_secure_api_key(self, business_service):
        """Test API key generation"""
        business_id = str(uuid4())
        
        api_key = business_service._generate_secure_api_key(business_id)
        
        assert isinstance(api_key, str)
        assert len(api_key) == 64  # SHA-256 hex digest length
        assert api_key.isalnum()  # Should be alphanumeric
    
    def test_generate_secure_api_key_uniqueness(self, business_service):
        """Test that API keys are unique"""
        business_id = str(uuid4())
        
        key1 = business_service._generate_secure_api_key(business_id)
        key2 = business_service._generate_secure_api_key(business_id)
        
        assert key1 != key2  # Should be different due to timestamp and UUID
    
    @pytest.mark.asyncio
    async def test_gather_business_metrics(self, business_service):
        """Test business metrics gathering"""
        business_id = str(uuid4())
        
        metrics = await business_service._gather_business_metrics(business_id)
        
        assert isinstance(metrics, dict)
        assert "total_interactions" in metrics
        assert "successful_bookings" in metrics
        assert "revenue_today" in metrics
        assert "avg_response_time_ms" in metrics
        
        # Verify metric types
        assert isinstance(metrics["total_interactions"], int)
        assert isinstance(metrics["successful_bookings"], int)
        assert isinstance(metrics["revenue_today"], (int, float))
        assert isinstance(metrics["avg_response_time_ms"], int)


class TestBusinessSearchCriteria:
    """Test suite for BusinessSearchCriteria parameter object"""
    
    def test_default_values(self):
        """Test default values for search criteria"""
        criteria = BusinessSearchCriteria()
        
        assert criteria.business_type is None
        assert criteria.status is None
        assert criteria.city is None
        assert criteria.limit == 100  # From constants
        assert criteria.offset == 0
    
    def test_custom_values(self):
        """Test custom values for search criteria"""
        criteria = BusinessSearchCriteria(
            business_type="hospitality",
            status="active",
            city="New York",
            limit=50,
            offset=10
        )
        
        assert criteria.business_type == "hospitality"
        assert criteria.status == "active"
        assert criteria.city == "New York"
        assert criteria.limit == 50
        assert criteria.offset == 10
    
    def test_partial_criteria(self):
        """Test search criteria with partial values"""
        criteria = BusinessSearchCriteria(
            business_type="restaurant",
            limit=25
        )
        
        assert criteria.business_type == "restaurant"
        assert criteria.status is None
        assert criteria.city is None
        assert criteria.limit == 25
        assert criteria.offset == 0


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
