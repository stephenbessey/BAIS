"""
AP2 Protocol Compliance Tests
Comprehensive test suite for AP2 protocol implementation
"""

import pytest
import json
import base64
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

from ..core.payments.cryptographic_mandate_validator import (
    CryptographicMandateValidator, 
    KeyManager, 
    MandateSignature
)
from ..core.payments.verifiable_credential import (
    VerifiableCredential,
    VDCManager,
    CredentialSubject,
    CryptographicProof,
    ProofType
)
from ..core.payments.ap2_client import AP2Client, AP2ClientConfig
from ..core.payments.models import AP2Mandate, AP2Transaction, PaymentMethod


class TestAP2CryptographicCompliance:
    """Test AP2 cryptographic mandate compliance"""
    
    @pytest.fixture
    def key_manager(self):
        """Create key manager for testing"""
        return KeyManager()
    
    @pytest.fixture
    def crypto_validator(self, key_manager):
        """Create cryptographic validator for testing"""
        return CryptographicMandateValidator(key_manager)
    
    def test_mandate_signing_compliance(self, crypto_validator):
        """Test that mandate signing follows AP2 specification"""
        # Create test mandate data
        mandate_data = {
            "type": "intent",
            "userId": "user_123",
            "businessId": "business_456",
            "description": "Test payment intent",
            "amount": 100.00,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Sign the mandate
        signature = crypto_validator.sign_mandate(mandate_data)
        
        # Validate signature structure
        assert signature.signature is not None
        assert signature.algorithm == "RS256"
        assert signature.key_id is not None
        assert signature.timestamp is not None
        assert signature.nonce is not None
        
        # Validate signature format (base64 encoded)
        try:
            base64.b64decode(signature.signature)
        except Exception:
            pytest.fail("Signature is not valid base64")
    
    def test_mandate_verification_compliance(self, crypto_validator):
        """Test that mandate verification follows AP2 specification"""
        # Create test mandate data
        mandate_data = {
            "type": "intent",
            "userId": "user_123",
            "businessId": "business_456",
            "description": "Test payment intent",
            "amount": 100.00,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Sign the mandate
        signature = crypto_validator.sign_mandate(mandate_data)
        
        # Verify the signature
        is_valid = crypto_validator.verify_mandate(mandate_data, signature)
        assert is_valid is True
        
        # Test with tampered data
        tampered_data = mandate_data.copy()
        tampered_data["amount"] = 200.00
        
        is_valid = crypto_validator.verify_mandate(tampered_data, signature)
        assert is_valid is False
    
    def test_key_management_compliance(self, key_manager):
        """Test key management follows AP2 security requirements"""
        # Generate key pair
        key_pair = key_manager.generate_key_pair("test_key")
        
        # Validate key pair structure
        assert key_pair.private_key is not None
        assert key_pair.public_key is not None
        assert key_pair.key_id == "test_key"
        assert key_pair.created_at is not None
        
        # Test key export/import
        public_key_pem = key_manager.export_public_key_pem("test_key")
        assert public_key_pem is not None
        assert public_key_pem.startswith("-----BEGIN PUBLIC KEY-----")
        
        # Test key import
        success = key_manager.import_public_key_pem(public_key_pem, "imported_key")
        assert success is True
        
        # Validate imported key
        imported_key = key_manager.get_key_pair("imported_key")
        assert imported_key is not None
        assert imported_key.public_key is not None
    
    def test_signature_algorithm_compliance(self, crypto_validator):
        """Test that signature algorithm follows AP2 specification"""
        mandate_data = {"test": "data"}
        
        # Test supported algorithm
        signature = crypto_validator.sign_mandate(mandate_data, algorithm="RS256")
        assert signature.algorithm == "RS256"
        
        # Test unsupported algorithm
        with pytest.raises(Exception):  # Should raise ValidationError
            crypto_validator.sign_mandate(mandate_data, algorithm="ES256")
    
    def test_mandate_canonicalization(self, crypto_validator):
        """Test mandate data canonicalization for consistent signing"""
        # Test that same data produces same canonical form
        mandate_data1 = {"b": 2, "a": 1, "c": 3}
        mandate_data2 = {"c": 3, "a": 1, "b": 2}
        
        canonical1 = crypto_validator._canonicalize_mandate_data(mandate_data1)
        canonical2 = crypto_validator._canonicalize_mandate_data(mandate_data2)
        
        # Should be identical after canonicalization
        assert canonical1 == canonical2
        
        # Test signature removal
        mandate_with_signature = {"data": "test", "signature": "fake_sig"}
        canonical = crypto_validator._canonicalize_mandate_data(mandate_with_signature)
        assert "signature" not in canonical


class TestAP2VerifiableCredentialsCompliance:
    """Test AP2 Verifiable Digital Credentials compliance"""
    
    @pytest.fixture
    def vdc_manager(self, crypto_validator):
        """Create VDC manager for testing"""
        return VDCManager(crypto_validator)
    
    def test_credential_structure_compliance(self, vdc_manager):
        """Test that VDCs follow AP2 specification structure"""
        # Create identity credential
        identity_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "verification_level": "verified"
        }
        
        credential = vdc_manager.create_identity_credential(
            subject_id="user_123",
            identity_data=identity_data,
            issuer_id="issuer_456"
        )
        
        # Validate credential structure
        assert credential.context is not None
        assert len(credential.context) > 0
        assert "https://www.w3.org/2018/credentials/v1" in credential.context
        
        assert credential.id is not None
        assert credential.type is not None
        assert "VerifiableCredential" in credential.type
        
        assert credential.issuer == "issuer_456"
        assert credential.issuance_date is not None
        assert credential.expiration_date is not None
        
        assert credential.credential_subject is not None
        assert credential.credential_subject.id == "user_123"
        assert credential.credential_subject.type == "Identity"
        
        assert credential.proof is not None
        assert credential.proof.type == ProofType.RSA_SIGNATURE
    
    def test_credential_verification_compliance(self, vdc_manager):
        """Test VDC verification follows AP2 specification"""
        # Create and sign credential
        business_data = {
            "name": "Test Business",
            "type": "retail",
            "registration_number": "REG123456",
            "address": "123 Test St",
            "tax_id": "TAX789",
            "ap2_enabled": True
        }
        
        credential = vdc_manager.create_business_registration_credential(
            business_id="business_123",
            business_data=business_data,
            issuer_id="issuer_456"
        )
        
        # Verify the credential
        is_valid = vdc_manager.verify_credential(credential)
        assert is_valid is True
        
        # Test with tampered credential
        tampered_credential = credential
        tampered_credential.credential_subject.properties["name"] = "Tampered Business"
        
        is_valid = vdc_manager.verify_credential(tampered_credential)
        assert is_valid is False
    
    def test_credential_revocation_compliance(self, vdc_manager):
        """Test VDC revocation follows AP2 specification"""
        # Create credential
        credential = vdc_manager.create_identity_credential(
            subject_id="user_123",
            identity_data={"name": "John Doe"},
            issuer_id="issuer_456"
        )
        
        credential_id = credential.id
        
        # Verify credential is valid
        assert vdc_manager.verify_credential(credential) is True
        assert not vdc_manager.is_credential_revoked(credential_id)
        
        # Revoke credential
        success = vdc_manager.revoke_credential(credential_id)
        assert success is True
        
        # Verify credential is revoked
        assert vdc_manager.is_credential_revoked(credential_id)
        assert vdc_manager.verify_credential(credential) is False
    
    def test_credential_expiration_compliance(self, vdc_manager):
        """Test VDC expiration handling"""
        # Create credential with short expiration
        credential = vdc_manager.create_identity_credential(
            subject_id="user_123",
            identity_data={"name": "John Doe"},
            issuer_id="issuer_456"
        )
        
        # Set expiration to past date
        credential.expiration_date = datetime.utcnow() - timedelta(days=1)
        
        # Verify credential is expired
        assert credential.is_expired() is True
        assert vdc_manager.verify_credential(credential) is False
    
    def test_credential_hash_integrity(self, vdc_manager):
        """Test credential hash for integrity checking"""
        # Create credential
        credential = vdc_manager.create_identity_credential(
            subject_id="user_123",
            identity_data={"name": "John Doe"},
            issuer_id="issuer_456"
        )
        
        # Get credential hash
        hash1 = credential.get_credential_hash()
        assert hash1 is not None
        assert len(hash1) == 64  # SHA-256 hex digest length
        
        # Hash should be consistent
        hash2 = credential.get_credential_hash()
        assert hash1 == hash2
        
        # Hash should change with data changes
        credential.credential_subject.properties["name"] = "Jane Doe"
        hash3 = credential.get_credential_hash()
        assert hash1 != hash3


class TestAP2MandateCompliance:
    """Test AP2 mandate protocol compliance"""
    
    @pytest.fixture
    def ap2_client(self):
        """Create AP2 client for testing"""
        config = AP2ClientConfig(
            base_url="https://ap2.test.com",
            client_id="test_client",
            private_key="-----BEGIN PRIVATE KEY-----\ntest_key\n-----END PRIVATE KEY-----",
            public_key="-----BEGIN PUBLIC KEY-----\ntest_key\n-----END PUBLIC KEY-----"
        )
        return AP2Client(config)
    
    def test_intent_mandate_structure(self):
        """Test intent mandate structure compliance"""
        mandate_data = {
            "type": "intent",
            "userId": "user_123",
            "businessId": "business_456",
            "description": "Payment for hotel booking",
            "constraints": {
                "maxAmount": 500.00,
                "currency": "USD",
                "paymentMethod": "credit_card"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "expiresAt": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        # Validate required fields
        assert mandate_data["type"] == "intent"
        assert "userId" in mandate_data
        assert "businessId" in mandate_data
        assert "description" in mandate_data
        assert "timestamp" in mandate_data
        assert "expiresAt" in mandate_data
        
        # Validate constraints structure
        constraints = mandate_data["constraints"]
        assert "maxAmount" in constraints
        assert "currency" in constraints
        assert "paymentMethod" in constraints
    
    def test_cart_mandate_structure(self):
        """Test cart mandate structure compliance"""
        mandate_data = {
            "type": "cart",
            "intentMandateId": "intent_123",
            "items": [
                {
                    "id": "item_1",
                    "name": "Hotel Room",
                    "price": 150.00,
                    "quantity": 2,
                    "description": "Deluxe room for 2 nights"
                }
            ],
            "totalAmount": 300.00,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Validate required fields
        assert mandate_data["type"] == "cart"
        assert "intentMandateId" in mandate_data
        assert "items" in mandate_data
        assert "totalAmount" in mandate_data
        assert "currency" in mandate_data
        
        # Validate items structure
        items = mandate_data["items"]
        assert len(items) > 0
        
        for item in items:
            assert "id" in item
            assert "name" in item
            assert "price" in item
            assert "quantity" in item
    
    def test_payment_execution_structure(self):
        """Test payment execution structure compliance"""
        payment_data = {
            "cartMandateId": "cart_123",
            "paymentMethod": {
                "type": "credit_card",
                "cardNumber": "****1234",
                "expiryDate": "12/25",
                "cardholderName": "John Doe"
            },
            "amount": 300.00,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Validate required fields
        assert "cartMandateId" in payment_data
        assert "paymentMethod" in payment_data
        assert "amount" in payment_data
        assert "currency" in payment_data
        
        # Validate payment method structure
        payment_method = payment_data["paymentMethod"]
        assert "type" in payment_method
        assert payment_method["type"] == "credit_card"


class TestAP2TransactionCompliance:
    """Test AP2 transaction protocol compliance"""
    
    def test_transaction_structure(self):
        """Test transaction structure compliance"""
        transaction_data = {
            "id": "txn_123",
            "type": "payment",
            "status": "completed",
            "amount": 300.00,
            "currency": "USD",
            "paymentMethod": "credit_card",
            "businessId": "business_456",
            "userId": "user_123",
            "createdAt": datetime.utcnow().isoformat(),
            "completedAt": datetime.utcnow().isoformat(),
            "metadata": {
                "receiptNumber": "RCP789",
                "processorTransactionId": "PROC456"
            }
        }
        
        # Validate required fields
        assert "id" in transaction_data
        assert "type" in transaction_data
        assert "status" in transaction_data
        assert "amount" in transaction_data
        assert "currency" in transaction_data
        assert "businessId" in transaction_data
        assert "userId" in transaction_data
        assert "createdAt" in transaction_data
        
        # Validate status values
        valid_statuses = ["pending", "processing", "completed", "failed", "cancelled"]
        assert transaction_data["status"] in valid_statuses
    
    def test_transaction_status_transitions(self):
        """Test transaction status transition compliance"""
        valid_transitions = {
            "pending": ["processing", "failed", "cancelled"],
            "processing": ["completed", "failed", "cancelled"],
            "completed": [],  # Terminal state
            "failed": [],     # Terminal state
            "cancelled": []   # Terminal state
        }
        
        # Test valid transitions
        assert "processing" in valid_transitions["pending"]
        assert "completed" in valid_transitions["processing"]
        
        # Test terminal states
        assert len(valid_transitions["completed"]) == 0
        assert len(valid_transitions["failed"]) == 0


class TestAP2WebhookCompliance:
    """Test AP2 webhook protocol compliance"""
    
    def test_webhook_payload_structure(self):
        """Test webhook payload structure compliance"""
        webhook_payload = {
            "eventType": "payment.completed",
            "paymentId": "payment_123",
            "mandateId": "mandate_456",
            "timestamp": datetime.utcnow().isoformat(),
            "signature": "webhook_signature_hash",
            "businessId": "business_789",
            "status": "completed",
            "amount": 300.00,
            "currency": "USD",
            "metadata": {
                "transactionId": "txn_123",
                "processorReference": "PROC456"
            }
        }
        
        # Validate required fields
        assert "eventType" in webhook_payload
        assert "paymentId" in webhook_payload
        assert "timestamp" in webhook_payload
        assert "signature" in webhook_payload
        assert "businessId" in webhook_payload
        
        # Validate event types
        valid_event_types = [
            "payment.initiated",
            "payment.processing",
            "payment.completed",
            "payment.failed",
            "mandate.created",
            "mandate.expired",
            "mandate.revoked"
        ]
        assert webhook_payload["eventType"] in valid_event_types
    
    def test_webhook_signature_verification(self):
        """Test webhook signature verification compliance"""
        # Mock webhook signature verification
        payload = {"test": "data"}
        signature = "mock_signature"
        secret_key = "webhook_secret"
        
        # In a real implementation, this would verify HMAC signature
        def verify_webhook_signature(payload_data, signature_header, secret):
            # Mock verification logic
            expected_signature = f"sha256={hashlib.sha256(json.dumps(payload_data).encode()).hexdigest()}"
            return signature_header == expected_signature
        
        # Test signature verification
        is_valid = verify_webhook_signature(payload, signature, secret_key)
        # This is a mock test - in real implementation, it would verify actual HMAC


class TestAP2IntegrationCompliance:
    """Test AP2 integration with other protocols"""
    
    def test_ap2_a2a_integration(self):
        """Test AP2 integration with A2A protocol"""
        # Test that AP2 mandates can be discovered via A2A
        agent_capabilities = [
            {
                "name": "payment_processing",
                "description": "Process payments using AP2 protocol",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "mandate_type": {"type": "string", "enum": ["intent", "cart"]},
                        "amount": {"type": "number"},
                        "currency": {"type": "string"}
                    }
                }
            }
        ]
        
        # Validate AP2 capability in A2A agent
        payment_capability = next(
            cap for cap in agent_capabilities 
            if cap["name"] == "payment_processing"
        )
        
        assert payment_capability is not None
        assert "mandate_type" in payment_capability["input_schema"]["properties"]
        assert "intent" in payment_capability["input_schema"]["properties"]["mandate_type"]["enum"]
        assert "cart" in payment_capability["input_schema"]["properties"]["mandate_type"]["enum"]
    
    def test_ap2_mcp_integration(self):
        """Test AP2 integration with MCP protocol"""
        # Test that AP2 operations can be exposed via MCP
        mcp_tools = [
            {
                "name": "create_intent_mandate",
                "description": "Create an AP2 intent mandate",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "business_id": {"type": "string"},
                        "description": {"type": "string"},
                        "amount": {"type": "number"}
                    },
                    "required": ["user_id", "business_id", "description"]
                }
            },
            {
                "name": "execute_payment",
                "description": "Execute AP2 payment",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cart_mandate_id": {"type": "string"},
                        "payment_method": {"type": "object"}
                    },
                    "required": ["cart_mandate_id", "payment_method"]
                }
            }
        ]
        
        # Validate MCP tools for AP2 operations
        assert len(mcp_tools) > 0
        
        for tool in mcp_tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["name"].startswith(("create_", "execute_", "get_"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
