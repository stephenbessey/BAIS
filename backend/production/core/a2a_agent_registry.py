"""
A2A Agent Discovery Registry
Implements proper A2A agent discovery and registration functionality

This module addresses the critical gap in A2A agent discovery by implementing
a proper agent registry system that integrates with the A2A network.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import httpx
import json
import uuid
from fastapi import HTTPException

from .a2a_integration import (
    A2AAgent, A2ACapability, A2AAgentCard, 
    A2ADiscoveryRequest, A2ADiscoveryResponse
)


class AgentStatus(Enum):
    """Agent registration status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class CapabilityCategory(Enum):
    """Capability categories for agent discovery"""
    BOOKING = "booking"
    PAYMENT = "payment"
    INFORMATION = "information"
    COORDINATION = "coordination"
    VALIDATION = "validation"


@dataclass
class A2AAgentRegistry:
    """Represents an agent in the A2A registry"""
    agent_id: str
    name: str
    description: str
    endpoint: str
    capabilities: List[A2ACapability]
    status: AgentStatus
    registered_at: datetime
    last_seen: datetime
    metadata: Dict[str, Any] = None
    tags: Set[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = set()
    
    def to_agent_card(self) -> A2AAgentCard:
        """Convert to A2A agent card format"""
        return A2AAgentCard(
            agent=A2AAgent(
                name=self.name,
                description=self.description,
                capabilities=self.capabilities,
                endpoint=self.endpoint
            ),
            discovery_url=f"{self.endpoint}/.well-known/agent.json",
            registered_at=self.registered_at.isoformat(),
            last_updated=self.last_seen.isoformat()
        )


@dataclass
class AgentDiscoveryCriteria:
    """Criteria for agent discovery - Parameter Object pattern"""
    capabilities_needed: List[str]
    business_types: List[str] = None
    geographic_region: str = None
    max_response_time_ms: int = 5000
    min_availability_score: float = 0.8
    tags: List[str] = None
    
    def __post_init__(self):
        if self.business_types is None:
            self.business_types = []
        if self.tags is None:
            self.tags = []


class A2AAgentRegistryClient:
    """
    A2A Agent Registry Client
    
    Implements proper agent discovery by integrating with A2A registry services.
    This addresses the critical gap where the current implementation only
    returns self-capabilities instead of discovering other agents.
    """
    
    def __init__(self, registry_endpoints: List[str]):
        """
        Initialize registry client
        
        Args:
            registry_endpoints: List of A2A registry endpoints to query
        """
        self.registry_endpoints = registry_endpoints
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.discovered_agents: Dict[str, A2AAgentRegistry] = {}
        self.agent_cache: Dict[str, A2AAgentCard] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(minutes=5)
    
    async def register_agent(self, agent_card: A2AAgentCard) -> bool:
        """
        Register agent with A2A registry network
        
        Args:
            agent_card: Agent card to register
            
        Returns:
            True if registration successful, False otherwise
        """
        registration_data = {
            "agent_id": str(uuid.uuid4()),
            "agent_card": agent_card.dict(),
            "registered_at": datetime.utcnow().isoformat(),
            "status": AgentStatus.ACTIVE.value
        }
        
        success_count = 0
        for endpoint in self.registry_endpoints:
            try:
                response = await self.http_client.post(
                    f"{endpoint}/agents/register",
                    json=registration_data,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                success_count += 1
                
            except Exception as e:
                print(f"Failed to register with {endpoint}: {e}")
        
        return success_count > 0
    
    async def discover_agents(self, criteria: AgentDiscoveryCriteria) -> A2ADiscoveryResponse:
        """
        Discover agents matching criteria from A2A registry
        
        Args:
            criteria: Discovery criteria
            
        Returns:
            A2ADiscoveryResponse with matching agents
        """
        all_agents = []
        search_id = str(uuid.uuid4())
        
        # Check cache first
        cache_key = self._generate_cache_key(criteria)
        if cache_key in self.agent_cache:
            if self.cache_expiry.get(cache_key, datetime.min) > datetime.utcnow():
                cached_agents = self.agent_cache[cache_key]
                return A2ADiscoveryResponse(
                    agents=[cached_agents],
                    search_id=search_id,
                    total_found=1
                )
        
        # Query all registry endpoints
        discovery_tasks = []
        for endpoint in self.registry_endpoints:
            task = self._query_registry_endpoint(endpoint, criteria)
            discovery_tasks.append(task)
        
        # Wait for all queries to complete
        results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                print(f"Registry query failed: {result}")
                continue
            
            if isinstance(result, list):
                all_agents.extend(result)
        
        # Filter and score agents
        filtered_agents = self._filter_agents_by_criteria(all_agents, criteria)
        scored_agents = self._score_agents(filtered_agents, criteria)
        
        # Cache results
        if scored_agents:
            self.agent_cache[cache_key] = scored_agents[0]  # Cache best match
            self.cache_expiry[cache_key] = datetime.utcnow() + self.cache_ttl
        
        return A2ADiscoveryResponse(
            agents=scored_agents,
            search_id=search_id,
            total_found=len(scored_agents)
        )
    
    async def _query_registry_endpoint(
        self, 
        endpoint: str, 
        criteria: AgentDiscoveryCriteria
    ) -> List[A2AAgentCard]:
        """Query a specific registry endpoint"""
        try:
            discovery_request = {
                "capabilities_needed": criteria.capabilities_needed,
                "business_types": criteria.business_types,
                "geographic_region": criteria.geographic_region,
                "max_response_time_ms": criteria.max_response_time_ms,
                "min_availability_score": criteria.min_availability_score,
                "tags": criteria.tags,
                "requesting_agent": "bais-coordinator",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = await self.http_client.post(
                f"{endpoint}/agents/discover",
                json=discovery_request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            discovery_response = response.json()
            agents = []
            
            for agent_data in discovery_response.get("agents", []):
                try:
                    agent_card = A2AAgentCard(**agent_data)
                    agents.append(agent_card)
                except Exception as e:
                    print(f"Failed to parse agent data: {e}")
                    continue
            
            return agents
            
        except Exception as e:
            print(f"Failed to query registry {endpoint}: {e}")
            return []
    
    def _filter_agents_by_criteria(
        self, 
        agents: List[A2AAgentCard], 
        criteria: AgentDiscoveryCriteria
    ) -> List[A2AAgentCard]:
        """Filter agents based on discovery criteria"""
        filtered_agents = []
        
        for agent in agents:
            # Check capability match
            agent_capabilities = {cap.name for cap in agent.agent.capabilities}
            required_capabilities = set(criteria.capabilities_needed)
            
            if not required_capabilities.issubset(agent_capabilities):
                continue
            
            # Check business type match if specified
            if criteria.business_types:
                agent_business_types = agent.agent.metadata.get("business_types", [])
                if not any(bt in agent_business_types for bt in criteria.business_types):
                    continue
            
            # Check geographic region if specified
            if criteria.geographic_region:
                agent_region = agent.agent.metadata.get("geographic_region")
                if agent_region and agent_region != criteria.geographic_region:
                    continue
            
            # Check tags if specified
            if criteria.tags:
                agent_tags = set(agent.agent.metadata.get("tags", []))
                required_tags = set(criteria.tags)
                if not required_tags.issubset(agent_tags):
                    continue
            
            filtered_agents.append(agent)
        
        return filtered_agents
    
    def _score_agents(
        self, 
        agents: List[A2AAgentCard], 
        criteria: AgentDiscoveryCriteria
    ) -> List[A2AAgentCard]:
        """Score and rank agents by relevance"""
        
        def calculate_score(agent: A2AAgentCard) -> float:
            score = 0.0
            
            # Base score for capability match
            agent_capabilities = {cap.name for cap in agent.agent.capabilities}
            required_capabilities = set(criteria.capabilities_needed)
            capability_match_ratio = len(required_capabilities & agent_capabilities) / len(required_capabilities)
            score += capability_match_ratio * 0.4
            
            # Availability score
            availability_score = agent.agent.metadata.get("availability_score", 0.5)
            score += availability_score * 0.3
            
            # Response time score
            avg_response_time = agent.agent.metadata.get("avg_response_time_ms", 1000)
            response_time_score = max(0, 1 - (avg_response_time / criteria.max_response_time_ms))
            score += response_time_score * 0.2
            
            # Reputation score
            reputation_score = agent.agent.metadata.get("reputation_score", 0.5)
            score += reputation_score * 0.1
            
            return score
        
        # Score and sort agents
        scored_agents = [(agent, calculate_score(agent)) for agent in agents]
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Filter by minimum availability score
        filtered_agents = [
            agent for agent, score in scored_agents 
            if score >= criteria.min_availability_score
        ]
        
        return filtered_agents
    
    def _generate_cache_key(self, criteria: AgentDiscoveryCriteria) -> str:
        """Generate cache key for discovery criteria"""
        key_data = {
            "capabilities": sorted(criteria.capabilities_needed),
            "business_types": sorted(criteria.business_types or []),
            "region": criteria.geographic_region,
            "tags": sorted(criteria.tags or [])
        }
        return json.dumps(key_data, sort_keys=True)
    
    async def get_agent_by_id(self, agent_id: str) -> Optional[A2AAgentCard]:
        """Get agent by ID from registry"""
        for endpoint in self.registry_endpoints:
            try:
                response = await self.http_client.get(
                    f"{endpoint}/agents/{agent_id}",
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                agent_data = response.json()
                return A2AAgentCard(**agent_data)
                
            except Exception as e:
                print(f"Failed to get agent {agent_id} from {endpoint}: {e}")
                continue
        
        return None
    
    async def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """Update agent status in registry"""
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        success_count = 0
        for endpoint in self.registry_endpoints:
            try:
                response = await self.http_client.put(
                    f"{endpoint}/agents/{agent_id}/status",
                    json=update_data,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                success_count += 1
                
            except Exception as e:
                print(f"Failed to update agent {agent_id} status at {endpoint}: {e}")
        
        return success_count > 0
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


class A2AAgentRegistryManager:
    """
    Manager for A2A agent registry operations
    
    Provides high-level operations for agent discovery and management.
    """
    
    def __init__(self, registry_client: A2AAgentRegistryClient):
        self.registry_client = registry_client
        self.registered_agents: Dict[str, A2AAgentRegistry] = {}
    
    async def register_business_agent(
        self, 
        business_id: str,
        agent_card: A2AAgentCard
    ) -> bool:
        """Register a business agent with the A2A network"""
        try:
            # Register with registry network
            registration_success = await self.registry_client.register_agent(agent_card)
            
            if registration_success:
                # Store locally
                agent_registry = A2AAgentRegistry(
                    agent_id=str(uuid.uuid4()),
                    name=agent_card.agent.name,
                    description=agent_card.agent.description,
                    endpoint=agent_card.agent.endpoint,
                    capabilities=agent_card.agent.capabilities,
                    status=AgentStatus.ACTIVE,
                    registered_at=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    metadata={"business_id": business_id}
                )
                
                self.registered_agents[business_id] = agent_registry
                
            return registration_success
            
        except Exception as e:
            print(f"Failed to register business agent {business_id}: {e}")
            return False
    
    async def discover_business_agents(
        self, 
        business_type: str,
        capabilities_needed: List[str]
    ) -> List[A2AAgentCard]:
        """Discover agents for a specific business type and capabilities"""
        criteria = AgentDiscoveryCriteria(
            capabilities_needed=capabilities_needed,
            business_types=[business_type],
            min_availability_score=0.8
        )
        
        discovery_response = await self.registry_client.discover_agents(criteria)
        return discovery_response.agents
    
    async def find_coordination_partners(
        self, 
        current_agent_capabilities: List[str],
        business_context: Dict[str, Any]
    ) -> List[A2AAgentCard]:
        """Find agents that can coordinate with current agent"""
        
        # Determine complementary capabilities needed
        coordination_capabilities = self._determine_coordination_capabilities(
            current_agent_capabilities, 
            business_context
        )
        
        criteria = AgentDiscoveryCriteria(
            capabilities_needed=coordination_capabilities,
            business_types=business_context.get("business_types", []),
            geographic_region=business_context.get("geographic_region"),
            min_availability_score=0.7
        )
        
        discovery_response = await self.registry_client.discover_agents(criteria)
        return discovery_response.agents
    
    def _determine_coordination_capabilities(
        self, 
        current_capabilities: List[str], 
        business_context: Dict[str, Any]
    ) -> List[str]:
        """Determine what capabilities are needed for coordination"""
        
        # Map current capabilities to coordination needs
        coordination_map = {
            "booking": ["payment", "validation"],
            "payment": ["booking", "confirmation"],
            "information": ["booking", "validation"],
            "validation": ["payment", "confirmation"]
        }
        
        needed_capabilities = set()
        for capability in current_capabilities:
            if capability in coordination_map:
                needed_capabilities.update(coordination_map[capability])
        
        # Add context-specific capabilities
        if business_context.get("requires_payment"):
            needed_capabilities.add("payment")
        if business_context.get("requires_validation"):
            needed_capabilities.add("validation")
        
        return list(needed_capabilities)
    
    async def cleanup_inactive_agents(self, max_age_hours: int = 24) -> int:
        """Clean up agents that haven't been seen recently"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        agents_to_remove = []
        for business_id, agent in self.registered_agents.items():
            if agent.last_seen < cutoff_time:
                agents_to_remove.append(business_id)
        
        for business_id in agents_to_remove:
            # Update status to inactive
            agent = self.registered_agents[business_id]
            agent.status = AgentStatus.INACTIVE
            
            # Update in registry
            await self.registry_client.update_agent_status(agent.agent_id, AgentStatus.INACTIVE)
            
            del self.registered_agents[business_id]
            cleaned_count += 1
        
        return cleaned_count


# Factory for creating registry components
class A2AAgentRegistryFactory:
    """Factory for creating A2A agent registry components"""
    
    @staticmethod
    def create_registry_client(registry_endpoints: List[str]) -> A2AAgentRegistryClient:
        """Create registry client with endpoints"""
        return A2AAgentRegistryClient(registry_endpoints)
    
    @staticmethod
    def create_registry_manager(registry_client: A2AAgentRegistryClient) -> A2AAgentRegistryManager:
        """Create registry manager with client"""
        return A2AAgentRegistryManager(registry_client)
    
    @staticmethod
    def create_default_registry() -> tuple[A2AAgentRegistryClient, A2AAgentRegistryManager]:
        """Create default registry setup"""
        # Default registry endpoints - would be configured in production
        default_endpoints = [
            "https://registry.a2a-network.org",
            "https://backup-registry.a2a-network.org"
        ]
        
        client = A2AAgentRegistryClient(default_endpoints)
        manager = A2AAgentRegistryManager(client)
        
        return client, manager
