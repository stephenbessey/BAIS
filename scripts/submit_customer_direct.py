#!/usr/bin/env python3
"""
Direct customer submission script that works without full server stack.
This script directly uses the business service components.
"""

import json
import sys
import re
import asyncio
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "production"))


def extract_json_from_markdown(file_path: Path) -> Dict[str, Any]:
    """Extract JSON from a markdown file that contains JSON in code blocks."""
    content = file_path.read_text()
    
    # Try to find JSON in code blocks
    json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r'```\s*\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("Could not find JSON in the file")
    
    return json.loads(json_str)


async def submit_directly(data: Dict[str, Any]):
    """
    Directly submit using the business service without HTTP.
    This is a fallback if the server isn't running.
    """
    try:
        from backend.production.api_models import BusinessRegistrationRequest
        from backend.production.services.business_service import BusinessService
        from backend.production.core.database_models import DatabaseManager
        from fastapi import BackgroundTasks
        
        print("📦 Using direct service submission (no HTTP server required)")
        print()
        
        # Create request object
        request = BusinessRegistrationRequest(**data)
        
        # Create service
        db_manager = DatabaseManager("sqlite:///bais.db")
        business_service = BusinessService(db_manager, BackgroundTasks())
        
        # Register business
        result = await business_service.register_business(request)
        
        return result
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Please install: pip3 install fastapi sqlalchemy pydantic")
        return None
    except Exception as e:
        print(f"❌ Error during direct submission: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python submit_customer_direct.py <customer_json_file>")
        print("Example: python submit_customer_direct.py customers/NewLifeNewImage_CORRECTED_BAIS_Submission.json")
        sys.exit(1)
    
    customer_file = Path(sys.argv[1])
    
    if not customer_file.exists():
        print(f"❌ Error: File not found: {customer_file}")
        sys.exit(1)
    
    print(f"📄 Reading customer data from: {customer_file}")
    print()
    
    try:
        # Extract JSON from file
        raw_data = extract_json_from_markdown(customer_file)
        
        # Prepare registration data (only required fields)
        registration_data = {
            "business_name": raw_data["business_name"],
            "business_type": raw_data["business_type"],
            "contact_info": raw_data["contact_info"],
            "location": raw_data["location"],
            "services_config": raw_data["services_config"]
        }
        
        print(f"📤 Preparing to submit:")
        print(f"   Business: {registration_data['business_name']}")
        print(f"   Type: {registration_data['business_type']}")
        print(f"   Services: {len(registration_data['services_config'])}")
        print()
        
        # Try direct submission
        result = asyncio.run(submit_directly(registration_data))
        
        if result:
            print("✅ Business registration successful!")
            print()
            print("📋 Registration Details:")
            if hasattr(result, 'business_id'):
                print(f"   Business ID: {result.business_id}")
            if hasattr(result, 'status'):
                print(f"   Status: {result.status}")
            if hasattr(result, 'mcp_endpoint'):
                print(f"   MCP Endpoint: {result.mcp_endpoint}")
            if hasattr(result, 'a2a_endpoint'):
                print(f"   A2A Endpoint: {result.a2a_endpoint}")
            print()
            print("🎉 Customer is now registered and ready to use BAIS!")
        else:
            print("❌ Registration failed. Please check the errors above.")
            sys.exit(1)
        
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

