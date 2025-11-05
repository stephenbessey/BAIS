#!/usr/bin/env python3
"""
Claude API Wrapper with BAIS Tools
This script makes BAIS tools available to Claude, so any user query
can discover and book with BAIS businesses.
"""

import os
import json
import sys
import requests
from typing import Dict, Any, Optional

# Configuration - Update these with your Railway URL
BAIS_WEBHOOK_URL = os.getenv("BAIS_WEBHOOK_URL", "http://localhost:8000/api/v1/llm-webhooks/claude/tool-use")
BAIS_TOOLS_URL = os.getenv("BAIS_TOOLS_URL", "http://localhost:8000/api/v1/llm-webhooks/tools/definitions")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def get_bais_tool_definitions() -> list:
    """Get BAIS tool definitions for Claude"""
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
            # Fallback: try to extract from any structure
            return data.get("claude", [])
    except Exception as e:
        print(f"⚠️  Warning: Could not fetch BAIS tools from {BAIS_TOOLS_URL}")
        print(f"   Error: {e}")
        print("   Using default tool definitions...")
        # Return default tool definitions
        return [
            {
                "name": "bais_search_businesses",
                "description": "Search for businesses on the BAIS platform. Find restaurants, hotels, services, and more that accept AI-assisted purchases.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (business name, type, or location)"},
                        "category": {"type": "string", "enum": ["restaurant", "hotel", "retail", "service", "healthcare"], "description": "Filter by business category"},
                        "location": {"type": "string", "description": "City or address to search near"}
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
                        "business_id": {"type": "string", "description": "Business identifier from search results"}
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
                        "parameters": {"type": "object", "description": "Service-specific parameters"},
                        "customer_info": {"type": "object", "description": "Customer information"}
                    },
                    "required": ["business_id", "service_id", "customer_info"]
                }
            }
        ]


def call_bais_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Call a BAIS tool via webhook"""
    try:
        response = requests.post(
            BAIS_WEBHOOK_URL,
            json={
                "content": [{
                    "name": tool_name,
                    "input": tool_input,
                    "id": "claude-call"
                }]
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        content = result.get("content", "{}")
        if isinstance(content, str):
            return json.loads(content)
        return content
    except Exception as e:
        print(f"❌ Error calling BAIS tool {tool_name}: {e}")
        return {"error": str(e)}


def ask_claude_with_bais(user_query: str) -> str:
    """
    Ask Claude a question with BAIS tools enabled.
    This makes BAIS businesses discoverable automatically.
    """
    try:
        import anthropic
    except ImportError:
        print("❌ Error: anthropic package not installed")
        print("   Install with: pip3 install anthropic")
        sys.exit(1)
    
    if not ANTHROPIC_API_KEY:
        print("❌ Error: ANTHROPIC_API_KEY not set")
        print("   Set it as environment variable or pass as argument")
        sys.exit(1)
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Get BAIS tool definitions
    print("🔧 Loading BAIS tools...")
    bais_tools = get_bais_tool_definitions()
    
    # Convert to Claude's tool format
    claude_tools = []
    for tool in bais_tools:
        claude_tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"]
        })
    
    print(f"✅ Loaded {len(claude_tools)} BAIS tools")
    print()
    
    # Create message with tools
    print(f"💬 Asking Claude: {user_query}")
    print()
    
    messages = [{"role": "user", "content": user_query}]
    max_iterations = 5  # Limit tool use iterations
    iteration = 0
    
    while iteration < max_iterations:
        try:
            # Only send tools on first iteration
            create_params = {
                "model": "claude-sonnet-4-20250514",  # Claude Sonnet 4 (latest model)
                "max_tokens": 4096,
                "messages": messages
            }
            if iteration == 0:
                create_params["tools"] = claude_tools
            
            response = client.messages.create(**create_params)
            
            # Check if Claude wants to use a tool
            if response.stop_reason == "tool_use":
                # Find the tool use block in content
                tool_use = None
                for item in response.content:
                    if hasattr(item, 'type') and item.type == 'tool_use':
                        tool_use = item
                        break
                    elif hasattr(item, 'name'):  # Direct tool_use object
                        tool_use = item
                        break
                
                if not tool_use:
                    # Fallback: check if first item is tool_use
                    if hasattr(response.content[0], 'name'):
                        tool_use = response.content[0]
                    else:
                        # No tool use found, return text response
                        return response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
                
                print(f"🔧 Claude wants to use tool: {tool_use.name}")
                print(f"   Input: {json.dumps(tool_use.input, indent=2)}")
                print()
                
                # Call BAIS tool
                print(f"📡 Calling BAIS: {tool_use.name}...")
                tool_result = call_bais_tool(tool_use.name, tool_use.input)
                
                print(f"✅ BAIS returned result")
                print()
                
                # Add tool result to conversation
                # Claude API expects content as list of content blocks
                # Convert response.content to proper format
                assistant_content = []
                for item in response.content:
                    if hasattr(item, 'model_dump'):  # Pydantic v2
                        assistant_content.append(item.model_dump())
                    elif hasattr(item, 'dict'):  # Pydantic v1
                        assistant_content.append(item.dict())
                    elif hasattr(item, '__dict__'):
                        assistant_content.append(item.__dict__)
                    else:
                        # Try to convert to dict if it's a tool_use object
                        if hasattr(item, 'type') and item.type == 'tool_use':
                            assistant_content.append({
                                "type": "tool_use",
                                "id": item.id,
                                "name": item.name,
                                "input": item.input
                            })
                        else:
                            assistant_content.append(str(item))
                
                messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })
                
                # Add tool result - format content as string
                tool_result_content = json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": tool_result_content
                    }]
                })
                
                iteration += 1
                # Don't send tools again in next iteration
                continue
            else:
                # Claude has a final answer - extract text from content
                for item in response.content:
                    if hasattr(item, 'text'):
                        return item.text
                # Fallback
                return str(response.content[0]) if response.content else "No response"
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return f"Error occurred: {str(e)}"
    
    return "Max iterations reached"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🤖 Claude with BAIS - Business Discovery Tool")
        print()
        print("Usage: python claude_with_bais.py 'your question'")
        print()
        print("Examples:")
        print("  python claude_with_bais.py 'find a med spa in Las Vegas'")
        print("  python claude_with_bais.py 'search for New Life New Image Med Spa'")
        print("  python claude_with_bais.py 'book a Botox appointment at a med spa in Vegas'")
        print()
        print("Environment variables:")
        print("  BAIS_WEBHOOK_URL - Your BAIS webhook URL (default: http://localhost:8000)")
        print("  BAIS_TOOLS_URL - Your BAIS tools endpoint (default: http://localhost:8000)")
        print("  ANTHROPIC_API_KEY - Your Anthropic API key")
        print()
        sys.exit(1)
    
    user_query = sys.argv[1]
    
    print("=" * 60)
    print("🤖 Claude with BAIS Tools Enabled")
    print("=" * 60)
    print()
    
    result = ask_claude_with_bais(user_query)
    
    print("=" * 60)
    print("✅ Claude's Response:")
    print("=" * 60)
    print()
    print(result)
    print()

