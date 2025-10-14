"""
Google Gemini API Integration Service
Provides seamless integration with Google's Gemini models for BAIS
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class GeminiContent(BaseModel):
    parts: List[Dict[str, str]] = Field(..., description="Content parts")
    role: str = Field(..., description="Content role: user or model")

class GeminiRequest(BaseModel):
    contents: List[GeminiContent] = Field(..., description="Conversation contents")
    generationConfig: Dict[str, Any] = Field(default_factory=dict)
    safetySettings: List[Dict[str, Any]] = Field(default_factory=list)

class GeminiResponse(BaseModel):
    candidates: List[Dict[str, Any]]
    usageMetadata: Dict[str, int]

class GeminiService:
    """Google Gemini API integration for BAIS"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.default_model = "gemini-pro"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            params={"key": self.api_key}
        )
        
    def _get_api_key(self) -> str:
        """Get Google AI API key from environment"""
        import os
        api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY or GEMINI_API_KEY environment variable is required")
        return api_key
    
    async def send_chat_message(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send chat message to Gemini"""
        
        contents = []
        
        # Add system prompt as user message if provided
        if system_prompt:
            contents.append(GeminiContent(
                parts=[{"text": system_prompt}],
                role="user"
            ))
            # Add empty model response to maintain conversation flow
            contents.append(GeminiContent(
                parts=[{"text": "I understand. I'm ready to help with your request."}],
                role="model"
            ))
        
        # Add user prompt
        contents.append(GeminiContent(
            parts=[{"text": prompt}],
            role="user"
        ))
        
        request = GeminiRequest(
            contents=contents,
            generationConfig=self._build_generation_config(**kwargs),
            safetySettings=self._get_default_safety_settings()
        )
        
        try:
            model_name = model or self.default_model
            logger.info(f"Sending request to Gemini {model_name}")
            start_time = datetime.now()
            
            response = await self.client.post(
                f"{self.base_url}/models/{model_name}:generateContent",
                json=request.dict()
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Gemini response received in {duration:.2f}s")
            
            return self._process_response(response_data, duration, model_name)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Gemini API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Gemini request failed: {str(e)}")
            raise
    
    def _build_generation_config(
        self,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        top_k: int = 40,
        **kwargs
    ) -> Dict[str, Any]:
        """Build generation configuration for Gemini"""
        
        config = {
            "temperature": temperature,
            "topP": top_p,
            "topK": top_k,
        }
        
        if max_tokens:
            config["maxOutputTokens"] = max_tokens
        
        return config
    
    def _get_default_safety_settings(self) -> List[Dict[str, Any]]:
        """Get default safety settings for Gemini"""
        return [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
    
    def _process_response(self, response_data: Dict, duration: float, model: str) -> Dict[str, Any]:
        """Process Gemini response into BAIS format"""
        
        if not response_data.get("candidates"):
            raise Exception("No candidates in Gemini response")
        
        candidate = response_data["candidates"][0]
        
        if "content" not in candidate:
            raise Exception("No content in Gemini candidate")
        
        content = candidate["content"]["parts"][0]["text"]
        
        return {
            "content": content,
            "model": model,
            "usage": response_data.get("usageMetadata", {}),
            "total_duration": duration,
            "finish_reason": candidate.get("finishReason", "STOP"),
            "timestamp": datetime.now().isoformat(),
            "safety_ratings": candidate.get("safetyRatings", [])
        }
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available Gemini models"""
        
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            models_data = response.json()
            
            # Filter for generative models
            generative_models = [
                model for model in models_data.get("models", [])
                if "generateContent" in model.get("supportedGenerationMethods", [])
            ]
            
            return [
                {
                    "id": model["name"].split("/")[-1],
                    "name": model["name"],
                    "provider": "google",
                    "description": model.get("displayName", model["name"]),
                    "version": model.get("version", "unknown")
                }
                for model in generative_models
            ]
            
        except Exception as e:
            logger.error(f"Failed to get Gemini models: {str(e)}")
            return []
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

# Gemini function calling support
class GeminiFunctionCall:
    """Gemini function calling integration for BAIS tools"""
    
    def __init__(self, gemini_service: GeminiService):
        self.gemini_service = gemini_service
    
    async def call_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: str = "gemini-pro"
    ) -> Dict[str, Any]:
        """Send request with function calling capabilities"""
        
        contents = []
        
        # Add system prompt
        if system_prompt:
            contents.append(GeminiContent(
                parts=[{"text": system_prompt}],
                role="user"
            ))
            contents.append(GeminiContent(
                parts=[{"text": "I understand and can use the provided functions."}],
                role="model"
            ))
        
        # Add user prompt
        contents.append(GeminiContent(
            parts=[{"text": prompt}],
            role="user"
        ))
        
        request_data = {
            "contents": [content.dict() for content in contents],
            "tools": [{"functionDeclarations": functions}],
            "generationConfig": self.gemini_service._build_generation_config()
        }
        
        try:
            response = await self.gemini_service.client.post(
                f"{self.gemini_service.base_url}/models/{model}:generateContent",
                json=request_data
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            return self._process_function_response(response_data, model)
            
        except Exception as e:
            logger.error(f"Gemini function call failed: {str(e)}")
            raise
    
    def _process_function_response(self, response_data: Dict, model: str) -> Dict[str, Any]:
        """Process function calling response"""
        
        candidate = response_data["candidates"][0]
        content = candidate["content"]
        
        result = {
            "content": content["parts"][0]["text"] if content["parts"] else None,
            "function_calls": [
                part for part in content["parts"] 
                if "functionCall" in part
            ],
            "model": model,
            "usage": response_data.get("usageMetadata", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        return result

# BAIS Integration Adapter
class BAISGeminiAdapter:
    """BAIS adapter for Gemini integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.gemini_service = GeminiService(api_key)
        self.function_caller = GeminiFunctionCall(self.gemini_service)
    
    async def process_bais_request(
        self,
        prompt: str,
        business_type: str,
        request_type: str,
        user_preferences: Optional[str] = None,
        model: str = "gemini-pro"
    ) -> Dict[str, Any]:
        """Process BAIS request through Gemini"""
        
        system_prompt = self._build_bais_system_prompt(
            business_type, request_type, user_preferences
        )
        
        response = await self.gemini_service.send_chat_message(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model
        )
        
        # Add BAIS metadata
        response.update({
            "business_type": business_type,
            "request_type": request_type,
            "ai_provider": "google",
            "model_used": model
        })
        
        return response
    
    def _build_bais_system_prompt(
        self, 
        business_type: str, 
        request_type: str, 
        user_preferences: Optional[str]
    ) -> str:
        """Build BAIS-specific system prompt for Gemini"""
        
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
        await self.gemini_service.close()



