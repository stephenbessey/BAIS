"""
Business Command Repository
Handles write operations for business entities following CQRS pattern
"""

from typing import Dict, Any, Optional
from uuid import UUID
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
