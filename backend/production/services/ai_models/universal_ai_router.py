"""
Universal AI Model Router for BAIS
Routes requests to appropriate AI models (OpenAI, Google, Anthropic, Ollama, etc.)
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import os

from .openai_service import BAISOpenAIAdapter
from .gemini_service import BAISGeminiAdapter
from .claude_service import BAISClaudeAdapter

logger = logging.getLogger(__name__)

class AIProvider(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    AUTO = "auto"

class UniversalAIRouter:
    """Universal router for multiple AI providers in BAIS"""
    
    def __init__(self):
        self.adapters = {}
        self.default_provider = self._get_default_provider()
        self._initialize_adapters()
    
    def _get_default_provider(self) -> AIProvider:
        """Get default AI provider from environment or config"""
        provider = os.getenv("BAIS_DEFAULT_AI_PROVIDER", "auto")
        return AIProvider(provider.lower())
    
    def _initialize_adapters(self):
        """Initialize available AI adapters"""
        
        # OpenAI adapter
        if os.getenv("OPENAI_API_KEY"):
            try:
                self.adapters[AIProvider.OPENAI] = BAISOpenAIAdapter()
                logger.info("OpenAI adapter initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI adapter: {e}")
        
        # Google Gemini adapter
        if os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY"):
            try:
                self.adapters[AIProvider.GOOGLE] = BAISGeminiAdapter()
                logger.info("Google Gemini adapter initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Gemini adapter: {e}")
        
        # Anthropic Claude adapter
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.adapters[AIProvider.ANTHROPIC] = BAISClaudeAdapter()
                logger.info("Anthropic Claude adapter initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic Claude adapter: {e}")
        
        # Ollama adapter (existing)
        try:
            from ..ollama_service import OllamaService
            self.adapters[AIProvider.OLLAMA] = OllamaService()
            logger.info("Ollama adapter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama adapter: {e}")
    
    async def process_request(
        self,
        prompt: str,
        business_type: str,
        request_type: str,
        user_preferences: Optional[str] = None,
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process request through specified or auto-selected AI provider"""
        
        # Determine which provider to use
        selected_provider = provider or self.default_provider
        
        if selected_provider == AIProvider.AUTO:
            selected_provider = self._select_best_provider(business_type, request_type)
        
        if selected_provider not in self.adapters:
            raise Exception(f"AI provider {selected_provider} not available")
        
        adapter = self.adapters[selected_provider]
        
        try:
            logger.info(f"Processing request with {selected_provider.value}")
            
            if selected_provider == AIProvider.OLLAMA:
                # Ollama has different interface
                response = await adapter.sendChatMessage(prompt)
                return self._standardize_ollama_response(response, business_type, request_type)
            else:
                # Standard BAIS adapter interface
                response = await adapter.process_bais_request(
                    prompt=prompt,
                    business_type=business_type,
                    request_type=request_type,
                    user_preferences=user_preferences,
                    model=model
                )
                return response
                
        except Exception as e:
            logger.error(f"Request failed with {selected_provider.value}: {e}")
            
            # Try fallback providers
            fallback_providers = [p for p in self.adapters.keys() if p != selected_provider]
            for fallback in fallback_providers:
                try:
                    logger.info(f"Trying fallback provider: {fallback.value}")
                    adapter = self.adapters[fallback]
                    
                    if fallback == AIProvider.OLLAMA:
                        response = await adapter.sendChatMessage(prompt)
                        return self._standardize_ollama_response(response, business_type, request_type)
                    else:
                        response = await adapter.process_bais_request(
                            prompt=prompt,
                            business_type=business_type,
                            request_type=request_type,
                            user_preferences=user_preferences,
                            model=model
                        )
                        return response
                        
                except Exception as fallback_error:
                    logger.error(f"Fallback {fallback.value} also failed: {fallback_error}")
                    continue
            
            raise Exception(f"All AI providers failed. Last error: {e}")
    
    def _select_best_provider(self, business_type: str, request_type: str) -> AIProvider:
        """Select best AI provider based on request characteristics"""
        
        # Priority order for different use cases
        if request_type in ["book", "modify", "cancel"]:
            # Transaction-heavy operations - prefer Claude for reliability
            if AIProvider.ANTHROPIC in self.adapters:
                return AIProvider.ANTHROPIC
        
        if business_type == "retail" and request_type == "search":
            # Product search - prefer GPT-4 for reasoning
            if AIProvider.OPENAI in self.adapters:
                return AIProvider.OPENAI
        
        # Default priority: Claude > OpenAI > Google > Ollama
        priority_order = [
            AIProvider.ANTHROPIC,
            AIProvider.OPENAI,
            AIProvider.GOOGLE,
            AIProvider.OLLAMA
        ]
        
        for provider in priority_order:
            if provider in self.adapters:
                return provider
        
        raise Exception("No AI providers available")
    
    def _standardize_ollama_response(
        self, 
        ollama_response: Dict, 
        business_type: str, 
        request_type: str
    ) -> Dict[str, Any]:
        """Standardize Ollama response to match other providers"""
        
        return {
            "content": ollama_response.get("content", ""),
            "model": ollama_response.get("model", "unknown"),
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            "total_duration": ollama_response.get("total_duration", 0),
            "timestamp": datetime.now().isoformat(),
            "business_type": business_type,
            "request_type": request_type,
            "ai_provider": "ollama",
            "model_used": ollama_response.get("model", "unknown")
        }
    
    async def get_available_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available models from all providers"""
        
        models = {}
        
        for provider, adapter in self.adapters.items():
            try:
                if provider == AIProvider.OLLAMA:
                    # Ollama models are handled differently
                    models[provider.value] = [
                        {
                            "id": "ollama-local",
                            "name": "ollama-local",
                            "provider": "ollama",
                            "description": "Local Ollama model"
                        }
                    ]
                else:
                    provider_models = await adapter.get_available_models()
                    models[provider.value] = provider_models
                    
            except Exception as e:
                logger.error(f"Failed to get models from {provider.value}: {e}")
                models[provider.value] = []
        
        return models
    
    async def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all AI providers"""
        
        status = {}
        
        for provider, adapter in self.adapters.items():
            try:
                # Test each provider with a simple request
                test_prompt = "Hello, this is a test message."
                
                if provider == AIProvider.OLLAMA:
                    response = await adapter.sendChatMessage(test_prompt)
                    status[provider.value] = {
                        "available": True,
                        "response_time": response.get("total_duration", 0),
                        "model": response.get("model", "unknown")
                    }
                else:
                    response = await adapter.process_bais_request(
                        prompt=test_prompt,
                        business_type="test",
                        request_type="search"
                    )
                    status[provider.value] = {
                        "available": True,
                        "response_time": response.get("total_duration", 0),
                        "model": response.get("model_used", "unknown")
                    }
                    
            except Exception as e:
                status[provider.value] = {
                    "available": False,
                    "error": str(e)
                }
        
        return status
    
    async def close(self):
        """Close all adapter connections"""
        
        for adapter in self.adapters.values():
            try:
                if hasattr(adapter, 'close'):
                    await adapter.close()
            except Exception as e:
                logger.error(f"Error closing adapter: {e}")

# Global router instance
universal_router = UniversalAIRouter()

# Convenience functions
async def process_bais_request(
    prompt: str,
    business_type: str,
    request_type: str,
    user_preferences: Optional[str] = None,
    provider: Optional[AIProvider] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Process BAIS request through universal AI router"""
    return await universal_router.process_request(
        prompt=prompt,
        business_type=business_type,
        request_type=request_type,
        user_preferences=user_preferences,
        provider=provider,
        model=model
    )

async def get_available_models() -> Dict[str, List[Dict[str, Any]]]:
    """Get all available AI models"""
    return await universal_router.get_available_models()

async def get_provider_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all AI providers"""
    return await universal_router.get_provider_status()



