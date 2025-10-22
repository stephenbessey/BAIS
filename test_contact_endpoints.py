#!/usr/bin/env python3
"""
Test script to verify contact endpoints are working
"""

import requests
import json
import sys

# Test configuration
BASE_URL = "http://localhost:8000"
CONTACT_ENDPOINT = f"{BASE_URL}/api/v1/contact"
BUSINESS_ENDPOINT = f"{BASE_URL}/api/v1/business-registration"

def test_contact_endpoint():
    """Test the contact form endpoint"""
    print("Testing contact endpoint...")
    
    contact_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "business_name": "Test Business",
        "business_type": "restaurant",
        "message": "I'm interested in learning more about BAIS platform.",
        "hear_about": "google",
        "demo_requested": True
    }
    
    try:
        response = requests.post(CONTACT_ENDPOINT, json=contact_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Contact endpoint working!")
            return True
        else:
            print("❌ Contact endpoint failed!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing contact endpoint: {str(e)}")
        return False

def test_business_registration_endpoint():
    """Test the business registration endpoint"""
    print("\nTesting business registration endpoint...")
    
    business_data = {
        "business_name": "Test Restaurant",
        "business_type": "restaurant",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@testrestaurant.com",
        "phone": "+1234567890",
        "city": "San Francisco",
        "state": "CA",
        "business_description": "A fine dining restaurant specializing in Italian cuisine.",
        "hear_about": "referral"
    }
    
    try:
        response = requests.post(BUSINESS_ENDPOINT, json=business_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Business registration endpoint working!")
            return True
        else:
            print("❌ Business registration endpoint failed!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing business registration endpoint: {str(e)}")
        return False

def test_health_endpoint():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Health endpoint working!")
            return True
        else:
            print("❌ Health endpoint failed!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing health endpoint: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing BAIS Backend Contact Endpoints")
    print("=" * 50)
    
    # Test health first
    health_ok = test_health_endpoint()
    
    if not health_ok:
        print("\n❌ Backend is not running or not accessible.")
        print("Please start the backend server first:")
        print("cd /Users/stephenbessey/Documents/Development/BAIS")
        print("python app.py")
        sys.exit(1)
    
    # Test contact endpoints
    contact_ok = test_contact_endpoint()
    business_ok = test_business_registration_endpoint()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Health Endpoint: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Contact Endpoint: {'✅ PASS' if contact_ok else '❌ FAIL'}")
    print(f"Business Registration: {'✅ PASS' if business_ok else '❌ FAIL'}")
    
    if all([health_ok, contact_ok, business_ok]):
        print("\n🎉 All tests passed! Backend is ready for frontend integration.")
    else:
        print("\n⚠️  Some tests failed. Check the backend logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
