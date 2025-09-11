"""
BAIS Business Service Schema Validator
Implements the actual BAIS v1.0 specification for business service schemas
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
import json
from enum import Enum
from dataclasses import dataclass

class ServiceType(str, Enum):
    HOSPITALITY = "hospitality"
    FOOD_SERVICE = "food_service"
    RETAIL = "retail"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"

class WorkflowPattern(str, Enum):
    BOOKING_CONFIRMATION_PAYMENT = "booking_confirmation_payment"
    SEARCH_PURCHASE = "search_purchase"
    APPOINTMENT_SCHEDULING = "appointment_scheduling"
    CONSULTATION_BOOKING = "consultation_booking"

class CancellationPolicy(str, Enum):
    FLEXIBLE = "flexible"
    MODERATE = "moderate"
    STRICT = "strict"
    NON_REFUNDABLE = "non_refundable"

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    DIGITAL_WALLET = "digital_wallet"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"

class Location(BaseModel):
    address: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="US", max_length=5)
    coordinates: Optional[List[float]] = Field(None, min_items=2, max_items=2)
    timezone: str = Field(default="UTC", max_length=50)

class ContactInfo(BaseModel):
    website: Optional[str] = Field(None, regex=r'^https?://.+')
    phone: Optional[str] = Field(None, regex=r'^\+?[1-9]\d{1,14}$')
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')

class BusinessInfo(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    type: ServiceType
    location: Location
    contact: ContactInfo
    description: Optional[str] = Field(None, max_length=1000)
    established: Optional[date] = None
    capacity: Optional[int] = Field(None, ge=1)

class PricingModel(BaseModel):
    base_rate: float = Field(..., ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    tax_rate: Optional[float] = Field(None, ge=0, le=1)
    service_fee: Optional[float] = Field(None, ge=0)
    minimum_charge: Optional[float] = Field(None, ge=0)

class ServiceParameter(BaseModel):
    type: str = Field(..., regex=r'^(string|integer|number|boolean|array|object)$')
    description: str = Field(..., min_length=1, max_length=500)
    required: bool = Field(default=False)
    default: Optional[Any] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    enum: Optional[List[str]] = None
    format: Optional[str] = None
    pricing: Optional[Dict[str, PricingModel]] = None

class WorkflowStep(BaseModel):
    step: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=255)
    required: bool = Field(default=True)
    timeout_minutes: Optional[int] = Field(None, ge=1, le=1440)
    retry_attempts: int = Field(default=3, ge=0, le=10)

class WorkflowDefinition(BaseModel):
    pattern: WorkflowPattern
    steps: List[WorkflowStep] = Field(..., min_items=1)
    total_timeout_minutes: int = Field(default=30, ge=1, le=1440)
    requires_human_approval: bool = Field(default=False)

class AvailabilityConfig(BaseModel):
    endpoint: str = Field(..., regex=r'^/api/.+')
    real_time: bool = Field(default=True)
    cache_timeout_seconds: int = Field(default=300, ge=0, le=3600)
    advance_booking_days: int = Field(default=365, ge=1, le=730)

class CancellationPolicyDetails(BaseModel):
    type: CancellationPolicy
    free_until_hours: int = Field(default=24, ge=0, le=168)
    penalty_percentage: float = Field(default=0, ge=0, le=100)
    description: str = Field(..., min_length=1, max_length=500)

class PaymentConfig(BaseModel):
    methods: List[PaymentMethod] = Field(..., min_items=1)
    processing: str = Field(default="secure_tokenized")
    timing: str = Field(default="at_booking", regex=r'^(at_booking|on_arrival|after_service)$')
    deposit_required: bool = Field(default=False)
    deposit_percentage: Optional[float] = Field(None, ge=0, le=100)

class ServicePolicies(BaseModel):
    cancellation: CancellationPolicyDetails
    payment: PaymentConfig
    modification_fee: Optional[float] = Field(None, ge=0)
    no_show_penalty: Optional[float] = Field(None, ge=0)

class BusinessService(BaseModel):
    id: str = Field(..., min_length=1, max_length=100, regex=r'^[a-z0-9_]+$')
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1000)
    category: str = Field(..., min_length=1, max_length=100)
    workflow: WorkflowDefinition
    parameters: Dict[str, ServiceParameter] = Field(..., min_items=1)
    availability: AvailabilityConfig
    policies: ServicePolicies
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('parameters')
    def validate_required_parameters(cls, v):
        required_params = ['check_in', 'check_out', 'guests'] if any(
            'booking' in str(v).lower() for v in v.keys()
        ) else []
        
        for param in required_params:
            if param not in v:
                raise ValueError(f"Required parameter '{param}' missing for booking service")
        return v

class MCPIntegration(BaseModel):
    endpoint: str = Field(..., regex=r'^https?://.+/mcp$')
    transport: str = Field(default="http", regex=r'^(http|websocket)$')
    authentication: str = Field(default="oauth2")
    version: str = Field(default="2025-06-18")

class A2AIntegration(BaseModel):
    discovery_url: str = Field(..., regex=r'^https?://.+/.well-known/agent.json$')
    capabilities: List[str] = Field(default_factory=lambda: ["task_execution", "context_sharing"])
    max_concurrent_sessions: int = Field(default=10, ge=1, le=100)

class WebhookConfig(BaseModel):
    events: List[str] = Field(..., min_items=1)
    endpoint: str = Field(..., regex=r'^https?://.+/webhooks/bais$')
    signing_secret: Optional[str] = Field(None, min_length=32)
    retry_attempts: int = Field(default=3, ge=0, le=10)

class IntegrationConfig(BaseModel):
    mcp_server: MCPIntegration
    a2a_endpoint: A2AIntegration
    webhooks: WebhookConfig

class BAISBusinessSchema(BaseModel):
    bais_version: str = Field(default="1.0", regex=r'^\d+\.\d+$')
    schema_version: str = Field(default="1.0.0", regex=r'^\d+\.\d+\.\d+$')
    business_info: BusinessInfo
    services: List[BusinessService] = Field(..., min_items=1, max_items=50)
    integration: IntegrationConfig
    compliance: Dict[str, bool] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('services')
    def validate_unique_service_ids(cls, v):
        service_ids = [service.id for service in v]
        if len(service_ids) != len(set(service_ids)):
            raise ValueError("Service IDs must be unique")
        return v

    def to_json(self) -> str:
        """Convert schema to JSON string"""
        return self.json(indent=2, exclude_none=True)

    @classmethod
    def from_json(cls, json_str: str) -> 'BAISBusinessSchema':
        """Create schema from JSON string"""
        return cls.parse_raw(json_str)

    def validate_mcp_compatibility(self) -> List[str]:
        """Validate MCP protocol compatibility"""
        issues = []
        
        for service in self.services:
            # Check required MCP resource patterns
            if not service.availability.endpoint.startswith('/api/'):
                issues.append(f"Service {service.id}: availability endpoint must follow MCP pattern")
            
            # Validate parameter types for MCP tools
            for param_name, param in service.parameters.items():
                if param.type not in ['string', 'integer', 'number', 'boolean', 'array']:
                    issues.append(f"Service {service.id}: parameter {param_name} has invalid type for MCP")
        
        return issues

    def validate_a2a_compatibility(self) -> List[str]:
        """Validate A2A protocol compatibility"""
        issues = []
        
        if not self.integration.a2a_endpoint.discovery_url:
            issues.append("A2A discovery URL is required")
        
        required_capabilities = ["task_execution"]
        for cap in required_capabilities:
            if cap not in self.integration.a2a_endpoint.capabilities:
                issues.append(f"Missing required A2A capability: {cap}")
        
        return issues

@dataclass
class SchemaValidationResult:
    """Result of schema validation"""
    is_valid: bool
    issues: List[str]
    schema: Optional[BAISBusinessSchema] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    @classmethod
    def success(cls, schema: BAISBusinessSchema) -> 'SchemaValidationResult':
        """Create a successful validation result"""
        return cls(is_valid=True, issues=[], schema=schema)
    
    @classmethod
    def failure(cls, issues: List[str], warnings: List[str] = None) -> 'SchemaValidationResult':
        """Create a failed validation result"""
        return cls(is_valid=False, issues=issues, warnings=warnings or [])


class BAISSchemaValidator:
    """Validator for BAIS business schemas"""
    
    @staticmethod
    def validate_schema(schema_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate a BAIS schema and return validation result"""
        try:
            validation_result = BAISSchemaValidator._validate_schema_structure(schema_data)
            if not validation_result.is_valid:
                return False, validation_result.issues
            
            schema = validation_result.schema
            validation_result = BAISSchemaValidator._run_comprehensive_validation(schema)
            
            return validation_result.is_valid, validation_result.issues
            
        except Exception as e:
            return False, [f"Schema validation error: {str(e)}"]
    
    @staticmethod
    def _validate_schema_structure(schema_data: Dict[str, Any]) -> SchemaValidationResult:
        """Validate basic schema structure and parsing"""
        try:
            schema = BAISBusinessSchema(**schema_data)
            return SchemaValidationResult.success(schema)
        except Exception as e:
            return SchemaValidationResult.failure([f"Schema parsing error: {str(e)}"])
    
    @staticmethod
    def _run_comprehensive_validation(schema: BAISBusinessSchema) -> SchemaValidationResult:
        """Run comprehensive validation on parsed schema"""
        issues = []
        
        # Validate MCP compatibility
        mcp_issues = schema.validate_mcp_compatibility()
        issues.extend(mcp_issues)
        
        # Validate A2A compatibility
        a2a_issues = schema.validate_a2a_compatibility()
        issues.extend(a2a_issues)
        
        # Validate business-specific requirements
        business_issues = BAISSchemaValidator._validate_business_requirements(schema)
        issues.extend(business_issues)
        
        return SchemaValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            schema=schema if len(issues) == 0 else None
        )
    
    @staticmethod
    def _validate_business_requirements(schema: BAISBusinessSchema) -> List[str]:
        """Validate business-specific requirements"""
        issues = []
        
        # Check if business has at least one service
        if not schema.services:
            issues.append("Business must have at least one service")
        
        # Validate service IDs are unique
        service_ids = [service.id for service in schema.services]
        if len(service_ids) != len(set(service_ids)):
            issues.append("Service IDs must be unique")
        
        # Validate required endpoints
        if not schema.integration.mcp_server.endpoint:
            issues.append("MCP server endpoint is required")
        
        if not schema.integration.a2a_endpoint.discovery_url:
            issues.append("A2A discovery URL is required")
        
        return issues
    
    @staticmethod
    def create_hospitality_template() -> BAISBusinessSchema:
        """Create a template schema for hospitality businesses"""
        return BAISBusinessSchema(
            business_info=BusinessInfo(
                id="example_hotel",
                name="Example Hotel",
                type=ServiceType.HOSPITALITY,
                location=Location(
                    address="123 Main St",
                    city="Anytown",
                    state="CA",
                    postal_code="90210",
                    coordinates=[34.0522, -118.2437]
                ),
                contact=ContactInfo(
                    website="https://example-hotel.com",
                    phone="+1-555-123-4567",
                    email="reservations@example-hotel.com"
                )
            ),
            services=[
                BusinessService(
                    id="room_booking",
                    name="Hotel Room Reservation",
                    description="Book hotel rooms with various amenities",
                    category="accommodation",
                    workflow=WorkflowDefinition(
                        pattern=WorkflowPattern.BOOKING_CONFIRMATION_PAYMENT,
                        steps=[
                            WorkflowStep(step="availability_check", description="Check room availability"),
                            WorkflowStep(step="reservation", description="Create reservation"),
                            WorkflowStep(step="payment", description="Process payment"),
                            WorkflowStep(step="confirmation", description="Send confirmation")
                        ]
                    ),
                    parameters={
                        "check_in": ServiceParameter(
                            type="string",
                            format="date",
                            description="Check-in date (YYYY-MM-DD)",
                            required=True
                        ),
                        "check_out": ServiceParameter(
                            type="string", 
                            format="date",
                            description="Check-out date (YYYY-MM-DD)",
                            required=True
                        ),
                        "guests": ServiceParameter(
                            type="integer",
                            description="Number of guests",
                            required=True,
                            minimum=1,
                            maximum=6,
                            default=2
                        )
                    },
                    availability=AvailabilityConfig(
                        endpoint="/api/v1/availability",
                        real_time=True
                    ),
                    policies=ServicePolicies(
                        cancellation=CancellationPolicyDetails(
                            type=CancellationPolicy.FLEXIBLE,
                            free_until_hours=24,
                            penalty_percentage=50,
                            description="Free cancellation up to 24 hours before check-in"
                        ),
                        payment=PaymentConfig(
                            methods=[PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD],
                            timing="at_booking"
                        )
                    )
                )
            ],
            integration=IntegrationConfig(
                mcp_server=MCPIntegration(
                    endpoint="https://api.example-hotel.com/mcp"
                ),
                a2a_endpoint=A2AIntegration(
                    discovery_url="https://api.example-hotel.com/.well-known/agent.json"
                ),
                webhooks=WebhookConfig(
                    events=["booking_confirmed", "payment_processed"],
                    endpoint="https://api.example-hotel.com/webhooks/bais"
                )
            )
        )