"""
Business Service - Handles business registration and status management

This module provides services for registering new businesses in the BAIS system,
validating their schemas, and managing their operational status.
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
from ..core.database_models import DatabaseManager, BusinessRepository
from ..core.bais_schema_validator import BAISSchemaValidator
from ..utils.schema_factory import BusinessSchemaFactory
from ..core.exceptions import (
    BusinessRegistrationError,
    SchemaValidationError,
    BusinessNotFoundError,
    DatabaseError
)


class BusinessServiceError(Exception):
    """Base exception for business service operations"""
    pass


class BusinessRegistrationError(BusinessServiceError):
    """Raised when business registration fails"""
    pass


class BusinessNotFoundError(BusinessServiceError):
    """Raised when a business is not found"""
    pass


class SchemaValidationError(BusinessServiceError):
    """Raised when schema validation fails"""
    pass


class BusinessService:
    """
    Service for managing business registrations and status.
    
    This service handles the complete lifecycle of business registration,
    including schema validation, API key generation, and server setup.
    """
    
    def __init__(self, db_manager: DatabaseManager, background_tasks: BackgroundTasks):
        """
        Initialize the business service.
        
        Args:
            db_manager: Database manager for persistence operations
            background_tasks: FastAPI background tasks for async operations
        """
        self.db_manager = db_manager
        self.background_tasks = background_tasks
        self._business_repository = BusinessRepository(db_manager)
    
    async def register_business(self, request: BusinessRegistrationRequest) -> BusinessRegistrationResponse:
        """
        Register a new business in the BAIS system.
        
        This method orchestrates the complete business registration workflow
        by delegating to focused, single-responsibility methods.
        
        Args:
            request: Business registration request containing business details
            
        Returns:
            BusinessRegistrationResponse with registration details
            
        Raises:
            HTTPException: If schema validation fails or registration encounters errors
        """
        try:
            # Step 1: Create and validate business schema
            schema = await self._create_and_validate_schema(request)
            
            # Step 2: Generate secure API key
            api_key = self._generate_secure_api_key(schema.business_info.id)
            
            # Step 3: Persist business data
            await self._persist_business_data(schema, api_key)
            
            # Step 4: Schedule server setup
            self._schedule_server_setup(schema)
            
            # Step 5: Build and return response
            return self._build_registration_response(schema, api_key)
            
        except BusinessRegistrationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    
    async def _create_and_validate_schema(self, request: BusinessRegistrationRequest):
        """Create business schema and validate it against BAIS standards."""
        schema = self._create_business_schema(request)
        self._validate_business_schema(schema)
        return schema
    
    async def get_business_status(self, business_id: str) -> BusinessStatusResponse:
        """
        Retrieve the current status and metrics for a business.
        
        Args:
            business_id: Unique identifier for the business
            
        Returns:
            BusinessStatusResponse with current status and metrics
            
        Raises:
            HTTPException: If business is not found or status retrieval fails
        """
        try:
            business_data = await self._business_repository.get_business_by_id(business_id)
            if not business_data:
                raise BusinessNotFoundError(f"Business {business_id} not found")
            
            metrics = await self._gather_business_metrics(business_id)
            
            return BusinessStatusResponse(
                business_id=business_id,
                name=business_data.name,
                status=business_data.status,
                services_enabled=len(business_data.services),
                mcp_server_active=business_data.mcp_server_active,
                a2a_server_active=business_data.a2a_server_active,
                last_updated=datetime.utcnow(),
                metrics=metrics
            )
            
        except BusinessNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")
    
    def _create_business_schema(self, registration_request: BusinessRegistrationRequest):
        """Create a business schema from the registration request."""
        return BusinessSchemaFactory.create_from_request(registration_request)
    
    def _validate_business_schema(self, business_schema) -> None:
        """Validate the business schema against BAIS standards."""
        try:
            is_valid, validation_issues = BAISSchemaValidator.validate_schema(business_schema.dict())
            if not is_valid:
                raise SchemaValidationError(f"Invalid business schema: {'; '.join(validation_issues)}")
        except Exception as validation_error:
            if isinstance(validation_error, SchemaValidationError):
                raise
            raise SchemaValidationError(f"Schema validation failed: {str(validation_error)}")
    
    def _generate_secure_api_key(self, business_id: str) -> str:
        """
        Generate a cryptographically secure API key for the business.
        
        The API key is generated using SHA-256 hash of:
        - Business ID
        - Current timestamp
        - Random UUID
        
        This ensures uniqueness and prevents key collisions.
        """
        timestamp = datetime.utcnow().isoformat()
        random_uuid = str(uuid.uuid4())
        data = f"{business_id}:{timestamp}:{random_uuid}".encode()
        return hashlib.sha256(data).hexdigest()
    
    async def _persist_business_data(self, business_schema, generated_api_key: str) -> None:
        """Persist business data to the database."""
        # Implementation would save to database here
        # For now, this is a placeholder for the actual persistence logic
        pass
    
    def _schedule_server_setup(self, business_schema) -> None:
        """Schedule background task for server setup."""
        # Implementation would add background task here
        # self.background_tasks.add_task(setup_business_servers, business_schema)
        pass
    
    def _build_registration_response(self, business_schema, generated_api_key: str) -> BusinessRegistrationResponse:
        """Build the registration response."""
        return BusinessRegistrationResponse(
            business_id=business_schema.business_info.id,
            status="registered",
            mcp_endpoint=business_schema.integration.mcp_server.endpoint,
            a2a_endpoint=business_schema.integration.a2a_endpoint.discovery_url,
            api_keys={"primary": generated_api_key},
            setup_complete=False  # Will be updated by background task
        )
    
    async def _gather_business_metrics(self, business_id: str) -> Dict[str, Any]:
        """Gather current metrics for the business."""
        # Implementation would gather real metrics from monitoring systems
        return {
            "total_interactions": 156,
            "successful_bookings": 23,
            "revenue_today": 2847.50,
            "avg_response_time_ms": 145
        }