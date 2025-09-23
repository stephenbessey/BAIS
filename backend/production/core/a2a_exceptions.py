"""
A2A Protocol Specific Exceptions
Custom exception classes for A2A agent-to-agent protocol errors
"""

from typing import Optional, Dict, Any, List
from .exceptions import BAISException


class A2AException(BAISException):
    """Base exception for all A2A-related errors"""
    pass


class A2ATaskProcessingError(A2AException):
    """Raised when A2A task processing fails"""
    
    def __init__(
        self, 
        message: str, 
        task_id: Optional[str] = None,
        capability: Optional[str] = None,
        agent_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.task_id = task_id
        self.capability = capability
        self.agent_id = agent_id


class A2AAgentDiscoveryError(A2AException):
    """Raised when A2A agent discovery fails"""
    
    def __init__(
        self, 
        message: str, 
        discovery_criteria: Optional[Dict[str, Any]] = None,
        registry_endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.discovery_criteria = discovery_criteria
        self.registry_endpoint = registry_endpoint


class A2AAgentRegistrationError(A2AException):
    """Raised when A2A agent registration fails"""
    
    def __init__(
        self, 
        message: str, 
        agent_id: Optional[str] = None,
        registry_endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.agent_id = agent_id
        self.registry_endpoint = registry_endpoint


class A2AStreamingError(A2AException):
    """Raised when A2A streaming operations fail"""
    
    def __init__(
        self, 
        message: str, 
        stream_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.stream_id = stream_id
        self.task_id = task_id


class A2ACapabilityError(A2AException):
    """Raised when A2A capability operations fail"""
    
    def __init__(
        self, 
        message: str, 
        capability: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.capability = capability
        self.required_capabilities = required_capabilities


class A2ACommunicationError(A2AException):
    """Raised when A2A agent communication fails"""
    
    def __init__(
        self, 
        message: str, 
        target_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.target_agent = target_agent
        self.endpoint = endpoint


class A2AProcessorInitializationError(A2AException):
    """Raised when A2A processor initialization fails"""
    
    def __init__(
        self, 
        message: str, 
        initialization_step: Optional[str] = None,
        retry_count: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.initialization_step = initialization_step
        self.retry_count = retry_count
