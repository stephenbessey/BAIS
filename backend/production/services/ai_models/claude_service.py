"""
Anthropic Claude API Integration Service
Provides seamless integration with Anthropic's Claude models for BAIS
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ClaudeMessage(BaseModel):
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")

class ClaudeRequest(BaseModel):
    model: str = Field(default="claude-3-sonnet-20240229", description="Claude model to use")
    max_tokens: int = Field(default=1024, ge=1, le=4096)
    messages: List[ClaudeMessage] = Field(..., description="Conversation messages")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=1, le=500)
    stop_sequences: List[str] = Field(default_factory=list)
    stream: bool = Field(default=False)

class ClaudeResponse(BaseModel):
    id: str
    type: str
    role: str
    content: List[Dict[str, Any]]
    model: str
    stop_reason: str
    stop_sequence: Optional[str]
    usage: Dict[str, int]

class ClaudeService:
    """Anthropic Claude API integration for BAIS"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://api.anthropic.com/v1"
        self.default_model = "claude-3-sonnet-20240229"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        )
        
    def _get_api_key(self) -> str:
        """Get Anthropic API key from environment"""
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        return api_key
    
    async def send_chat_message(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send chat message to Claude"""
        
        messages = [ClaudeMessage(role="user", content=prompt)]
        
        request = ClaudeRequest(
            model=model or self.default_model,
            messages=messages,
            **kwargs
        )
        
        # Add system prompt if provided
        request_data = request.dict()
        if system_prompt:
            request_data["system"] = system_prompt
        
        try:
            logger.info(f"Sending request to Claude {request.model}")
            start_time = datetime.now()
            
            response = await self.client.post(
                f"{self.base_url}/messages",
                json=request_data
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Claude response received in {duration:.2f}s")
            
            return self._process_response(response_data, duration)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Claude API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Claude API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Claude request failed: {str(e)}")
            raise
    
    def _process_response(self, response_data: Dict, duration: float) -> Dict[str, Any]:
        """Process Claude response into BAIS format"""
        
        content = response_data["content"][0]["text"]
        
        return {
            "content": content,
            "model": response_data["model"],
            "usage": response_data["usage"],
            "total_duration": duration,
            "finish_reason": response_data["stop_reason"],
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available Claude models"""
        
        # Claude models are static, so we return the known models
        models = [
            {
                "id": "claude-3-opus-20240229",
                "name": "claude-3-opus-20240229",
                "provider": "anthropic",
                "description": "Claude 3 Opus - Most powerful model for complex tasks",
                "max_tokens": 4096
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "claude-3-sonnet-20240229",
                "provider": "anthropic",
                "description": "Claude 3 Sonnet - Balanced performance and speed",
                "max_tokens": 4096
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "claude-3-haiku-20240307",
                "provider": "anthropic",
                "description": "Claude 3 Haiku - Fast and efficient for simple tasks",
                "max_tokens": 4096
            }
        ]
        
        return models
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

# Claude function calling support
class ClaudeFunctionCall:
    """Claude function calling integration for BAIS tools"""
    
    def __init__(self, claude_service: ClaudeService):
        self.claude_service = claude_service
    
    async def call_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: str = "claude-3-sonnet-20240229"
    ) -> Dict[str, Any]:
        """Send request with function calling capabilities"""
        
        messages = [ClaudeMessage(role="user", content=prompt)]
        
        request_data = {
            "model": model,
            "messages": [msg.dict() for msg in messages],
            "max_tokens": 1024,
            "tools": functions
        }
        
        if system_prompt:
            request_data["system"] = system_prompt
        
        try:
            response = await self.claude_service.client.post(
                f"{self.claude_service.base_url}/messages",
                json=request_data
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            return self._process_function_response(response_data)
            
        except Exception as e:
            logger.error(f"Claude function call failed: {str(e)}")
            raise
    
    def _process_function_response(self, response_data: Dict) -> Dict[str, Any]:
        """Process function calling response"""
        
        content = response_data["content"][0]["text"]
        tools_used = []
        
        # Check for tool use in content
        for item in response_data["content"]:
            if item["type"] == "tool_use":
                tools_used.append(item)
        
        result = {
            "content": content,
            "tools_used": tools_used,
            "model": response_data["model"],
            "usage": response_data["usage"],
            "timestamp": datetime.now().isoformat()
        }
        
        return result

# BAIS Integration Adapter
class BAISClaudeAdapter:
    """BAIS adapter for Claude integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.claude_service = ClaudeService(api_key)
        self.function_caller = ClaudeFunctionCall(self.claude_service)
    
    async def process_bais_request(
        self,
        prompt: str,
        business_type: str,
        request_type: str,
        user_preferences: Optional[str] = None,
        model: str = "claude-3-sonnet-20240229"
    ) -> Dict[str, Any]:
        """Process BAIS request through Claude"""
        
        system_prompt = self._build_bais_system_prompt(
            business_type, request_type, user_preferences
        )
        
        response = await self.claude_service.send_chat_message(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model
        )
        
        # Add BAIS metadata
        response.update({
            "business_type": business_type,
            "request_type": request_type,
            "ai_provider": "anthropic",
            "model_used": model
        })
        
        return response
    
    def _build_bais_system_prompt(
        self, 
        business_type: str, 
        request_type: str, 
        user_preferences: Optional[str]
    ) -> str:
        """Build BAIS-specific system prompt for Claude"""
        
        base_prompt = f"""You are a BAIS (Business-Agent Integration Standard) AI assistant specializing in {business_type} businesses.

You help users with {request_type} requests by providing accurate, helpful responses and guiding them through business processes.

Key guidelines:
- Be professional and helpful
- Provide accurate information
- Guide users through business workflows
- Ask clarifying questions when needed
- Maintain context throughout the conversation
"""
        
        if user_preferences:
            base_prompt += f"\nUser preferences: {user_preferences}"
        
        return base_prompt
    
    async def close(self):
        """Close connections"""
        await self.claude_service.close()



