"""
MCP Route Handlers - Clean Code Implementation
Refactored route handlers following Single Responsibility Principle
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime

from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials

from .mcp_authentication_service import AuthContext, get_auth_context
from .mcp_error_handler import (
    MCPErrorHandler, ValidationError, BusinessRuleError, NotFoundError,
    AuthorizationError, get_error_handler
)

logger = logging.getLogger(__name__)


class MCPRouteHandler(ABC):
    """Base class for MCP route handlers following Clean Code principles"""
    
    def __init__(self, auth_service, error_handler: MCPErrorHandler):
        self._auth_service = auth_service
        self._error_handler = error_handler
    
    async def authenticate_request(self, auth: HTTPAuthorizationCredentials, resource_uri: str = None) -> AuthContext:
        """Authenticate request with proper error handling"""
        try:
            return await self._auth_service.validate_token(auth.credentials, resource_uri or "default")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication service error: {e}")
            raise HTTPException(500, "Authentication service unavailable")


class ResourceHandler(MCPRouteHandler):
    """Handler for MCP resource endpoints following Single Responsibility Principle"""
    
    def __init__(self, auth_service, error_handler: MCPErrorHandler, business_adapter):
        super().__init__(auth_service, error_handler)
        self._business_adapter = business_adapter
    
    async def list_resources(self, auth: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """List available resources with proper error handling"""
        auth_context = None
        try:
            auth_context = await self.authenticate_request(auth)
            
            if not auth_context.has_scope('resource:read'):
                raise AuthorizationError(
                    "Insufficient permissions for resource access",
                    required_scopes=['resource:read'],
                    user_scopes=auth_context.scopes
                )
            
            # Get resources from business adapter
            resources = await self._business_adapter.get_available_resources(auth_context)
            
            return {
                "resources": [
                    {
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mimeType": resource.mime_type
                    }
                    for resource in resources
                ]
            }
            
        except (HTTPException, AuthorizationError):
            raise
        except Exception as e:
            user_context = {"user_id": auth_context.user_id if auth_context else None}
            error_response = self._error_handler.handle_resource_error(e, "list_resources", user_context)
            raise HTTPException(500, detail=error_response)
    
    async def read_resource(self, request: Dict[str, Any], auth: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """Read specific resource with validation"""
        auth_context = None
        try:
            resource_uri = request.get("uri")
            if not resource_uri:
                raise ValidationError("Resource URI is required", "uri")
            
            auth_context = await self.authenticate_request(auth, resource_uri)
            
            # Validate URI format
            if not self._is_valid_resource_uri(resource_uri):
                raise ValidationError("Invalid resource URI format", "uri", resource_uri)
            
            # Check resource-specific permissions
            if not auth_context.has_resource_access(resource_uri):
                raise AuthorizationError(
                    f"Insufficient permissions for resource: {resource_uri}",
                    required_scopes=[f"resource:{resource_uri.split('://')[0]}"],
                    user_scopes=auth_context.scopes
                )
            
            # Get resource content
            content = await self._business_adapter.get_resource_content(resource_uri, auth_context)
            
            return {
                "contents": [{
                    "uri": resource_uri,
                    "mimeType": "application/json",
                    "text": json.dumps(content, indent=2)
                }]
            }
            
        except (HTTPException, ValidationError, AuthorizationError):
            raise
        except Exception as e:
            user_context = {"user_id": auth_context.user_id if auth_context else None}
            error_response = self._error_handler.handle_resource_error(e, "read_resource", user_context)
            raise HTTPException(500, detail=error_response)
    
    def _is_valid_resource_uri(self, uri: str) -> bool:
        """Validate resource URI format following Clean Code principles"""
        valid_schemes = ['availability', 'service', 'business']
        try:
            scheme, path = uri.split('://', 1)
            return scheme in valid_schemes and len(path) > 0
        except ValueError:
            return False


class ToolHandler(MCPRouteHandler):
    """Handler for MCP tool endpoints following Single Responsibility Principle"""
    
    def __init__(self, auth_service, error_handler: MCPErrorHandler, business_adapter):
        super().__init__(auth_service, error_handler)
        self._business_adapter = business_adapter
    
    async def list_tools(self, auth: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """List available tools with proper authentication"""
        auth_context = None
        try:
            auth_context = await self.authenticate_request(auth)
            
            if not auth_context.has_scope('tool:execute'):
                raise AuthorizationError(
                    "Insufficient permissions for tool access",
                    required_scopes=['tool:execute'],
                    user_scopes=auth_context.scopes
                )
            
            # Get tools from business adapter
            tools = await self._business_adapter.get_available_tools(auth_context)
            
            return {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema
                    }
                    for tool in tools
                ]
            }
            
        except (HTTPException, AuthorizationError):
            raise
        except Exception as e:
            user_context = {"user_id": auth_context.user_id if auth_context else None}
            error_response = self._error_handler.handle_tool_error(e, "list_tools", user_context)
            raise HTTPException(500, detail=error_response)
    
    async def call_tool(self, request: Dict[str, Any], auth: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """Execute tool with comprehensive error handling and validation"""
        auth_context = None
        try:
            auth_context = await self.authenticate_request(auth)
            
            if not auth_context.has_scope('tool:execute'):
                raise AuthorizationError(
                    "Insufficient permissions for tool execution",
                    required_scopes=['tool:execute'],
                    user_scopes=auth_context.scopes
                )
            
            # Validate tool request
            tool_name = request.get("name")
            if not tool_name:
                raise ValidationError("Tool name is required", "name")
            
            tool_arguments = request.get("arguments", {})
            
            # Parse and validate tool request
            tool_spec = self._parse_tool_name(tool_name)
            validated_args = self._validate_tool_arguments(tool_spec, tool_arguments)
            
            # Execute tool
            result = await self._business_adapter.execute_tool(
                tool_spec.action,
                tool_spec.service_id,
                validated_args,
                auth_context
            )
            
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
            
        except (HTTPException, ValidationError, AuthorizationError):
            raise
        except Exception as e:
            user_context = {"user_id": auth_context.user_id if auth_context else None}
            error_response = self._error_handler.handle_tool_error(e, tool_name or "unknown", user_context)
            raise HTTPException(500, detail=error_response)
    
    def _parse_tool_name(self, tool_name: str) -> 'ToolSpec':
        """Parse tool name to extract action and service ID"""
        # Expected format: "search_availability" or "book_service"
        parts = tool_name.split('_', 1)
        if len(parts) != 2:
            raise ValidationError("Invalid tool name format", "name", tool_name)
        
        action, service_id = parts
        return ToolSpec(action=action, service_id=service_id)
    
    def _validate_tool_arguments(self, tool_spec: 'ToolSpec', arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool arguments based on tool specification"""
        # This would implement specific validation logic for each tool
        # For now, we'll do basic validation
        
        if tool_spec.action == "search":
            return self._validate_search_arguments(arguments)
        elif tool_spec.action == "book":
            return self._validate_booking_arguments(arguments)
        else:
            # Default validation - just ensure arguments is a dict
            if not isinstance(arguments, dict):
                raise ValidationError("Tool arguments must be a dictionary", "arguments", arguments)
            return arguments
    
    def _validate_search_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate search tool arguments"""
        # Validate required fields for search operations
        if "location" not in arguments:
            raise ValidationError("Location is required for search operations", "arguments.location")
        
        return arguments
    
    def _validate_booking_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate booking tool arguments"""
        # Validate required fields for booking operations
        required_fields = ["service_id", "date", "time"]
        for field in required_fields:
            if field not in arguments:
                raise ValidationError(f"{field} is required for booking operations", f"arguments.{field}")
        
        return arguments


class PromptHandler(MCPRouteHandler):
    """Handler for MCP prompt endpoints following Single Responsibility Principle"""
    
    def __init__(self, auth_service, error_handler: MCPErrorHandler, business_adapter):
        super().__init__(auth_service, error_handler)
        self._business_adapter = business_adapter
    
    async def list_prompts(self, auth: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """List available prompts with proper authentication"""
        auth_context = None
        try:
            auth_context = await self.authenticate_request(auth)
            
            if not auth_context.has_scope('prompt:read'):
                raise AuthorizationError(
                    "Insufficient permissions for prompt access",
                    required_scopes=['prompt:read'],
                    user_scopes=auth_context.scopes
                )
            
            # Get prompts from business adapter
            prompts = await self._business_adapter.get_available_prompts(auth_context)
            
            return {
                "prompts": [
                    {
                        "name": prompt.name,
                        "description": prompt.description,
                        "arguments": prompt.arguments
                    }
                    for prompt in prompts
                ]
            }
            
        except (HTTPException, AuthorizationError):
            raise
        except Exception as e:
            user_context = {"user_id": auth_context.user_id if auth_context else None}
            error_response = self._error_handler.handle_tool_error(e, "list_prompts", user_context)
            raise HTTPException(500, detail=error_response)
    
    async def get_prompt(self, request: Dict[str, Any], auth: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """Get prompt with arguments and generate response"""
        auth_context = None
        try:
            auth_context = await self.authenticate_request(auth)
            
            if not auth_context.has_scope('prompt:execute'):
                raise AuthorizationError(
                    "Insufficient permissions for prompt execution",
                    required_scopes=['prompt:execute'],
                    user_scopes=auth_context.scopes
                )
            
            prompt_name = request.get("name")
            if not prompt_name:
                raise ValidationError("Prompt name is required", "name")
            
            prompt_arguments = request.get("arguments", {})
            
            # Get prompt from business adapter
            prompt_content = await self._business_adapter.get_prompt_content(
                prompt_name, 
                prompt_arguments, 
                auth_context
            )
            
            return {
                "messages": [{
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt_content
                    }
                }]
            }
            
        except (HTTPException, ValidationError, AuthorizationError):
            raise
        except Exception as e:
            user_context = {"user_id": auth_context.user_id if auth_context else None}
            error_response = self._error_handler.handle_tool_error(e, f"prompt:{prompt_name or 'unknown'}", user_context)
            raise HTTPException(500, detail=error_response)


class InitializationHandler:
    """Handler for MCP initialization following Single Responsibility Principle"""
    
    def __init__(self, business_schema):
        self._business_schema = business_schema
    
    async def handle_initialization(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialization following protocol specification"""
        try:
            # Validate protocol version
            protocol_version = request.get("protocolVersion")
            if protocol_version != "2025-06-18":
                raise ValidationError(
                    f"Unsupported protocol version: {protocol_version}",
                    "protocolVersion",
                    protocol_version
                )
            
            # Build server capabilities
            capabilities = {
                "resources": {"listChanged": True},
                "tools": {"listChanged": True},
                "prompts": {"listChanged": True}
            }
            
            # Build server info
            server_info = {
                "name": f"bais-{self._business_schema.business_info.type.value}-server",
                "version": "1.0.0"
            }
            
            return {
                "protocolVersion": "2025-06-18",
                "capabilities": capabilities,
                "serverInfo": server_info
            }
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise HTTPException(500, "Initialization failed")


# Helper classes for tool parsing
class ToolSpec:
    """Tool specification for parsing tool names"""
    
    def __init__(self, action: str, service_id: str):
        self.action = action
        self.service_id = service_id


# Global handler instances
_resource_handler: Optional[ResourceHandler] = None
_tool_handler: Optional[ToolHandler] = None
_prompt_handler: Optional[PromptHandler] = None


def get_resource_handler() -> ResourceHandler:
    """Get the global resource handler instance"""
    global _resource_handler
    if _resource_handler is None:
        from .mcp_authentication_service import get_authentication_service
        auth_service = get_authentication_service()
        error_handler = get_error_handler()
        # Business adapter would be injected in real implementation
        business_adapter = None  # This would come from dependency injection
        _resource_handler = ResourceHandler(auth_service, error_handler, business_adapter)
    return _resource_handler


def get_tool_handler() -> ToolHandler:
    """Get the global tool handler instance"""
    global _tool_handler
    if _tool_handler is None:
        from .mcp_authentication_service import get_authentication_service
        auth_service = get_authentication_service()
        error_handler = get_error_handler()
        # Business adapter would be injected in real implementation
        business_adapter = None  # This would come from dependency injection
        _tool_handler = ToolHandler(auth_service, error_handler, business_adapter)
    return _tool_handler


def get_prompt_handler() -> PromptHandler:
    """Get the global prompt handler instance"""
    global _prompt_handler
    if _prompt_handler is None:
        from .mcp_authentication_service import get_authentication_service
        auth_service = get_authentication_service()
        error_handler = get_error_handler()
        # Business adapter would be injected in real implementation
        business_adapter = None  # This would come from dependency injection
        _prompt_handler = PromptHandler(auth_service, error_handler, business_adapter)
    return _prompt_handler
