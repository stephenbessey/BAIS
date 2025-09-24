"""
Baseline Performance Test
Establishes performance baseline before load testing
"""

import asyncio
import httpx
import time
from statistics import mean, median, stdev
from typing import List

class BaselinePerformanceTest:
    """Baseline performance testing"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.response_times = []
    
    async def test_endpoint(self, method: str, path: str, iterations: int = 100):
        """Test endpoint performance"""
        print(f"\nTesting {method} {path} - {iterations} iterations...")
        
        async with httpx.AsyncClient() as client:
            for i in range(iterations):
                start = time.time()
                
                try:
                    if method == "GET":
                        response = await client.get(f"{self.base_url}{path}")
                    elif method == "POST":
                        response = await client.post(
                            f"{self.base_url}{path}",
                            json={"test": "data"}
                        )
                    
                    elapsed = (time.time() - start) * 1000  # Convert to ms
                    self.response_times.append(elapsed)
                    
                    if i % 10 == 0:
                        print(f"  Progress: {i}/{iterations} - Last: {elapsed:.2f}ms")
                
                except Exception as e:
                    print(f"  Error on iteration {i}: {e}")
        
        self._print_statistics()
    
    def _print_statistics(self):
        """Print performance statistics"""
        if not self.response_times:
            print("  No data collected")
            return
        
        print(f"\n  Results:")
        print(f"    Mean:   {mean(self.response_times):.2f}ms")
        print(f"    Median: {median(self.response_times):.2f}ms")
        print(f"    Min:    {min(self.response_times):.2f}ms")
        print(f"    Max:    {max(self.response_times):.2f}ms")
        print(f"    StdDev: {stdev(self.response_times):.2f}ms")
        
        # Check against 200ms threshold
        if mean(self.response_times) > 200:
            print(f"    ⚠️  WARNING: Mean response time exceeds 200ms threshold")
        else:
            print(f"    ✅ PASS: Mean response time within threshold")
        
        self.response_times = []

async def main():
    """Run baseline tests"""
    tester = BaselinePerformanceTest("http://localhost:8000")
    
    # Test MCP endpoints
    await tester.test_endpoint("GET", "/mcp/resources/list", 100)
    await tester.test_endpoint("GET", "/mcp/tools/list", 100)
    await tester.test_endpoint("POST", "/mcp/tools/call", 100)
    
    # Test A2A endpoints
    await tester.test_endpoint("GET", "/a2a/v1/discover", 100)
    
    # Test AP2 endpoints
    await tester.test_endpoint("POST", "/api/v1/payments/mandates/intent", 50)

if __name__ == "__main__":
    asyncio.run(main())
