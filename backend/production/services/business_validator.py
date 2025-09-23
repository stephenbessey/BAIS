"""
Business Validator
Handles business schema validation following Single Responsibility Principle

This module extracts validation logic from BusinessService to follow
the Single Responsibility Principle.
"""

from typing import Dict, Any, List
from ..core.bais_schema_validator import BAISSchemaValidator
from ..core.exceptions import ValidationError, SchemaValidationError
from ..api_models import BusinessRegistrationRequest


class BusinessValidator:
    """
    Validates business registration requests and schemas
    
    Single Responsibility: Only handles validation logic
    """
    
    def __init__(self):
        self.schema_validator = BAISSchemaValidator()
    
    def validate_registration_request(self, request: BusinessRegistrationRequest) -> List[str]:
        """
        Validate business registration request
        
        Args:
            request: Business registration request
            
        Returns:
            List of validation issues (empty if valid)
            
        Raises:
            ValidationError: If validation fails
        """
        issues = []
        
        # Validate business name
        if not request.business_name or len(request.business_name.strip()) < 1:
            issues.append("Business name is required and must not be empty")
        
        if len(request.business_name) > 255:
            issues.append("Business name must not exceed 255 characters")
        
        # Validate business type
        if not request.business_type:
            issues.append("Business type is required")
        
        # Validate services
        if not request.services or len(request.services) == 0:
            issues.append("At least one service is required")
        
        # Validate service details
        for i, service in enumerate(request.services):
            service_issues = self._validate_service(service, i)
            issues.extend(service_issues)
        
        # Validate contact information
        if not request.contact_email:
            issues.append("Contact email is required")
        
        if request.contact_email and not self._is_valid_email(request.contact_email):
            issues.append("Contact email format is invalid")
        
        # Validate business address
        if request.business_address:
            address_issues = self._validate_address(request.business_address)
            issues.extend(address_issues)
        
        return issues
    
    def validate_business_schema(self, business_schema) -> None:
        """
        Validate business schema against BAIS standards
        
        Args:
            business_schema: Business schema to validate
            
        Raises:
            SchemaValidationError: If schema validation fails
        """
        try:
            is_valid, validation_issues = self.schema_validator.validate_schema(business_schema.dict())
            if not is_valid:
                raise SchemaValidationError(f"Invalid business schema: {'; '.join(validation_issues)}")
        except Exception as validation_error:
            if isinstance(validation_error, SchemaValidationError):
                raise
            raise SchemaValidationError(f"Schema validation failed: {str(validation_error)}")
    
    def _validate_service(self, service: Dict[str, Any], index: int) -> List[str]:
        """Validate individual service"""
        issues = []
        prefix = f"Service {index + 1}: "
        
        # Validate service name
        if not service.get('name'):
            issues.append(f"{prefix}Service name is required")
        
        if service.get('name') and len(service['name']) > 255:
            issues.append(f"{prefix}Service name must not exceed 255 characters")
        
        # Validate service description
        if not service.get('description'):
            issues.append(f"{prefix}Service description is required")
        
        if service.get('description') and len(service['description']) > 1000:
            issues.append(f"{prefix}Service description must not exceed 1000 characters")
        
        # Validate service category
        if not service.get('category'):
            issues.append(f"{prefix}Service category is required")
        
        # Validate pricing
        pricing = service.get('pricing', {})
        if pricing.get('price_per_unit') is not None:
            try:
                price = float(pricing['price_per_unit'])
                if price < 0:
                    issues.append(f"{prefix}Price per unit must not be negative")
            except (ValueError, TypeError):
                issues.append(f"{prefix}Price per unit must be a valid number")
        
        # Validate availability
        availability = service.get('availability', {})
        if availability.get('cache_timeout_seconds'):
            try:
                timeout = int(availability['cache_timeout_seconds'])
                if timeout < 1:
                    issues.append(f"{prefix}Cache timeout must be at least 1 second")
                if timeout > 3600:
                    issues.append(f"{prefix}Cache timeout must not exceed 3600 seconds")
            except (ValueError, TypeError):
                issues.append(f"{prefix}Cache timeout must be a valid integer")
        
        return issues
    
    def _validate_address(self, address: Dict[str, Any]) -> List[str]:
        """Validate business address"""
        issues = []
        
        # Validate required address fields
        required_fields = ['street', 'city', 'state', 'zip_code', 'country']
        for field in required_fields:
            if not address.get(field):
                issues.append(f"Address {field} is required")
        
        # Validate address length
        for field in ['street', 'city', 'state']:
            if address.get(field) and len(address[field]) > 255:
                issues.append(f"Address {field} must not exceed 255 characters")
        
        # Validate zip code format
        zip_code = address.get('zip_code')
        if zip_code:
            if len(zip_code) < 5 or len(zip_code) > 10:
                issues.append("ZIP code must be between 5 and 10 characters")
        
        return issues
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_business_update(self, business_id: str, update_data: Dict[str, Any]) -> List[str]:
        """
        Validate business update data
        
        Args:
            business_id: Business identifier
            update_data: Update data to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Validate business ID
        if not business_id:
            issues.append("Business ID is required for updates")
        
        # Validate update fields
        if 'name' in update_data:
            if not update_data['name'] or len(update_data['name'].strip()) < 1:
                issues.append("Business name cannot be empty")
            if len(update_data['name']) > 255:
                issues.append("Business name must not exceed 255 characters")
        
        if 'contact_email' in update_data:
            if update_data['contact_email'] and not self._is_valid_email(update_data['contact_email']):
                issues.append("Contact email format is invalid")
        
        if 'services' in update_data:
            for i, service in enumerate(update_data['services']):
                service_issues = self._validate_service(service, i)
                issues.extend(service_issues)
        
        return issues
    
    def validate_service_parameters(self, service_parameters: Dict[str, Any]) -> List[str]:
        """
        Validate service parameters
        
        Args:
            service_parameters: Service parameters to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        
        for param_name, param_config in service_parameters.items():
            param_prefix = f"Parameter '{param_name}': "
            
            # Validate parameter type
            if not param_config.get('type'):
                issues.append(f"{param_prefix}Type is required")
            
            # Validate parameter schema
            param_schema = param_config.get('schema')
            if not param_schema:
                issues.append(f"{param_prefix}Schema is required")
            
            # Validate required flag
            required = param_config.get('required', False)
            if not isinstance(required, bool):
                issues.append(f"{param_prefix}Required must be a boolean")
            
            # Validate default value matches type
            if 'default' in param_config:
                default_value = param_config['default']
                param_type = param_config.get('type')
                
                if param_type == 'string' and not isinstance(default_value, str):
                    issues.append(f"{param_prefix}Default value must be a string for string type")
                elif param_type == 'number' and not isinstance(default_value, (int, float)):
                    issues.append(f"{param_prefix}Default value must be a number for number type")
                elif param_type == 'boolean' and not isinstance(default_value, bool):
                    issues.append(f"{param_prefix}Default value must be a boolean for boolean type")
        
        return issues
