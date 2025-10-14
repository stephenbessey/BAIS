from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from uuid import uuid4


class PaymentStatus(Enum):
    INITIALIZING = "initializing"
    INTENT_AUTHORIZED = "intent_authorized"
    CART_CONFIRMED = "cart_confirmed"
    PAYMENT_PROCESSING = "payment_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentMethodType(Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    STABLECOIN = "stablecoin"
    DIGITAL_WALLET = "digital_wallet"


@dataclass
class AP2Mandate:
    """Represents an AP2 mandate (intent or cart)"""
    id: str
    type: str  # "intent" or "cart"
    user_id: str
    business_id: str
    data: Dict[str, Any]
    signature: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    status: str = "active"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AP2Mandate':
        """Create mandate from API response"""
        return cls(
            id=data["id"],
            type=data["type"],
            user_id=data["userId"],
            business_id=data["businessId"],
            data=data.get("data", {}),
            signature=data["signature"],
            created_at=datetime.fromisoformat(data["createdAt"]),
            expires_at=datetime.fromisoformat(data["expiresAt"]) if data.get("expiresAt") else None,
            status=data.get("status", "active")
        )


@dataclass
class PaymentMethod:
    """Represents a payment method"""
    id: str
    type: PaymentMethodType
    display_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_default: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AP2 requests"""
        return {
            "id": self.id,
            "type": self.type.value,
            "displayName": self.display_name,
            "metadata": self.metadata,
            "isDefault": self.is_default
        }


@dataclass
class AP2Transaction:
    """Represents an AP2 transaction"""
    id: str
    cart_mandate_id: str
    payment_method: PaymentMethod
    amount: float
    currency: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AP2Transaction':
        """Create transaction from API response"""
        return cls(
            id=data["id"],
            cart_mandate_id=data["cartMandateId"],
            payment_method=PaymentMethod(
                id=data["paymentMethod"]["id"],
                type=PaymentMethodType(data["paymentMethod"]["type"]),
                display_name=data["paymentMethod"]["displayName"],
                metadata=data["paymentMethod"].get("metadata", {})
            ),
            amount=float(data["amount"]),
            currency=data["currency"],
            status=data["status"],
            created_at=datetime.fromisoformat(data["createdAt"]),
            completed_at=datetime.fromisoformat(data["completedAt"]) if data.get("completedAt") else None,
            error_message=data.get("errorMessage")
        )


@dataclass
class PaymentWorkflow:
    """Represents a complete payment workflow"""
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    business_id: str = ""
    agent_id: str = ""
    status: PaymentStatus = PaymentStatus.INITIALIZING
    current_step: Optional['PaymentWorkflowStep'] = None
    
    # AP2 IDs
    intent_mandate_id: Optional[str] = None
    cart_mandate_id: Optional[str] = None
    transaction_id: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def update_status(self, status: PaymentStatus, error_message: Optional[str] = None):
        """Update workflow status with timestamp"""
        self.status = status
        self.updated_at = datetime.utcnow()
        self.error_message = error_message
        
        if status in [PaymentStatus.COMPLETED, PaymentStatus.FAILED, PaymentStatus.CANCELLED]:
            self.completed_at = datetime.utcnow()


@dataclass
class VerifiableCredential:
    """Represents a verifiable credential for AP2"""
    id: str
    type: str
    issuer: str
    subject: str
    claims: Dict[str, Any]
    proof: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None


class BusinessIntent(BaseModel):
    """Business intent for payment processing"""
    business_id: str
    intent_type: str
    amount: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}
