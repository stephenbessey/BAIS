#!/usr/bin/env python3
"""
Test script to verify dashboard API integration
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
API_BASE_URL = "http://localhost:8000"  # Update with your actual API URL
BUSINESS_ID = "test-business-id"  # Update with actual business ID

def test_platform_dashboard():
    """Test platform dashboard endpoint"""
    print("Testing Platform Dashboard...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/dashboard/platform")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Platform Dashboard API working")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Platform Dashboard API failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Platform Dashboard API error: {e}")
        return False

def test_business_dashboard():
    """Test business dashboard endpoint"""
    print("Testing Business Dashboard...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/dashboard/business/{BUSINESS_ID}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Business Dashboard API working")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        elif response.status_code == 404:
            print(f"⚠️  Business Dashboard API - Business not found (expected for test)")
            return True
        else:
            print(f"❌ Business Dashboard API failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Business Dashboard API error: {e}")
        return False

def test_platform_health():
    """Test platform health endpoint"""
    print("Testing Platform Health...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/dashboard/platform/health")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Platform Health API working")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Platform Health API failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Platform Health API error: {e}")
        return False

def main():
    """Run all dashboard tests"""
    print("🚀 Testing BAIS Dashboard API Integration")
    print("=" * 50)
    
    tests = [
        test_platform_dashboard,
        test_business_dashboard,
        test_platform_health
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All dashboard tests passed! Ready for customer onboarding.")
    else:
        print("⚠️  Some tests failed. Check the backend implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
