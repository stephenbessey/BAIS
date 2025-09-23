"""
Verifiable Digital Credentials (VDC) Implementation
Complete AP2 VDC structure with cryptographic proof and chain of trust
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from .cryptographic_mandate_validator import CryptographicMandateValidator, MandateSignature


class VCType(Enum):
    """Verifiable Credential types"""
    IDENTITY = "IdentityCredential"
    BUSINESS_REGISTRATION = "BusinessRegistrationCredential"
    PAYMENT_AUTHORIZATION = "PaymentAuthorizationCredential"
    MANDATE_PROOF = "MandateProofCredential"
    TRANSACTION_RECEIPT = "TransactionReceiptCredential"


class ProofType(Enum):
    """Cryptographic proof types"""
    RSA_SIGNATURE = "RsaSignature2018"
    ECDSA_SIGNATURE = "EcdsaSignature2019"
    JWT_PROOF = "JwtProof2020"


@dataclass
class CryptographicProof:
    """Cryptographic proof for verifiable credentials"""
    type: ProofType
    created: datetime
    verification_method: str
    proof_purpose: str = "assertionMethod"
    jws: Optional[str] = None  # JSON Web Signature
    proof_value: Optional[str] = None  # Base64 encoded signature
    nonce: Optional[str] = None  # For replay protection
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": self.type.value,
            "created": self.created.isoformat(),
            "verificationMethod": self.verification_method,
            "proofPurpose": self.proof_purpose,
            "jws": self.jws,
            "proofValue": self.proof_value,
            "nonce": self.nonce
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CryptographicProof':
        """Create from dictionary"""
        return cls(
            type=ProofType(data["type"]),
            created=datetime.fromisoformat(data["created"]),
            verification_method=data["verificationMethod"],
            proof_purpose=data.get("proofPurpose", "assertionMethod"),
            jws=data.get("jws"),
            proof_value=data.get("proofValue"),
            nonce=data.get("nonce")
        )


@dataclass
class CredentialSubject:
    """Subject of the verifiable credential"""
    id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": self.type,
            **self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CredentialSubject':
        """Create from dictionary"""
        id_value = data.pop("id")
        type_value = data.pop("type")
        return cls(
            id=id_value,
            type=type_value,
            properties=data
        )


@dataclass
class VerifiableCredential:
    """Complete Verifiable Digital Credential structure following AP2 specification"""
    context: List[str] = field(default_factory=lambda: [
        "https://www.w3.org/2018/credentials/v1",
        "https://ap2-protocol.org/credentials/v1"
    ])
    id: str = field(default_factory=lambda: f"vc:{uuid.uuid4()}")
    type: List[str] = field(default_factory=lambda: ["VerifiableCredential"])
    issuer: str = ""
    issuance_date: datetime = field(default_factory=datetime.utcnow)
    expiration_date: Optional[datetime] = None
    credential_subject: Optional[CredentialSubject] = None
    credential_status: Optional[Dict[str, Any]] = None
    proof: Optional[CryptographicProof] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default expiration date if not provided"""
        if self.expiration_date is None:
            self.expiration_date = self.issuance_date + timedelta(days=365)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "@context": self.context,
            "id": self.id,
            "type": self.type,
            "issuer": self.issuer,
            "issuanceDate": self.issuance_date.isoformat(),
            "credentialSubject": self.credential_subject.to_dict() if self.credential_subject else None
        }
        
        if self.expiration_date:
            result["expirationDate"] = self.expiration_date.isoformat()
        
        if self.credential_status:
            result["credentialStatus"] = self.credential_status
        
        if self.proof:
            result["proof"] = self.proof.to_dict()
        
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VerifiableCredential':
        """Create from dictionary"""
        # Handle context (can be string or list)
        context = data.get("@context", [])
        if isinstance(context, str):
            context = [context]
        
        # Handle type (can be string or list)
        vc_type = data.get("type", ["VerifiableCredential"])
        if isinstance(vc_type, str):
            vc_type = [vc_type]
        
        # Parse dates
        issuance_date = datetime.fromisoformat(data["issuanceDate"])
        expiration_date = None
        if "expirationDate" in data:
            expiration_date = datetime.fromisoformat(data["expirationDate"])
        
        # Parse credential subject
        credential_subject = None
        if "credentialSubject" in data:
            credential_subject = CredentialSubject.from_dict(data["credentialSubject"])
        
        # Parse proof
        proof = None
        if "proof" in data:
            proof = CryptographicProof.from_dict(data["proof"])
        
        return cls(
            context=context,
            id=data["id"],
            type=vc_type,
            issuer=data["issuer"],
            issuance_date=issuance_date,
            expiration_date=expiration_date,
            credential_subject=credential_subject,
            credential_status=data.get("credentialStatus"),
            proof=proof,
            metadata=data.get("metadata", {})
        )
    
    def is_expired(self) -> bool:
        """Check if credential is expired"""
        if self.expiration_date is None:
            return False
        return datetime.utcnow() > self.expiration_date
    
    def get_credential_hash(self) -> str:
        """Get SHA-256 hash of credential data for integrity checking"""
        # Create canonical representation without proof
        credential_data = self.to_dict()
        credential_data.pop("proof", None)
        
        canonical_json = json.dumps(credential_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


class VDCManager:
    """Manages Verifiable Digital Credentials with cryptographic operations"""
    
    def __init__(self, crypto_validator: CryptographicMandateValidator):
        self._crypto_validator = crypto_validator
        self._issued_credentials: Dict[str, VerifiableCredential] = {}
        self._revoked_credentials: set = set()
    
    def create_identity_credential(self, 
                                 subject_id: str,
                                 identity_data: Dict[str, Any],
                                 issuer_id: str) -> VerifiableCredential:
        """Create an identity verifiable credential"""
        credential_subject = CredentialSubject(
            id=subject_id,
            type="Identity",
            properties={
                "name": identity_data.get("name"),
                "email": identity_data.get("email"),
                "phone": identity_data.get("phone"),
                "address": identity_data.get("address"),
                "verified_at": datetime.utcnow().isoformat()
            }
        )
        
        vc = VerifiableCredential(
            id=f"vc:identity:{uuid.uuid4()}",
            type=["VerifiableCredential", "IdentityCredential"],
            issuer=issuer_id,
            credential_subject=credential_subject,
            metadata={
                "credential_type": "identity",
                "verification_level": identity_data.get("verification_level", "basic"),
                "issuer_authority": issuer_id
            }
        )
        
        return self._sign_credential(vc, issuer_id)
    
    def create_business_registration_credential(self,
                                              business_id: str,
                                              business_data: Dict[str, Any],
                                              issuer_id: str) -> VerifiableCredential:
        """Create a business registration verifiable credential"""
        credential_subject = CredentialSubject(
            id=business_id,
            type="Business",
            properties={
                "name": business_data.get("name"),
                "type": business_data.get("type"),
                "registration_number": business_data.get("registration_number"),
                "address": business_data.get("address"),
                "tax_id": business_data.get("tax_id"),
                "registration_date": business_data.get("registration_date", datetime.utcnow().isoformat()),
                "status": business_data.get("status", "active"),
                "ap2_enabled": business_data.get("ap2_enabled", False)
            }
        )
        
        vc = VerifiableCredential(
            id=f"vc:business:{uuid.uuid4()}",
            type=["VerifiableCredential", "BusinessRegistrationCredential"],
            issuer=issuer_id,
            credential_subject=credential_subject,
            metadata={
                "credential_type": "business_registration",
                "jurisdiction": business_data.get("jurisdiction"),
                "regulatory_body": business_data.get("regulatory_body"),
                "verification_date": datetime.utcnow().isoformat()
            }
        )
        
        return self._sign_credential(vc, issuer_id)
    
    def create_payment_authorization_credential(self,
                                              user_id: str,
                                              business_id: str,
                                              authorization_data: Dict[str, Any],
                                              issuer_id: str) -> VerifiableCredential:
        """Create a payment authorization verifiable credential"""
        credential_subject = CredentialSubject(
            id=user_id,
            type="PaymentAuthorization",
            properties={
                "authorized_for_business": business_id,
                "max_amount": authorization_data.get("max_amount"),
                "currency": authorization_data.get("currency", "USD"),
                "authorization_type": authorization_data.get("type", "mandate"),
                "expires_at": authorization_data.get("expires_at"),
                "scope": authorization_data.get("scope", ["payment", "mandate"]),
                "authorized_at": datetime.utcnow().isoformat()
            }
        )
        
        vc = VerifiableCredential(
            id=f"vc:payment_auth:{uuid.uuid4()}",
            type=["VerifiableCredential", "PaymentAuthorizationCredential"],
            issuer=issuer_id,
            credential_subject=credential_subject,
            metadata={
                "credential_type": "payment_authorization",
                "authorization_method": authorization_data.get("method", "user_consent"),
                "verification_level": authorization_data.get("verification_level", "standard")
            }
        )
        
        return self._sign_credential(vc, issuer_id)
    
    def create_mandate_proof_credential(self,
                                      mandate_id: str,
                                      mandate_data: Dict[str, Any],
                                      issuer_id: str) -> VerifiableCredential:
        """Create a mandate proof verifiable credential"""
        credential_subject = CredentialSubject(
            id=mandate_id,
            type="MandateProof",
            properties={
                "mandate_type": mandate_data.get("type"),
                "user_id": mandate_data.get("user_id"),
                "business_id": mandate_data.get("business_id"),
                "amount": mandate_data.get("amount"),
                "currency": mandate_data.get("currency"),
                "intent": mandate_data.get("intent"),
                "created_at": mandate_data.get("created_at"),
                "expires_at": mandate_data.get("expires_at"),
                "mandate_hash": self._get_mandate_hash(mandate_data)
            }
        )
        
        vc = VerifiableCredential(
            id=f"vc:mandate:{uuid.uuid4()}",
            type=["VerifiableCredential", "MandateProofCredential"],
            issuer=issuer_id,
            credential_subject=credential_subject,
            metadata={
                "credential_type": "mandate_proof",
                "mandate_version": mandate_data.get("version", "1.0"),
                "proof_generation_date": datetime.utcnow().isoformat()
            }
        )
        
        return self._sign_credential(vc, issuer_id)
    
    def create_transaction_receipt_credential(self,
                                            transaction_id: str,
                                            transaction_data: Dict[str, Any],
                                            issuer_id: str) -> VerifiableCredential:
        """Create a transaction receipt verifiable credential"""
        credential_subject = CredentialSubject(
            id=transaction_id,
            type="TransactionReceipt",
            properties={
                "transaction_type": transaction_data.get("type", "payment"),
                "user_id": transaction_data.get("user_id"),
                "business_id": transaction_data.get("business_id"),
                "amount": transaction_data.get("amount"),
                "currency": transaction_data.get("currency"),
                "payment_method": transaction_data.get("payment_method"),
                "status": transaction_data.get("status"),
                "processed_at": transaction_data.get("processed_at"),
                "transaction_hash": self._get_transaction_hash(transaction_data)
            }
        )
        
        vc = VerifiableCredential(
            id=f"vc:transaction:{uuid.uuid4()}",
            type=["VerifiableCredential", "TransactionReceiptCredential"],
            issuer=issuer_id,
            credential_subject=credential_subject,
            metadata={
                "credential_type": "transaction_receipt",
                "receipt_number": transaction_data.get("receipt_number"),
                "generation_date": datetime.utcnow().isoformat()
            }
        )
        
        return self._sign_credential(vc, issuer_id)
    
    def verify_credential(self, credential: VerifiableCredential) -> bool:
        """Verify a verifiable credential"""
        try:
            # Check if credential is expired
            if credential.is_expired():
                return False
            
            # Check if credential is revoked
            if credential.id in self._revoked_credentials:
                return False
            
            # Verify cryptographic proof
            if not credential.proof:
                return False
            
            # Verify signature using cryptographic validator
            credential_data = credential.to_dict()
            proof_data = credential_data.pop("proof")
            
            # Create signature object for verification
            signature = MandateSignature(
                signature=proof_data["proofValue"] or proof_data["jws"],
                algorithm="RS256",  # Assuming RSA signature
                key_id=proof_data["verificationMethod"],
                timestamp=datetime.fromisoformat(proof_data["created"]),
                nonce=proof_data.get("nonce")
            )
            
            return self._crypto_validator.verify_mandate(credential_data, signature)
            
        except Exception:
            return False
    
    def revoke_credential(self, credential_id: str) -> bool:
        """Revoke a verifiable credential"""
        if credential_id in self._issued_credentials:
            self._revoked_credentials.add(credential_id)
            return True
        return False
    
    def is_credential_revoked(self, credential_id: str) -> bool:
        """Check if a credential is revoked"""
        return credential_id in self._revoked_credentials
    
    def get_credential(self, credential_id: str) -> Optional[VerifiableCredential]:
        """Get a credential by ID"""
        return self._issued_credentials.get(credential_id)
    
    def list_credentials(self, subject_id: str = None, issuer_id: str = None) -> List[VerifiableCredential]:
        """List credentials with optional filtering"""
        credentials = list(self._issued_credentials.values())
        
        if subject_id:
            credentials = [vc for vc in credentials 
                          if vc.credential_subject and vc.credential_subject.id == subject_id]
        
        if issuer_id:
            credentials = [vc for vc in credentials if vc.issuer == issuer_id]
        
        return credentials
    
    def _sign_credential(self, credential: VerifiableCredential, issuer_id: str) -> VerifiableCredential:
        """Sign a credential with cryptographic proof"""
        # Create credential data for signing
        credential_data = credential.to_dict()
        credential_data.pop("proof", None)  # Remove any existing proof
        
        # Sign the credential
        signature = self._crypto_validator.sign_mandate(credential_data, issuer_id)
        
        # Create cryptographic proof
        proof = CryptographicProof(
            type=ProofType.RSA_SIGNATURE,
            created=signature.timestamp,
            verification_method=signature.key_id,
            proof_purpose="assertionMethod",
            proof_value=signature.signature,
            nonce=signature.nonce
        )
        
        credential.proof = proof
        
        # Store the signed credential
        self._issued_credentials[credential.id] = credential
        
        return credential
    
    def _get_mandate_hash(self, mandate_data: Dict[str, Any]) -> str:
        """Get hash of mandate data"""
        canonical_data = json.dumps(mandate_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_data.encode('utf-8')).hexdigest()
    
    def _get_transaction_hash(self, transaction_data: Dict[str, Any]) -> str:
        """Get hash of transaction data"""
        canonical_data = json.dumps(transaction_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_data.encode('utf-8')).hexdigest()


# Global VDC manager instance
_vdc_manager: Optional[VDCManager] = None


def get_vdc_manager() -> VDCManager:
    """Get the global VDC manager instance"""
    global _vdc_manager
    if _vdc_manager is None:
        from .cryptographic_mandate_validator import get_mandate_validator
        _vdc_manager = VDCManager(get_mandate_validator())
    return _vdc_manager
