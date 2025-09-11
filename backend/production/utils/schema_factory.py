import uuid
from ..api_models import BusinessRegistrationRequest
from ..core.bais_schema_validator import (
    BAISBusinessSchema, BusinessInfo, Location, ContactInfo, BusinessService,
    WorkflowDefinition, WorkflowPattern, WorkflowStep, ServiceParameter,
    AvailabilityConfig, ServicePolicies, CancellationPolicyDetails,
    CancellationPolicy, PaymentConfig, PaymentMethod, IntegrationConfig,
    MCPIntegration, A2AIntegration, WebhookConfig, ServiceType
)

class BusinessSchemaFactory:
    @staticmethod
    def create_from_request(request: BusinessRegistrationRequest) -> BAISBusinessSchema:
        """Creates a BAISBusinessSchema from a BusinessRegistrationRequest."""
        business_id = str(uuid.uuid4())
        
        business_info = BusinessInfo(
            id=business_id,
            name=request.business_name,
            type=ServiceType(request.business_type),
            location=Location(**request.location),
            contact=ContactInfo(**request.contact_info)
        )

        services = [
            BusinessSchemaFactory._create_service_from_config(business_id, service_config)
            for service_config in request.services_config
        ]

        integration = BusinessSchemaFactory._create_integration_config(request)

        return BAISBusinessSchema(
            business_info=business_info,
            services=services,
            integration=integration
        )

    @staticmethod
    def _create_service_from_config(business_id: str, service_config: dict) -> BusinessService:
        """Builds a BusinessService object from a dictionary configuration."""
        workflow = WorkflowDefinition(
            pattern=WorkflowPattern(service_config.get("workflow_pattern", "booking_confirmation_payment")),
            steps=[
                WorkflowStep(step=step["step"], description=step["description"])
                for step in service_config.get("workflow_steps", [
                    {"step": "availability_check", "description": "Check availability"},
                    {"step": "booking", "description": "Create booking"},
                    {"step": "payment", "description": "Process payment"},
                    {"step": "confirmation", "description": "Send confirmation"}
                ])
            ]
        )

        parameters = {
            param_name: ServiceParameter(**param_config)
            for param_name, param_config in service_config.get("parameters", {}).items()
        }

        policies = ServicePolicies(
            cancellation=CancellationPolicyDetails(
                type=CancellationPolicy.FLEXIBLE,
                free_until_hours=24,
                penalty_percentage=0,
                description="Free cancellation"
            ),
            payment=PaymentConfig(
                methods=[PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD],
                timing="at_booking"
            )
        )

        return BusinessService(
            id=service_config["id"],
            name=service_config["name"],
            description=service_config.get("description", ""),
            category=service_config.get("category", "general"),
            workflow=workflow,
            parameters=parameters,
            availability=AvailabilityConfig(
                endpoint=f"/api/v1/businesses/{business_id}/services/{service_config['id']}/availability"
            ),
            policies=policies
        )

    @staticmethod
    def _create_integration_config(request: BusinessRegistrationRequest) -> IntegrationConfig:
        """Builds an IntegrationConfig object for the business."""
        safe_name = request.business_name.lower().replace(' ', '-').strip()
        base_url = f"https://api.{safe_name}.com"
        
        return IntegrationConfig(
            mcp_server=MCPIntegration(endpoint=f"{base_url}/mcp"),
            a2a_endpoint=A2AIntegration(discovery_url=f"{base_url}/.well-known/agent.json"),
            webhooks=WebhookConfig(
                events=["booking_confirmed", "payment_processed"],
                endpoint=f"{base_url}/webhooks/bais"
            )
        )