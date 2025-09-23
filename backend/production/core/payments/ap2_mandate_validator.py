"""
AP2 Mandate Cryptographic Validator
Implements critical security validation for AP2 mandates using cryptographic signatures

This module addresses the critical security gap in mandate verification
by implementing proper cryptographic signature validation.
"""

import json
import base64
from typing import Dict, Any, Optional
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

from .models import AP2Mandate


class AP2MandateValidationError(Exception):
    """Raised when mandate cryptographic validation fails"""
    pass


class AP2MandateValidator:
    """
    Cryptographic validator for AP2 mandates
    
    Implements the critical security requirement for mandate signature verification
    using RSA-PSS with SHA-256 as specified in the AP2 protocol.
    """
    
    def __init__(self, public_key_pem: str):
        """
        Initialize validator with public key
        
        Args:
            public_key_pem: PEM-formatted public key for signature verification
        """
        self.public_key = self._load_public_key(public_key_pem)
    
    def verify_mandate(self, mandate: AP2Mandate) -> bool:
        """
        Verify mandate cryptographic signature
        
        Args:
            mandate: AP2Mandate to verify
            
        Returns:
            True if signature is valid, False otherwise
            
        Raises:
            AP2MandateValidationError: If validation fails
        """
        try:
            return self._verify_signature(mandate.data, mandate.signature)
        except Exception as e:
            raise AP2MandateValidationError(f"Mandate validation failed: {str(e)}")
    
    def verify_mandate_from_dict(self, mandate_data: Dict[str, Any], signature: str, public_key: Optional[str] = None) -> bool:
        """
        Verify mandate signature from dictionary data
        
        Args:
            mandate_data: Mandate data dictionary
            signature: Base64-encoded signature
            public_key: Optional public key (uses instance key if not provided)
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            if public_key:
                # Use provided public key for this verification
                pk = self._load_public_key(public_key)
                return self._verify_signature_with_key(mandate_data, signature, pk)
            else:
                # Use instance public key
                return self._verify_signature(mandate_data, signature)
        except Exception as e:
            raise AP2MandateValidationError(f"Mandate validation failed: {str(e)}")
    
    def _verify_signature(self, mandate_data: Dict[str, Any], signature: str) -> bool:
        """Verify signature using instance public key"""
        return self._verify_signature_with_key(mandate_data, signature, self.public_key)
    
    def _verify_signature_with_key(self, mandate_data: Dict[str, Any], signature: str, public_key) -> bool:
        """
        Verify signature with specific public key
        
        Args:
            mandate_data: Mandate data dictionary
            signature: Base64-encoded signature
            public_key: RSA public key object
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Remove signature from data if present to avoid circular verification
            data_for_verification = mandate_data.copy()
            if 'signature' in data_for_verification:
                del data_for_verification['signature']
            
            # Create canonical JSON representation
            message = json.dumps(data_for_verification, sort_keys=True, separators=(',', ':')).encode('utf-8')
            
            # Decode signature from base64
            signature_bytes = base64.b64decode(signature)
            
            # Verify signature using RSA-PSS with SHA-256
            public_key.verify(
                signature_bytes,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except InvalidSignature:
            return False
        except Exception as e:
            raise AP2MandateValidationError(f"Signature verification error: {str(e)}")
    
    def _load_public_key(self, public_key_pem: str):
        """Load public key from PEM format"""
        try:
            return serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
        except Exception as e:
            raise AP2MandateValidationError(f"Failed to load public key: {str(e)}")
    
    def validate_mandate_expiry(self, mandate: AP2Mandate) -> bool:
        """
        Validate mandate hasn't expired
        
        Args:
            mandate: AP2Mandate to check
            
        Returns:
            True if mandate is still valid, False if expired
        """
        if not mandate.expires_at:
            return True  # No expiry set
        
        return datetime.utcnow() < mandate.expires_at
    
    def validate_mandate_structure(self, mandate_data: Dict[str, Any]) -> bool:
        """
        Validate mandate data structure
        
        Args:
            mandate_data: Mandate data dictionary
            
        Returns:
            True if structure is valid, False otherwise
        """
        required_fields = ['type', 'userId', 'businessId', 'timestamp']
        
        for field in required_fields:
            if field not in mandate_data:
                return False
        
        # Validate mandate type
        if mandate_data['type'] not in ['intent', 'cart']:
            return False
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(mandate_data['timestamp'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return False
        
        return True
    
    def comprehensive_validate(self, mandate: AP2Mandate) -> Dict[str, Any]:
        """
        Perform comprehensive mandate validation
        
        Args:
            mandate: AP2Mandate to validate
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check signature
        try:
            if not self.verify_mandate(mandate):
                results['is_valid'] = False
                results['errors'].append('Invalid cryptographic signature')
        except AP2MandateValidationError as e:
            results['is_valid'] = False
            results['errors'].append(f'Signature verification failed: {str(e)}')
        
        # Check expiry
        if not self.validate_mandate_expiry(mandate):
            results['is_valid'] = False
            results['errors'].append('Mandate has expired')
        
        # Check structure
        if not self.validate_mandate_structure(mandate.data):
            results['is_valid'] = False
            results['errors'].append('Invalid mandate structure')
        
        # Check status
        if mandate.status not in ['active', 'pending', 'used', 'expired', 'revoked']:
            results['warnings'].append(f'Unknown mandate status: {mandate.status}')
        
        return results


class AP2MandateValidatorFactory:
    """Factory for creating mandate validators with different configurations"""
    
    @staticmethod
    def create_validator(public_key_pem: str) -> AP2MandateValidator:
        """Create validator with public key"""
        return AP2MandateValidator(public_key_pem)
    
    @staticmethod
    def create_validator_from_file(public_key_file_path: str) -> AP2MandateValidator:
        """Create validator from public key file"""
        with open(public_key_file_path, 'r') as f:
            public_key_pem = f.read()
        return AP2MandateValidator(public_key_pem)
    
    @staticmethod
    def create_test_validator() -> AP2MandateValidator:
        """Create validator for testing with generated key pair"""
        # Generate test key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return AP2MandateValidator(public_key_pem)


# Middleware for automatic mandate validation
class AP2MandateValidationMiddleware:
    """
    Middleware for automatic mandate validation in FastAPI applications
    
    This middleware can be integrated into AP2 endpoints to automatically
    validate all incoming mandates.
    """
    
    def __init__(self, validator: AP2MandateValidator):
        self.validator = validator
    
    async def validate_request(self, mandate_data: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """
        Validate mandate in request
        
        Args:
            mandate_data: Mandate data from request
            signature: Signature from request headers or body
            
        Returns:
            Validation results
            
        Raises:
            AP2MandateValidationError: If validation fails
        """
        validation_result = self.validator.comprehensive_validate(
            AP2Mandate(
                id=mandate_data.get('id', 'unknown'),
                type=mandate_data.get('type', 'unknown'),
                user_id=mandate_data.get('userId', ''),
                business_id=mandate_data.get('businessId', ''),
                data=mandate_data,
                signature=signature,
                created_at=datetime.utcnow()
            )
        )
        
        if not validation_result['is_valid']:
            raise AP2MandateValidationError(
                f"Mandate validation failed: {'; '.join(validation_result['errors'])}"
            )
        
        return validation_result
