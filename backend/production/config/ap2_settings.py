"""
AP2 (Agent Payments Protocol) Configuration Settings
"""
from typing import List, Optional
from pydantic import BaseSettings, Field
import os


class AP2Settings(BaseSettings):
    """AP2 Protocol configuration settings"""
    
    # AP2 Network Configuration
    ap2_base_url: str = Field(
        default="https://ap2-network.example.com",
        description="Base URL for AP2 network endpoints"
    )
    ap2_client_id: str = Field(
        default="",
        description="AP2 client ID for authentication"
    )
    ap2_private_key: str = Field(
        default="",
        description="AP2 private key in PEM format"
    )
    ap2_public_key: str = Field(
        default="",
        description="AP2 public key in PEM format"
    )
    
    # AP2 Protocol Settings
    ap2_version: str = Field(default="1.0", description="AP2 protocol version")
    ap2_timeout: int = Field(default=30, description="AP2 request timeout in seconds")
    ap2_retry_attempts: int = Field(default=3, description="Number of retry attempts for failed requests")
    ap2_retry_delay: float = Field(default=1.0, description="Delay between retry attempts in seconds")
    
    # Mandate Configuration
    ap2_default_mandate_expiry_hours: int = Field(
        default=24,
        description="Default expiry time for mandates in hours"
    )
    ap2_max_mandate_expiry_hours: int = Field(
        default=168,  # 7 days
        description="Maximum allowed expiry time for mandates in hours"
    )
    
    # Payment Method Configuration
    ap2_supported_payment_methods: List[str] = Field(
        default=["credit_card", "debit_card", "bank_transfer", "digital_wallet"],
        description="List of supported payment method types"
    )
    ap2_default_currency: str = Field(default="USD", description="Default currency for payments")
    
    # Security Configuration
    ap2_verification_required: bool = Field(
        default=True,
        description="Whether AP2 verification is required for all transactions"
    )
    ap2_signature_algorithm: str = Field(
        default="RS256",
        description="Signature algorithm for AP2 mandates"
    )
    
    # Webhook Configuration
    ap2_webhook_secret: Optional[str] = Field(
        default=None,
        description="Secret for AP2 webhook verification"
    )
    ap2_webhook_timeout: int = Field(
        default=10,
        description="Webhook request timeout in seconds"
    )
    
    # Development/Testing Settings
    ap2_sandbox_mode: bool = Field(
        default=False,
        description="Enable sandbox mode for testing"
    )
    ap2_mock_responses: bool = Field(
        default=False,
        description="Enable mock responses for development"
    )
    
    class Config:
        env_prefix = "AP2_"
        case_sensitive = False
        env_file = ".env"


# Global AP2 settings instance
ap2_settings = AP2Settings()


def get_ap2_config() -> AP2Settings:
    """Get AP2 configuration settings"""
    return ap2_settings


def is_ap2_enabled() -> bool:
    """Check if AP2 is enabled and properly configured"""
    return (
        bool(ap2_settings.ap2_client_id) and
        bool(ap2_settings.ap2_private_key) and
        bool(ap2_settings.ap2_public_key) and
        bool(ap2_settings.ap2_base_url)
    )


def get_ap2_client_config() -> dict:
    """Get AP2 client configuration dictionary"""
    return {
        "base_url": ap2_settings.ap2_base_url,
        "client_id": ap2_settings.ap2_client_id,
        "private_key": ap2_settings.ap2_private_key,
        "public_key": ap2_settings.ap2_public_key,
        "timeout": ap2_settings.ap2_timeout
    }
