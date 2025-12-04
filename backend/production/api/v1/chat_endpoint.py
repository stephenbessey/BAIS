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
import re
import requests
import logging
import traceback
from datetime import datetime
from requests.exceptions import ConnectionError, Timeout, RequestException

# Import BAIS tools directly
from ...core.universal_tools import BAISUniversalToolHandler, BAISUniversalTool
from ...core.database_models import DatabaseManager, Business

# Optional imports (only imported when needed)
try:
    import anthropic
except ImportError:
    anthropic = None

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
    """Get BAIS tool handler with database connection - ALWAYS prioritize database"""
    try:
        database_url = os.getenv("DATABASE_URL")
        # Log what we got (but mask password for security)
        if database_url:
            masked_url = database_url.split('@')[1] if '@' in database_url else "***"
            logger.info(f"📊 DATABASE_URL found: postgresql://***@{masked_url}")
        else:
            logger.warning("⚠️ DATABASE_URL environment variable not found")
            # Try alternative names Railway might use
            database_url = os.getenv("POSTGRES_URL") or os.getenv("PGDATABASE_URL")
            if database_url:
                logger.info(f"📊 Found alternative DATABASE_URL: postgresql://***@{database_url.split('@')[1] if '@' in database_url else '***'}")
        
        if database_url and database_url.strip() and database_url != "not_set":
            try:
                db_manager = DatabaseManager(database_url)
                logger.info(f"✅ Created BAIS tool handler with Railway database connection")
                # Test connection by checking business count
                try:
                    with db_manager.get_session() as session:
                        count = session.query(Business).count()
                        active_count = session.query(Business).filter(Business.status == "active").count()
                        logger.info(f"✅ Database connection verified: {count} total businesses, {active_count} active")
                except Exception as test_error:
                    logger.warning(f"⚠️ Database connection test failed: {test_error}")
                    logger.debug(f"Connection test error details: {traceback.format_exc()}")
                return BAISUniversalToolHandler(db_manager=db_manager)
            except Exception as e:
                logger.error(f"❌ Could not create database manager: {e}")
                logger.error(f"Database manager creation error: {traceback.format_exc()}")
                # Still return handler, but it won't have database access
                return BAISUniversalToolHandler()
        else:
            # No DATABASE_URL is OK for local development - will use in-memory storage
            logger.info("ℹ️  No DATABASE_URL configured - using in-memory storage (data resets on restart)")
            logger.info("   For production/persistence, set DATABASE_URL. See DATABASE_SETUP.md for details.")
        return BAISUniversalToolHandler()
    except Exception as e:
        logger.error(f"❌ Error creating tool handler: {e}")
        logger.error(f"Tool handler creation error: {traceback.format_exc()}")
        return BAISUniversalToolHandler()


def clean_json_artifacts(text: str) -> str:
    """Remove JSON tool call artifacts from response text"""
    if not text:
        return text
    
    # Remove complete JSON tool call blocks like {"tool_call": {...}}
    # Match various formats including nested braces
    json_pattern = r'\{"tool_call"\s*:\s*\{[^}]*\{[^}]*\}[^}]*\}\}'
    text = re.sub(json_pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any remaining JSON-like artifacts
    json_pattern2 = r'\{[^{}]*"tool_call"[^{}]*\}'
    text = re.sub(json_pattern2, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove leftover closing braces at the start (common artifact)
    text = re.sub(r'^[\s}]*\}*\s*', '', text)
    text = re.sub(r'^[\s}]*\}*\s*', '', text)  # Run twice for nested cases
    
    # Remove standalone closing braces that don't match opening braces
    # Only remove if they appear at the start or are clearly artifacts
    text = re.sub(r'^[}\s]+', '', text)
    
    # Clean up multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Remove any remaining leading/trailing braces
    text = text.strip()
    if text.startswith('}'):
        text = text.lstrip('}')
    if text.endswith('{') and not text.startswith('{'):
        text = text.rstrip('{')
    
    return text.strip()


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
            # get_business_services returns a dict with business_id, business_name, and services
            return result if isinstance(result, dict) else {"error": "Failed to get services", "services": []}
            
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
    if anthropic is None:
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
CRITICAL WORKFLOW FOR COMPLETE BOOKINGS:
1. SEARCH: When user wants to find a business, use bais_search_businesses with their query/location
   - After search, remember the business_id from the results
   - The service names shown are PREVIEWS only - you need full details to book
   
2. GET SERVICES (REQUIRED STEP): When user mentions ANY service name OR wants to book:
   - IMMEDIATELY call bais_get_business_services with business_id from step 1
   - DO NOT respond based only on search results
   - DO NOT say a service is not available until you've called bais_get_business_services
   - DO NOT call bais_search_businesses again - you already have the business
   - The search results show service names but you MUST get service_ids via bais_get_business_services
   
3. MATCH SERVICE: When user mentions a service name:
   - Match it to the service_id from the services list returned by bais_get_business_services
   - Use the exact service_id (not the service name) when calling bais_execute_service
   
4. GATHER DETAILS: Collect from conversation:
   - Service name (already mentioned) -> match to service_id
   - Date and time preference
   - Name, email, and phone number
   
5. EXECUTE BOOKING: Once you have all details, use bais_execute_service with:
   - business_id: from search results (not from searching again)
   - service_id: from services list (match service name to service_id)
   - customer_info: {name, email, phone}
   - parameters: {date, time}

IMPORTANT CONVERSATION RULES:
- ALWAYS maintain full conversation context - remember everything discussed
- If user mentions ANY service name (e.g., "laser hair removal", "botox", "I want [service]"):
  a) IMMEDIATELY call bais_get_business_services with the business_id from earlier search
  b) DO NOT respond without calling the tool first
  c) DO NOT search again - you already know which business
  d) DO NOT say a service is unavailable until you've checked via bais_get_business_services
- If user says "book [service]" or "I want [service]":
  a) Call bais_get_business_services first (required)
  b) Match the service name to service_id
  c) If you have date/time/contact info, call bais_execute_service immediately
  d) If missing info, ask for it, then call bais_execute_service
- NEVER say a service is not available if it was mentioned in search results
- All services returned from bais_get_business_services ARE available for booking

CRITICAL: When you need to use a tool, respond ONLY with valid JSON in this exact format:
{"tool_call": {"name": "tool_name", "input": {...}}}

Do NOT include any other text before or after the JSON. Just the JSON object.

AFTER I execute the tool and provide results:
- Respond naturally and conversationally to the user
- NEVER include JSON, tool calls, or technical details in your response
- NEVER repeat the tool call JSON in your response
- Just provide a helpful, natural conversation response
- MAINTAIN FULL CONVERSATION CONTEXT - remember what was discussed earlier
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
                # Remove the JSON from response_text since we extracted it
                response_text = ""
        except json.JSONDecodeError:
            # More comprehensive pattern to match JSON tool calls with nested braces
            json_pattern = r'\{"tool_call"\s*:\s*\{[^}]*\{[^}]*\}[^}]*\}\}'
            json_match = re.search(json_pattern, response_text, re.DOTALL | re.IGNORECASE)
            if json_match:
                try:
                    tool_call_data = json.loads(json_match.group())
                    if isinstance(tool_call_data, dict) and "tool_call" in tool_call_data:
                        tool_call = tool_call_data.get("tool_call", {})
                        tool_name = tool_call.get("name")
                        tool_input = tool_call.get("input", {})
                        # Remove the JSON block from response_text, including any trailing braces
                        before = response_text[:json_match.start()].rstrip('}')
                        after = response_text[json_match.end():].lstrip('}')
                        response_text = before + after
                        response_text = clean_json_artifacts(response_text)
                except json.JSONDecodeError:
                    # If JSON parsing fails, try a simpler pattern
                    simple_pattern = r'\{[^{}]*"tool_call"[^{}]*\}'
                    simple_match = re.search(simple_pattern, response_text, re.DOTALL | re.IGNORECASE)
                    if simple_match:
                        before = response_text[:simple_match.start()].rstrip('}')
                        after = response_text[simple_match.end():].lstrip('}')
                        response_text = clean_json_artifacts(before + after)
                    else:
                        # No match found, just clean the text
                        response_text = clean_json_artifacts(response_text)
        
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
                    
                    # Extract business_id from first result for reference
                    first_business_id = actual_result[0].get('business_id') or actual_result[0].get('id', '')
                    
                    # Extract services list from search results to use as fallback
                    search_services = []
                    for biz in actual_result:
                        if 'services' in biz:
                            search_services.extend([s.get('name', '') for s in biz.get('services', []) if s.get('name')])
                    
                    # Store search result services in conversation context for later reference
                    search_services_text = "\n".join([f"- {s}" for s in search_services[:10]]) if search_services else "Services shown in search results above"
                    
                    follow_up_prompt = f"""{system_prompt}

Full Conversation History:
{conversation_history}User: {last_message}
Assistant: I searched the BAIS platform and found these businesses:

{businesses_list}

RESPONSE STRUCTURE (follow this order):
1. FIRST: Say you found a business and mention the business name (e.g., "I found New Life New Image Med Spa")
2. SECOND: Provide key information from the list above:
   - Location/address
   - Phone number (if available)
   - Website (if available)
3. THIRD: List the services they offer
4. FOURTH: Offer to help (e.g., "Would you like more details about any of these services, or would you like to schedule an appointment?")

IMPORTANT: Present this information naturally and conversationally. Introduce the business FIRST, then offer assistance. Do NOT immediately jump to asking what service they want - first properly introduce the business you found.

CRITICAL INSTRUCTIONS FOR FUTURE MESSAGES (not this response):
- **THE BUSINESS_ID IS EXACTLY: "{first_business_id}"** - MEMORIZE THIS EXACT VALUE
- When calling bais_get_business_services, you MUST use: business_id="{first_business_id}"
- Copy it EXACTLY - do NOT change hyphens (-) to underscores (_), do NOT remove hyphens, do NOT combine words
- The correct format has hyphens: "{first_business_id}"
- WRONG formats that will NOT work: "new_life_new_image_med_spa", "newlife_newimage_medspa", "new-life_new-image_med-spa"
- ONLY use the exact format: "{first_business_id}"
- FALLBACK: If bais_get_business_services returns no services, use the services shown in the search results above - they ARE available
- IMPORTANT: The service names shown above are just PREVIEWS - you MUST get full service details to help the user
- If the user mentions ANY service name (like "laser hair removal", "botox", "I want [service]", "I would like [service]"), you MUST:
  1. IMMEDIATELY call bais_get_business_services with business_id="{first_business_id}" (use this EXACT value, do NOT modify it)
  2. DO NOT respond with text - you MUST call the tool first
  3. DO NOT say a service is not available - you haven't checked yet via the tool
  4. DO NOT call bais_search_businesses again - you already have the business
  5. DO NOT try to help based only on search results - you need full service details
  6. DO NOT change the business_id format - use "{first_business_id}" exactly as shown (with hyphens, not underscores)
- After calling bais_get_business_services, you'll get the complete service list with service_ids
- Then you can help the user with accurate information about services
- You MUST ONLY mention and recommend businesses from the list above
- Do NOT mention, suggest, or reference ANY other businesses
- Do NOT make up business names, addresses, or phone numbers
- Maintain full conversation context - remember what the user said earlier

Available tools:
- bais_get_business_services: REQUIRED when user mentions ANY service name - use business_id="{first_business_id}" (EXACTLY as shown, with hyphens)

IMPORTANT: 
- For THIS response (after search): 
  * Do NOT call any tools - just provide a natural text response
  * Follow the RESPONSE STRUCTURE above
  * Introduce the business first, then offer to help
- For FUTURE messages: If the user mentions a service or wants to book, THEN call bais_get_business_services

**MEMORIZE THIS BUSINESS_ID: "{first_business_id}"** - When you call bais_get_business_services, use this EXACT string (with hyphens, in quotes). Do NOT convert hyphens to underscores. Do NOT change the format.

CRITICAL RULE (for future messages, not this one): If the user's message contains ANY service-related words (service names, "book", "appointment", "schedule", "I want", "I would like"), you MUST respond with a tool call to bais_get_business_services using business_id="{first_business_id}" (EXACTLY as shown). Call the tool first, then respond based on the tool results.

Respond naturally and conversationally. DO NOT include any JSON, tool calls, or technical formatting in your response. ONLY reference the businesses in the list above."""
                else:
                    follow_up_prompt = f"""The user asked: "{last_message}"

I searched the BAIS platform but didn't find any businesses matching that criteria. 

Let the user know that no businesses were found matching their search, and suggest they try a different search term or location."""
            elif tool_name == "bais_get_business_services":
                # actual_result is a dict with business_id, business_name, and services
                if isinstance(actual_result, dict) and "services" in actual_result:
                    business_name = actual_result.get("business_name", "this business")
                    services = actual_result.get("services", [])
                    
                    services_list = []
                    for svc in services:
                        service_text = f"• {svc.get('name', 'Unknown')} - {svc.get('description', '')}"
                        # Add pricing if available
                        if "pricing" in svc:
                            pricing = svc["pricing"]
                            if isinstance(pricing, dict):
                                if "base_price" in pricing:
                                    service_text += f" (${pricing['base_price']}"
                                    if "unit" in pricing:
                                        service_text += f" per {pricing['unit']}"
                                    service_text += ")"
                                elif "typical_range" in pricing:
                                    service_text += f" (Typical range: ${pricing['typical_range']})"
                        services_list.append(service_text)
                    
                    services_text = "\n".join(services_list)
                    
                    # Create a mapping of service names to service_ids for the LLM
                    # Include multiple variations for better matching
                    service_mapping = {}
                    service_details = {}
                    for svc in services:
                        service_name = svc.get('name', '').lower()
                        service_id = svc.get('service_id', svc.get('id', ''))
                        if service_name and service_id:
                            service_mapping[service_name] = service_id
                            service_details[service_name] = svc
                            # Add variations for common service names
                            if 'laser hair' in service_name or 'hair removal' in service_name:
                                service_mapping['laser hair removal'] = service_id
                                service_mapping['hair removal'] = service_id
                                service_mapping['laser hair'] = service_id
                            if 'botox' in service_name:
                                service_mapping['botox'] = service_id
                                service_mapping['botox treatment'] = service_id
                            if 'filler' in service_name.lower():
                                service_mapping['dermal fillers'] = service_id
                                service_mapping['fillers'] = service_id
                    
                    business_id = actual_result.get('business_id', '')
                    
                    # Extract what the user already provided from conversation history
                    user_message_lower = last_message.lower()
                    has_service = any(word in user_message_lower for word in ['laser hair', 'botox', 'filler', 'hydrafacial', 'coolsculpting', 'service'])
                    has_date_time = any(word in user_message_lower for word in ['tomorrow', 'today', 'am', 'pm', 'morning', 'afternoon', 'evening', 'at ', ':', 'book', 'schedule', 'appointment'])
                    has_contact = any(word in user_message_lower for word in ['name', 'email', 'phone', '@', '.com'])

                    # Prepare conditional text outside f-string to avoid backslash issues
                    if has_service and has_date_time:
                        decision_text = f"""- YOU HAVE ALL INFO: IMMEDIATELY call bais_execute_service with:
  * business_id="{business_id}"
  * service_id=<matched from above>
  * parameters={{date/time from conversation}}
  * customer_info={{name, email, phone from conversation}}"""
                    else:
                        decision_text = """- YOU ARE MISSING INFO: Ask ONLY for what's missing, then call bais_execute_service
- If missing service: Match user's request to service_id from list above
- If missing date/time: Ask "What date and time would work for you?"
- If missing contact: Ask "I'll need your name, email, and phone number to complete the booking" """

                    final_instruction = "READY TO BOOK: You have the service and time. Call bais_execute_service now, or ask for missing contact info." if has_date_time else "GATHER INFO: Ask for the missing information needed to complete the booking."

                    follow_up_prompt = f"""{system_prompt}

Full Conversation History:
{conversation_history}User: {last_message}
Assistant: I retrieved the available services from {business_name}.

Here are ALL available services (business_id: "{business_id}" - use EXACTLY this format with hyphens):

{services_text}

Service ID mapping (use these EXACT service_ids when calling bais_execute_service):
{chr(10).join([f"- '{name}' -> service_id='{sid}'" for name, sid in sorted(service_mapping.items(), key=lambda x: x[0])[:15]])}

BOOKING WORKFLOW - Follow these steps:

STEP 1: Identify what the user wants:
- Review conversation history - user said: "{last_message}"
- What service did they mention? Match it to a service_id above (be flexible: "laser hair removal" = "laser-hair-removal-service")
- What date/time did they specify? Extract it.
- Do they have contact info? Check conversation history.

STEP 2: Check if you have ALL required information:
Required for booking:
- business_id: "{business_id}" (use EXACTLY this - it has hyphens, not underscores)
- service_id: from the mapping above (based on service name user mentioned)
- parameters: {{"date": "...", "time": "..."}} (if user provided date/time)
- customer_info: {{"name": "...", "email": "...", "phone": "..."}} (if user provided)

STEP 3: Decision making:
{decision_text}

CRITICAL RULES:
- business_id MUST be "{business_id}" (with hyphens, exactly as shown - do NOT use underscores)
- ALL services listed above ARE available - never say a service is unavailable
- Once you have service_id, date/time, and contact info, IMMEDIATELY call bais_execute_service
- DO NOT call bais_get_business_services again - you already have the services
- DO NOT say "I found some information" - be specific about what you're doing
- Maintain conversation context - remember everything the user said

{final_instruction}"""
                elif isinstance(actual_result, dict) and ("error" in actual_result or actual_result.get("services") == [] or len(actual_result.get("services", [])) == 0):
                    # Services not found - this might be a business_id format issue
                    error_msg = actual_result.get('error', 'No services found')

                    # Try to get services from previous search results in conversation history
                    # Extract business name and services from conversation context
                    business_name_from_context = "this business"
                    services_from_context = []

                    # Parse conversation history to find business info
                    if "I searched the BAIS platform and found these businesses:" in conversation_history:
                        # Try to extract business name and services from previous search results
                        import re
                        # Extract business name pattern
                        name_match = re.search(r'1\.\s+([^\n]+)', conversation_history)
                        if name_match:
                            business_name_from_context = name_match.group(1).strip()

                        # Extract services from context
                        services_match = re.search(r'Services:\s+([^\n]+)', conversation_history)
                        if services_match:
                            services_text = services_match.group(1)
                            services_from_context = [s.strip() for s in services_text.split(',')]

                    # Build service list text
                    if services_from_context:
                        services_list_text = "\n".join([f"- {svc}" for svc in services_from_context])
                    else:
                        services_list_text = "(Services were shown in the search results earlier)"

                    follow_up_prompt = f"""{system_prompt}

Full Conversation History:
{conversation_history}User: {last_message}
Assistant: I encountered a technical issue retrieving detailed service information, but I can see from our earlier search that {business_name_from_context} offers services.

{services_list_text if services_from_context else ''}

CRITICAL INSTRUCTIONS - READ CAREFULLY:
- DO NOT say "doesn't have any services" or "no services available" - services exist from search results
- DO NOT suggest finding another business - this business has the services the user wants
- The user said: "{last_message}" - they want to book a service
- PROCEED WITH BOOKING: Even though we couldn't retrieve detailed service info, we can still help them book
- Ask for booking details:
  * Confirm which service they want (match to services from earlier search)
  * Ask: "What date and time would you like for your [service name] appointment?"
  * Ask: "I'll need your name, email, and phone number to complete the booking"

Respond naturally by confirming you can help them book and asking for the missing information. NEVER say services are unavailable."""
                else:
                    follow_up_prompt = f"""{system_prompt}

Full Conversation History:
{conversation_history}User: {last_message}
Assistant: I tried to get services but no services were found.

Let the user know that no services are currently available for this business."""
            elif tool_name == "bais_execute_service":
                # Handle service execution result
                if isinstance(actual_result, dict):
                    if actual_result.get("success"):
                        confirmation_id = actual_result.get("confirmation_id", "N/A")
                        confirmation_msg = actual_result.get("confirmation_message", "Booking confirmed!")
                        details = actual_result.get("details", {})
                        
                        follow_up_prompt = f"""{system_prompt}

Full Conversation History:
{conversation_history}User: {last_message}
Assistant: I successfully executed the booking using bais_execute_service.

Booking Result:
{confirmation_msg}
Confirmation ID: {confirmation_id}

Provide a warm, natural confirmation message to the user. Include the confirmation ID and let them know their booking is confirmed. Offer to help with anything else."""
                    else:
                        error_msg = actual_result.get("error", "Unknown error")
                        follow_up_prompt = f"""{system_prompt}

Full Conversation History:
{conversation_history}User: {last_message}
Assistant: I tried to execute the booking but encountered an error: {error_msg}

Apologize to the user and let them know there was an issue completing the booking. Suggest they try again or contact the business directly."""
                else:
                    tool_result_text = json.dumps(actual_result, indent=2)
                    follow_up_prompt = f"""{system_prompt}

Full Conversation History:
{conversation_history}User: {last_message}
Assistant: I executed the service. Result: {tool_result_text}

Provide a natural, helpful response based on this result. Maintain conversation context."""
            else:
                tool_result_text = json.dumps(actual_result, indent=2)
                follow_up_prompt = f"""{system_prompt}

Full Conversation History:
{conversation_history}User: {last_message}
Assistant: Tool result: {tool_result_text}

Provide a natural, helpful, conversational response based on this result. Maintain conversation context. 
CRITICAL: DO NOT include any JSON, tool calls, or technical formatting in your response. Just provide a friendly, helpful message to the user."""
            
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
            
            # Clean any JSON artifacts from the final response
            final_response = clean_json_artifacts(final_response)
            
            if not final_response or final_response == response_text:
                final_response = "I found some information. Let me help you with that."
            
            return ChatResponse(
                message=final_response,
                tool_calls=[{"name": tool_name, "input": tool_input}]
            )
        
        # Clean any JSON artifacts that might be in the response
        response_text = clean_json_artifacts(response_text)
        
        # Check if user mentioned a service but LLM didn't call a tool
        # If so, we need to guide them to call bais_get_business_services
        user_mentioned_service = any(keyword in last_message.lower() for keyword in [
            'laser hair', 'hair removal', 'botox', 'filler', 'dermal', 'hydrafacial',
            'coolsculpting', 'service', 'appointment', 'book', 'schedule', 'i want',
            'i would like', 'i need', 'get'
        ])
        
        # If user mentioned a service and we have conversation history (previous search),
        # but LLM didn't call a tool, guide them to get services
        if user_mentioned_service and conversation_history and response_text and not response_text.startswith('{'):
            # Check if previous conversation included a business search
            if 'bais_search_businesses' in conversation_history.lower() or 'new life' in conversation_history.lower():
                # LLM should have called bais_get_business_services but didn't
                # Return a response that guides them, but better to fix this in the prompt
                # For now, just return the response and hope the prompt fixes work
                pass
        
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

