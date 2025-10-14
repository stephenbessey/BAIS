"""
OpenAI ChatGPT API Integration Service
Provides seamless integration with OpenAI's GPT models for BAIS
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class OpenAIMessage(BaseModel):
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")

class OpenAIRequest(BaseModel):
    model: str = Field(default="gpt-4", description="OpenAI model to use")
    messages: List[OpenAIMessage] = Field(..., description="Conversation messages")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4096)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    stream: bool = Field(default=False)

class OpenAIResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

class OpenAIService:
    """OpenAI ChatGPT API integration for BAIS"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://api.openai.com/v1"
        self.default_model = "gpt-4"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
    def _get_api_key(self) -> str:
        """Get OpenAI API key from environment"""
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return api_key
    
    async def send_chat_message(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send chat message to OpenAI"""
        
        messages = []
        
        if system_prompt:
            messages.append(OpenAIMessage(role="system", content=system_prompt))
        
        messages.append(OpenAIMessage(role="user", content=prompt))
        
        request = OpenAIRequest(
            model=model or self.default_model,
            messages=messages,
            **kwargs
        )
        
        try:
            logger.info(f"Sending request to OpenAI {request.model}")
            start_time = datetime.now()
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=request.dict()
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"OpenAI response received in {duration:.2f}s")
            
            return self._process_response(response_data, duration)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"OpenAI API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"OpenAI request failed: {str(e)}")
            raise
    
    def _process_response(self, response_data: Dict, duration: float) -> Dict[str, Any]:
        """Process OpenAI response into BAIS format"""
        
        choice = response_data["choices"][0]
        message = choice["message"]
        
        return {
            "content": message["content"],
            "model": response_data["model"],
            "usage": response_data["usage"],
            "total_duration": duration,
            "finish_reason": choice["finish_reason"],
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available OpenAI models"""
        
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            models_data = response.json()
            
            # Filter for chat completion models
            chat_models = [
                model for model in models_data["data"] 
                if "gpt" in model["id"].lower()
            ]
            
            return [
                {
                    "id": model["id"],
                    "name": model["id"],
                    "provider": "openai",
                    "description": f"OpenAI {model['id']} model"
                }
                for model in chat_models
            ]
            
        except Exception as e:
            logger.error(f"Failed to get OpenAI models: {str(e)}")
            return []
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

# ChatGPT-specific function calling support
class ChatGPTFunctionCall:
    """ChatGPT function calling integration for BAIS tools"""
    
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service
    
    async def call_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """Send request with function calling capabilities"""
        
        messages = []
        
        if system_prompt:
            messages.append(OpenAIMessage(role="system", content=system_prompt))
        
        messages.append(OpenAIMessage(role="user", content=prompt))
        
        request_data = {
            "model": model,
            "messages": [msg.dict() for msg in messages],
            "functions": functions,
            "function_call": "auto"
        }
        
        try:
            response = await self.openai_service.client.post(
                f"{self.openai_service.base_url}/chat/completions",
                json=request_data
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            return self._process_function_response(response_data)
            
        except Exception as e:
            logger.error(f"ChatGPT function call failed: {str(e)}")
            raise
    
    def _process_function_response(self, response_data: Dict) -> Dict[str, Any]:
        """Process function calling response"""
        
        choice = response_data["choices"][0]
        message = choice["message"]
        
        result = {
            "content": message.get("content"),
            "function_call": message.get("function_call"),
            "model": response_data["model"],
            "usage": response_data["usage"],
            "timestamp": datetime.now().isoformat()
        }
        
        return result

# BAIS Integration Adapter
class BAISOpenAIAdapter:
    """BAIS adapter for OpenAI integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.openai_service = OpenAIService(api_key)
        self.function_caller = ChatGPTFunctionCall(self.openai_service)
    
    async def process_bais_request(
        self,
        prompt: str,
        business_type: str,
        request_type: str,
        user_preferences: Optional[str] = None,
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """Process BAIS request through OpenAI"""
        
        system_prompt = self._build_bais_system_prompt(
            business_type, request_type, user_preferences
        )
        
        response = await self.openai_service.send_chat_message(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model
        )
        
        # Add BAIS metadata
        response.update({
            "business_type": business_type,
            "request_type": request_type,
            "ai_provider": "openai",
            "model_used": model
        })
        
        return response
    
    def _build_bais_system_prompt(
        self, 
        business_type: str, 
        request_type: str, 
        user_preferences: Optional[str]
    ) -> str:
        """Build BAIS-specific system prompt for OpenAI"""
        
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
        await self.openai_service.close()



