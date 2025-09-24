"""
Cache Performance Testing
Validates caching improves performance
"""

import asyncio
import time
import httpx
from statistics import mean

async def test_cache_effectiveness(base_url: str, endpoint: str, iterations: int = 100):
    """Test cache performance improvement"""
    
    print(f"\nTesting cache effectiveness for {endpoint}")
    print("="*80)
    
    async with httpx.AsyncClient() as client:
        # Test without cache (first request)
        uncached_times = []
        for i in range(iterations):
            # Add random query param to bust cache
            start = time.time()
            response = await client.get(
                f"{base_url}{endpoint}?bust_cache={i}"
            )
            elapsed = (time.time() - start) * 1000
            uncached_times.append(elapsed)
        
        # Test with cache (same request repeated)
        cached_times = []
        for i in range(iterations):
            start = time.time()
            response = await client.get(f"{base_url}{endpoint}")
            elapsed = (time.time() - start) * 1000
            cached_times.append(elapsed)
        
        # Results
        avg_uncached = mean(uncached_times)
        avg_cached = mean(cached_times)
        improvement = ((avg_uncached - avg_cached) / avg_uncached) * 100
        
        print(f"  Average Uncached Response: {avg_uncached:.2f}ms")
        print(f"  Average Cached Response:   {avg_cached:.2f}ms")
        print(f"  Performance Improvement:   {improvement:.1f}%")
        
        if improvement > 50:
            print(f"  ✅ EXCELLENT: Cache provides {improvement:.1f}% improvement")
        elif improvement > 25:
            print(f"  ✅ GOOD: Cache provides {improvement:.1f}% improvement")
        else:
            print(f"  ⚠️  WARNING: Cache only provides {improvement:.1f}% improvement")

async def main():
    base_url = "http://localhost:8000"
    
    await test_cache_effectiveness(base_url, "/mcp/resources/list?business_id=hotel_123")
    await test_cache_effectiveness(base_url, "/mcp/tools/list?business_id=hotel_123")
    await test_cache_effectiveness(base_url, "/api/v1/businesses/hotel_123")

if __name__ == "__main__":
    asyncio.run(main())
