"""
Business Server Factory
Handles MCP and A2A server creation following Single Responsibility Principle

This module extracts server creation logic from BusinessService to follow
the Single Responsibility Principle.
"""

from typing import Dict, Any, Optional
from ..core.mcp_server_generator import BAISMCPServer, BusinessSystemAdapter
from ..core.a2a_integration import BAISA2AServer
from ..core.a2a_streaming_tasks import A2AStreamingFactory
from ..core.a2a_agent_registry import A2AAgentRegistryFactory
from ..utils.schema_factory import BusinessSchemaFactory


class MCPServerFactory:
    """
    Factory for creating MCP servers
    
    Single Responsibility: Only handles MCP server creation
    """
    
    def __init__(self):
        self.created_servers: Dict[str, BAISMCPServer] = {}
    
    def create_server(
        self, 
        business_schema: Any,
        business_config: Dict[str, Any]
    ) -> BAISMCPServer:
        """
        Create MCP server for business
        
        Args:
            business_schema: Business schema
            business_config: Business configuration
            
        Returns:
            Created MCP server
        """
        # Create business system adapter
        business_adapter = BusinessSystemAdapter(business_config)
        
        # Create MCP server
        mcp_server = BAISMCPServer(business_schema, business_adapter)
        
        # Store for later reference
        self.created_servers[business_schema.business_info.id] = mcp_server
        
        return mcp_server
    
    def get_server(self, business_id: str) -> Optional[BAISMCPServer]:
        """Get existing MCP server by business ID"""
        return self.created_servers.get(business_id)
    
    def remove_server(self, business_id: str) -> bool:
        """Remove MCP server"""
        if business_id in self.created_servers:
            del self.created_servers[business_id]
            return True
        return False


class A2AServerFactory:
    """
    Factory for creating A2A servers
    
    Single Responsibility: Only handles A2A server creation
    """
    
    def __init__(self):
        self.created_servers: Dict[str, BAISMC2AServer] = {}
        self.streaming_managers: Dict[str, Any] = {}
    
    def create_server(
        self, 
        business_schema: Any,
        mcp_server: BAISMCPServer,
        enable_streaming: bool = True
    ) -> BAISMC2AServer:
        """
        Create A2A server for business
        
        Args:
            business_schema: Business schema
            mcp_server: Associated MCP server
            enable_streaming: Whether to enable streaming features
            
        Returns:
            Created A2A server
        """
        # Create A2A server
        a2a_server = BAISMC2AServer(business_schema, mcp_server)
        
        # Enable streaming if requested
        if enable_streaming:
            streaming_manager = A2AStreamingFactory.create_integrated_server(a2a_server)
            self.streaming_managers[business_schema.business_info.id] = streaming_manager
        
        # Store for later reference
        self.created_servers[business_schema.business_info.id] = a2a_server
        
        return a2a_server
    
    def get_server(self, business_id: str) -> Optional[BAISMC2AServer]:
        """Get existing A2A server by business ID"""
        return self.created_servers.get(business_id)
    
    def get_streaming_manager(self, business_id: str) -> Optional[Any]:
        """Get streaming manager for business"""
        return self.streaming_managers.get(business_id)
    
    def remove_server(self, business_id: str) -> bool:
        """Remove A2A server and streaming manager"""
        removed = False
        
        if business_id in self.created_servers:
            del self.created_servers[business_id]
            removed = True
        
        if business_id in self.streaming_managers:
            del self.streaming_managers[business_id]
        
        return removed


class BusinessSystemAdapterFactory:
    """
    Factory for creating business system adapters
    
    Single Responsibility: Only handles adapter creation
    """
    
    @staticmethod
    def create_adapter(business_config: Dict[str, Any]) -> BusinessSystemAdapter:
        """
        Create business system adapter
        
        Args:
            business_config: Business configuration
            
        Returns:
            Created business system adapter
        """
        return BusinessSystemAdapter(business_config)
    
    @staticmethod
    def create_hospitality_adapter(hotel_config: Dict[str, Any]) -> BusinessSystemAdapter:
        """Create adapter for hospitality businesses"""
        # Add hospitality-specific configuration
        hospitality_config = {
            **hotel_config,
            "business_type": "hospitality",
            "integration_type": "pms",  # Property Management System
            "supported_operations": ["booking", "availability", "pricing", "guest_management"]
        }
        
        return BusinessSystemAdapter(hospitality_config)
    
    @staticmethod
    def create_restaurant_adapter(restaurant_config: Dict[str, Any]) -> BusinessSystemAdapter:
        """Create adapter for restaurant businesses"""
        # Add restaurant-specific configuration
        restaurant_config = {
            **restaurant_config,
            "business_type": "restaurant",
            "integration_type": "pos",  # Point of Sale
            "supported_operations": ["reservation", "menu", "ordering", "payment"]
        }
        
        return BusinessSystemAdapter(restaurant_config)
    
    @staticmethod
    def create_retail_adapter(retail_config: Dict[str, Any]) -> BusinessSystemAdapter:
        """Create adapter for retail businesses"""
        # Add retail-specific configuration
        retail_config = {
            **retail_config,
            "business_type": "retail",
            "integration_type": "ecommerce",
            "supported_operations": ["inventory", "ordering", "payment", "shipping"]
        }
        
        return BusinessSystemAdapter(retail_config)


class BusinessServerOrchestrator:
    """
    Orchestrates the creation and management of business servers
    
    Single Responsibility: Coordinates server creation without doing the work itself
    """
    
    def __init__(self):
        self.mcp_factory = MCPServerFactory()
        self.a2a_factory = A2AServerFactory()
        self.adapter_factory = BusinessSystemAdapterFactory()
    
    async def setup_business_servers(
        self, 
        business_schema: Any,
        business_config: Dict[str, Any],
        enable_mcp: bool = True,
        enable_a2a: bool = True,
        enable_streaming: bool = True
    ) -> Dict[str, Any]:
        """
        Setup complete server infrastructure for business
        
        Args:
            business_schema: Business schema
            business_config: Business configuration
            enable_mcp: Whether to create MCP server
            enable_a2a: Whether to create A2A server
            enable_streaming: Whether to enable streaming features
            
        Returns:
            Dictionary with server information
        """
        servers = {}
        business_id = business_schema.business_info.id
        
        try:
            # Create MCP server if requested
            if enable_mcp:
                mcp_server = self.mcp_factory.create_server(business_schema, business_config)
                servers['mcp_server'] = mcp_server
                servers['mcp_endpoint'] = business_schema.integration.mcp_server.endpoint
            
            # Create A2A server if requested
            if enable_a2a and enable_mcp:
                mcp_server = servers.get('mcp_server')
                a2a_server = self.a2a_factory.create_server(
                    business_schema, 
                    mcp_server, 
                    enable_streaming
                )
                servers['a2a_server'] = a2a_server
                servers['a2a_endpoint'] = business_schema.integration.a2a_endpoint.discovery_url
                
                if enable_streaming:
                    streaming_manager = self.a2a_factory.get_streaming_manager(business_id)
                    servers['streaming_manager'] = streaming_manager
            
            # Register with A2A agent registry if A2A is enabled
            if enable_a2a and 'a2a_server' in servers:
                await self._register_with_a2a_registry(business_schema, servers['a2a_server'])
            
            servers['setup_complete'] = True
            servers['business_id'] = business_id
            
        except Exception as e:
            # Cleanup on failure
            await self._cleanup_failed_setup(business_id)
            raise Exception(f"Failed to setup business servers: {str(e)}")
        
        return servers
    
    async def _register_with_a2a_registry(
        self, 
        business_schema: Any, 
        a2a_server: BAISMC2AServer
    ) -> None:
        """Register business with A2A agent registry"""
        try:
            # Create registry client and manager
            registry_client, registry_manager = A2AAgentRegistryFactory.create_default_registry()
            
            # Generate agent card
            agent_card = a2a_server.agent_card
            
            # Register with registry
            success = await registry_manager.register_business_agent(
                business_schema.business_info.id,
                agent_card
            )
            
            if not success:
                print(f"Warning: Failed to register business {business_schema.business_info.id} with A2A registry")
            
        except Exception as e:
            print(f"Warning: A2A registry registration failed: {e}")
    
    async def _cleanup_failed_setup(self, business_id: str) -> None:
        """Cleanup servers on setup failure"""
        self.mcp_factory.remove_server(business_id)
        self.a2a_factory.remove_server(business_id)
    
    async def shutdown_business_servers(self, business_id: str) -> bool:
        """
        Shutdown servers for business
        
        Args:
            business_id: Business identifier
            
        Returns:
            True if shutdown successful
        """
        try:
            # Remove servers
            mcp_removed = self.mcp_factory.remove_server(business_id)
            a2a_removed = self.a2a_factory.remove_server(business_id)
            
            return mcp_removed or a2a_removed
            
        except Exception as e:
            print(f"Error shutting down servers for {business_id}: {e}")
            return False
    
    def get_server_status(self, business_id: str) -> Dict[str, Any]:
        """
        Get status of business servers
        
        Args:
            business_id: Business identifier
            
        Returns:
            Server status information
        """
        status = {
            'business_id': business_id,
            'mcp_server_active': business_id in self.mcp_factory.created_servers,
            'a2a_server_active': business_id in self.a2a_factory.created_servers,
            'streaming_active': business_id in self.a2a_factory.streaming_managers
        }
        
        return status
    
    def get_all_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all business servers"""
        all_business_ids = set()
        all_business_ids.update(self.mcp_factory.created_servers.keys())
        all_business_ids.update(self.a2a_factory.created_servers.keys())
        
        return {
            business_id: self.get_server_status(business_id)
            for business_id in all_business_ids
        }
