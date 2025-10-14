"""
AI Models Integration Package for BAIS
Provides universal access to multiple AI providers
"""

from .universal_ai_router import (
    UniversalAIRouter,
    AIProvider,
    process_bais_request,
    get_available_models,
    get_provider_status,
    universal_router
)

from .openai_service import BAISOpenAIAdapter
from .gemini_service import BAISGeminiAdapter
from .claude_service import BAISClaudeAdapter

__all__ = [
    "UniversalAIRouter",
    "AIProvider", 
    "process_bais_request",
    "get_available_models",
    "get_provider_status",
    "universal_router",
    "BAISOpenAIAdapter",
    "BAISGeminiAdapter", 
    "BAISClaudeAdapter"
]



