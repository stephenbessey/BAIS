"""
AP2 Cryptographic Mandate Validator - Complete Implementation
Implements proper cryptographic signing and verification for AP2 mandates
"""

import json
import base64
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidSignature, InvalidKey
import secrets

from .models import AP2Mandate
from ..exceptions import ValidationError, AuthenticationError


@dataclass
class CryptographicKeyPair:
    """Cryptographic key pair for AP2 mandates"""
    private_key: rsa.RSAPrivateKey
    public_key: rsa.RSAPublicKey
    key_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class MandateSignature:
    """Mandate signature with metadata"""
    signature: str
    algorithm: str
    key_id: str
    timestamp: datetime
    nonce: str


class KeyManager:
    """Manages cryptographic keys for AP2 mandates - follows Single Responsibility Principle"""
    
    def __init__(self):
        self._key_pairs: Dict[str, CryptographicKeyPair] = {}
        self._current_key_id: Optional[str] = None
    
    def generate_key_pair(self, key_id: str = None, key_size: int = 2048) -> CryptographicKeyPair:
        """Generate a new RSA key pair for mandate signing"""
        if not key_id:
            key_id = f"key_{secrets.token_hex(8)}"
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=None
        )
        
        # Get public key
        public_key = private_key.public_key()
        
        # Create key pair
        key_pair = CryptographicKeyPair(
            private_key=private_key,
            public_key=public_key,
            key_id=key_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year expiry
        )
        
        # Store key pair
        self._key_pairs[key_id] = key_pair
        
        # Set as current key if none set
        if not self._current_key_id:
            self._current_key_id = key_id
        
        return key_pair
    
    def get_key_pair(self, key_id: str) -> Optional[CryptographicKeyPair]:
        """Get key pair by ID"""
        return self._key_pairs.get(key_id)
    
    def get_current_key_pair(self) -> Optional[CryptographicKeyPair]:
        """Get current active key pair"""
        if self._current_key_id:
            return self._key_pairs.get(self._current_key_id)
        return None
    
    def set_current_key(self, key_id: str) -> bool:
        """Set current active key"""
        if key_id in self._key_pairs:
            self._current_key_id = key_id
            return True
        return False
    
    def export_public_key_pem(self, key_id: str) -> Optional[str]:
        """Export public key in PEM format"""
        key_pair = self.get_key_pair(key_id)
        if key_pair:
            pem = key_pair.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return pem.decode('utf-8')
        return None
    
    def export_private_key_pem(self, key_id: str, password: str = None) -> Optional[str]:
        """Export private key in PEM format"""
        key_pair = self.get_key_pair(key_id)
        if key_pair:
            encryption_algorithm = serialization.NoEncryption()
            if password:
                encryption_algorithm = serialization.BestAvailableEncryption(password.encode())
            
            pem = key_pair.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption_algorithm
            )
            return pem.decode('utf-8')
        return None
    
    def import_public_key_pem(self, pem_data: str, key_id: str) -> bool:
        """Import public key from PEM format"""
        try:
            public_key = serialization.load_pem_public_key(
                pem_data.encode(),
                backend=None
            )
            
            # Create key pair with imported public key
            key_pair = CryptographicKeyPair(
                private_key=None,  # No private key for imported public key
                public_key=public_key,
                key_id=key_id,
                created_at=datetime.utcnow()
            )
            
            self._key_pairs[key_id] = key_pair
            return True
            
        except Exception:
            return False
    
    def import_private_key_pem(self, pem_data: str, key_id: str, password: str = None) -> bool:
        """Import private key from PEM format"""
        try:
            private_key = serialization.load_pem_private_key(
                pem_data.encode(),
                password=password.encode() if password else None,
                backend=None
            )
            
            public_key = private_key.public_key()
            
            key_pair = CryptographicKeyPair(
                private_key=private_key,
                public_key=public_key,
                key_id=key_id,
                created_at=datetime.utcnow()
            )
            
            self._key_pairs[key_id] = key_pair
            return True
            
        except Exception:
            return False
    
    def list_keys(self) -> List[str]:
        """List all key IDs"""
        return list(self._key_pairs.keys())
    
    def delete_key(self, key_id: str) -> bool:
        """Delete a key pair"""
        if key_id in self._key_pairs:
            del self._key_pairs[key_id]
            if self._current_key_id == key_id:
                self._current_key_id = None
            return True
        return False


class CryptographicMandateValidator:
    """
    Complete AP2 mandate cryptographic validation implementation.
    Follows best practices with proper separation of concerns.
    """
    
    def __init__(self, key_manager: KeyManager):
        self._key_manager = key_manager
    
    def sign_mandate(self, 
                    mandate_data: Dict[str, Any], 
                    key_id: str = None,
                    algorithm: str = "RS256") -> MandateSignature:
        """
        Sign mandate data with cryptographic signature.
        
        Args:
            mandate_data: The mandate data to sign
            key_id: Key ID to use for signing (uses current key if not provided)
            algorithm: Signing algorithm (currently supports RS256)
            
        Returns:
            MandateSignature object with signature and metadata
        """
        if algorithm != "RS256":
            raise ValidationError(f"Unsupported signing algorithm: {algorithm}")
        
        # Get key pair for signing
        if key_id:
            key_pair = self._key_manager.get_key_pair(key_id)
        else:
            key_pair = self._key_manager.get_current_key_pair()
        
        if not key_pair or not key_pair.private_key:
            raise ValidationError("No valid private key available for signing")
        
        # Prepare data for signing (canonical JSON)
        canonical_data = self._canonicalize_mandate_data(mandate_data)
        
        # Generate nonce for replay protection
        nonce = secrets.token_hex(16)
        
        # Create message to sign (data + nonce + timestamp)
        timestamp = datetime.utcnow().isoformat()
        message_data = {
            "mandate_data": canonical_data,
            "nonce": nonce,
            "timestamp": timestamp,
            "algorithm": algorithm
        }
        
        message = json.dumps(message_data, sort_keys=True).encode('utf-8')
        
        # Sign the message
        signature = key_pair.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Encode signature as base64
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return MandateSignature(
            signature=signature_b64,
            algorithm=algorithm,
            key_id=key_pair.key_id,
            timestamp=datetime.utcnow(),
            nonce=nonce
        )
    
    def verify_mandate(self, 
                      mandate_data: Dict[str, Any], 
                      signature: MandateSignature) -> bool:
        """
        Verify mandate signature.
        
        Args:
            mandate_data: The mandate data to verify
            signature: The signature to verify against
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Get public key for verification
            key_pair = self._key_manager.get_key_pair(signature.key_id)
            if not key_pair or not key_pair.public_key:
                raise ValidationError(f"Public key not found for key_id: {signature.key_id}")
            
            # Check key expiration
            if key_pair.expires_at and datetime.utcnow() > key_pair.expires_at:
                raise ValidationError(f"Key {signature.key_id} has expired")
            
            # Check signature age (prevent replay attacks)
            max_age = timedelta(hours=24)
            if datetime.utcnow() - signature.timestamp > max_age:
                raise ValidationError("Signature is too old")
            
            # Prepare data for verification (same as signing)
            canonical_data = self._canonicalize_mandate_data(mandate_data)
            
            # Recreate message
            message_data = {
                "mandate_data": canonical_data,
                "nonce": signature.nonce,
                "timestamp": signature.timestamp.isoformat(),
                "algorithm": signature.algorithm
            }
            
            message = json.dumps(message_data, sort_keys=True).encode('utf-8')
            
            # Decode signature
            signature_bytes = base64.b64decode(signature.signature)
            
            # Verify signature
            key_pair.public_key.verify(
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
            raise ValidationError(f"Signature verification failed: {str(e)}")
    
    def create_signed_mandate(self, 
                            mandate_data: Dict[str, Any],
                            key_id: str = None) -> Dict[str, Any]:
        """
        Create a complete signed mandate with embedded signature.
        
        Args:
            mandate_data: The mandate data to sign
            key_id: Key ID to use for signing
            
        Returns:
            Complete mandate with embedded signature
        """
        # Add metadata
        mandate_data["signature_metadata"] = {
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        # Sign the mandate
        signature = self.sign_mandate(mandate_data, key_id)
        
        # Create complete signed mandate
        signed_mandate = {
            "mandate": mandate_data,
            "signature": {
                "signature": signature.signature,
                "algorithm": signature.algorithm,
                "key_id": signature.key_id,
                "timestamp": signature.timestamp.isoformat(),
                "nonce": signature.nonce
            }
        }
        
        return signed_mandate
    
    def verify_signed_mandate(self, signed_mandate: Dict[str, Any]) -> bool:
        """
        Verify a complete signed mandate.
        
        Args:
            signed_mandate: Complete signed mandate with embedded signature
            
        Returns:
            True if mandate is valid, False otherwise
        """
        try:
            # Extract mandate data and signature
            mandate_data = signed_mandate.get("mandate")
            signature_data = signed_mandate.get("signature")
            
            if not mandate_data or not signature_data:
                raise ValidationError("Invalid signed mandate structure")
            
            # Create signature object
            signature = MandateSignature(
                signature=signature_data["signature"],
                algorithm=signature_data["algorithm"],
                key_id=signature_data["key_id"],
                timestamp=datetime.fromisoformat(signature_data["timestamp"]),
                nonce=signature_data["nonce"]
            )
            
            # Verify the signature
            return self.verify_mandate(mandate_data, signature)
            
        except Exception as e:
            raise ValidationError(f"Signed mandate verification failed: {str(e)}")
    
    def _canonicalize_mandate_data(self, mandate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Canonicalize mandate data for consistent signing/verification.
        Removes signature fields and sorts keys.
        """
        canonical = mandate_data.copy()
        
        # Remove signature-related fields
        canonical.pop("signature", None)
        canonical.pop("signature_metadata", None)
        
        # Recursively sort nested dictionaries
        def sort_dict_recursively(obj):
            if isinstance(obj, dict):
                return {k: sort_dict_recursively(v) for k, v in sorted(obj.items())}
            elif isinstance(obj, list):
                return [sort_dict_recursively(item) for item in obj]
            else:
                return obj
        
        return sort_dict_recursively(canonical)
    
    def get_mandate_hash(self, mandate_data: Dict[str, Any]) -> str:
        """Get SHA-256 hash of mandate data for integrity checking"""
        canonical_data = self._canonicalize_mandate_data(mandate_data)
        data_json = json.dumps(canonical_data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(data_json).hexdigest()


# Global key manager instance
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """Get the global key manager instance"""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
        # Generate default key pair
        _key_manager.generate_key_pair("default_key")
    return _key_manager


def get_mandate_validator() -> CryptographicMandateValidator:
    """Get a mandate validator with the global key manager"""
    return CryptographicMandateValidator(get_key_manager())
