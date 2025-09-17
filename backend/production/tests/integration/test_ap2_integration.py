"""
AP2 Integration Tests
Tests for AP2 (Agent Payments Protocol) integration with BAIS
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from ...core.payments.ap2_client import AP2Client, AP2ClientConfig
from ...core.payments.mandate_manager import MandateManager, MandateValidationError
from ...core.payments.payment_coordinator import PaymentCoordinator, PaymentCoordinationRequest
from ...core.payments.models import AP2Mandate, PaymentStatus, PaymentMethod, PaymentMethodType
from ...config.ap2_settings import AP2Settings


class TestAP2Client:
    """Test AP2 client functionality"""
    
    @pytest.fixture
    def ap2_config(self):
        """AP2 client configuration for testing"""
        return AP2ClientConfig(
            base_url="https://test-ap2.example.com",
            client_id="test_client_id",
            private_key="-----BEGIN PRIVATE KEY-----\nMOCK_KEY\n-----END PRIVATE KEY-----",
            public_key="-----BEGIN PUBLIC KEY-----\nMOCK_PUBLIC_KEY\n-----END PUBLIC KEY-----",
            timeout=30
        )
    
    @pytest.fixture
    def ap2_client(self, ap2_config):
        """AP2 client instance for testing"""
        with patch('cryptography.hazmat.primitives.serialization.load_pem_private_key'):
            return AP2Client(ap2_config)
    
    @pytest.mark.asyncio
    async def test_create_intent_mandate(self, ap2_client):
        """Test intent mandate creation"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "mandate_123",
                "type": "intent",
                "userId": "user_456",
                "businessId": "business_789",
                "data": {"description": "Test intent"},
                "signature": "mock_signature",
                "createdAt": datetime.utcnow().isoformat(),
                "expiresAt": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "status": "active"
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            mandate = await ap2_client.create_intent_mandate(
                user_id="user_456",
                business_id="business_789",
                intent_description="Test intent",
                constraints={"max_amount": 100.0}
            )
            
            assert mandate.id == "mandate_123"
            assert mandate.type == "intent"
            assert mandate.user_id == "user_456"
            assert mandate.business_id == "business_789"
    
    @pytest.mark.asyncio
    async def test_create_cart_mandate(self, ap2_client):
        """Test cart mandate creation"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "cart_mandate_123",
                "type": "cart",
                "userId": "user_456",
                "businessId": "business_789",
                "data": {"items": [{"name": "Test item", "price": 50.0}]},
                "signature": "mock_signature",
                "createdAt": datetime.utcnow().isoformat(),
                "status": "active"
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            mandate = await ap2_client.create_cart_mandate(
                intent_mandate_id="intent_123",
                cart_items=[{"name": "Test item", "price": 50.0, "quantity": 1}],
                total_amount=50.0,
                currency="USD"
            )
            
            assert mandate.id == "cart_mandate_123"
            assert mandate.type == "cart"


class TestMandateManager:
    """Test mandate manager functionality"""
    
    @pytest.fixture
    def mock_business_repo(self):
        """Mock business repository"""
        repo = Mock()
        business = Mock()
        business.ap2_enabled = True
        business.ap2_supported_payment_methods = ["credit_card", "debit_card"]
        repo.find_by_id.return_value = business
        return repo
    
    @pytest.fixture
    def mandate_manager(self, mock_business_repo):
        """Mandate manager instance for testing"""
        ap2_client = Mock()
        return MandateManager(ap2_client, mock_business_repo)
    
    @pytest.mark.asyncio
    async def test_create_intent_mandate_validation(self, mandate_manager):
        """Test intent mandate creation with validation"""
        mandate_manager._ap2_client.create_intent_mandate = AsyncMock(return_value=Mock(
            id="mandate_123",
            type="intent",
            user_id="user_456",
            business_id="business_789",
            data={"constraints": {"max_amount": 100.0}},
            signature="mock_signature",
            created_at=datetime.utcnow(),
            status="active"
        ))
        
        mandate = await mandate_manager.create_intent_mandate(
            user_id="user_456",
            business_id="business_789",
            intent_description="Test intent",
            constraints={"max_amount": 100.0}
        )
        
        assert mandate.id == "mandate_123"
        assert mandate.type == "intent"
    
    @pytest.mark.asyncio
    async def test_business_not_ap2_enabled(self, mandate_manager):
        """Test validation when business is not AP2-enabled"""
        mandate_manager._business_repository.find_by_id.return_value.ap2_enabled = False
        
        with pytest.raises(MandateValidationError, match="not AP2-enabled"):
            await mandate_manager.create_intent_mandate(
                user_id="user_456",
                business_id="business_789",
                intent_description="Test intent",
                constraints={}
            )


class TestPaymentCoordinator:
    """Test payment coordinator functionality"""
    
    @pytest.fixture
    def mock_business_repo(self):
        """Mock business repository"""
        repo = Mock()
        business = Mock()
        business.ap2_enabled = True
        repo.find_by_id.return_value = business
        return repo
    
    @pytest.fixture
    def payment_coordinator(self, mock_business_repo):
        """Payment coordinator instance for testing"""
        ap2_client = Mock()
        return PaymentCoordinator(ap2_client, mock_business_repo)
    
    @pytest.mark.asyncio
    async def test_payment_workflow_success(self, payment_coordinator):
        """Test successful payment workflow"""
        # Mock AP2 client methods
        payment_coordinator._ap2_client.create_intent_mandate = AsyncMock(return_value=Mock(
            id="intent_123",
            type="intent",
            user_id="user_456",
            business_id="business_789",
            data={},
            signature="mock_signature",
            created_at=datetime.utcnow(),
            status="active"
        ))
        
        payment_coordinator._ap2_client.create_cart_mandate = AsyncMock(return_value=Mock(
            id="cart_123",
            type="cart",
            user_id="user_456",
            business_id="business_789",
            data={},
            signature="mock_signature",
            created_at=datetime.utcnow(),
            status="active"
        ))
        
        payment_coordinator._ap2_client.execute_payment = AsyncMock(return_value=Mock(
            id="transaction_123",
            cart_mandate_id="cart_123",
            payment_method=Mock(),
            amount=100.0,
            currency="USD",
            status="completed",
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        ))
        
        request = PaymentCoordinationRequest(
            user_id="user_456",
            business_id="business_789",
            agent_id="agent_123",
            intent_description="Test payment",
            cart_items=[{"name": "Test item", "price": 100.0, "quantity": 1}],
            payment_constraints={},
            payment_method_id="pm_123"
        )
        
        workflow = await payment_coordinator.initiate_payment_workflow(request)
        
        assert workflow.status == PaymentStatus.COMPLETED
        assert workflow.intent_mandate_id == "intent_123"
        assert workflow.cart_mandate_id == "cart_123"
        assert workflow.transaction_id == "transaction_123"


class TestAP2Settings:
    """Test AP2 settings configuration"""
    
    def test_default_settings(self):
        """Test default AP2 settings"""
        settings = AP2Settings()
        
        assert settings.ap2_version == "1.0"
        assert settings.ap2_timeout == 30
        assert settings.ap2_default_currency == "USD"
        assert settings.ap2_verification_required is True
    
    def test_supported_payment_methods(self):
        """Test supported payment methods configuration"""
        settings = AP2Settings()
        
        expected_methods = ["credit_card", "debit_card", "bank_transfer", "digital_wallet"]
        assert settings.ap2_supported_payment_methods == expected_methods


@pytest.mark.integration
class TestAP2Integration:
    """Integration tests for AP2 functionality"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_payment_flow(self):
        """Test complete AP2 payment flow"""
        # This would be a more comprehensive integration test
        # that tests the entire flow from mandate creation to payment completion
        pass
    
    @pytest.mark.asyncio
    async def test_mandate_validation_flow(self):
        """Test mandate validation flow"""
        # This would test the complete mandate validation process
        pass
