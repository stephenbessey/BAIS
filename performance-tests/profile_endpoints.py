"""
API Endpoint Profiler
Identifies performance bottlenecks in API endpoints
"""

import cProfile
import pstats
import io
from fastapi.testclient import TestClient
import sys
sys.path.append('../backend/production')

from main import app

client = TestClient(app)

def profile_endpoint(method: str, path: str, json_data=None):
    """Profile a single endpoint"""
    print(f"\n{'='*80}")
    print(f"PROFILING: {method} {path}")
    print(f"{'='*80}")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Execute request
    if method == "GET":
        response = client.get(path)
    elif method == "POST":
        response = client.post(path, json=json_data)
    
    profiler.disable()
    
    # Print results
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 functions
    
    print(s.getvalue())
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Time: {response.elapsed.total_seconds()*1000:.2f}ms")

# Profile key endpoints
if __name__ == "__main__":
    print("Starting API Endpoint Profiling...")
    
    # Test basic endpoints first
    try:
        profile_endpoint("GET", "/")
        profile_endpoint("GET", "/health")
    except Exception as e:
        print(f"Error profiling basic endpoints: {e}")
    
    # Test MCP endpoints
    try:
        profile_endpoint("GET", "/mcp/resources/list?business_id=hotel_123")
        profile_endpoint("GET", "/mcp/tools/list?business_id=hotel_123")
        profile_endpoint("POST", "/mcp/tools/call", {
            "name": "search_hotel_rooms",
            "arguments": {"check_in": "2024-12-01", "guests": 2}
        })
    except Exception as e:
        print(f"Error profiling MCP endpoints: {e}")
    
    # Test A2A endpoints
    try:
        profile_endpoint("GET", "/a2a/v1/discover?capabilities=booking")
    except Exception as e:
        print(f"Error profiling A2A endpoints: {e}")
    
    # Test AP2 endpoints
    try:
        profile_endpoint("POST", "/api/v1/payments/mandates/intent", {
            "user_id": "user123",
            "business_id": "hotel123",
            "intent_description": "Book room",
            "constraints": {"max_amount": 500}
        })
    except Exception as e:
        print(f"Error profiling AP2 endpoints: {e}")
    
    print("\nProfiling complete!")
