"""
Business Service - Refactored using Single Responsibility Principle

This module now uses the BusinessRegistrationOrchestrator pattern to follow
clean code principles and separate concerns.
"""

from typing import Dict, Any
from fastapi import HTTPException, BackgroundTasks

from ..api_models import (
    BusinessRegistrationRequest, 
    BusinessRegistrationResponse, 
    BusinessStatusResponse
)
from ..core.database_models import DatabaseManager
from .business_registration_orchestrator import BusinessServiceFactory


class BusinessService:
    """
    Refactored Business Service using Single Responsibility Principle
    
    This service now delegates to specialized components following clean code principles:
    - Single Responsibility: Each component has one job
    - Dependency Injection: Components are injected, not created
    - Open/Closed: Easy to extend without modifying existing code
    """
    
    def __init__(self, db_manager: DatabaseManager, background_tasks: BackgroundTasks):
        """
        Initialize the business service with clean architecture.
        
        Args:
            db_manager: Database manager for persistence operations
            background_tasks: FastAPI background tasks for async operations
        """
        # Create orchestrator using factory pattern
        self.orchestrator = BusinessServiceFactory.create_orchestrator(
            db_manager=db_manager,
            background_tasks=background_tasks
        )
    
    async def register_business(self, request: BusinessRegistrationRequest) -> BusinessRegistrationResponse:
        """
        Register a new business using the orchestrator pattern.
        
        This method now delegates to a focused orchestrator that coordinates
        specialized components, following clean code principles.
        
        Args:
            request: Business registration request containing business details
            
        Returns:
            BusinessRegistrationResponse with registration details
            
        Raises:
            HTTPException: If registration fails
        """
        return await self.orchestrator.register_business(request)
    
    async def get_business_status(self, business_id: str) -> BusinessStatusResponse:
        """
        Get business status using the orchestrator pattern.
        
        Args:
            business_id: Unique identifier for the business
            
        Returns:
            BusinessStatusResponse with current status and metrics
            
        Raises:
            HTTPException: If business is not found or status retrieval fails
        """
        return await self.orchestrator.get_business_status(business_id)