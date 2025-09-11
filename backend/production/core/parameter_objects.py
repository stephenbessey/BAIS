"""
Parameter Objects for Clean Code Compliance
Replaces functions with many parameters with structured data objects
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from uuid import UUID
from .constants import DatabaseLimits, BusinessLimits


@dataclass
class BusinessSearchCriteria:
    """Search criteria for business queries"""
    business_type: Optional[str] = None
    status: Optional[str] = None
    city: Optional[str] = None
    limit: int = DatabaseLimits.DEFAULT_QUERY_LIMIT
    offset: int = DatabaseLimits.DEFAULT_OFFSET


@dataclass
class BusinessCreationRequest:
    """Request object for creating a new business"""
    name: str
    business_type: str
    description: Optional[str] = None
    contact_info: Dict[str, str] = None
    location: Dict[str, Any] = None
    services_config: List[Dict[str, Any]] = None


@dataclass
class ServiceConfiguration:
    """Configuration for a business service"""
    service_id: str
    name: str
    description: str
    category: str
    workflow_pattern: str
    parameters_schema: Dict[str, Any]
    availability_endpoint: str
    cancellation_policy: Dict[str, Any]
    payment_config: Dict[str, Any]


@dataclass
class ContactInfo:
    """Contact information for businesses"""
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class LocationInfo:
    """Location information for businesses"""
    address: str
    city: str
    state: str
    postal_code: Optional[str] = None
    country: str = "US"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: str = "UTC"


@dataclass
class APIKeyCreationRequest:
    """Request for creating API keys"""
    business_id: UUID
    key_name: str
    scopes: List[str]
    permissions: Dict[str, Any] = None
    rate_limit_per_hour: int = BusinessLimits.DEFAULT_RATE_LIMIT_PER_HOUR
    expires_at: Optional[str] = None


@dataclass
class BookingSearchCriteria:
    """Search criteria for bookings"""
    business_id: Optional[UUID] = None
    service_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    customer_email: Optional[str] = None
    limit: int = DatabaseLimits.DEFAULT_QUERY_LIMIT // 2  # Smaller limit for bookings
    offset: int = DatabaseLimits.DEFAULT_OFFSET


@dataclass
class BookingCreationRequest:
    """Request for creating a booking"""
    business_id: UUID
    service_id: str
    customer_info: Dict[str, str]
    booking_details: Dict[str, Any]
    preferences: Dict[str, Any] = None


@dataclass
class ValidationResult:
    """Result of schema validation"""
    is_valid: bool
    issues: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    @classmethod
    def success(cls) -> 'ValidationResult':
        """Create a successful validation result"""
        return cls(is_valid=True, issues=[])
    
    @classmethod
    def failure(cls, issues: List[str], warnings: List[str] = None) -> 'ValidationResult':
        """Create a failed validation result"""
        return cls(is_valid=False, issues=issues, warnings=warnings or [])


@dataclass
class OAuth2ClientRegistrationRequest:
    """Request for registering OAuth 2.0 clients"""
    client_name: str
    redirect_uris: List[str]
    scopes: List[str]
    grant_types: List[str] = None
    response_types: List[str] = None
    
    def __post_init__(self):
        if self.grant_types is None:
            self.grant_types = ["authorization_code", "client_credentials"]
        if self.response_types is None:
            self.response_types = ["code"]


@dataclass
class MCPConfiguration:
    """Configuration for MCP server setup"""
    business_id: UUID
    endpoint: str
    capabilities: Dict[str, Any]
    authentication: Dict[str, Any] = None
    rate_limits: Dict[str, int] = None


@dataclass
class A2AConfiguration:
    """Configuration for A2A server setup"""
    business_id: UUID
    discovery_url: str
    capabilities: List[str]
    timeout_seconds: int = 30
    retry_attempts: int = 3
