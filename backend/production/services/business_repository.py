"""
Business Repository
Handles business data persistence following Single Responsibility Principle

This module extracts data persistence logic from BusinessService to follow
the Single Responsibility Principle and implement proper repository patterns.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
from ..core.database_models import DatabaseManager, BusinessRepository as BaseBusinessRepository
from ..core.exceptions import DatabaseError, BusinessNotFoundError


class BusinessRepository:
    """
    Repository for business data operations
    
    Single Responsibility: Only handles data persistence operations
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._business_repository = BaseBusinessRepository(db_manager)
    
    async def create_business(self, business_data: Dict[str, Any]) -> str:
        """
        Create a new business record
        
        Args:
            business_data: Business data to persist
            
        Returns:
            Business ID of created business
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            business_id = await self._business_repository.create_business(business_data)
            return business_id
        except Exception as e:
            raise DatabaseError(f"Failed to create business: {str(e)}")
    
    async def get_business_by_id(self, business_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve business by ID
        
        Args:
            business_id: Business identifier
            
        Returns:
            Business data or None if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self._business_repository.get_business_by_id(business_id)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve business {business_id}: {str(e)}")
    
    async def update_business(self, business_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update business data
        
        Args:
            business_id: Business identifier
            update_data: Data to update
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Add update timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            return await self._business_repository.update_business(business_id, update_data)
        except Exception as e:
            raise DatabaseError(f"Failed to update business {business_id}: {str(e)}")
    
    async def delete_business(self, business_id: str) -> bool:
        """
        Delete business record
        
        Args:
            business_id: Business identifier
            
        Returns:
            True if deletion successful, False otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self._business_repository.delete_business(business_id)
        except Exception as e:
            raise DatabaseError(f"Failed to delete business {business_id}: {str(e)}")
    
    async def list_businesses(
        self, 
        limit: int = 100, 
        offset: int = 0,
        business_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List businesses with optional filtering
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            business_type: Filter by business type
            status: Filter by status
            
        Returns:
            List of business data
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self._business_repository.list_businesses(
                limit=limit,
                offset=offset,
                business_type=business_type,
                status=status
            )
        except Exception as e:
            raise DatabaseError(f"Failed to list businesses: {str(e)}")
    
    async def find_businesses_with_capabilities(self, capabilities: List[str]) -> List[Dict[str, Any]]:
        """
        Find businesses with specific capabilities
        
        Args:
            capabilities: List of capabilities to search for
            
        Returns:
            List of businesses with matching capabilities
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self._business_repository.find_businesses_with_capabilities(capabilities)
        except Exception as e:
            raise DatabaseError(f"Failed to find businesses with capabilities: {str(e)}")
    
    async def update_business_status(self, business_id: str, status: str) -> bool:
        """
        Update business status
        
        Args:
            business_id: Business identifier
            status: New status
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow()
            }
            return await self.update_business(business_id, update_data)
        except Exception as e:
            raise DatabaseError(f"Failed to update business status: {str(e)}")
    
    async def update_business_metrics(self, business_id: str, metrics: Dict[str, Any]) -> bool:
        """
        Update business metrics
        
        Args:
            business_id: Business identifier
            metrics: Metrics data to update
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            update_data = {
                'metrics': metrics,
                'metrics_updated_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            return await self.update_business(business_id, update_data)
        except Exception as e:
            raise DatabaseError(f"Failed to update business metrics: {str(e)}")
    
    async def store_api_key(self, business_id: str, api_key: str, key_type: str = "primary") -> bool:
        """
        Store API key for business
        
        Args:
            business_id: Business identifier
            api_key: API key to store
            key_type: Type of API key
            
        Returns:
            True if storage successful, False otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            api_key_data = {
                'api_key': api_key,
                'key_type': key_type,
                'created_at': datetime.utcnow(),
                'is_active': True
            }
            
            return await self._business_repository.store_api_key(business_id, api_key_data)
        except Exception as e:
            raise DatabaseError(f"Failed to store API key: {str(e)}")
    
    async def get_business_api_keys(self, business_id: str) -> List[Dict[str, Any]]:
        """
        Get API keys for business
        
        Args:
            business_id: Business identifier
            
        Returns:
            List of API key data
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self._business_repository.get_business_api_keys(business_id)
        except Exception as e:
            raise DatabaseError(f"Failed to get API keys: {str(e)}")
    
    async def deactivate_api_key(self, business_id: str, api_key: str) -> bool:
        """
        Deactivate API key
        
        Args:
            business_id: Business identifier
            api_key: API key to deactivate
            
        Returns:
            True if deactivation successful, False otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self._business_repository.deactivate_api_key(business_id, api_key)
        except Exception as e:
            raise DatabaseError(f"Failed to deactivate API key: {str(e)}")
    
    async def find_businesses_by_type(self, business_type: str) -> List[Dict[str, Any]]:
        """
        Find businesses by type
        
        Args:
            business_type: Business type to search for
            
        Returns:
            List of businesses of specified type
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self.list_businesses(business_type=business_type)
        except Exception as e:
            raise DatabaseError(f"Failed to find businesses by type: {str(e)}")
    
    async def find_active_businesses(self) -> List[Dict[str, Any]]:
        """
        Find all active businesses
        
        Returns:
            List of active businesses
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self.list_businesses(status="active")
        except Exception as e:
            raise DatabaseError(f"Failed to find active businesses: {str(e)}")
    
    async def get_business_count_by_type(self) -> Dict[str, int]:
        """
        Get count of businesses by type
        
        Returns:
            Dictionary mapping business type to count
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self._business_repository.get_business_count_by_type()
        except Exception as e:
            raise DatabaseError(f"Failed to get business count by type: {str(e)}")
    
    async def search_businesses(
        self, 
        query: str,
        limit: int = 50,
        business_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search businesses by name or description
        
        Args:
            query: Search query
            limit: Maximum number of results
            business_type: Optional business type filter
            
        Returns:
            List of matching businesses
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self._business_repository.search_businesses(
                query=query,
                limit=limit,
                business_type=business_type
            )
        except Exception as e:
            raise DatabaseError(f"Failed to search businesses: {str(e)}")
    
    async def get_business_statistics(self) -> Dict[str, Any]:
        """
        Get business statistics
        
        Returns:
            Dictionary with business statistics
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self._business_repository.get_business_statistics()
        except Exception as e:
            raise DatabaseError(f"Failed to get business statistics: {str(e)}")
    
    async def backup_business_data(self, business_id: str) -> Dict[str, Any]:
        """
        Create backup of business data
        
        Args:
            business_id: Business identifier
            
        Returns:
            Backup data
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            business_data = await self.get_business_by_id(business_id)
            if not business_data:
                raise BusinessNotFoundError(f"Business {business_id} not found")
            
            backup_data = {
                'business_data': business_data,
                'backup_timestamp': datetime.utcnow(),
                'backup_type': 'full'
            }
            
            return backup_data
        except Exception as e:
            raise DatabaseError(f"Failed to backup business data: {str(e)}")
