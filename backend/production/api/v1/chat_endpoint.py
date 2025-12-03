"""
Chat Endpoint for LLM Integration
Handles chat conversations with Claude, ChatGPT, Gemini, and Ollama
with BAIS tool integration
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
import json
import requests
import logging
from datetime import datetime
from requests.exceptions import ConnectionError, Timeout, RequestException

# Import BAIS tools directly
from ...core.universal_tools import BAISUniversalToolHandler, BAISUniversalTool
from ...core.database_models import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat Interface"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    model: str  # "claude", "chatgpt", "gemini", "ollama"
    messages: List[ChatMessage]
    api_key: Optional[str] = None  # For client-side API key (optional, can use env vars)
    ollama_host: Optional[str] = None  # For Ollama
    ollama_model_name: Optional[str] = None  # For Ollama


class ChatResponse(BaseModel):
    message: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


def get_bais_tool_handler() -> BAISUniversalToolHandler:
    """Get BAIS tool handler with database connection"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url and database_url != "not_set":
            try:
                db_manager = DatabaseManager(database_url)
                logger.info(f"Created BAIS tool handler with database connection")
                # Test connection by checking business count
                try:
                    with db_manager.get_session() as session:
                        from ...core.database_models import Business
                        count = session.query(Business).count()
                        logger.info(f"Database connection verified: {count} businesses in database")
                except Exception as test_error:
                    logger.warning(f"Database connection test failed: {test_error}")
                return BAISUniversalToolHandler(db_manager=db_manager)
            except Exception as e:
                logger.warning(f"Could not create database manager, using handler without DB: {e}")
                import traceback
                logger.debug(f"Database manager creation error: {traceback.format_exc()}")
        else:
            logger.warning("No DATABASE_URL configured, tool handler will use in-memory storage only")
        return BAISUniversalToolHandler()
    except Exception as e:
        logger.warning(f"Error creating tool handler: {e}")
        import traceback
        logger.debug(f"Tool handler creation error: {traceback.format_exc()}")
        return BAISUniversalToolHandler()


def get_bais_tool_definitions() -> List[Dict[str, Any]]:
    """Get BAIS tool definitions directly from the tool class"""
    try:
        tool_defs = BAISUniversalTool.get_tool_definitions()
        return tool_defs.get("claude", [])
    except Exception as e:
        logger.warning(f"Could not get BAIS tool definitions: {e}")
        # Return default tool definitions as fallback
        return [
            {
                "name": "bais_search_businesses",
                "description": "Search for businesses on the BAIS platform",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "category": {"type": "string", "enum": ["restaurant", "hotel", "retail", "service", "healthcare"]},
                        "location": {"type": "string", "description": "City or address"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "bais_get_business_services",
                "description": "Get all available services for a specific business",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "business_id": {"type": "string", "description": "Business identifier"}
                    },
                    "required": ["business_id"]
                }
            },
            {
                "name": "bais_execute_service",
                "description": "Execute a service (create booking, make reservation, etc.)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "business_id": {"type": "string"},
                        "service_id": {"type": "string"},
                        "parameters": {"type": "object"},
                        "customer_info": {"type": "object"}
                    },
                    "required": ["business_id", "service_id", "customer_info"]
                }
            }
        ]


async def call_bais_tool(tool_name: str, tool_input: Dict[str, Any], handler: BAISUniversalToolHandler) -> Dict[str, Any]:
    """Call a BAIS tool directly using the handler (no HTTP overhead)"""
    try:
        if tool_name == "bais_search_businesses":
            result = await handler.search_businesses(
                query=tool_input.get("query", ""),
                category=tool_input.get("category"),
                location=tool_input.get("location")
            )
            return result if isinstance(result, list) else []
            
        elif tool_name == "bais_get_business_services":
            result = await handler.get_business_services(
                business_id=tool_input.get("business_id", "")
            )
            return result if isinstance(result, list) else []
            
        elif tool_name == "bais_execute_service":
            result = await handler.execute_service(
                business_id=tool_input.get("business_id", ""),
                service_id=tool_input.get("service_id", ""),
                parameters=tool_input.get("parameters", {}),
                customer_info=tool_input.get("customer_info", {})
            )
            return result if isinstance(result, dict) else {}
        else:
            logger.warning(f"Unknown tool name: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error(f"Error calling BAIS tool {tool_name}: {e}", exc_info=True)
        return {"error": str(e)}


async def chat_with_claude(messages: List[ChatMessage], api_key: str) -> ChatResponse:
    """Chat with Claude using BAIS tools"""
    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail="anthropic package not installed")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Get BAIS tool handler
    handler = get_bais_tool_handler()
    
    # Get BAIS tools
    bais_tools = get_bais_tool_definitions()
    claude_tools = []
    for tool in bais_tools:
        claude_tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"]
        })
    
    # Convert messages to Claude format
    claude_messages = []
    for msg in messages:
        claude_messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Call Claude with tools
    max_iterations = 5
    iteration = 0
    tool_calls_made = []
    
    while iteration < max_iterations:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=claude_tools,
            messages=claude_messages
        )
        
        # Check if Claude wants to use a tool
        tool_uses = [item for item in response.content if hasattr(item, 'type') and item.type == 'tool_use']
        
        if not tool_uses:
            # Final answer
            text_content = [item for item in response.content if hasattr(item, 'text')]
            if text_content:
                return ChatResponse(message=text_content[0].text, tool_calls=tool_calls_made)
            return ChatResponse(message=str(response.content[0]), tool_calls=tool_calls_made)
        
        # Handle tool calls
        for tool_use in tool_uses:
            tool_calls_made.append({
                "name": tool_use.name,
                "input": tool_use.input
            })
            
            # Call BAIS tool directly (no HTTP overhead)
            tool_result = await call_bais_tool(tool_use.name, tool_use.input, handler)
            
            # Add tool result to conversation
            claude_messages.append({
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": tool_use.id,
                    "name": tool_use.name,
                    "input": tool_use.input
                }]
            })
            
            claude_messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(tool_result)
                }]
            })
        
        iteration += 1
    
    return ChatResponse(message="Max iterations reached", tool_calls=tool_calls_made)


async def chat_with_ollama(messages: List[ChatMessage], host: str, model_name: str) -> ChatResponse:
    """Chat with Ollama using BAIS tools"""
    # Get BAIS tool handler
    handler = get_bais_tool_handler()
    bais_tools = get_bais_tool_definitions()
    
    system_prompt = """You are a helpful AI assistant with access to BAIS (Business-Agent Integration Standard) tools for discovering and booking with businesses.

Available tools:
"""
    for tool in bais_tools:
        system_prompt += f"- {tool['name']}: {tool['description']}\n"
    
    system_prompt += """
IMPORTANT: When you need to use a tool, respond ONLY with valid JSON in this exact format:
{"tool_call": {"name": "tool_name", "input": {...}}}

Do NOT include any other text before or after the JSON. Just the JSON object.

After I execute the tool and provide results, I will give you the tool results and you should respond naturally to help the user.
"""
    
    conversation_history = ""
    for msg in messages[:-1]:
        conversation_history += f"{msg.role.capitalize()}: {msg.content}\n"
    
    last_message = messages[-1].content if messages else ""
    
    if conversation_history:
        full_prompt = f"{system_prompt}\n\nConversation:\n{conversation_history}User: {last_message}\nAssistant:"
    else:
        full_prompt = f"{system_prompt}\n\nUser: {last_message}\nAssistant:"
    
    ollama_url = f"{host}/api/generate"
    payload = {
        "model": model_name,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(ollama_url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        response_text = result.get("response", "").strip()
        
        tool_call_data = None
        tool_name = None
        tool_input = None
        
        try:
            tool_call_data = json.loads(response_text)
            if isinstance(tool_call_data, dict) and "tool_call" in tool_call_data:
                tool_call = tool_call_data.get("tool_call", {})
                tool_name = tool_call.get("name")
                tool_input = tool_call.get("input", {})
        except json.JSONDecodeError:
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*"tool_call"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            if json_match:
                try:
                    tool_call_data = json.loads(json_match.group())
                    if isinstance(tool_call_data, dict) and "tool_call" in tool_call_data:
                        tool_call = tool_call_data.get("tool_call", {})
                        tool_name = tool_call.get("name")
                        tool_input = tool_call.get("input", {})
                except json.JSONDecodeError:
                    pass
        
        if tool_name and tool_input:
            tool_result = await call_bais_tool(tool_name, tool_input, handler)
            logger.info(f"Tool {tool_name} returned: {type(tool_result)}, length: {len(tool_result) if isinstance(tool_result, (list, dict)) else 'N/A'}")
            
            # Tool result is already the actual result (not wrapped in response)
            actual_result = tool_result
            
            # Handle error case
            if isinstance(actual_result, dict) and "error" in actual_result:
                logger.error(f"Tool {tool_name} returned error: {actual_result.get('error')}")
                actual_result = [] if tool_name == "bais_search_businesses" else {}
            
            logger.info(f"Actual result type: {type(actual_result)}, is list: {isinstance(actual_result, list)}, length: {len(actual_result) if isinstance(actual_result, list) else 'N/A'}")
            if isinstance(actual_result, list) and len(actual_result) > 0:
                logger.info(f"First business in results: {actual_result[0].get('name', 'Unknown') if isinstance(actual_result[0], dict) else 'Not a dict'}")
            
            if tool_name == "bais_search_businesses":
                if isinstance(actual_result, list) and len(actual_result) > 0:
                    businesses_formatted = []
                    for idx, biz in enumerate(actual_result[:5], 1):
                        name = biz.get('name', 'Unknown Business')
                        address = biz.get('location', {}).get('address', '')
                        city = biz.get('location', {}).get('city', '')
                        state = biz.get('location', {}).get('state', '')
                        phone = biz.get('phone', '')
                        website = biz.get('website', '')
                        services = [s.get('name', '') for s in biz.get('services', [])[:5]]
                        
                        biz_text = f"{idx}. {name}\n"
                        biz_text += f"   Location: {address}, {city}, {state}\n"
                        if phone:
                            biz_text += f"   Phone: {phone}\n"
                        if website:
                            biz_text += f"   Website: {website}\n"
                        if services:
                            biz_text += f"   Services: {', '.join(services)}\n"
                        businesses_formatted.append(biz_text)
                    
                    businesses_list = "\n".join(businesses_formatted)
                    
                    follow_up_prompt = f"""The user asked: "{last_message}"

I searched the BAIS platform and found these REAL businesses that are registered and available for booking:

{businesses_list}

CRITICAL INSTRUCTIONS:
- You MUST ONLY mention and recommend businesses from the list above
- Do NOT mention, suggest, or reference ANY other businesses
- Do NOT make up business names, addresses, or phone numbers
- If the user wants to book, use ONLY businesses from this list
- Present the information naturally but ONLY use the businesses provided above
- If asked about booking, guide them to use one of the businesses listed above

Respond naturally and helpfully, but ONLY reference the businesses in the list above."""
                else:
                    follow_up_prompt = f"""The user asked: "{last_message}"

I searched the BAIS platform but didn't find any businesses matching that criteria. 

Let the user know that no businesses were found matching their search, and suggest they try a different search term or location."""
            elif tool_name == "bais_get_business_services":
                if isinstance(actual_result, list) and len(actual_result) > 0:
                    services_list = "\n".join([
                        f"• {svc.get('name', 'Unknown')} - {svc.get('description', '')}"
                        for svc in actual_result
                    ])
                    follow_up_prompt = f"""The user asked: "{last_message}"

Here are the available services from the BAIS business:

{services_list}

Present these services naturally and helpfully. Do NOT mention tool calls or JSON."""
                else:
                    follow_up_prompt = f"""The user asked: "{last_message}"

No services were found. Let the user know that no services are currently available."""
            else:
                tool_result_text = json.dumps(actual_result, indent=2)
                follow_up_prompt = f"""The user asked: "{last_message}"

Tool result:
{tool_result_text}

Provide a natural, helpful response based on this result. Do NOT mention tool calls or JSON."""
            
            follow_up_payload = {
                "model": model_name,
                "prompt": follow_up_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7
                }
            }
            
            follow_up_response = requests.post(ollama_url, json=follow_up_payload, timeout=60)
            follow_up_response.raise_for_status()
            follow_up_result = follow_up_response.json()
            final_response = follow_up_result.get("response", "").strip()
            
            if not final_response or final_response == response_text:
                final_response = "I found some information. Let me help you with that."
            
            return ChatResponse(
                message=final_response,
                tool_calls=[{"name": tool_name, "input": tool_input}]
            )
        
        if response_text and not response_text.startswith('{'):
            return ChatResponse(message=response_text)
        
        return ChatResponse(message="I'm here to help you find and book with businesses. What would you like to search for?")
        
    except ConnectionError as e:
        error_msg = str(e)
        if "Connection refused" in error_msg or "Failed to establish" in error_msg:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to connect to Ollama server at {host}. Please verify the server is running and the address is correct."
            )
        raise HTTPException(status_code=503, detail=f"Connection error: {str(e)}")
    except Timeout:
        raise HTTPException(
            status_code=504,
            detail=f"Connection to Ollama server at {host} timed out. Please check your network connection."
        )
    except RequestException as e:
        logger.error(f"Ollama request error: {e}")
        raise HTTPException(status_code=500, detail=f"Error communicating with Ollama server: {str(e)}")
    except Exception as e:
        logger.error(f"Ollama error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """Handle chat messages with LLM integration"""
    
    try:
        if request.model == "claude":
            api_key = request.api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY required")
            return await chat_with_claude(request.messages, api_key)
        
        elif request.model == "ollama":
            host = request.ollama_host or os.getenv("OLLAMA_HOST", "http://golem:11434")
            model_name = request.ollama_model_name or os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
            return await chat_with_ollama(request.messages, host, model_name)
        
        elif request.model == "chatgpt":
            raise HTTPException(status_code=501, detail="ChatGPT integration coming soon")
        
        elif request.model == "gemini":
            raise HTTPException(status_code=501, detail="Gemini integration coming soon")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown model: {request.model}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/models")
async def get_available_models():
    """Get list of available models"""
    return {
        "models": [
            {
                "id": "claude",
                "name": "Claude (Anthropic)",
                "description": "Claude Sonnet 4 with BAIS tools",
                "requires_api_key": True
            },
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "description": "Local Ollama instance with BAIS tools",
                "requires_api_key": False,
                "requires_host": True
            },
            {
                "id": "chatgpt",
                "name": "ChatGPT (OpenAI)",
                "description": "Coming soon",
                "requires_api_key": True,
                "coming_soon": True
            },
            {
                "id": "gemini",
                "name": "Gemini (Google)",
                "description": "Coming soon",
                "requires_api_key": True,
                "coming_soon": True
            }
        ]
    }

