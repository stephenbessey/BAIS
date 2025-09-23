"""
Business Query Repository
Handles read operations for business entities following CQRS pattern
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from .database_models import Business, BusinessService, BusinessAPIKey
from .parameter_objects import BusinessSearchCriteria


class BusinessQueryRepository:
    """Repository for business read operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def find_by_id(self, business_id: UUID) -> Optional[Business]:
        """Find business by ID"""
        return self.db_session.get(Business, business_id)
    
    def find_by_external_id(self, external_id: str) -> Optional[Business]:
        """Find business by external ID"""
        return self.db_session.query(Business).filter(
            Business.external_id == external_id
        ).first()
    
    def search_businesses(self, criteria: BusinessSearchCriteria) -> List[Business]:
        """Search businesses with criteria"""
        query = self.db_session.query(Business)
        
        # Apply filters
        if criteria.business_type:
            query = query.filter(Business.business_type == criteria.business_type)
        
        if criteria.status:
            query = query.filter(Business.status == criteria.status)
        
        if criteria.city:
            query = query.filter(Business.city.ilike(f"%{criteria.city}%"))
        
        # Apply pagination
        query = query.offset(criteria.offset).limit(criteria.limit)
        
        return query.all()
    
    def find_by_location(self, city: str, state: str = None) -> List[Business]:
        """Find businesses by location"""
        query = self.db_session.query(Business).filter(Business.city.ilike(f"%{city}%"))
        
        if state:
            query = query.filter(Business.state == state)
        
        return query.all()
    
    def find_active_businesses(self) -> List[Business]:
        """Find all active businesses"""
        return self.db_session.query(Business).filter(
            Business.status == "active"
        ).all()
    
    def find_businesses_by_type(self, business_type: str) -> List[Business]:
        """Find businesses by type"""
        return self.db_session.query(Business).filter(
            and_(
                Business.business_type == business_type,
                Business.status == "active"
            )
        ).all()
    
    def get_business_services(self, business_id: UUID) -> List[BusinessService]:
        """Get all services for a business"""
        return self.db_session.query(BusinessService).filter(
            BusinessService.business_id == business_id
        ).all()
    
    def get_business_service_by_id(self, business_id: UUID, service_id: str) -> Optional[BusinessService]:
        """Get specific service for a business"""
        return self.db_session.query(BusinessService).filter(
            and_(
                BusinessService.business_id == business_id,
                BusinessService.service_id == service_id
            )
        ).first()
    
    def get_business_api_keys(self, business_id: UUID) -> List[BusinessAPIKey]:
        """Get all API keys for a business"""
        return self.db_session.query(BusinessAPIKey).filter(
            and_(
                BusinessAPIKey.business_id == business_id,
                BusinessAPIKey.active == True
            )
        ).all()
    
    def find_api_key_by_hash(self, key_hash: str) -> Optional[BusinessAPIKey]:
        """Find API key by hash"""
        return self.db_session.query(BusinessAPIKey).filter(
            and_(
                BusinessAPIKey.key_hash == key_hash,
                BusinessAPIKey.active == True
            )
        ).first()
    
    def get_business_count(self) -> int:
        """Get total number of businesses"""
        return self.db_session.query(Business).count()
    
    def get_business_count_by_type(self, business_type: str) -> int:
        """Get count of businesses by type"""
        return self.db_session.query(Business).filter(
            Business.business_type == business_type
        ).count()
    
    def get_business_count_by_status(self, status: str) -> int:
        """Get count of businesses by status"""
        return self.db_session.query(Business).filter(
            Business.status == status
        ).count()
    
    def find_businesses_with_services(self) -> List[Business]:
        """Find businesses that have services configured"""
        return self.db_session.query(Business).join(BusinessService).distinct().all()
    
    def find_businesses_by_service_category(self, category: str) -> List[Business]:
        """Find businesses that have services in a specific category"""
        return self.db_session.query(Business).join(BusinessService).filter(
            BusinessService.category == category
        ).distinct().all()
    
    def find_businesses_with_a2a_capabilities(self, capabilities: List[str]) -> List[Business]:
        """
        Find businesses with specific A2A capabilities
        
        Args:
            capabilities: List of A2A capabilities to search for
            
        Returns:
            List of businesses with matching capabilities
        """
        # This would implement actual A2A capability search
        # For now, return businesses that have A2A integration enabled
        return self.db_session.query(Business).filter(
            Business.a2a_enabled == True
        ).all()
    
    def find_businesses_with_ap2_integration(self) -> List[Business]:
        """Find businesses with AP2 payment integration enabled"""
        return self.db_session.query(Business).filter(
            Business.ap2_enabled == True
        ).all()
    
    def get_business_metrics(self, business_id: UUID) -> Optional[dict]:
        """Get business metrics and statistics"""
        business = self.find_by_id(business_id)
        if not business:
            return None
        
        # Get service count
        service_count = len(self.get_business_services(business_id))
        
        # Get API key count
        api_keys = self.get_business_api_keys(business_id)
        
        return {
            'service_count': service_count,
            'active_api_keys': len(api_keys),
            'created_at': business.created_at,
            'last_updated': business.updated_at,
            'status': business.status
        }
    
    def search_businesses_by_name(self, name_query: str, limit: int = 50) -> List[Business]:
        """Search businesses by name"""
        return self.db_session.query(Business).filter(
            Business.name.ilike(f"%{name_query}%")
        ).limit(limit).all()
    
    def get_recently_registered_businesses(self, days: int = 7, limit: int = 20) -> List[Business]:
        """Get recently registered businesses"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return self.db_session.query(Business).filter(
            Business.created_at >= cutoff_date
        ).order_by(Business.created_at.desc()).limit(limit).all()
    
    def find_businesses_by_integration_type(self, integration_type: str) -> List[Business]:
        """Find businesses by integration type"""
        # This would search based on integration configuration
        # For now, return businesses with specific integration flags
        if integration_type == "mcp":
            return self.db_session.query(Business).filter(
                Business.mcp_enabled == True
            ).all()
        elif integration_type == "a2a":
            return self.db_session.query(Business).filter(
                Business.a2a_enabled == True
            ).all()
        elif integration_type == "ap2":
            return self.db_session.query(Business).filter(
                Business.ap2_enabled == True
            ).all()
        else:
            return []