#!/usr/bin/env python3
"""
Script to submit a customer business registration to the BAIS backend.
"""

import json
import sys
import os
import re
import requests
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def extract_json_from_markdown(file_path: Path) -> Dict[str, Any]:
    """
    Extract JSON from a markdown file that contains JSON in code blocks.
    """
    content = file_path.read_text()
    
    # Try to find JSON in code blocks
    json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON without language tag
        json_match = re.search(r'```\s*\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("Could not find JSON in the file")
    
    return json.loads(json_str)


def prepare_registration_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare the business registration data according to BusinessRegistrationRequest schema.
    Includes all optional fields for complete registration.
    """
    # Extract required and optional fields
    registration_data = {
        "business_name": data["business_name"],
        "business_type": data["business_type"],
        "contact_info": data["contact_info"],
        "location": data["location"],
        "services_config": data["services_config"]
    }
    
    # Include optional fields if present
    if "business_info" in data:
        registration_data["business_info"] = data["business_info"]
    if "integration" in data:
        registration_data["integration"] = data["integration"]
    if "ap2_config" in data:
        registration_data["ap2_config"] = data["ap2_config"]
    
    return registration_data


def submit_business_registration(
    registration_data: Dict[str, Any],
    api_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """
    Submit business registration to the BAIS backend API.
    """
    endpoint = f"{api_url}/api/v1/businesses"
    
    print(f"📤 Submitting business registration to {endpoint}")
    print(f"   Business: {registration_data['business_name']}")
    print(f"   Type: {registration_data['business_type']}")
    print(f"   Services: {len(registration_data['services_config'])}")
    print()
    
    try:
        response = requests.post(
            endpoint,
            json=registration_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the backend server.")
        print(f"   Make sure the server is running at {api_url}")
        print()
        print("   To start the server:")
        print("   1. Install dependencies: pip3 install -r backend/production/requirements.txt")
        print("   2. Start server: python3 -m uvicorn backend.production.main:app --host 127.0.0.1 --port 8000")
        print()
        print("   Or use the simple server:")
        print("   python3 -m uvicorn app:app --host 127.0.0.1 --port 8000")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error submitting registration: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python submit_customer.py <customer_json_file> [api_url]")
        print("Example: python submit_customer.py customers/NewLifeNewImage_CORRECTED_BAIS_Submission.json")
        sys.exit(1)
    
    customer_file = Path(sys.argv[1])
    # Default to Railway production URL, fallback to localhost
    api_url = sys.argv[2] if len(sys.argv) > 2 else os.getenv("RAILWAY_URL") or os.getenv("BAIS_BASE_URL") or "http://localhost:8000"
    
    if not customer_file.exists():
        print(f"❌ Error: File not found: {customer_file}")
        sys.exit(1)
    
    print(f"📄 Reading customer data from: {customer_file}")
    print()
    
    try:
        # Extract JSON from file
        raw_data = extract_json_from_markdown(customer_file)
        
        # Prepare registration data
        registration_data = prepare_registration_data(raw_data)
        
        # Submit to backend
        result = submit_business_registration(registration_data, api_url)
        
        # Display results
        print("✅ Business registration successful!")
        print()
        print("📋 Registration Details:")
        print(f"   Business ID: {result.get('business_id', 'N/A')}")
        print(f"   Status: {result.get('status', 'N/A')}")
        print(f"   Setup Complete: {result.get('setup_complete', 'N/A')}")
        print()
        
        if 'mcp_endpoint' in result:
            print(f"   MCP Endpoint: {result.get('mcp_endpoint', 'N/A')}")
        if 'a2a_endpoint' in result:
            print(f"   A2A Endpoint: {result.get('a2a_endpoint', 'N/A')}")
        if 'api_keys' in result:
            print(f"   API Keys: Generated")
            if 'primary' in result.get('api_keys', {}):
                print(f"      Primary: {result['api_keys']['primary'][:20]}...")
        
        # Display LLM Discovery Status
        llm_discovery = result.get('llm_discovery', {})
        if llm_discovery:
            print()
            print("🤖 LLM Discovery Status:")
            discovery_status = llm_discovery.get('status', 'unknown')
            message = llm_discovery.get('message', '')
            print(f"   Status: {discovery_status.upper()}")
            print(f"   {message}")
            
            registered = llm_discovery.get('registered_platforms', [])
            unregistered = llm_discovery.get('unregistered_platforms', [])
            
            if registered:
                print(f"   ✅ Registered: {', '.join(registered).title()}")
            if unregistered:
                print(f"   ⏳ Pending: {', '.join(unregistered).title()}")
            
            instructions = llm_discovery.get('registration_instructions', [])
            if instructions:
                print()
                print("   📝 To Enable LLM Discovery:")
                for inst in instructions[:1]:  # Show first platform as example
                    print(f"      {inst['platform']}: {inst['action']}")
                    print(f"      → {inst['url']}")
                    print(f"      → Webhook: {inst['webhook_url']}")
                if len(instructions) > 1:
                    print(f"      ... and {len(instructions)-1} more platform(s)")
                print()
                print("   💡 Tip: Register BAIS once with each LLM provider to make")
                print("      ALL businesses discoverable automatically!")
        
        print()
        print("🎉 Customer is now registered and ready to use BAIS!")
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

