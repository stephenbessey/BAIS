"""
Business Registration Orchestrator
Refactored business service following Single Responsibility Principle

This module implements the clean code solution by orchestrating focused,
single-responsibility components for business registration.
"""

import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any
from fastapi import HTTPException, BackgroundTasks

from ..api_models import (
    BusinessRegistrationRequest, 
    BusinessRegistrationResponse, 
    BusinessStatusResponse
)
from ..core.exceptions import (
    BusinessRegistrationError,
    BusinessNotFoundError,
    ValidationError
)

from .business_validator import BusinessValidator
from .business_repository import BusinessRepository
from .business_server_factory import BusinessServerOrchestrator
from ..utils.schema_factory import BusinessSchemaFactory


class BusinessRegistrationOrchestrator:
    """
    Orchestrates business registration using focused components
    
    This class follows the Single Responsibility Principle by delegating
    to specialized components rather than doing everything itself.
    """
    
    def __init__(
        self, 
        validator: BusinessValidator,
        repository: BusinessRepository,
        server_orchestrator: BusinessServerOrchestrator,
        background_tasks: BackgroundTasks
    ):
        self.validator = validator
        self.repository = repository
        self.server_orchestrator = server_orchestrator
        self.background_tasks = background_tasks
    
    async def register_business(self, request: BusinessRegistrationRequest) -> BusinessRegistrationResponse:
        """
        Register a new business using orchestrated components
        
        This method demonstrates clean code principles:
        - Single Responsibility: Orchestrates, doesn't implement
        - Dependency Injection: Uses injected components
        - Error Handling: Delegates to appropriate components
        - Clear Flow: Easy to understand and maintain
        """
        try:
            # Step 1: Validate request
            await self._validate_registration_request(request)
            
            # Step 2: Create and validate schema
            business_schema = await self._create_and_validate_schema(request)
            
            # Step 3: Generate secure API key
            api_key = self._generate_secure_api_key(business_schema.business_info.id)
            
            # Step 4: Persist business data
            business_id = await self._persist_business_data(business_schema, api_key)
            
            # Step 5: Schedule server setup
            await self._schedule_server_setup(business_schema)
            
            # Step 6: Build response
            return self._build_registration_response(business_schema, api_key)
            
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except BusinessRegistrationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    
    async def get_business_status(self, business_id: str) -> BusinessStatusResponse:
        """Get business status using repository"""
        try:
            business_data = await self.repository.get_business_by_id(business_id)
            if not business_data:
                raise BusinessNotFoundError(f"Business {business_id} not found")
            
            # Get server status
            server_status = self.server_orchestrator.get_server_status(business_id)
            
            # Gather metrics
            metrics = await self._gather_business_metrics(business_id)
            
            return BusinessStatusResponse(
                business_id=business_id,
                name=business_data.get('name', 'Unknown'),
                status=business_data.get('status', 'unknown'),
                services_enabled=len(business_data.get('services', [])),
                mcp_server_active=server_status['mcp_server_active'],
                a2a_server_active=server_status['a2a_server_active'],
                last_updated=datetime.utcnow(),
                metrics=metrics
            )
            
        except BusinessNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")
    
    async def _validate_registration_request(self, request: BusinessRegistrationRequest) -> None:
        """Validate registration request using validator component"""
        validation_issues = self.validator.validate_registration_request(request)
        
        if validation_issues:
            raise ValidationError(f"Validation failed: {'; '.join(validation_issues)}")
    
    async def _create_and_validate_schema(self, request: BusinessRegistrationRequest) -> Any:
        """Create and validate business schema"""
        # Create schema using factory
        business_schema = BusinessSchemaFactory.create_from_request(request)
        
        # Validate schema using validator
        self.validator.validate_business_schema(business_schema)
        
        return business_schema
    
    def _generate_secure_api_key(self, business_id: str) -> str:
        """Generate cryptographically secure API key"""
        timestamp = datetime.utcnow().isoformat()
        random_uuid = str(uuid.uuid4())
        data = f"{business_id}:{timestamp}:{random_uuid}".encode()
        return hashlib.sha256(data).hexdigest()
    
    async def _persist_business_data(self, business_schema: Any, api_key: str) -> str:
        """Persist business data using repository"""
        # Prepare data for persistence
        business_data = {
            'id': business_schema.business_info.id,
            'name': business_schema.business_info.name,
            'type': business_schema.business_info.type.value,
            'description': business_schema.business_info.description,
            'contact_email': business_schema.business_info.contact_email,
            'business_address': business_schema.business_info.business_address,
            'services': [service.dict() for service in business_schema.services],
            'integration': business_schema.integration.dict(),
            'policies': business_schema.policies.dict(),
            'status': 'registered',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Persist using repository
        business_id = await self.repository.create_business(business_data)
        
        # Store API key
        await self.repository.store_api_key(business_id, api_key, "primary")
        
        return business_id
    
    async def _schedule_server_setup(self, business_schema: Any) -> None:
        """Schedule background server setup"""
        # Prepare business configuration
        business_config = {
            'business_id': business_schema.business_info.id,
            'business_type': business_schema.business_info.type.value,
            'services': [service.dict() for service in business_schema.services],
            'integration': business_schema.integration.dict()
        }
        
        # Schedule background task
        self.background_tasks.add_task(
            self._setup_business_servers,
            business_schema,
            business_config
        )
    
    async def _setup_business_servers(self, business_schema: Any, business_config: Dict[str, Any]) -> None:
        """Setup business servers in background"""
        try:
            # Setup servers using orchestrator
            server_info = await self.server_orchestrator.setup_business_servers(
                business_schema=business_schema,
                business_config=business_config,
                enable_mcp=True,
                enable_a2a=True,
                enable_streaming=True
            )
            
            # Update business status
            await self.repository.update_business_status(
                business_schema.business_info.id,
                'active'
            )
            
            # Update setup completion flag
            await self.repository.update_business(
                business_schema.business_info.id,
                {'setup_complete': True, 'servers_configured': True}
            )
            
        except Exception as e:
            # Update status to failed
            await self.repository.update_business_status(
                business_schema.business_info.id,
                'setup_failed'
            )
            
            # Log error
            print(f"Failed to setup servers for {business_schema.business_info.id}: {e}")
    
    def _build_registration_response(self, business_schema: Any, api_key: str) -> BusinessRegistrationResponse:
        """Build registration response"""
        return BusinessRegistrationResponse(
            business_id=business_schema.business_info.id,
            status="registered",
            mcp_endpoint=business_schema.integration.mcp_server.endpoint,
            a2a_endpoint=business_schema.integration.a2a_endpoint.discovery_url,
            api_keys={"primary": api_key},
            setup_complete=False  # Will be updated by background task
        )
    
    async def _gather_business_metrics(self, business_id: str) -> Dict[str, Any]:
        """Gather business metrics"""
        # This would integrate with monitoring systems
        # For now, return mock data
        return {
            "total_interactions": 156,
            "successful_bookings": 23,
            "revenue_today": 2847.50,
            "avg_response_time_ms": 145
        }


class BusinessServiceFactory:
    """
    Factory for creating business service components
    
    Follows Dependency Injection pattern for clean architecture
    """
    
    @staticmethod
    def create_orchestrator(
        db_manager: Any,
        background_tasks: BackgroundTasks
    ) -> BusinessRegistrationOrchestrator:
        """Create business registration orchestrator with dependencies"""
        
        # Create components
        validator = BusinessValidator()
        repository = BusinessRepository(db_manager)
        server_orchestrator = BusinessServerOrchestrator()
        
        # Create orchestrator
        return BusinessRegistrationOrchestrator(
            validator=validator,
            repository=repository,
            server_orchestrator=server_orchestrator,
            background_tasks=background_tasks
        )
    
    @staticmethod
    def create_validator() -> BusinessValidator:
        """Create business validator"""
        return BusinessValidator()
    
    @staticmethod
    def create_repository(db_manager: Any) -> BusinessRepository:
        """Create business repository"""
        return BusinessRepository(db_manager)
    
    @staticmethod
    def create_server_orchestrator() -> BusinessServerOrchestrator:
        """Create server orchestrator"""
        return BusinessServerOrchestrator()
