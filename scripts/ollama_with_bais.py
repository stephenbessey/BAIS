#!/usr/bin/env python3
"""
Ollama API Wrapper with BAIS Tools
This script makes BAIS tools available to Ollama models, enabling business discovery and booking.
Since Ollama models don't support native function calling, we use structured prompts and JSON parsing.
"""

import os
import json
import sys
import re
import requests
from typing import Dict, Any, Optional, List

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://golem:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
BAIS_WEBHOOK_URL = os.getenv("BAIS_WEBHOOK_URL", "https://bais-production.up.railway.app/api/v1/llm-webhooks/claude/tool-use")
BAIS_TOOLS_URL = os.getenv("BAIS_TOOLS_URL", "https://bais-production.up.railway.app/api/v1/llm-webhooks/tools/definitions")


def get_bais_tool_definitions() -> list:
    """Get BAIS tool definitions"""
    try:
        response = requests.get(BAIS_TOOLS_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Handle different response structures
        if "tools" in data and isinstance(data["tools"], dict):
            return data["tools"].get("claude", [])
        elif "claude" in data:
            return data.get("claude", [])
        else:
            return data.get("claude", [])
    except Exception as e:
        print(f"⚠️  Warning: Could not fetch BAIS tools from {BAIS_TOOLS_URL}")
        print(f"   Error: {e}")
        print("   Using default tool definitions...")
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
                "description": "Get services for a specific business",
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
                    "required": ["business_id", "service_id", "parameters", "customer_info"]
                }
            }
        ]


def call_bais_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Call a BAIS tool via webhook"""
    try:
        # Format request for BAIS webhook (Claude format)
        webhook_payload = {
            "content": [{
                "type": "tool_use",
                "name": tool_name,
                "input": tool_input,
                "id": f"ollama-call-{hash(str(tool_input))}"
            }]
        }
        
        response = requests.post(
            BAIS_WEBHOOK_URL,
            json=webhook_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        # Handle UniversalToolResponse format
        if isinstance(result, dict):
            # Check for UniversalToolResponse structure
            if "success" in result:
                if result.get("success") and "result" in result:
                    return result["result"]
                elif not result.get("success") and "error" in result:
                    return {"error": result["error"]}
            
            # Check for direct result/content
            if "result" in result:
                return result["result"]
            elif "content" in result:
                content = result["content"]
                if isinstance(content, str):
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"content": content}
                return content
            else:
                # Return the whole result if it's a dict
                return result
        
        # If it's a list, return as-is
        if isinstance(result, list):
            return result
            
        return result
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - Status: {e.response.status_code}"
        print(f"❌ Error calling BAIS tool {tool_name}: {error_msg}")
        return {"error": error_msg}
    except Exception as e:
        print(f"❌ Error calling BAIS tool {tool_name}: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def build_system_prompt(tools: List[Dict]) -> str:
    """Build system prompt that guides the model to use tools"""
    tools_desc = "\n".join([
        f"- {tool['name']}: {tool['description']}"
        for tool in tools
    ])
    
    return f"""You are a helpful AI assistant that can search and book services through BAIS (Business-Agent Integration Standard).

You have access to these tools:
{tools_desc}

When you need to use a tool, respond with a JSON object in this exact format:
{{
  "tool_call": {{
    "name": "tool_name",
    "input": {{"param": "value"}}
  }}
}}

When you have a final answer, respond normally without the tool_call JSON.

Tool descriptions:
1. bais_search_businesses: Search for businesses. Input: query (required), category (optional), location (optional)
2. bais_get_business_services: Get services for a business. Input: business_id (required)
3. bais_execute_service: Book or purchase a service. Input: business_id, service_id, parameters, customer_info (all required)

Always use tools when the user asks about:
- Finding businesses (restaurants, hotels, services, med spas, etc.)
- Getting information about a business
- Booking appointments or services
- Making reservations

Respond to tool results naturally and helpfully."""


def parse_tool_call(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse tool call from model response"""
    # Clean up the response text
    response_text = response_text.strip()
    
    # Method 1: Look for {"tool_call": {...}} pattern (nested)
    patterns = [
        # Standard nested format
        r'\{"tool_call":\s*\{[^}]*"name"[^}]*"input"[^}]*\}\}',
        # With more whitespace
        r'\{[^{}]*"tool_call"[^{}]*\{[^{}]*"name"[^{}]*"input"[^{}]*[^}]*\}[^}]*\}',
        # Simpler nested
        r'\{[^{}]*"tool_call"[^{}]*\{.*?\}.*?\}',
    ]
    
    for pattern in patterns:
        json_match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                if "tool_call" in parsed:
                    return parsed["tool_call"]
            except json.JSONDecodeError:
                continue
    
    # Method 2: Look for direct tool call format {"name": "...", "input": {...}}
    direct_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"input"\s*:\s*\{[^}]*\}\s*\}'
    json_match = re.search(direct_pattern, response_text, re.DOTALL | re.IGNORECASE)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if "name" in parsed and "input" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass
    
    # Method 3: Find any JSON object and check if it looks like a tool call
    try:
        # Find all JSON objects in the response
        start = 0
        while True:
            start = response_text.find('{', start)
            if start == -1:
                break
            
            # Find matching closing brace
            brace_count = 0
            end = start
            for i, char in enumerate(response_text[start:], start=start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            if end > start:
                try:
                    parsed = json.loads(response_text[start:end])
                    # Check if it's a tool call structure
                    if "tool_call" in parsed and isinstance(parsed["tool_call"], dict):
                        return parsed["tool_call"]
                    if "name" in parsed and "input" in parsed:
                        # Check if name looks like a BAIS tool
                        if parsed["name"].startswith("bais_"):
                            return parsed
                except json.JSONDecodeError:
                    pass
            
            start = end
            
    except (ValueError, IndexError):
        pass
    
    # Method 4: Look for tool name in text and try to extract parameters
    for tool_name in ["bais_search_businesses", "bais_get_business_services", "bais_execute_service"]:
        if tool_name in response_text.lower():
            # Try to find JSON near the tool name
            tool_idx = response_text.lower().find(tool_name.lower())
            if tool_idx != -1:
                # Look for JSON starting before or after the tool name
                search_start = max(0, tool_idx - 200)
                search_end = min(len(response_text), tool_idx + 500)
                search_text = response_text[search_start:search_end]
                
                json_match = re.search(r'\{[^{}]*"name"[^{}]*' + tool_name + r'[^{}]*"input"[^{}]*[^}]*\}', search_text, re.DOTALL | re.IGNORECASE)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        if "name" in parsed and "input" in parsed:
                            return parsed
                    except json.JSONDecodeError:
                        pass
    
    return None


def ask_ollama(prompt: str, system_prompt: str, model: str, host: str) -> str:
    """Send a request to Ollama"""
    try:
        url = f"{host}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        
        # Extract message content
        if "message" in data and "content" in data["message"]:
            return data["message"]["content"]
        elif "response" in data:
            return data["response"]
        else:
            return str(data)
    except Exception as e:
        print(f"❌ Ollama API error: {e}")
        raise


def ask_ollama_with_bais(user_query: str) -> str:
    """Ask Ollama a question with BAIS tools enabled"""
    print("🔧 Loading BAIS tools...")
    bais_tools = get_bais_tool_definitions()
    print(f"✅ Loaded {len(bais_tools)} BAIS tools")
    print()
    
    # Build system prompt
    system_prompt = build_system_prompt(bais_tools)
    
    print(f"💬 Asking Ollama: {user_query}")
    print()
    
    conversation_history = []
    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        try:
            # Build current prompt with conversation history
            if iteration == 0:
                current_prompt = user_query
            else:
                # Build conversation context
                context_parts = [f"User: {user_query}"]
                for msg in conversation_history:
                    if isinstance(msg, dict):
                        if "tool_result" in msg:
                            context_parts.append(f"Tool Result for {msg.get('tool_name', 'tool')}: {json.dumps(msg['tool_result'], indent=2)}")
                        elif "assistant_response" in msg:
                            context_parts.append(f"Assistant: {msg['assistant_response']}")
                    else:
                        context_parts.append(f"Assistant: {msg}")
                context_parts.append("User: Based on the tool results above, provide a helpful final answer to my original question.")
                current_prompt = "\n\n".join(context_parts)
            
            # Call Ollama
            print(f"🔄 Iteration {iteration + 1}/{max_iterations}...")
            response = ask_ollama(current_prompt, system_prompt, OLLAMA_MODEL, OLLAMA_HOST)
            
            # Check if response contains a tool call
            tool_call = parse_tool_call(response)
            
            if tool_call:
                tool_name = tool_call.get("name", "")
                tool_input = tool_call.get("input", {})
                
                if not tool_name or not tool_input:
                    print(f"⚠️  Invalid tool call format: {tool_call}")
                    print(f"   Response: {response[:500]}")
                    # Continue anyway, might be a final answer
                    conversation_history.append({"assistant_response": response})
                    iteration += 1
                    continue
                
                print(f"🔧 Ollama wants to use tool: {tool_name}")
                print(f"   Input: {json.dumps(tool_input, indent=2)}")
                print()
                
                # Call BAIS tool
                print(f"📡 Calling BAIS: {tool_name}...")
                tool_result = call_bais_tool(tool_name, tool_input)
                
                print(f"✅ BAIS returned result")
                if isinstance(tool_result, dict):
                    result_preview = json.dumps(tool_result, indent=2)[:300]
                else:
                    result_preview = str(tool_result)[:300]
                print(f"   Result preview: {result_preview}...")
                print()
                
                # Store conversation history
                conversation_history.append({"assistant_response": response})
                conversation_history.append({
                    "tool_result": tool_result,
                    "tool_name": tool_name
                })
                
                iteration += 1
                continue
            else:
                # No tool call detected - check if we should continue or return
                # If this is the first iteration and no tool was called, the model might not understand
                # If we have tool results, this is likely the final answer
                if iteration > 0 or "tool" not in response.lower():
                    # We have tool results or model is giving final answer
                    return response
                else:
                    # First iteration, no tool call - might need to prompt differently
                    print(f"⚠️  No tool call detected in response")
                    print(f"   Response preview: {response[:300]}...")
                    print()
                    # Add the response and ask for tool usage
                    conversation_history.append({"assistant_response": response})
                    current_prompt = f"{user_query}\n\nAssistant: {response}\n\nUser: Please use the bais_search_businesses tool to find businesses matching my query."
                    iteration += 1
                    continue
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return f"Error occurred: {str(e)}"
    
    # If we've exhausted iterations, return the last response
    if conversation_history:
        last_msg = conversation_history[-1]
        if isinstance(last_msg, dict) and "assistant_response" in last_msg:
            return last_msg["assistant_response"]
        elif isinstance(last_msg, str):
            return last_msg
    
    return "Max iterations reached. Please try rephrasing your question."


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🤖 Ollama with BAIS - Business Discovery Tool")
        print()
        print("Usage: python ollama_with_bais.py 'your question'")
        print()
        print("Examples:")
        print("  python ollama_with_bais.py 'find a med spa in Las Vegas'")
        print("  python ollama_with_bais.py 'search for New Life New Image Med Spa'")
        print("  python ollama_with_bais.py 'book a Botox appointment at a med spa in Vegas'")
        print()
        print("Environment variables:")
        print("  OLLAMA_HOST - Ollama server URL (default: http://golem:11434)")
        print("  OLLAMA_MODEL - Model name (default: gpt-oss:120b)")
        print("  BAIS_WEBHOOK_URL - BAIS webhook URL")
        print("  BAIS_TOOLS_URL - BAIS tools endpoint")
        print()
        sys.exit(1)
    
    user_query = sys.argv[1]
    
    print("=" * 60)
    print("🤖 Ollama with BAIS Tools Enabled")
    print(f"   Model: {OLLAMA_MODEL}")
    print(f"   Host: {OLLAMA_HOST}")
    print("=" * 60)
    print()
    
    result = ask_ollama_with_bais(user_query)
    
    print("=" * 60)
    print("✅ Ollama's Response:")
    print("=" * 60)
    print()
    print(result)
    print()

