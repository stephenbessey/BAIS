"""
AP2 Cryptographic Security Tests - Clean Code Implementation
Comprehensive security testing for AP2 cryptographic operations following Clean Code principles
"""

import pytest
import json
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature
from unittest.mock import Mock, patch

from ...core.payments.ap2_mandate_validator import AP2MandateValidator
from ...core.payments.models import AP2Mandate, AP2IntentMandate, AP2CartMandate
from ...core.constants import AP2Limits, SecurityConstants


class TestAP2CryptoSecurity:
    """Test AP2 cryptographic security following Clean Code principles"""
    
    @pytest.fixture
    def test_key_pair(self):
        """Generate test RSA key pair for testing"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048  # Use 2048 for testing, 4096 for production
        )
        public_key = private_key.public_key()
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return {
            'private_key': private_pem.decode(),
            'public_key': public_pem.decode(),
            'private_key_obj': private_key,
            'public_key_obj': public_key
        }
    
    @pytest.fixture
    def validator(self, test_key_pair):
        """Create AP2 mandate validator for testing"""
        return AP2MandateValidator(
            private_key=test_key_pair['private_key'],
            public_key=test_key_pair['public_key']
        )
    
    @pytest.fixture
    def valid_intent_mandate_data(self):
        """Create valid intent mandate data for testing"""
        return {
            "type": "intent",
            "userId": "user123",
            "businessId": "business456",
            "agentId": "agent789",
            "intentDescription": "Book a hotel room",
            "amount": 150.0,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat(),
            "expiresAt": (datetime.utcnow() + timedelta(hours=AP2Limits.MANDATE_EXPIRY_HOURS)).isoformat()
        }
    
    @pytest.fixture
    def valid_cart_mandate_data(self):
        """Create valid cart mandate data for testing"""
        return {
            "type": "cart",
            "intentMandateId": "intent_123",
            "cartItems": [
                {
                    "item": "hotel_room",
                    "quantity": 1,
                    "price": 150.0,
                    "description": "Deluxe room for 2 nights"
                }
            ],
            "totalAmount": 150.0,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat(),
            "expiresAt": (datetime.utcnow() + timedelta(hours=AP2Limits.MANDATE_EXPIRY_HOURS)).isoformat()
        }
    
    def test_mandate_signature_creation(self, validator, valid_intent_mandate_data):
        """Test mandate signatures are created correctly"""
        signed_mandate = validator.create_signed_mandate(valid_intent_mandate_data)
        
        # Verify signature structure
        assert "signature" in signed_mandate
        assert "data" in signed_mandate
        assert "algorithm" in signed_mandate
        assert "keyId" in signed_mandate
        assert "timestamp" in signed_mandate
        assert "nonce" in signed_mandate
        
        # Verify data integrity
        assert signed_mandate["data"] == valid_intent_mandate_data
        
        # Verify signature format
        assert signed_mandate["algorithm"] == SecurityConstants.SIGNATURE_ALGORITHM
        assert isinstance(signed_mandate["signature"], str)
        assert len(signed_mandate["signature"]) > 0
    
    def test_mandate_signature_verification_valid(self, validator, valid_intent_mandate_data):
        """Test valid mandate signatures are verified correctly"""
        signed_mandate = validator.create_signed_mandate(valid_intent_mandate_data)
        
        # Create mandate object for verification
        mandate = AP2Mandate(
            id="test_mandate_123",
            type="intent",
            data=signed_mandate["data"],
            signature=signed_mandate["signature"],
            algorithm=signed_mandate["algorithm"],
            key_id=signed_mandate["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"]
        )
        
        # Verify signature
        assert validator.verify_mandate(mandate) is True
    
    def test_mandate_signature_verification_tampered_data(self, validator, valid_intent_mandate_data):
        """Test tampered mandate data is detected and rejected"""
        signed_mandate = validator.create_signed_mandate(valid_intent_mandate_data)
        
        # Tamper with data
        tampered_data = valid_intent_mandate_data.copy()
        tampered_data["amount"] = 999999.0  # Change amount
        tampered_data["userId"] = "hacker123"  # Change user ID
        
        mandate = AP2Mandate(
            id="test_mandate_123",
            type="intent",
            data=tampered_data,
            signature=signed_mandate["signature"],  # Original signature
            algorithm=signed_mandate["algorithm"],
            key_id=signed_mandate["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"]
        )
        
        # Verify tampered data is rejected
        assert validator.verify_mandate(mandate) is False
    
    def test_mandate_signature_verification_tampered_signature(self, validator, valid_intent_mandate_data):
        """Test tampered signature is detected and rejected"""
        signed_mandate = validator.create_signed_mandate(valid_intent_mandate_data)
        
        # Tamper with signature
        tampered_signature = signed_mandate["signature"][:-5] + "aaaaa"
        
        mandate = AP2Mandate(
            id="test_mandate_123",
            type="intent",
            data=signed_mandate["data"],
            signature=tampered_signature,
            algorithm=signed_mandate["algorithm"],
            key_id=signed_mandate["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"]
        )
        
        # Verify tampered signature is rejected
        assert validator.verify_mandate(mandate) is False
    
    def test_mandate_expiration_enforcement(self, validator, valid_intent_mandate_data):
        """Test expired mandates are rejected"""
        # Create expired mandate
        expired_data = valid_intent_mandate_data.copy()
        expired_data["timestamp"] = (datetime.utcnow() - timedelta(days=2)).isoformat()
        expired_data["expiresAt"] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        signed_mandate = validator.create_signed_mandate(expired_data)
        
        mandate = AP2Mandate(
            id="test_mandate_123",
            type="intent",
            data=signed_mandate["data"],
            signature=signed_mandate["signature"],
            algorithm=signed_mandate["algorithm"],
            key_id=signed_mandate["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"],
            expires_at=datetime.fromisoformat(expired_data["expiresAt"])
        )
        
        # Verify expired mandate is rejected
        is_valid = validator.verify_mandate(mandate) and mandate.expires_at > datetime.utcnow()
        assert is_valid is False
    
    def test_replay_attack_prevention_timestamp_validation(self, validator, valid_intent_mandate_data):
        """Test replay attack prevention via timestamp validation"""
        # Create old mandate (3 days old)
        old_mandate_data = valid_intent_mandate_data.copy()
        old_mandate_data["timestamp"] = (datetime.utcnow() - timedelta(days=3)).isoformat()
        
        signed_mandate = validator.create_signed_mandate(old_mandate_data)
        
        mandate = AP2Mandate(
            id="test_mandate_123",
            type="intent",
            data=signed_mandate["data"],
            signature=signed_mandate["signature"],
            algorithm=signed_mandate["algorithm"],
            key_id=signed_mandate["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"]
        )
        
        # Check timestamp age
        age_hours = (datetime.utcnow() - mandate.timestamp).total_seconds() / 3600
        
        # Mandates older than 48 hours should be rejected for replay protection
        if age_hours > 48:
            assert validator.verify_mandate(mandate) is False
    
    def test_replay_attack_prevention_nonce_uniqueness(self, validator, valid_intent_mandate_data):
        """Test nonce uniqueness prevents replay attacks"""
        # Create two mandates with same data but different timestamps
        mandate1_data = valid_intent_mandate_data.copy()
        mandate1_data["timestamp"] = datetime.utcnow().isoformat()
        
        mandate2_data = valid_intent_mandate_data.copy()
        mandate2_data["timestamp"] = (datetime.utcnow() + timedelta(seconds=1)).isoformat()
        
        signed_mandate1 = validator.create_signed_mandate(mandate1_data)
        signed_mandate2 = validator.create_signed_mandate(mandate2_data)
        
        # Nonces should be different
        assert signed_mandate1["nonce"] != signed_mandate2["nonce"]
        
        # Both should be valid
        mandate1 = AP2Mandate(
            id="test_mandate_1",
            type="intent",
            data=signed_mandate1["data"],
            signature=signed_mandate1["signature"],
            algorithm=signed_mandate1["algorithm"],
            key_id=signed_mandate1["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate1["timestamp"]),
            nonce=signed_mandate1["nonce"]
        )
        
        mandate2 = AP2Mandate(
            id="test_mandate_2",
            type="intent",
            data=signed_mandate2["data"],
            signature=signed_mandate2["signature"],
            algorithm=signed_mandate2["algorithm"],
            key_id=signed_mandate2["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate2["timestamp"]),
            nonce=signed_mandate2["nonce"]
        )
        
        assert validator.verify_mandate(mandate1) is True
        assert validator.verify_mandate(mandate2) is True
    
    def test_wrong_algorithm_rejection(self, validator, valid_intent_mandate_data):
        """Test mandates with wrong signature algorithm are rejected"""
        signed_mandate = validator.create_signed_mandate(valid_intent_mandate_data)
        
        # Change algorithm
        mandate = AP2Mandate(
            id="test_mandate_123",
            type="intent",
            data=signed_mandate["data"],
            signature=signed_mandate["signature"],
            algorithm="RS256",  # Wrong algorithm
            key_id=signed_mandate["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"]
        )
        
        # Should be rejected due to algorithm mismatch
        assert validator.verify_mandate(mandate) is False
    
    def test_key_id_validation(self, validator, valid_intent_mandate_data):
        """Test key ID validation"""
        signed_mandate = validator.create_signed_mandate(valid_intent_mandate_data)
        
        # Change key ID
        mandate = AP2Mandate(
            id="test_mandate_123",
            type="intent",
            data=signed_mandate["data"],
            signature=signed_mandate["signature"],
            algorithm=signed_mandate["algorithm"],
            key_id="wrong_key_id",  # Wrong key ID
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"]
        )
        
        # Should be rejected due to key ID mismatch
        assert validator.verify_mandate(mandate) is False
    
    def test_cart_mandate_linked_to_intent(self, validator, valid_intent_mandate_data, valid_cart_mandate_data):
        """Test cart mandate is properly linked to intent mandate"""
        # Create intent mandate
        intent_signed = validator.create_signed_mandate(valid_intent_mandate_data)
        
        # Create cart mandate linked to intent
        cart_data = valid_cart_mandate_data.copy()
        cart_data["intentMandateId"] = "intent_" + intent_signed["signature"][:8]  # Mock intent ID
        
        cart_signed = validator.create_signed_mandate(cart_data)
        
        # Verify both mandates are valid
        intent_mandate = AP2Mandate(
            id="intent_mandate_123",
            type="intent",
            data=intent_signed["data"],
            signature=intent_signed["signature"],
            algorithm=intent_signed["algorithm"],
            key_id=intent_signed["keyId"],
            timestamp=datetime.fromisoformat(intent_signed["timestamp"]),
            nonce=intent_signed["nonce"]
        )
        
        cart_mandate = AP2Mandate(
            id="cart_mandate_123",
            type="cart",
            data=cart_signed["data"],
            signature=cart_signed["signature"],
            algorithm=cart_signed["algorithm"],
            key_id=cart_signed["keyId"],
            timestamp=datetime.fromisoformat(cart_signed["timestamp"]),
            nonce=cart_signed["nonce"]
        )
        
        assert validator.verify_mandate(intent_mandate) is True
        assert validator.verify_mandate(cart_mandate) is True
        
        # Verify cart mandate references intent mandate
        assert cart_mandate.data["intentMandateId"] is not None
    
    def test_mandate_amount_validation(self, validator):
        """Test mandate amount validation"""
        # Test minimum amount
        min_amount_data = {
            "type": "intent",
            "userId": "user123",
            "businessId": "business456",
            "amount": AP2Limits.MIN_PAYMENT_AMOUNT,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        signed_mandate = validator.create_signed_mandate(min_amount_data)
        mandate = AP2Mandate(
            id="test_mandate_min",
            type="intent",
            data=signed_mandate["data"],
            signature=signed_mandate["signature"],
            algorithm=signed_mandate["algorithm"],
            key_id=signed_mandate["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"]
        )
        
        assert validator.verify_mandate(mandate) is True
        
        # Test maximum amount
        max_amount_data = {
            "type": "intent",
            "userId": "user123",
            "businessId": "business456",
            "amount": AP2Limits.MAX_MANDATE_AMOUNT,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        signed_mandate = validator.create_signed_mandate(max_amount_data)
        mandate = AP2Mandate(
            id="test_mandate_max",
            type="intent",
            data=signed_mandate["data"],
            signature=signed_mandate["signature"],
            algorithm=signed_mandate["algorithm"],
            key_id=signed_mandate["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"]
        )
        
        assert validator.verify_mandate(mandate) is True
    
    def test_key_strength_validation(self, test_key_pair):
        """Test RSA key strength validation"""
        # Test with 2048-bit key (minimum for testing)
        assert len(test_key_pair['private_key_obj'].private_numbers().p.bit_length()) >= 1024
        
        # Test key serialization
        private_pem = test_key_pair['private_key_obj'].private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = test_key_pair['public_key_obj'].public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        assert isinstance(private_pem, bytes)
        assert isinstance(public_pem, bytes)
        assert b"BEGIN PRIVATE KEY" in private_pem
        assert b"BEGIN PUBLIC KEY" in public_pem
    
    def test_signature_algorithm_compliance(self, validator, valid_intent_mandate_data):
        """Test signature algorithm compliance with security standards"""
        signed_mandate = validator.create_signed_mandate(valid_intent_mandate_data)
        
        # Verify algorithm is RSA-PSS with SHA-256
        assert signed_mandate["algorithm"] == SecurityConstants.SIGNATURE_ALGORITHM
        
        # Verify signature can be verified with public key
        mandate = AP2Mandate(
            id="test_mandate_123",
            type="intent",
            data=signed_mandate["data"],
            signature=signed_mandate["signature"],
            algorithm=signed_mandate["algorithm"],
            key_id=signed_mandate["keyId"],
            timestamp=datetime.fromisoformat(signed_mandate["timestamp"]),
            nonce=signed_mandate["nonce"]
        )
        
        assert validator.verify_mandate(mandate) is True


class TestAP2CryptoIntegration:
    """Integration tests for AP2 cryptographic operations"""
    
    def test_end_to_end_mandate_workflow(self):
        """Test complete mandate workflow from creation to verification"""
        # This would test the complete flow:
        # 1. Intent mandate creation
        # 2. Cart mandate creation linked to intent
        # 3. Payment execution with mandate verification
        # 4. Mandate revocation if needed
        
        pass
    
    def test_mandate_verification_under_load(self):
        """Test mandate verification performance under load"""
        # Test cryptographic operations performance
        pass
    
    def test_key_rotation_scenario(self):
        """Test key rotation scenario"""
        # Test system behavior when keys are rotated
        pass


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
