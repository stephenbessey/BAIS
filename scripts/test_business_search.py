#!/usr/bin/env python3
"""Test script to verify business search is working"""

import requests
import json
import sys

RAILWAY_URL = "https://bais-production.up.railway.app"

def test_search():
    """Test business search"""
    print("🔍 Testing BAIS Business Search")
    print("=" * 60)
    print()
    
    # Test 1: Check debug endpoint
    print("1. Checking registered businesses...")
    try:
        response = requests.get(f"{RAILWAY_URL}/api/v1/debug/businesses", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Found {data.get('count', 0)} businesses")
            if data.get('businesses'):
                for bid, biz in data['businesses'].items():
                    print(f"      - {biz.get('name')} ({biz.get('city')}, {biz.get('state')})")
            else:
                print("   ⚠️  No businesses found in storage")
        else:
            print(f"   ⚠️  Debug endpoint returned {response.status_code}")
            print(f"      {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error checking businesses: {e}")
    
    print()
    
    # Test 2: Search for med spa
    print("2. Searching for 'med spa' in Las Vegas...")
    try:
        response = requests.post(
            f"{RAILWAY_URL}/api/v1/llm-webhooks/claude/tool-use",
            json={
                "content": [{
                    "name": "bais_search_businesses",
                    "input": {"query": "med spa", "location": "Las Vegas"},
                    "id": "test-search"
                }]
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                results = data.get("result", [])
                print(f"   ✅ Search returned {len(results)} results")
                if results:
                    for biz in results[:3]:
                        print(f"      - {biz.get('name')} ({biz.get('location', {}).get('city')})")
                else:
                    print("   ⚠️  No businesses found in search results")
                    print("   💡 The business may not be registered or the search isn't working")
            else:
                print(f"   ❌ Search failed: {data.get('error')}")
        else:
            print(f"   ❌ Search request failed: {response.status_code}")
            print(f"      {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error during search: {e}")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    test_search()

