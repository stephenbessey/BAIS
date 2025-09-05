"""
BAIS Database Models & Persistence Layer
Production-grade database schema with SQLAlchemy models
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy import create_engine, event
from datetime import datetime
import uuid
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import json

Base = declarative_base()

class Business(Base):
    """Business entity with BAIS integration"""
    __tablename__ = "businesses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    business_type = Column(String(50), nullable=False, index=True)
    description = Column(Text)
    
    # Location data
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False)
    postal_code = Column(String(20))
    country = Column(String(5), default="US")
    latitude = Column(Float)
    longitude = Column(Float)
    timezone = Column(String(50), default="UTC")
    
    # Contact information
    website = Column(String(255))
    phone = Column(String(20))
    email = Column(String(255))
    
    # Business metadata
    established_date = Column(DateTime)
    capacity = Column(Integer)
    
    # BAIS configuration
    bais_version = Column(String(10), default="1.0")
    schema_version = Column(String(20), default="1.0.0")
    mcp_endpoint = Column(String(255), nullable=False)
    a2a_endpoint = Column(String(255), nullable=False)
    webhook_endpoint = Column(String(255))
    
    # Status and metadata
    status = Column(String(20), default="active", index=True)
    compliance_flags = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    services = relationship("BusinessService", back_populates="business", cascade="all, delete-orphan")
    api_keys = relationship("BusinessAPIKey", back_populates="business", cascade="all, delete-orphan")
    oauth_clients = relationship("OAuthClient", back_populates="business", cascade="all, delete-orphan")
    agent_interactions = relationship("AgentInteraction", back_populates="business")
    bookings = relationship("Booking", back_populates="business")
    
    __table_args__ = (
        Index('idx_business_location', 'city', 'state'),
        Index('idx_business_type_status', 'business_type', 'status'),
        CheckConstraint('latitude >= -90 AND latitude <= 90', name='valid_latitude'),
        CheckConstraint('longitude >= -180 AND longitude <= 180', name='valid_longitude'),
    )

class BusinessService(Base):
    """Business service with BAIS schema"""
    __tablename__ = "business_services"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    service_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    
    # Service configuration
    workflow_pattern = Column(String(50), nullable=False)
    workflow_steps = Column(JSONB, nullable=False)
    parameters_schema = Column(JSONB, nullable=False)
    
    # Availability configuration
    availability_endpoint = Column(String(255), nullable=False)
    real_time_availability = Column(Boolean, default=True)
    cache_timeout_seconds = Column(Integer, default=300)
    advance_booking_days = Column(Integer, default=365)
    
    # Policies
    cancellation_policy = Column(JSONB, nullable=False)
    payment_config = Column(JSONB, nullable=False)
    modification_fee = Column(Float, default=0.0)
    no_show_penalty = Column(Float, default=0.0)
    
    # Service status
    enabled = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="services")
    bookings = relationship("Booking", back_populates="service")
    
    __table_args__ = (
        UniqueConstraint('business_id', 'service_id', name='unique_business_service'),
        Index('idx_service_category_enabled', 'category', 'enabled'),
    )

class BusinessAPIKey(Base):
    """API keys for business authentication"""
    __tablename__ = "business_api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    key_name = Column(String(100), nullable=False)
    key_hash = Column(String(128), nullable=False, unique=True, index=True)
    key_prefix = Column(String(8), nullable=False)
    
    # Permissions and scope
    scopes = Column(ARRAY(String), nullable=False)
    permissions = Column(JSONB, default=dict)
    
    # Key metadata
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)
    rate_limit_per_hour = Column(Integer, default=1000)
    
    # Status
    active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    business = relationship("Business", back_populates="api_keys")
    
    __table_args__ = (
        UniqueConstraint('business_id', 'key_name', name='unique_business_key_name'),
        Index('idx_api_key_active_expires', 'active', 'expires_at'),
    )

class OAuthClient(Base):
    """OAuth 2.0 clients for businesses"""
    __tablename__ = "oauth_clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    client_id = Column(String(255), unique=True, nullable=False, index=True)
    client_secret_hash = Column(String(128), nullable=False)
    client_name = Column(String(255), nullable=False)
    
    # OAuth configuration
    redirect_uris = Column(ARRAY(String), nullable=False)
    allowed_scopes = Column(ARRAY(String), nullable=False)
    grant_types = Column(ARRAY(String), nullable=False)
    response_types = Column(ARRAY(String), nullable=False)
    
    # Client metadata
    is_confidential = Column(Boolean, default=True)
    active = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="oauth_clients")
    access_tokens = relationship("OAuthAccessToken", back_populates="client", cascade="all, delete-orphan")
    
class OAuthAccessToken(Base):
    """OAuth 2.0 access tokens"""
    __tablename__ = "oauth_access_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(255), ForeignKey("oauth_clients.client_id"), nullable=False)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    
    # Token data
    scopes = Column(ARRAY(String), nullable=False)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    agent_id = Column(String(255))
    
    # Token lifecycle
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked = Column(Boolean, default=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("OAuthClient", back_populates="access_tokens")
    
    __table_args__ = (
        Index('idx_token_expires_revoked', 'expires_at', 'revoked'),
    )

class AgentInteraction(Base):
    """Agent interactions with business services"""
    __tablename__ = "agent_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("business_services.id"))
    
    # Agent information
    agent_id = Column(String(255), nullable=False, index=True)
    agent_type = Column(String(100), index=True)
    client_id = Column(String(255))
    
    # Interaction details
    interaction_type = Column(String(50), nullable=False, index=True)
    protocol_used = Column(String(20), nullable=False)  # 'mcp' or 'a2a'
    request_data = Column(JSONB, nullable=False)
    response_data = Column(JSONB)
    
    # Outcome tracking
    status = Column(String(20), nullable=False, index=True)
    error_message = Column(Text)
    processing_time_ms = Column(Integer)
    
    # Metrics
    tokens_used = Column(Integer)
    cost_cents = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    business = relationship("Business", back_populates="agent_interactions")
    
    __table_args__ = (
        Index('idx_interaction_business_agent', 'business_id', 'agent_id'),
        Index('idx_interaction_status_created', 'status', 'created_at'),
        Index('idx_interaction_type_protocol', 'interaction_type', 'protocol_used'),
    )

class Booking(Base):
    """Bookings created through BAIS"""
    __tablename__ = "bookings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("business_services.id"), nullable=False)
    
    # Booking identification
    confirmation_number = Column(String(50), unique=True, nullable=False, index=True)
    external_booking_id = Column(String(255))  # ID in business's own system
    
    # Agent and customer information
    agent_id = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False, index=True)
    customer_phone = Column(String(20))
    
    # Booking details
    booking_data = Column(JSONB, nullable=False)
    service_date = Column(DateTime, index=True)
    check_in = Column(DateTime, index=True)
    check_out = Column(DateTime, index=True)
    guests = Column(Integer)
    
    # Financial information
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    payment_status = Column(String(20), default="pending", index=True)
    payment_data = Column(JSONB)
    
    # Booking lifecycle
    status = Column(String(20), default="confirmed", nullable=False, index=True)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime, index=True)
    
    # Relationships
    business = relationship("Business", back_populates="bookings")
    service = relationship("BusinessService", back_populates="bookings")
    
    __table_args__ = (
        Index('idx_booking_business_status', 'business_id', 'status'),
        Index('idx_booking_service_date', 'service_date'),
        Index('idx_booking_customer_email', 'customer_email'),
        CheckConstraint('total_amount >= 0', name='positive_amount'),
    )

class BusinessMetrics(Base):
    """Aggregated business metrics"""
    __tablename__ = "business_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    # Time period
    metric_date = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(10), nullable=False)  # 'hour', 'day', 'week', 'month'
    
    # Interaction metrics
    total_interactions = Column(Integer, default=0)
    successful_interactions = Column(Integer, default=0)
    failed_interactions = Column(Integer, default=0)
    avg_response_time_ms = Column(Float)
    
    # Booking metrics
    total_bookings = Column(Integer, default=0)
    confirmed_bookings = Column(Integer, default=0)
    cancelled_bookings = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    
    # Agent metrics
    unique_agents = Column(Integer, default=0)
    mcp_interactions = Column(Integer, default=0)
    a2a_interactions = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('business_id', 'metric_date', 'period_type', name='unique_business_metric'),
        Index('idx_metrics_business_date', 'business_id', 'metric_date'),
    )

# Database session management
class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Setup database event listeners"""
        
        @event.listens_for(Business, 'before_update')
        def business_before_update(mapper, connection, target):
            target.updated_at = datetime.utcnow()
        
        @event.listens_for(BusinessService, 'before_update')
        def service_before_update(mapper, connection, target):
            target.updated_at = datetime.utcnow()
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def close(self):
        """Close database connections"""
        self.engine.dispose()

# Repository pattern for clean data access
class BusinessRepository:
    """Repository for business data operations"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_business(self, business_data: Dict[str, Any]) -> Business:
        """Create new business"""
        business = Business(**business_data)
        self.db.add(business)
        self.db.commit()
        self.db.refresh(business)
        return business
    
    def get_business(self, business_id: uuid.UUID) -> Optional[Business]:
        """Get business by ID"""
        return self.db.query(Business).filter(Business.id == business_id).first()
    
    def get_business_by_external_id(self, external_id: str) -> Optional[Business]:
        """Get business by external ID"""
        return self.db.query(Business).filter(Business.external_id == external_id).first()
    
    def update_business(self, business_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[Business]:
        """Update business"""
        business = self.get_business(business_id)
        if business:
            for key, value in update_data.items():
                setattr(business, key, value)
            self.db.commit()
            self.db.refresh(business)
        return business
    
    def list_businesses(self, 
                       business_type: Optional[str] = None,
                       status: Optional[str] = None,
                       city: Optional[str] = None,
                       limit: int = 100,
                       offset: int = 0) -> List[Business]:
        """List businesses with filters"""
        query = self.db.query(Business)
        
        if business_type:
            query = query.filter(Business.business_type == business_type)
        if status:
            query = query.filter(Business.status == status)
        if city:
            query = query.filter(Business.city.ilike(f"%{city}%"))
        
        return query.offset(offset).limit(limit).all()
    
    def delete_business(self, business_id: uuid.UUID) -> bool:
        """Delete business"""
        business = self.get_business(business_id)
        if business:
            self.db.delete(business)
            self.db.commit()
            return True
        return False

class ServiceRepository:
    """Repository for service data operations"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_service(self, service_data: Dict[str, Any]) -> BusinessService:
        """Create new service"""
        service = BusinessService(**service_data)
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service
    
    def get_services_by_business(self, business_id: uuid.UUID) -> List[BusinessService]:
        """Get all services for a business"""
        return self.db.query(BusinessService).filter(
            BusinessService.business_id == business_id,
            BusinessService.enabled == True
        ).all()
    
    def get_service(self, service_id: uuid.UUID) -> Optional[BusinessService]:
        """Get service by ID"""
        return self.db.query(BusinessService).filter(BusinessService.id == service_id).first()
    
    def update_service(self, service_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[BusinessService]:
        """Update service"""
        service = self.get_service(service_id)
        if service:
            for key, value in update_data.items():
                setattr(service, key, value)
            self.db.commit()
            self.db.refresh(service)
        return service

class BookingRepository:
    """Repository for booking data operations"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_booking(self, booking_data: Dict[str, Any]) -> Booking:
        """Create new booking"""
        booking = Booking(**booking_data)
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking
    
    def get_booking(self, booking_id: uuid.UUID) -> Optional[Booking]:
        """Get booking by ID"""
        return self.db.query(Booking).filter(Booking.id == booking_id).first()
    
    def get_booking_by_confirmation(self, confirmation_number: str) -> Optional[Booking]:
        """Get booking by confirmation number"""
        return self.db.query(Booking).filter(
            Booking.confirmation_number == confirmation_number
        ).first()
    
    def get_bookings_by_business(self, 
                                business_id: uuid.UUID,
                                status: Optional[str] = None,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> List[Booking]:
        """Get bookings for a business with filters"""
        query = self.db.query(Booking).filter(Booking.business_id == business_id)
        
        if status:
            query = query.filter(Booking.status == status)
        if start_date:
            query = query.filter(Booking.created_at >= start_date)
        if end_date:
            query = query.filter(Booking.created_at <= end_date)
        
        return query.order_by(Booking.created_at.desc()).all()

class MetricsRepository:
    """Repository for metrics and analytics"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def record_interaction(self, interaction_data: Dict[str, Any]) -> AgentInteraction:
        """Record agent interaction"""
        interaction = AgentInteraction(**interaction_data)
        self.db.add(interaction)
        self.db.commit()
        self.db.refresh(interaction)
        return interaction
    
    def get_business_metrics(self, 
                           business_id: uuid.UUID,
                           period_type: str = "day",
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[BusinessMetrics]:
        """Get business metrics"""
        query = self.db.query(BusinessMetrics).filter(
            BusinessMetrics.business_id == business_id,
            BusinessMetrics.period_type == period_type
        )
        
        if start_date:
            query = query.filter(BusinessMetrics.metric_date >= start_date)
        if end_date:
            query = query.filter(BusinessMetrics.metric_date <= end_date)
        
        return query.order_by(BusinessMetrics.metric_date.desc()).all()
    
    def aggregate_daily_metrics(self, business_id: uuid.UUID, date: datetime):
        """Aggregate daily metrics for a business"""
        # This would typically be run by a background job
        # Implementation would calculate daily totals from interaction and booking data
        pass

# Database initialization
def init_database(database_url: str) -> DatabaseManager:
    """Initialize database with connection and tables"""
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager

# Example usage and data seeding
async def seed_sample_data(db_manager: DatabaseManager):
    """Seed database with sample data for testing"""
    
    with db_manager.get_session() as session:
        business_repo = BusinessRepository(session)
        service_repo = ServiceRepository(session)
        
        # Create sample hotel
        hotel_data = {
            "external_id": "zion-adventure-lodge",
            "name": "Zion Adventure Lodge",
            "business_type": "hospitality",
            "description": "Luxury lodge near Zion National Park",
            "address": "123 Canyon View Dr",
            "city": "Springdale",
            "state": "UT",
            "postal_code": "84767",
            "latitude": 37.1889,
            "longitude": -112.9856,
            "website": "https://zionadventure.com",
            "phone": "+1-435-123-4567",
            "email": "reservations@zionadventure.com",
            "capacity": 47,
            "mcp_endpoint": "https://api.zionadventure.com/mcp",
            "a2a_endpoint": "https://api.zionadventure.com/.well-known/agent.json"
        }
        
        hotel = business_repo.create_business(hotel_data)
        
        # Create sample service
        service_data = {
            "business_id": hotel.id,
            "service_id": "room_booking",
            "name": "Hotel Room Reservation",
            "description": "Book hotel rooms with various amenities",
            "category": "accommodation",
            "workflow_pattern": "booking_confirmation_payment",
            "workflow_steps": [
                {"step": "availability_check", "description": "Check room availability"},
                {"step": "reservation", "description": "Create reservation"},
                {"step": "payment", "description": "Process payment"},
                {"step": "confirmation", "description": "Send confirmation"}
            ],
            "parameters_schema": {
                "check_in": {"type": "string", "format": "date", "required": True},
                "check_out": {"type": "string", "format": "date", "required": True},
                "guests": {"type": "integer", "minimum": 1, "maximum": 6, "default": 2}
            },
            "availability_endpoint": "/api/v1/availability",
            "cancellation_policy": {
                "type": "flexible",
                "free_until_hours": 24,
                "penalty_percentage": 0,
                "description": "Free cancellation up to 24 hours before check-in"
            },
            "payment_config": {
                "methods": ["credit_card", "debit_card"],
                "timing": "at_booking",
                "processing": "secure_tokenized"
            }
        }
        
        service_repo.create_service(service_data)
        
        print(f"Created sample business: {hotel.name} (ID: {hotel.id})")

if __name__ == "__main__":
    # Example usage
    DATABASE_URL = "postgresql://user:password@localhost/bais_db"
    
    db_manager = init_database(DATABASE_URL)
    
    # Seed sample data
    import asyncio
    asyncio.run(seed_sample_data(db_manager))