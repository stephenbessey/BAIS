"""
Universal BAIS Webhook Endpoints
Handles tool calls from Claude, ChatGPT, and Gemini for ALL businesses
"""

from fastapi import APIRouter, HTTPException, Header, Request, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import hmac
import hashlib
import json
import logging
from datetime import datetime

from ...core.universal_tools import BAISUniversalToolHandler
from ...core.database_models import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/llm-webhooks", tags=["Universal LLM Integration"])


# ============================================================================
# Dependency Injection
# ============================================================================

def get_universal_tool_handler() -> BAISUniversalToolHandler:
    """Get universal tool handler instance"""
    return BAISUniversalToolHandler()


# ============================================================================
# Universal Tool Handler (works for ALL businesses)
# ============================================================================

class UniversalToolRequest(BaseModel):
    """Base model for universal tool requests"""
    tool_name: str
    tool_input: Dict[str, Any]


class UniversalToolResponse(BaseModel):
    """Base model for universal tool responses"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = datetime.utcnow().isoformat()


# ============================================================================
# Claude Webhook Endpoint
# ============================================================================

@router.post("/claude/tool-use", response_model=UniversalToolResponse)
async def handle_claude_tool_use(
    request: Request,
    x_claude_signature: Optional[str] = Header(None),
    handler: BAISUniversalToolHandler = Depends(get_universal_tool_handler)
):
    """
    Receives tool use requests from Claude for ANY business.
    Claude can search, get info, and execute services for all BAIS businesses.
    """
    
    try:
        # Verify request is from Anthropic
        body = await request.body()
        if x_claude_signature:
            verify_claude_signature(body, x_claude_signature)
        
        data = await request.json()
        logger.info(f"Claude tool use request: {data}")
        
        # Extract tool call information
        tool_use = data.get("content", [{}])[0]
        tool_name = tool_use.get("name", "")
        tool_input = tool_use.get("input", {})
        tool_use_id = tool_use.get("id", "")
        
        # Route to appropriate handler based on tool name
        if tool_name == "bais_search_businesses":
            result = await handler.search_businesses(
                query=tool_input.get("query"),
                category=tool_input.get("category"),
                location=tool_input.get("location")
            )
            
        elif tool_name == "bais_get_business_services":
            result = await handler.get_business_services(
                business_id=tool_input.get("business_id")
            )
            
        elif tool_name == "bais_execute_service":
            result = await handler.execute_service(
                business_id=tool_input.get("business_id"),
                service_id=tool_input.get("service_id"),
                parameters=tool_input.get("parameters", {}),
                customer_info=tool_input.get("customer_info", {})
            )
            
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Return in UniversalToolResponse format
        return UniversalToolResponse(
            success=True,
            result=result,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Claude tool use error: {str(e)}", exc_info=True)
        tool_use_id = tool_use_id if 'tool_use_id' in locals() else ""
        return UniversalToolResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


# ============================================================================
# ChatGPT Webhook Endpoint
# ============================================================================

@router.post("/chatgpt/function-call", response_model=UniversalToolResponse)
async def handle_chatgpt_function_call(
    request: Request,
    x_openai_signature: Optional[str] = Header(None),
    handler: BAISUniversalToolHandler = Depends(get_universal_tool_handler)
):
    """
    Receives function calls from ChatGPT for ANY business.
    """
    
    try:
        body = await request.body()
        if x_openai_signature:
            verify_openai_signature(body, x_openai_signature)
        
        data = await request.json()
        logger.info(f"ChatGPT function call request: {data}")
        
        # Extract function call information
        message = data.get("message", {})
        function_call = message.get("function_call", {})
        function_name = function_call.get("name", "")
        function_args = json.loads(function_call.get("arguments", "{}"))
        
        # Route to appropriate handler
        if function_name == "bais_search_businesses":
            result = await handler.search_businesses(
                query=function_args.get("query"),
                category=function_args.get("category"),
                location=function_args.get("location")
            )
            
        elif function_name == "bais_get_business_services":
            result = await handler.get_business_services(
                business_id=function_args.get("business_id")
            )
            
        elif function_name == "bais_execute_service":
            result = await handler.execute_service(
                business_id=function_args.get("business_id"),
                service_id=function_args.get("service_id"),
                parameters=function_args.get("parameters", {}),
                customer_info=function_args.get("customer_info", {})
            )
            
        else:
            raise ValueError(f"Unknown function: {function_name}")
        
        # Return in OpenAI's expected format
        return {
            "role": "function",
            "name": function_name,
            "content": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"ChatGPT function call error: {str(e)}")
        return {
            "role": "function",
            "name": function_name if 'function_name' in locals() else "",
            "content": json.dumps({"error": str(e)})
        }


# ============================================================================
# Gemini Webhook Endpoint
# ============================================================================

@router.post("/gemini/function-call", response_model=UniversalToolResponse)
async def handle_gemini_function_call(
    request: Request,
    x_google_signature: Optional[str] = Header(None),
    handler: BAISUniversalToolHandler = Depends(get_universal_tool_handler)
):
    """
    Receives function calls from Gemini for ANY business.
    """
    
    try:
        body = await request.body()
        if x_google_signature:
            verify_google_signature(body, x_google_signature)
        
        data = await request.json()
        logger.info(f"Gemini function call request: {data}")
        
        # Extract function call information
        function_call = data.get("function_call", {})
        function_name = function_call.get("name", "")
        function_args = function_call.get("args", {})
        
        # Route to appropriate handler
        if function_name == "bais_search_businesses":
            result = await handler.search_businesses(
                query=function_args.get("query"),
                category=function_args.get("category"),
                location=function_args.get("location")
            )
            
        elif function_name == "bais_get_business_services":
            result = await handler.get_business_services(
                business_id=function_args.get("business_id")
            )
            
        elif function_name == "bais_execute_service":
            result = await handler.execute_service(
                business_id=function_args.get("business_id"),
                service_id=function_args.get("service_id"),
                parameters=function_args.get("parameters", {}),
                customer_info=function_args.get("customer_info", {})
            )
            
        else:
            raise ValueError(f"Unknown function: {function_name}")
        
        # Return in Gemini's expected format
        return {
            "functionResponse": {
                "name": function_name,
                "response": result
            }
        }
        
    except Exception as e:
        logger.error(f"Gemini function call error: {str(e)}")
        return {
            "functionResponse": {
                "name": function_name if 'function_name' in locals() else "",
                "response": {"error": str(e)}
            }
        }


# ============================================================================
# Signature Verification
# ============================================================================

def verify_claude_signature(payload: bytes, signature: str) -> None:
    """Verify webhook signature from Anthropic/Claude"""
    import os
    secret = os.getenv("CLAUDE_WEBHOOK_SECRET", "")
    
    if not secret:
        logger.warning("CLAUDE_WEBHOOK_SECRET not set, skipping signature verification")
        return
    
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid Claude signature")


def verify_openai_signature(payload: bytes, signature: str) -> None:
    """Verify webhook signature from OpenAI/ChatGPT"""
    import os
    secret = os.getenv("OPENAI_WEBHOOK_SECRET", "")
    
    if not secret:
        logger.warning("OPENAI_WEBHOOK_SECRET not set, skipping signature verification")
        return
    
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid OpenAI signature")


def verify_google_signature(payload: bytes, signature: str) -> None:
    """Verify webhook signature from Google/Gemini"""
    import os
    secret = os.getenv("GOOGLE_WEBHOOK_SECRET", "")
    
    if not secret:
        logger.warning("GOOGLE_WEBHOOK_SECRET not set, skipping signature verification")
        return
    
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid Google signature")


# ============================================================================
# Health Check and Testing
# ============================================================================

@router.get("/health")
async def webhook_health():
    """Health check for universal webhook endpoints"""
    return {
        "status": "healthy",
        "architecture": "universal",
        "description": "Handles requests for ALL BAIS businesses",
        "endpoints": {
            "claude": "/api/v1/llm-webhooks/claude/tool-use",
            "chatgpt": "/api/v1/llm-webhooks/chatgpt/function-call",
            "gemini": "/api/v1/llm-webhooks/gemini/function-call"
        },
        "tools": {
            "search": "bais_search_businesses",
            "services": "bais_get_business_services",
            "execute": "bais_execute_service"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/test", response_model=UniversalToolResponse)
async def test_universal_tools(
    request: UniversalToolRequest,
    handler: BAISUniversalToolHandler = Depends(get_universal_tool_handler)
):
    """Test endpoint to simulate LLM tool calls"""
    
    try:
        tool_name = request.tool_name
        tool_input = request.tool_input
        
        if tool_name == "bais_search_businesses":
            result = await handler.search_businesses(**tool_input)
        elif tool_name == "bais_get_business_services":
            result = await handler.get_business_services(**tool_input)
        elif tool_name == "bais_execute_service":
            result = await handler.execute_service(**tool_input)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        return UniversalToolResponse(
            success=True,
            result=result,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Test tool call error: {str(e)}")
        return UniversalToolResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


# ============================================================================
# Tool Definition Endpoints
# ============================================================================

@router.get("/tools/definitions")
async def get_tool_definitions():
    """Get tool definitions for all LLM providers"""
    from ...core.universal_tools import BAISUniversalTool
    
    return {
        "status": "success",
        "tools": BAISUniversalTool.get_tool_definitions(),
        "description": "Universal BAIS tools that work for ALL businesses",
        "registration_instructions": {
            "claude": "Register these tools in Anthropic Developer Console",
            "chatgpt": "Register as GPT Actions in OpenAI Platform",
            "gemini": "Register as Function Calling in Google AI Studio"
        }
    }


@router.get("/tools/claude")
async def get_claude_tools():
    """Get Claude-specific tool definitions"""
    from ...core.universal_tools import BAISUniversalTool
    
    return {
        "status": "success",
        "tools": BAISUniversalTool.get_tool_definitions()["claude"],
        "webhook_url": "https://api.baintegrate.com/api/v1/llm-webhooks/claude/tool-use"
    }


@router.get("/tools/chatgpt")
async def get_chatgpt_tools():
    """Get ChatGPT-specific tool definitions"""
    from ...core.universal_tools import BAISUniversalTool
    
    return {
        "status": "success",
        "tools": BAISUniversalTool.get_tool_definitions()["chatgpt"],
        "webhook_url": "https://api.baintegrate.com/api/v1/llm-webhooks/chatgpt/function-call"
    }


@router.get("/tools/gemini")
async def get_gemini_tools():
    """Get Gemini-specific tool definitions"""
    from ...core.universal_tools import BAISUniversalTool
    
    return {
        "status": "success",
        "tools": BAISUniversalTool.get_tool_definitions()["gemini"],
        "webhook_url": "https://api.baintegrate.com/api/v1/llm-webhooks/gemini/function-call"
    }
