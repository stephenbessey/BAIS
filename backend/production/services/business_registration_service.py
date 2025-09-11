"""
Business Registration Service
Orchestrates the complete business registration workflow
"""

from typing import Dict, Any, Optional
from uuid import UUID
from .business_service import BusinessService
from ..core.business_command_repository import BusinessCommandRepository
from ..core.business_query_repository import BusinessQueryRepository
from ..core.bais_schema_validator import BAISSchemaValidator
from ..core.parameter_objects import (
    BusinessCreationRequest, 
    BusinessRegistrationResult,
    ValidationResult
)
from ..core.exceptions import (
    BusinessRegistrationError,
    SchemaValidationError,
    ValidationError
)


class BusinessRegistrationService:
    """
    Service that orchestrates the complete business registration workflow.
    
    This service follows the Single Responsibility Principle by focusing
    only on business registration orchestration, delegating specific
    operations to appropriate repositories and validators.
    """
    
    def __init__(
        self,
        command_repo: BusinessCommandRepository,
        query_repo: BusinessQueryRepository,
        validator: BAISSchemaValidator
    ):
        self._command_repo = command_repo
        self._query_repo = query_repo
        self._validator = validator
    
    def register_business(self, request: BusinessCreationRequest) -> BusinessRegistrationResult:
        """
        Register a new business in the BAIS system.
        
        This method orchestrates the complete registration workflow:
        1. Validates the business creation request
        2. Checks for existing businesses
        3. Creates the business entity
        4. Sets up integration endpoints
        5. Returns registration result
        
        Args:
            request: Business creation request
            
        Returns:
            BusinessRegistrationResult with success/failure information
            
        Raises:
            BusinessRegistrationError: If registration fails
        """
        try:
            # Step 1: Validate the request
            validation_result = self._validate_registration_request(request)
            if not validation_result.is_valid:
                return BusinessRegistrationResult.failed(validation_result.issues)
            
            # Step 2: Check for existing business
            existing_business = self._check_existing_business(request)
            if existing_business:
                return BusinessRegistrationResult.failed([
                    f"Business with name '{request.name}' already exists"
                ])
            
            # Step 3: Create business entity
            business = self._create_business_entity(request)
            
            # Step 4: Setup integration endpoints
            integration_result = self._setup_integration_endpoints(business)
            if not integration_result.success:
                # Rollback business creation if integration setup fails
                self._command_repo.delete_business(business.id)
                return BusinessRegistrationResult.failed(integration_result.issues)
            
            # Step 5: Return success result
            return BusinessRegistrationResult.success(
                business_id=str(business.id),
                business_name=business.name,
                integration_endpoints=integration_result.endpoints
            )
            
        except Exception as e:
            raise BusinessRegistrationError(
                f"Business registration failed: {str(e)}",
                business_id=getattr(request, 'name', None)
            )
    
    def _validate_registration_request(self, request: BusinessCreationRequest) -> ValidationResult:
        """Validate the business registration request"""
        issues = []
        
        # Validate business name
        if not request.name or len(request.name.strip()) == 0:
            issues.append("Business name is required")
        elif len(request.name) > 255:
            issues.append("Business name must be 255 characters or less")
        
        # Validate business type
        if not request.business_type:
            issues.append("Business type is required")
        
        # Validate location information
        if not request.location:
            issues.append("Location information is required")
        else:
            location_issues = self._validate_location_info(request.location)
            issues.extend(location_issues)
        
        # Validate services configuration
        if not request.services_config:
            issues.append("At least one service configuration is required")
        else:
            service_issues = self._validate_services_config(request.services_config)
            issues.extend(service_issues)
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues
        )
    
    def _validate_location_info(self, location: Dict[str, Any]) -> list[str]:
        """Validate location information"""
        issues = []
        
        if not location.get("address"):
            issues.append("Address is required")
        
        if not location.get("city"):
            issues.append("City is required")
        
        if not location.get("state"):
            issues.append("State is required")
        
        return issues
    
    def _validate_services_config(self, services_config: list[Dict[str, Any]]) -> list[str]:
        """Validate services configuration"""
        issues = []
        
        if len(services_config) == 0:
            issues.append("At least one service must be configured")
            return issues
        
        service_ids = []
        for i, service in enumerate(services_config):
            if not service.get("service_id"):
                issues.append(f"Service {i+1}: Service ID is required")
            else:
                service_ids.append(service["service_id"])
            
            if not service.get("name"):
                issues.append(f"Service {i+1}: Service name is required")
        
        # Check for duplicate service IDs
        if len(service_ids) != len(set(service_ids)):
            issues.append("Service IDs must be unique")
        
        return issues
    
    def _check_existing_business(self, request: BusinessCreationRequest) -> Optional[Any]:
        """Check if a business with the same name already exists"""
        # This would typically check against external_id or name
        # For now, return None (no existing business)
        return None
    
    def _create_business_entity(self, request: BusinessCreationRequest) -> Any:
        """Create the business entity"""
        return self._command_repo.create_business(request)
    
    def _setup_integration_endpoints(self, business: Any) -> 'IntegrationSetupResult':
        """Setup integration endpoints for the business"""
        try:
            # This would setup MCP and A2A endpoints
            # For now, return a mock success result
            return IntegrationSetupResult(
                success=True,
                endpoints={
                    "mcp_endpoint": f"https://api.example.com/mcp/{business.id}",
                    "a2a_endpoint": f"https://api.example.com/a2a/{business.id}"
                }
            )
        except Exception as e:
            return IntegrationSetupResult(
                success=False,
                issues=[f"Failed to setup integration endpoints: {str(e)}"]
            )


class BusinessRegistrationResult:
    """Result of business registration operation"""
    
    def __init__(
        self,
        success: bool,
        business_id: Optional[str] = None,
        business_name: Optional[str] = None,
        integration_endpoints: Optional[Dict[str, str]] = None,
        issues: Optional[list[str]] = None
    ):
        self.success = success
        self.business_id = business_id
        self.business_name = business_name
        self.integration_endpoints = integration_endpoints or {}
        self.issues = issues or []
    
    @classmethod
    def success(
        cls, 
        business_id: str, 
        business_name: str,
        integration_endpoints: Dict[str, str]
    ) -> 'BusinessRegistrationResult':
        """Create a successful registration result"""
        return cls(
            success=True,
            business_id=business_id,
            business_name=business_name,
            integration_endpoints=integration_endpoints
        )
    
    @classmethod
    def failed(cls, issues: list[str]) -> 'BusinessRegistrationResult':
        """Create a failed registration result"""
        return cls(success=False, issues=issues)


class IntegrationSetupResult:
    """Result of integration endpoint setup"""
    
    def __init__(
        self,
        success: bool,
        endpoints: Optional[Dict[str, str]] = None,
        issues: Optional[list[str]] = None
    ):
        self.success = success
        self.endpoints = endpoints or {}
        self.issues = issues or []
