"""
BAIS Platform - Schema Generation Engine

This module generates BAIS-compliant schemas from business intelligence
extracted from websites, using template-based generation and AI inference.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import copy

from pydantic import BaseModel, Field

from ...core.bais_schema_validator import (
    BAISBusinessSchema, BusinessInfo, BusinessService, WorkflowDefinition,
    ServiceParameter, AvailabilityConfig, ServicePolicies, CancellationPolicyDetails,
    PaymentConfig, IntegrationConfig, MCPIntegration, A2AIntegration, WebhookConfig,
    CancellationPolicy, PaymentMethod
)
from ..scraper.website_analyzer import BusinessIntelligence, Service, BusinessCategory, ServiceType


@dataclass
class SchemaTemplate:
    """Template for generating BAIS schemas"""
    template_id: str
    business_type: BusinessCategory
    service_patterns: List[Dict[str, Any]]
    integration_defaults: Dict[str, Any]
    ui_components: List[str]
    metadata: Dict[str, Any]


class SchemaGenerator:
    """
    Schema Generation Engine for BAIS Demo Templates
    
    Generates BAIS-compliant schemas from business intelligence
    using template-based generation and AI inference.
    """
    
    def __init__(self, templates_path: str):
        self.templates_path = Path(templates_path)
        self.templates = self._load_templates()
        
        # Service type mappings
        self.service_type_mappings = {
            ServiceType.BOOKING: "booking",
            ServiceType.PURCHASE: "ecommerce",
            ServiceType.CONSULTATION: "consultation",
            ServiceType.SUBSCRIPTION: "subscription",
            ServiceType.RENTAL: "rental",
            ServiceType.DELIVERY: "delivery"
        }
        
        # Workflow patterns for different service types
        self.workflow_patterns = {
            "booking": {
                "pattern": "search_availability_book_confirm",
                "steps": [
                    {"name": "search_availability", "description": "Search for available slots"},
                    {"name": "select_options", "description": "Select service options"},
                    {"name": "provide_details", "description": "Provide customer details"},
                    {"name": "confirm_booking", "description": "Confirm booking"}
                ]
            },
            "ecommerce": {
                "pattern": "browse_cart_checkout_pay",
                "steps": [
                    {"name": "browse_products", "description": "Browse available products"},
                    {"name": "add_to_cart", "description": "Add items to cart"},
                    {"name": "checkout", "description": "Proceed to checkout"},
                    {"name": "payment", "description": "Complete payment"}
                ]
            },
            "consultation": {
                "pattern": "schedule_meet_consult_followup",
                "steps": [
                    {"name": "schedule_appointment", "description": "Schedule consultation"},
                    {"name": "prepare_meeting", "description": "Prepare for meeting"},
                    {"name": "conduct_consultation", "description": "Conduct consultation"},
                    {"name": "followup", "description": "Follow-up and recommendations"}
                ]
            }
        }
    
    def generate_bais_schema(
        self, 
        intelligence: BusinessIntelligence
    ) -> BAISBusinessSchema:
        """
        Generate BAIS-compliant schema from business intelligence
        
        Args:
            intelligence: Extracted business intelligence
            
        Returns:
            BAISBusinessSchema: Generated BAIS schema
        """
        try:
            # Select appropriate template
            base_template = self._select_template(intelligence.business_type)
            
            # Populate template with extracted data
            schema = self._populate_template(base_template, intelligence)
            
            # Enhance with AI inference
            schema = self._enhance_with_ai_inference(schema, intelligence)
            
            # Validate and refine
            schema = self._validate_and_refine(schema)
            
            return schema
            
        except Exception as e:
            raise Exception(f"Schema generation failed: {str(e)}")
    
    def _load_templates(self) -> Dict[str, SchemaTemplate]:
        """Load template definitions"""
        templates = {}
        
        # Define built-in templates
        templates["hotel_standard"] = SchemaTemplate(
            template_id="hotel_standard",
            business_type=BusinessCategory.HOTEL,
            service_patterns=[
                {
                    "service_type": "room_booking",
                    "workflow": "search_availability_book_confirm",
                    "required_params": ["check_in", "check_out", "guests"],
                    "optional_params": ["room_type", "special_requests"]
                }
            ],
            integration_defaults={
                "mcp_server": {
                    "resources": ["rooms", "availability", "bookings"],
                    "tools": ["search_rooms", "create_booking", "modify_booking"]
                },
                "acp_config": {
                    "checkout_fields": ["guest_details", "payment_method", "special_requests"],
                    "payment_timing": "at_booking"
                }
            },
            ui_components=[
                "room_gallery",
                "availability_calendar",
                "booking_form",
                "confirmation_display"
            ],
            metadata={"category": "hospitality"}
        )
        
        templates["restaurant_standard"] = SchemaTemplate(
            template_id="restaurant_standard",
            business_type=BusinessCategory.RESTAURANT,
            service_patterns=[
                {
                    "service_type": "table_reservation",
                    "workflow": "search_availability_book_confirm",
                    "required_params": ["date", "time", "guests"],
                    "optional_params": ["special_requests", "dietary_requirements"]
                }
            ],
            integration_defaults={
                "mcp_server": {
                    "resources": ["tables", "availability", "reservations"],
                    "tools": ["search_tables", "create_reservation", "modify_reservation"]
                },
                "acp_config": {
                    "checkout_fields": ["guest_details", "special_requests"],
                    "payment_timing": "at_reservation"
                }
            },
            ui_components=[
                "menu_display",
                "reservation_form",
                "table_availability",
                "confirmation_display"
            ],
            metadata={"category": "hospitality"}
        )
        
        templates["retail_standard"] = SchemaTemplate(
            template_id="retail_standard",
            business_type=BusinessCategory.RETAIL,
            service_patterns=[
                {
                    "service_type": "product_purchase",
                    "workflow": "browse_cart_checkout_pay",
                    "required_params": ["product_id", "quantity"],
                    "optional_params": ["shipping_address", "special_instructions"]
                }
            ],
            integration_defaults={
                "mcp_server": {
                    "resources": ["products", "inventory", "orders"],
                    "tools": ["search_products", "add_to_cart", "process_order"]
                },
                "acp_config": {
                    "checkout_fields": ["billing_address", "shipping_address", "payment_method"],
                    "payment_timing": "at_checkout"
                }
            },
            ui_components=[
                "product_catalog",
                "shopping_cart",
                "checkout_form",
                "order_confirmation"
            ],
            metadata={"category": "ecommerce"}
        )
        
        templates["service_standard"] = SchemaTemplate(
            template_id="service_standard",
            business_type=BusinessCategory.SERVICE,
            service_patterns=[
                {
                    "service_type": "service_booking",
                    "workflow": "schedule_meet_consult_followup",
                    "required_params": ["service_type", "date", "time"],
                    "optional_params": ["duration", "special_requirements"]
                }
            ],
            integration_defaults={
                "mcp_server": {
                    "resources": ["services", "availability", "appointments"],
                    "tools": ["search_services", "schedule_appointment", "reschedule_appointment"]
                },
                "acp_config": {
                    "checkout_fields": ["client_details", "service_preferences"],
                    "payment_timing": "at_booking"
                }
            },
            ui_components=[
                "service_catalog",
                "appointment_scheduler",
                "booking_form",
                "confirmation_display"
            ],
            metadata={"category": "professional_services"}
        )
        
        return templates
    
    def _select_template(self, business_type: BusinessCategory) -> SchemaTemplate:
        """Select appropriate template for business type"""
        template_key = f"{business_type.value}_standard"
        
        if template_key in self.templates:
            return self.templates[template_key]
        
        # Fallback to service template
        return self.templates["service_standard"]
    
    def _populate_template(
        self, 
        template: SchemaTemplate, 
        intelligence: BusinessIntelligence
    ) -> BAISBusinessSchema:
        """Fill template with extracted data"""
        # Generate business info
        business_info = BusinessInfo(
            external_id=self._generate_external_id(intelligence.business_name),
            name=intelligence.business_name,
            business_type=intelligence.business_type.value,
            description=intelligence.description,
            location=self._format_location(intelligence.location),
            contact_info=intelligence.contact_info.__dict__,
            operational_hours=intelligence.operational_hours.__dict__ if intelligence.operational_hours else None,
            established_date=None,  # Not available from website analysis
            capacity=None  # Not available from website analysis
        )
        
        # Generate services
        services = []
        for i, service in enumerate(intelligence.services):
            bais_service = self._create_bais_service(service, template, i)
            services.append(bais_service)
        
        # Generate integration config
        integration = self._create_integration_config(intelligence, template)
        
        # Create schema
        schema = BAISBusinessSchema(
            bais_version="1.0",
            schema_version="1.0.0",
            business_info=business_info,
            services=services,
            integration=integration,
            compliance={"mcp_compatible": True, "a2a_compatible": True, "acp_compatible": True}
        )
        
        return schema
    
    def _create_bais_service(
        self, 
        service: Service, 
        template: SchemaTemplate, 
        index: int
    ) -> BusinessService:
        """Create BAIS service from extracted service"""
        # Determine workflow pattern
        service_type_key = self.service_type_mappings.get(service.service_type, "booking")
        workflow_pattern = self.workflow_patterns.get(service_type_key, self.workflow_patterns["booking"])
        
        # Create workflow definition
        workflow = WorkflowDefinition(
            pattern=workflow_pattern["pattern"],
            steps=workflow_pattern["steps"],
            timeout_seconds=300,
            retry_attempts=3
        )
        
        # Create parameters based on service type
        parameters = self._create_service_parameters(service, template)
        
        # Create availability config
        availability = AvailabilityConfig(
            endpoint=f"/api/v1/services/{service.id}/availability",
            cache_timeout_seconds=300,
            advance_booking_days=365,
            real_time=True
        )
        
        # Create policies
        policies = self._create_service_policies(service)
        
        return BusinessService(
            id=service.id,
            name=service.name,
            description=service.description,
            category=service.category,
            workflow=workflow,
            parameters=parameters,
            availability=availability,
            policies=policies,
            enabled=True
        )
    
    def _create_service_parameters(
        self, 
        service: Service, 
        template: SchemaTemplate
    ) -> Dict[str, Any]:
        """Create service parameters based on service type"""
        parameters = {}
        
        # Get template pattern for this service
        pattern = None
        for service_pattern in template.service_patterns:
            if service_pattern["service_type"] in service.name.lower():
                pattern = service_pattern
                break
        
        if not pattern:
            pattern = template.service_patterns[0]  # Use first pattern as default
        
        # Add required parameters
        for param in pattern["required_params"]:
            parameters[param] = ServiceParameter(
                type=self._get_parameter_type(param),
                required=True,
                description=f"{param.replace('_', ' ').title()} parameter"
            )
        
        # Add optional parameters
        for param in pattern["optional_params"]:
            parameters[param] = ServiceParameter(
                type=self._get_parameter_type(param),
                required=False,
                description=f"Optional {param.replace('_', ' ').title()} parameter"
            )
        
        return parameters
    
    def _get_parameter_type(self, param_name: str) -> str:
        """Determine parameter type based on parameter name"""
        param_lower = param_name.lower()
        
        if any(keyword in param_lower for keyword in ['date', 'check_in', 'check_out']):
            return "string"  # Date strings
        elif any(keyword in param_lower for keyword in ['time', 'hour']):
            return "string"  # Time strings
        elif any(keyword in param_lower for keyword in ['guests', 'quantity', 'count', 'number']):
            return "integer"
        elif any(keyword in param_lower for keyword in ['price', 'amount', 'cost']):
            return "number"
        elif any(keyword in param_lower for keyword in ['enabled', 'active', 'confirmed']):
            return "boolean"
        elif any(keyword in param_lower for keyword in ['options', 'list', 'choices']):
            return "array"
        else:
            return "string"  # Default to string
    
    def _create_service_policies(self, service: Service) -> ServicePolicies:
        """Create service policies"""
        # Determine cancellation policy based on service type
        if service.service_type in [ServiceType.BOOKING, ServiceType.RESERVATION]:
            cancellation_policy = CancellationPolicyDetails(
                type=CancellationPolicy.FLEXIBLE,
                free_until_hours=24,
                penalty_percentage=50,
                description="Free cancellation up to 24 hours before service"
            )
        else:
            cancellation_policy = CancellationPolicyDetails(
                type=CancellationPolicy.STRICT,
                free_until_hours=48,
                penalty_percentage=100,
                description="Free cancellation up to 48 hours before service"
            )
        
        # Create payment config
        payment_methods = [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]
        if service.service_type == ServiceType.PURCHASE:
            payment_methods.extend([PaymentMethod.DIGITAL_WALLET, PaymentMethod.BUY_NOW_PAY_LATER])
        
        payment_config = PaymentConfig(
            methods=payment_methods,
            timing="at_booking",
            processing="secure_tokenized",
            deposit_required=False
        )
        
        return ServicePolicies(
            cancellation=cancellation_policy,
            payment=payment_config,
            modification_fee=0.0,
            no_show_penalty=0.0
        )
    
    def _create_integration_config(
        self, 
        intelligence: BusinessIntelligence, 
        template: SchemaTemplate
    ) -> IntegrationConfig:
        """Create integration configuration"""
        # Generate base URL
        safe_name = intelligence.business_name.lower().replace(' ', '-').strip()
        base_url = f"https://api.{safe_name}.com"
        
        # MCP integration
        mcp_integration = MCPIntegration(
            endpoint=f"{base_url}/mcp"
        )
        
        # A2A integration
        a2a_integration = A2AIntegration(
            discovery_url=f"{base_url}/.well-known/agent.json"
        )
        
        # Webhook configuration
        webhook_config = WebhookConfig(
            events=["booking_confirmed", "payment_processed", "service_completed"],
            endpoint=f"{base_url}/webhooks/bais"
        )
        
        return IntegrationConfig(
            mcp_server=mcp_integration,
            a2a_endpoint=a2a_integration,
            webhooks=webhook_config
        )
    
    def _enhance_with_ai_inference(
        self, 
        schema: BAISBusinessSchema, 
        intelligence: BusinessIntelligence
    ) -> BAISBusinessSchema:
        """Enhance schema with AI inference"""
        # This would integrate with AI models for intelligent enhancement
        # For now, we'll apply some basic enhancements
        
        # Enhance service descriptions
        for service in schema.services:
            if len(service.description) < 50:
                service.description = f"{service.description} - Professional {service.category} service available for booking through BAIS platform."
        
        # Add intelligent parameter suggestions based on business type
        if schema.business_info.business_type == "hotel":
            for service in schema.services:
                if "room" in service.name.lower():
                    service.parameters["amenities"] = ServiceParameter(
                        type="array",
                        required=False,
                        description="Requested amenities"
                    )
        
        return schema
    
    def _validate_and_refine(self, schema: BAISBusinessSchema) -> BAISBusinessSchema:
        """Validate and refine generated schema"""
        # Ensure all services have required parameters
        for service in schema.services:
            if not service.parameters:
                service.parameters = {
                    "service_date": ServiceParameter(
                        type="string",
                        required=True,
                        description="Service date"
                    )
                }
        
        # Ensure unique service IDs
        service_ids = [service.id for service in schema.services]
        for i, service_id in enumerate(service_ids):
            if service_ids.count(service_id) > 1:
                # Make ID unique
                new_id = f"{service_id}_{i}"
                schema.services[i].id = new_id
        
        return schema
    
    def _generate_external_id(self, business_name: str) -> str:
        """Generate external ID for business"""
        safe_name = business_name.lower().replace(' ', '-').replace('_', '-')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '-')
        safe_name = '-'.join(filter(None, safe_name.split('-')))
        return f"{safe_name}-{uuid.uuid4().hex[:8]}"
    
    def _format_location(self, location: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Format location data"""
        if not location:
            return None
        
        formatted = {}
        if 'latitude' in location:
            formatted['latitude'] = float(location['latitude'])
        if 'longitude' in location:
            formatted['longitude'] = float(location['longitude'])
        if 'address' in location:
            formatted['address'] = location['address']
        
        return formatted if formatted else None
