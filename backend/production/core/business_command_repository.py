"""
Business Command Repository
Handles write operations for business entities following CQRS pattern
"""

from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from .database_models import Business, BusinessService, BusinessAPIKey
from .parameter_objects import BusinessCreationRequest, ServiceConfiguration, APIKeyCreationRequest


class BusinessCommandRepository:
    """Repository for business write operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def create_business(self, request: BusinessCreationRequest) -> Business:
        """Create a new business entity"""
        business = Business(
            external_id=request.name.lower().replace(" ", "_"),
            name=request.name,
            business_type=request.business_type,
            description=request.description,
            address=request.location.get("address", ""),
            city=request.location.get("city", ""),
            state=request.location.get("state", ""),
            postal_code=request.location.get("postal_code"),
            country=request.location.get("country", "US"),
            latitude=request.location.get("latitude"),
            longitude=request.location.get("longitude"),
            timezone=request.location.get("timezone", "UTC"),
            website=request.contact_info.get("website"),
            phone=request.contact_info.get("phone"),
            email=request.contact_info.get("email")
        )
        
        self.db_session.add(business)
        self.db_session.commit()
        self.db_session.refresh(business)
        
        return business
    
    def update_business(self, business_id: UUID, update_data: Dict[str, Any]) -> Optional[Business]:
        """Update business entity"""
        business = self.db_session.get(Business, business_id)
        if not business:
            return None
        
        for key, value in update_data.items():
            if hasattr(business, key) and value is not None:
                setattr(business, key, value)
        
        self.db_session.commit()
        self.db_session.refresh(business)
        
        return business
    
    def delete_business(self, business_id: UUID) -> bool:
        """Delete business entity"""
        business = self.db_session.get(Business, business_id)
        if not business:
            return False
        
        self.db_session.delete(business)
        self.db_session.commit()
        
        return True
    
    def add_service_to_business(self, business_id: UUID, service_config: ServiceConfiguration) -> Optional[BusinessService]:
        """Add a service to a business"""
        business = self.db_session.get(Business, business_id)
        if not business:
            return None
        
        service = BusinessService(
            business_id=business_id,
            service_id=service_config.service_id,
            name=service_config.name,
            description=service_config.description,
            category=service_config.category,
            workflow_pattern=service_config.workflow_pattern,
            workflow_steps=service_config.parameters_schema,
            parameters_schema=service_config.parameters_schema,
            availability_endpoint=service_config.availability_endpoint,
            cancellation_policy=service_config.cancellation_policy,
            payment_config=service_config.payment_config
        )
        
        self.db_session.add(service)
        self.db_session.commit()
        self.db_session.refresh(service)
        
        return service
    
    def create_api_key(self, request: APIKeyCreationRequest) -> Optional[BusinessAPIKey]:
        """Create API key for business"""
        business = self.db_session.get(Business, request.business_id)
        if not business:
            return None
        
        import hashlib
        import secrets
        
        key_value = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()
        
        api_key = BusinessAPIKey(
            business_id=request.business_id,
            key_name=request.key_name,
            key_hash=key_hash,
            key_prefix=key_value[:8],
            scopes=request.scopes,
            permissions=request.permissions or {},
            rate_limit_per_hour=request.rate_limit_per_hour,
            expires_at=request.expires_at
        )
        
        self.db_session.add(api_key)
        self.db_session.commit()
        self.db_session.refresh(api_key)
        
        return api_key
    
    def update_business_status(self, business_id: UUID, status: str) -> bool:
        """Update business status"""
        business = self.db_session.get(Business, business_id)
        if not business:
            return False
        
        business.status = status
        self.db_session.commit()
        
        return True
    
    def update_a2a_configuration(self, business_id: UUID, config: Dict[str, Any]) -> bool:
        """
        Update A2A configuration for business
        
        Args:
            business_id: Business identifier
            config: A2A configuration data
            
        Returns:
            True if update successful, False otherwise
        """
        business = self.db_session.get(Business, business_id)
        if not business:
            return False
        
        # Update A2A configuration
        business.a2a_enabled = config.get('enabled', False)
        business.a2a_endpoint = config.get('endpoint')
        business.a2a_capabilities = config.get('capabilities', [])
        
        self.db_session.commit()
        return True
    
    def update_mcp_configuration(self, business_id: UUID, config: Dict[str, Any]) -> bool:
        """
        Update MCP configuration for business
        
        Args:
            business_id: Business identifier
            config: MCP configuration data
            
        Returns:
            True if update successful, False otherwise
        """
        business = self.db_session.get(Business, business_id)
        if not business:
            return False
        
        # Update MCP configuration
        business.mcp_enabled = config.get('enabled', False)
        business.mcp_endpoint = config.get('endpoint')
        business.mcp_version = config.get('version', '2025-06-18')
        
        self.db_session.commit()
        return True
    
    def update_ap2_configuration(self, business_id: UUID, config: Dict[str, Any]) -> bool:
        """
        Update AP2 configuration for business
        
        Args:
            business_id: Business identifier
            config: AP2 configuration data
            
        Returns:
            True if update successful, False otherwise
        """
        business = self.db_session.get(Business, business_id)
        if not business:
            return False
        
        # Update AP2 configuration
        business.ap2_enabled = config.get('enabled', False)
        business.ap2_public_key = config.get('public_key')
        business.ap2_supported_payment_methods = config.get('supported_payment_methods', [])
        
        self.db_session.commit()
        return True
    
    def deactivate_api_key(self, business_id: UUID, api_key_id: UUID) -> bool:
        """Deactivate API key"""
        api_key = self.db_session.query(BusinessAPIKey).filter(
            BusinessAPIKey.id == api_key_id,
            BusinessAPIKey.business_id == business_id
        ).first()
        
        if not api_key:
            return False
        
        api_key.active = False
        self.db_session.commit()
        
        return True
    
    def update_service_configuration(
        self, 
        business_id: UUID, 
        service_id: str, 
        config: Dict[str, Any]
    ) -> bool:
        """Update service configuration"""
        service = self.db_session.query(BusinessService).filter(
            BusinessService.business_id == business_id,
            BusinessService.service_id == service_id
        ).first()
        
        if not service:
            return False
        
        # Update service configuration
        for key, value in config.items():
            if hasattr(service, key):
                setattr(service, key, value)
        
        self.db_session.commit()
        return True
    
    def create_business_with_services(
        self, 
        request: BusinessCreationRequest,
        services: list
    ) -> Business:
        """Create business with services in a transaction"""
        try:
            # Create business
            business = self.create_business(request)
            
            # Add services
            for service_config in services:
                self.add_service_to_business(business.id, service_config)
            
            return business
            
        except Exception as e:
            self.db_session.rollback()
            raise e
    
    def bulk_update_business_status(self, business_ids: list, status: str) -> int:
        """Bulk update business status"""
        updated_count = self.db_session.query(Business).filter(
            Business.id.in_(business_ids)
        ).update({Business.status: status}, synchronize_session=False)
        
        self.db_session.commit()
        return updated_count
    
    def archive_business(self, business_id: UUID) -> bool:
        """Archive business (soft delete)"""
        business = self.db_session.get(Business, business_id)
        if not business:
            return False
        
        business.status = "archived"
        business.archived_at = datetime.utcnow()
        
        # Deactivate all API keys
        self.db_session.query(BusinessAPIKey).filter(
            BusinessAPIKey.business_id == business_id
        ).update({BusinessAPIKey.active: False})
        
        self.db_session.commit()
        return True
    
    def restore_business(self, business_id: UUID) -> bool:
        """Restore archived business"""
        business = self.db_session.get(Business, business_id)
        if not business or business.status != "archived":
            return False
        
        business.status = "active"
        business.archived_at = None
        
        self.db_session.commit()
        return True