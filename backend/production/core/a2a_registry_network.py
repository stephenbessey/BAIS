"""
A2A Registry Network Integration
Implements connection to public A2A registries for agent discovery
"""

import asyncio
import httpx
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum

from .a2a_integration import A2AAgentCard, A2ADiscoveryRequest, A2ADiscoveryResponse, A2AAgent
from ..config.protocol_settings import ProtocolConstants
from .connection_pool_manager import (
    get_connection_pool_manager, 
    REGISTRY_POOL_CONFIG,
    A2A_POOL_CONFIG
)

logger = logging.getLogger(__name__)


class RegistryNetworkType(Enum):
    """Types of A2A registry networks"""
    PUBLIC = "public"
    PRIVATE = "private"
    CONSORTIUM = "consortium"


@dataclass
class RegistryEndpoint:
    """A2A registry endpoint configuration"""
    url: str
    network_type: RegistryNetworkType
    priority: int = 1  # Lower number = higher priority
    timeout_seconds: int = 10
    requires_authentication: bool = False
    auth_token: Optional[str] = None
    max_agents_per_request: int = 100


@dataclass
class AgentDiscoveryCriteria:
    """Enhanced criteria for discovering agents across networks"""
    capabilities_needed: List[str] = field(default_factory=list)
    agent_type: Optional[str] = None
    location: Optional[str] = None
    business_category: Optional[str] = None
    min_reputation_score: float = 0.0
    max_response_time_ms: int = 5000
    preferred_networks: List[RegistryNetworkType] = field(default_factory=list)
    exclude_networks: List[RegistryNetworkType] = field(default_factory=list)
    max_results: int = 50


@dataclass
class AgentReputationScore:
    """Agent reputation scoring system"""
    agent_id: str
    overall_score: float  # 0.0 to 1.0
    response_time_score: float
    success_rate_score: float
    user_rating_score: float
    network_verification_score: float
    last_updated: datetime


class A2ARegistryNetworkClient:
    """
    Client for discovering agents across multiple A2A registry networks.
    Implements intelligent agent discovery with reputation scoring.
    """
    
    def __init__(self):
        # Initialize connection pool manager
        self._pool_manager = get_connection_pool_manager()
        self._registry_endpoints: List[RegistryEndpoint] = []
        self._agent_reputation_cache: Dict[str, AgentReputationScore] = {}
        self._discovery_cache: Dict[str, List[A2AAgent]] = {}
        self._cache_lock = asyncio.Lock()
        
        # Initialize with known public registries
        self._initialize_default_registries()
    
    def _initialize_default_registries(self):
        """Initialize with known public A2A registry endpoints"""
        default_registries = [
            RegistryEndpoint(
                url="https://registry.a2a-protocol.org/api/v1",
                network_type=RegistryNetworkType.PUBLIC,
                priority=1,
                timeout_seconds=15
            ),
            RegistryEndpoint(
                url="https://discovery.a2a-network.org/api/v1",
                network_type=RegistryNetworkType.PUBLIC,
                priority=2,
                timeout_seconds=10
            ),
            RegistryEndpoint(
                url="https://agents.a2a-consortium.org/api/v1",
                network_type=RegistryNetworkType.CONSORTIUM,
                priority=3,
                timeout_seconds=20,
                requires_authentication=True
            )
        ]
        
        self._registry_endpoints.extend(default_registries)
    
    def add_registry_endpoint(self, endpoint: RegistryEndpoint):
        """Add a custom registry endpoint"""
        self._registry_endpoints.append(endpoint)
        # Sort by priority
        self._registry_endpoints.sort(key=lambda x: x.priority)
    
    async def discover_agents_across_networks(
        self, 
        criteria: AgentDiscoveryCriteria
    ) -> A2ADiscoveryResponse:
        """
        Discover agents across multiple registry networks with intelligent filtering.
        """
        # Check cache first
        cache_key = self._generate_cache_key(criteria)
        cached_agents = await self._get_cached_agents(cache_key)
        if cached_agents:
            logger.info(f"Returning {len(cached_agents)} cached agents")
            return A2ADiscoveryResponse(agents=cached_agents, total_found=len(cached_agents))
        
        # Discover from all networks
        all_agents: List[A2AAgent] = []
        discovery_tasks = []
        
        # Filter endpoints based on criteria
        eligible_endpoints = self._filter_endpoints_by_criteria(criteria)
        
        for endpoint in eligible_endpoints:
            task = self._discover_from_registry(endpoint, criteria)
            discovery_tasks.append(task)
        
        # Execute all discovery requests concurrently
        if discovery_tasks:
            results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_agents.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Registry discovery failed: {result}")
        
        # Deduplicate agents by ID
        unique_agents = self._deduplicate_agents(all_agents)
        
        # Apply reputation filtering and scoring
        scored_agents = await self._apply_reputation_scoring(unique_agents, criteria)
        
        # Sort by reputation score and response time
        sorted_agents = self._sort_agents_by_quality(scored_agents, criteria)
        
        # Limit results
        final_agents = sorted_agents[:criteria.max_results]
        
        # Cache results
        await self._cache_agents(cache_key, final_agents)
        
        logger.info(f"Discovered {len(final_agents)} agents across {len(eligible_endpoints)} registries")
        
        return A2ADiscoveryResponse(agents=final_agents, total_found=len(final_agents))
    
    async def _discover_from_registry(
        self, 
        endpoint: RegistryEndpoint, 
        criteria: AgentDiscoveryCriteria
    ) -> List[A2AAgent]:
        """Discover agents from a specific registry endpoint"""
        try:
            headers = {}
            if endpoint.requires_authentication and endpoint.auth_token:
                headers["Authorization"] = f"Bearer {endpoint.auth_token}"
            
            # Prepare discovery request
            discovery_request = {
                "capabilities": criteria.capabilities_needed,
                "agent_type": criteria.agent_type,
                "location": criteria.location,
                "business_category": criteria.business_category,
                "max_results": min(criteria.max_results, endpoint.max_agents_per_request)
            }
            
            # Use connection pool for better performance
            pool_name = f"registry_{endpoint.url.replace('://', '_').replace('/', '_')}"
            pool_config = REGISTRY_POOL_CONFIG
            pool_config.connect_timeout = endpoint.timeout_seconds
            
            client = self._pool_manager.get_or_create_pool(pool_name, endpoint.url, pool_config)
            
            response = await client.post(
                "/discover",
                json=discovery_request,
                headers=headers
            )
            response.raise_for_status()
                
                data = response.json()
                agents_data = data.get("agents", [])
                
                # Convert to A2AAgent objects
                agents = []
                for agent_data in agents_data:
                    try:
                        agent = A2AAgent(**agent_data)
                        agents.append(agent)
                    except Exception as e:
                        logger.warning(f"Failed to parse agent data: {e}")
                        continue
                
                logger.info(f"Discovered {len(agents)} agents from {endpoint.url}")
                return agents
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout discovering from registry {endpoint.url}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error discovering from registry {endpoint.url}: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error discovering from registry {endpoint.url}: {e}")
            return []
    
    def _filter_endpoints_by_criteria(self, criteria: AgentDiscoveryCriteria) -> List[RegistryEndpoint]:
        """Filter registry endpoints based on discovery criteria"""
        eligible_endpoints = []
        
        for endpoint in self._registry_endpoints:
            # Check if network type is preferred
            if criteria.preferred_networks and endpoint.network_type not in criteria.preferred_networks:
                continue
            
            # Check if network type is excluded
            if endpoint.network_type in criteria.exclude_networks:
                continue
            
            eligible_endpoints.append(endpoint)
        
        return eligible_endpoints
    
    async def _apply_reputation_scoring(
        self, 
        agents: List[A2AAgent], 
        criteria: AgentDiscoveryCriteria
    ) -> List[A2AAgent]:
        """Apply reputation scoring to discovered agents"""
        scored_agents = []
        
        for agent in agents:
            # Get or calculate reputation score
            reputation = await self._get_agent_reputation(agent.id)
            
            if reputation.overall_score >= criteria.min_reputation_score:
                # Add reputation metadata to agent
                if not hasattr(agent, 'metadata'):
                    agent.metadata = {}
                agent.metadata['reputation_score'] = reputation.overall_score
                agent.metadata['response_time_ms'] = reputation.response_time_score * 5000  # Convert to ms
                
                scored_agents.append(agent)
        
        return scored_agents
    
    async def _get_agent_reputation(self, agent_id: str) -> AgentReputationScore:
        """Get agent reputation score, calculating if not cached"""
        if agent_id in self._agent_reputation_cache:
            cached = self._agent_reputation_cache[agent_id]
            # Check if cache is still valid (24 hours)
            if datetime.utcnow() - cached.last_updated < timedelta(hours=24):
                return cached
        
        # Calculate new reputation score
        reputation = await self._calculate_agent_reputation(agent_id)
        self._agent_reputation_cache[agent_id] = reputation
        return reputation
    
    async def _calculate_agent_reputation(self, agent_id: str) -> AgentReputationScore:
        """Calculate reputation score for an agent"""
        # This would integrate with reputation systems
        # For now, return a mock score based on agent ID hash
        import hashlib
        hash_value = int(hashlib.md5(agent_id.encode()).hexdigest()[:8], 16)
        
        # Generate scores between 0.3 and 1.0
        overall_score = 0.3 + (hash_value % 700) / 1000
        response_time_score = 0.5 + (hash_value % 400) / 1000
        success_rate_score = 0.7 + (hash_value % 300) / 1000
        user_rating_score = 0.4 + (hash_value % 600) / 1000
        network_verification_score = 0.8 + (hash_value % 200) / 1000
        
        return AgentReputationScore(
            agent_id=agent_id,
            overall_score=overall_score,
            response_time_score=response_time_score,
            success_rate_score=success_rate_score,
            user_rating_score=user_rating_score,
            network_verification_score=network_verification_score,
            last_updated=datetime.utcnow()
        )
    
    def _sort_agents_by_quality(
        self, 
        agents: List[A2AAgent], 
        criteria: AgentDiscoveryCriteria
    ) -> List[A2AAgent]:
        """Sort agents by quality metrics"""
        def quality_score(agent: A2AAgent) -> float:
            reputation = agent.metadata.get('reputation_score', 0.5)
            response_time = agent.metadata.get('response_time_ms', 5000)
            
            # Weight reputation more heavily than response time
            time_score = max(0, 1.0 - (response_time / criteria.max_response_time_ms))
            return (reputation * 0.7) + (time_score * 0.3)
        
        return sorted(agents, key=quality_score, reverse=True)
    
    def _generate_cache_key(self, criteria: AgentDiscoveryCriteria) -> str:
        """Generate cache key for discovery criteria"""
        import hashlib
        key_data = f"{criteria.capabilities_needed}:{criteria.agent_type}:{criteria.location}:{criteria.business_category}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _get_cached_agents(self, cache_key: str) -> Optional[List[A2AAgent]]:
        """Get cached agents if available and not expired"""
        async with self._cache_lock:
            if cache_key in self._discovery_cache:
                return self._discovery_cache[cache_key]
        return None
    
    async def _cache_agents(self, cache_key: str, agents: List[A2AAgent]):
        """Cache discovered agents"""
        async with self._cache_lock:
            self._discovery_cache[cache_key] = agents
            
            # Limit cache size
            if len(self._discovery_cache) > 100:
                # Remove oldest entries
                oldest_key = next(iter(self._discovery_cache))
                del self._discovery_cache[oldest_key]
    
    def _deduplicate_agents(self, agents: List[A2AAgent]) -> List[A2AAgent]:
        """Remove duplicate agents by ID"""
        seen_ids: Set[str] = set()
        unique_agents = []
        
        for agent in agents:
            if agent.id not in seen_ids:
                seen_ids.add(agent.id)
                unique_agents.append(agent)
        
        return unique_agents
    
    async def register_agent_with_networks(self, agent_card: A2AAgentCard) -> Dict[str, bool]:
        """Register this agent with all configured registry networks"""
        registration_results = {}
        
        for endpoint in self._registry_endpoints:
            try:
                success = await self._register_with_registry(endpoint, agent_card)
                registration_results[endpoint.url] = success
            except Exception as e:
                logger.error(f"Failed to register with {endpoint.url}: {e}")
                registration_results[endpoint.url] = False
        
        return registration_results
    
    async def _register_with_registry(self, endpoint: RegistryEndpoint, agent_card: A2AAgentCard) -> bool:
        """Register agent with a specific registry"""
        try:
            headers = {"Content-Type": "application/json"}
            if endpoint.requires_authentication and endpoint.auth_token:
                headers["Authorization"] = f"Bearer {endpoint.auth_token}"
            
            async with httpx.AsyncClient(timeout=endpoint.timeout_seconds) as client:
                response = await client.post(
                    f"{endpoint.url}/register",
                    json=agent_card.dict(),
                    headers=headers
                )
                response.raise_for_status()
                
                logger.info(f"Successfully registered agent with {endpoint.url}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register with registry {endpoint.url}: {e}")
            return False
    
    async def close(self):
        """Close HTTP client connections"""
        await self._http_client.aclose()


# Global registry network client instance
_registry_client: Optional[A2ARegistryNetworkClient] = None


def get_registry_network_client() -> A2ARegistryNetworkClient:
    """Get the global registry network client instance"""
    global _registry_client
    if _registry_client is None:
        _registry_client = A2ARegistryNetworkClient()
    return _registry_client


# Enhanced discovery endpoint
async def discover_agents_enhanced(criteria: AgentDiscoveryCriteria) -> A2ADiscoveryResponse:
    """
    Enhanced agent discovery across multiple registry networks.
    """
    client = get_registry_network_client()
    return await client.discover_agents_across_networks(criteria)
