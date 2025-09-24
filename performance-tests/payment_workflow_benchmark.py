"""
AP2 Payment Workflow Performance Benchmark
Tests payment workflow under various load conditions
"""

import asyncio
import time
from typing import List, Dict
from dataclasses import dataclass
import statistics

@dataclass
class PaymentWorkflowMetrics:
    """Metrics for payment workflow"""
    workflow_id: str
    intent_time_ms: float
    cart_time_ms: float
    payment_time_ms: float
    total_time_ms: float
    success: bool
    error: str = None


class PaymentWorkflowBenchmark:
    """Benchmark payment workflows"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.metrics: List[PaymentWorkflowMetrics] = []
    
    async def run_single_workflow(self, user_id: str) -> PaymentWorkflowMetrics:
        """Run a single payment workflow"""
        import httpx
        
        workflow_id = f"workflow_{user_id}_{int(time.time()*1000)}"
        
        async with httpx.AsyncClient() as client:
            # Step 1: Create intent mandate
            intent_start = time.time()
            try:
                intent_response = await client.post(
                    f"{self.base_url}/api/v1/payments/mandates/intent",
                    json={
                        "user_id": user_id,
                        "business_id": "hotel_123",
                        "intent_description": "Book hotel room",
                        "constraints": {
                            "max_amount": 500.0,
                            "currency": "USD"
                        }
                    }
                )
                intent_time = (time.time() - intent_start) * 1000
                
                if intent_response.status_code != 201:
                    return PaymentWorkflowMetrics(
                        workflow_id=workflow_id,
                        intent_time_ms=intent_time,
                        cart_time_ms=0,
                        payment_time_ms=0,
                        total_time_ms=intent_time,
                        success=False,
                        error=f"Intent failed: {intent_response.status_code}"
                    )
                
                intent_id = intent_response.json()["id"]
                
                # Step 2: Create cart mandate
                cart_start = time.time()
                cart_response = await client.post(
                    f"{self.base_url}/api/v1/payments/mandates/cart",
                    json={
                        "intent_mandate_id": intent_id,
                        "cart_items": [
                            {
                                "service_id": "room_001",
                                "name": "Deluxe Room",
                                "price": 299.0,
                                "quantity": 1,
                                "currency": "USD"
                            }
                        ]
                    }
                )
                cart_time = (time.time() - cart_start) * 1000
                
                if cart_response.status_code != 201:
                    return PaymentWorkflowMetrics(
                        workflow_id=workflow_id,
                        intent_time_ms=intent_time,
                        cart_time_ms=cart_time,
                        payment_time_ms=0,
                        total_time_ms=intent_time + cart_time,
                        success=False,
                        error=f"Cart failed: {cart_response.status_code}"
                    )
                
                cart_id = cart_response.json()["id"]
                
                # Step 3: Execute payment
                payment_start = time.time()
                payment_response = await client.post(
                    f"{self.base_url}/api/v1/payments/transactions/execute",
                    json={
                        "cart_mandate_id": cart_id,
                        "payment_method_id": "pm_test_123"
                    }
                )
                payment_time = (time.time() - payment_start) * 1000
                
                total_time = intent_time + cart_time + payment_time
                
                return PaymentWorkflowMetrics(
                    workflow_id=workflow_id,
                    intent_time_ms=intent_time,
                    cart_time_ms=cart_time,
                    payment_time_ms=payment_time,
                    total_time_ms=total_time,
                    success=payment_response.status_code == 200,
                    error=None if payment_response.status_code == 200 
                          else f"Payment failed: {payment_response.status_code}"
                )
                
            except Exception as e:
                return PaymentWorkflowMetrics(
                    workflow_id=workflow_id,
                    intent_time_ms=0,
                    cart_time_ms=0,
                    payment_time_ms=0,
                    total_time_ms=0,
                    success=False,
                    error=str(e)
                )
    
    async def run_concurrent_workflows(self, num_workflows: int) -> List[PaymentWorkflowMetrics]:
        """Run multiple workflows concurrently"""
        tasks = [
            self.run_single_workflow(f"user_{i}")
            for i in range(num_workflows)
        ]
        return await asyncio.gather(*tasks)
    
    def print_results(self, metrics: List[PaymentWorkflowMetrics]):
        """Print benchmark results"""
        successful = [m for m in metrics if m.success]
        failed = [m for m in metrics if not m.success]
        
        print("\n" + "="*80)
        print("PAYMENT WORKFLOW BENCHMARK RESULTS")
        print("="*80)
        
        print(f"\n📊 OVERVIEW")
        print(f"  Total Workflows:     {len(metrics)}")
        print(f"  Successful:          {len(successful)} ({len(successful)/len(metrics)*100:.1f}%)")
        print(f"  Failed:              {len(failed)} ({len(failed)/len(metrics)*100:.1f}%)")
        
        if successful:
            total_times = [m.total_time_ms for m in successful]
            intent_times = [m.intent_time_ms for m in successful]
            cart_times = [m.cart_time_ms for m in successful]
            payment_times = [m.payment_time_ms for m in successful]
            
            print(f"\n⏱️  TIMING BREAKDOWN (Successful Workflows)")
            print(f"  Intent Mandate:")
            print(f"    Mean:   {statistics.mean(intent_times):.2f}ms")
            print(f"    Median: {statistics.median(intent_times):.2f}ms")
            print(f"    P95:    {statistics.quantiles(intent_times, n=20)[18]:.2f}ms")
            
            print(f"  Cart Mandate:")
            print(f"    Mean:   {statistics.mean(cart_times):.2f}ms")
            print(f"    Median: {statistics.median(cart_times):.2f}ms")
            print(f"    P95:    {statistics.quantiles(cart_times, n=20)[18]:.2f}ms")
            
            print(f"  Payment Execution:")
            print(f"    Mean:   {statistics.mean(payment_times):.2f}ms")
            print(f"    Median: {statistics.median(payment_times):.2f}ms")
            print(f"    P95:    {statistics.quantiles(payment_times, n=20)[18]:.2f}ms")
            
            print(f"  Total Workflow:")
            print(f"    Mean:   {statistics.mean(total_times):.2f}ms")
            print(f"    Median: {statistics.median(total_times):.2f}ms")
            print(f"    P95:    {statistics.quantiles(total_times, n=20)[18]:.2f}ms")
            print(f"    Min:    {min(total_times):.2f}ms")
            print(f"    Max:    {max(total_times):.2f}ms")
            
            # Throughput calculation
            duration_seconds = sum(total_times) / 1000
            throughput = len(successful) / duration_seconds if duration_seconds > 0 else 0
            
            print(f"\n🚀 THROUGHPUT")
            print(f"  Workflows/second: {throughput:.2f}")
            
            if throughput >= 100:
                print(f"  ✅ PASSED: Throughput exceeds 100 workflows/second")
            else:
                print(f"  ❌ FAILED: Throughput below 100 workflows/second target")
        
        if failed:
            print(f"\n❌ FAILURES")
            error_counts = {}
            for m in failed:
                error_counts[m.error] = error_counts.get(m.error, 0) + 1
            
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count} occurrences")


async def main():
    """Run payment workflow benchmarks"""
    benchmark = PaymentWorkflowBenchmark("http://localhost:8000")
    
    print("Starting Payment Workflow Benchmark...")
    
    # Test different concurrency levels
    for concurrency in [10, 50, 100, 200]:
        print(f"\n\n{'='*80}")
        print(f"Testing with {concurrency} concurrent workflows")
        print(f"{'='*80}")
        
        start_time = time.time()
        metrics = await benchmark.run_concurrent_workflows(concurrency)
        elapsed = time.time() - start_time
        
        benchmark.print_results(metrics)
        print(f"\nTest Duration: {elapsed:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
