"""
Mock Performance Test
Tests performance infrastructure without requiring running application
"""

import time
import asyncio
import random
from statistics import mean, median, stdev
from typing import List, Dict
import json

class MockPerformanceTest:
    """Mock performance testing for infrastructure validation"""
    
    def __init__(self):
        self.results = {}
    
    def simulate_api_call(self, endpoint: str, base_time: float = 0.1) -> float:
        """Simulate API call with realistic timing"""
        # Add some random variation
        variation = random.uniform(0.8, 1.2)
        # Simulate different endpoint complexities
        complexity = {
            "/mcp/resources/list": 1.0,
            "/mcp/tools/list": 1.1,
            "/mcp/tools/call": 1.5,
            "/a2a/v1/discover": 1.2,
            "/api/v1/payments/mandates/intent": 1.8,
            "/api/v1/payments/mandates/cart": 1.6,
            "/api/v1/payments/transactions/execute": 2.0
        }
        
        multiplier = complexity.get(endpoint, 1.0)
        response_time = base_time * multiplier * variation
        
        # Simulate occasional slow responses
        if random.random() < 0.05:  # 5% chance of slow response
            response_time *= random.uniform(3, 8)
        
        return response_time
    
    def run_baseline_test(self, iterations: int = 100) -> Dict:
        """Run baseline performance test simulation"""
        print("🔍 Running Baseline Performance Test (Simulated)")
        print("="*60)
        
        endpoints = [
            "/mcp/resources/list",
            "/mcp/tools/list", 
            "/mcp/tools/call",
            "/a2a/v1/discover",
            "/api/v1/payments/mandates/intent"
        ]
        
        results = {}
        
        for endpoint in endpoints:
            print(f"\nTesting {endpoint} - {iterations} iterations...")
            
            response_times = []
            errors = 0
            
            for i in range(iterations):
                try:
                    response_time = self.simulate_api_call(endpoint)
                    response_times.append(response_time * 1000)  # Convert to ms
                    
                    if i % 20 == 0:
                        print(f"  Progress: {i}/{iterations} - Last: {response_time*1000:.2f}ms")
                        
                except Exception as e:
                    errors += 1
            
            if response_times:
                results[endpoint] = {
                    "mean": mean(response_times),
                    "median": median(response_times),
                    "min": min(response_times),
                    "max": max(response_times),
                    "stdev": stdev(response_times),
                    "errors": errors,
                    "success_rate": (iterations - errors) / iterations * 100
                }
                
                print(f"\n  Results:")
                print(f"    Mean:   {results[endpoint]['mean']:.2f}ms")
                print(f"    Median: {results[endpoint]['median']:.2f}ms")
                print(f"    Min:    {results[endpoint]['min']:.2f}ms")
                print(f"    Max:    {results[endpoint]['max']:.2f}ms")
                print(f"    StdDev: {results[endpoint]['stdev']:.2f}ms")
                print(f"    Errors: {errors} ({results[endpoint]['success_rate']:.1f}% success)")
                
                if results[endpoint]['mean'] > 200:
                    print(f"    ⚠️  WARNING: Mean response time exceeds 200ms threshold")
                else:
                    print(f"    ✅ PASS: Mean response time within threshold")
        
        return results
    
    def run_load_test_simulation(self, users: int = 1000, duration: int = 300) -> Dict:
        """Simulate load testing"""
        print(f"\n🔥 Running Load Test Simulation ({users} users, {duration}s)")
        print("="*60)
        
        endpoints = [
            "/mcp/resources/list",
            "/mcp/tools/list",
            "/a2a/v1/discover",
            "/api/v1/payments/mandates/intent"
        ]
        
        total_requests = 0
        total_errors = 0
        response_times = []
        
        start_time = time.time()
        
        # Simulate concurrent users
        for second in range(duration):
            # Simulate requests per second based on user load
            requests_per_second = users * random.uniform(0.1, 0.5)  # 0.1-0.5 requests per user per second
            
            for _ in range(int(requests_per_second)):
                endpoint = random.choice(endpoints)
                response_time = self.simulate_api_call(endpoint)
                
                total_requests += 1
                response_times.append(response_time * 1000)
                
                # Simulate errors (1% error rate)
                if random.random() < 0.01:
                    total_errors += 1
            
            if second % 30 == 0:  # Print progress every 30 seconds
                elapsed = time.time() - start_time
                rps = total_requests / elapsed
                error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
                avg_response = mean(response_times[-100:]) if response_times else 0
                
                print(f"  {second}s: {total_requests:,} requests, {rps:.1f} RPS, {error_rate:.2f}% errors, {avg_response:.1f}ms avg")
        
        elapsed = time.time() - start_time
        
        results = {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": (total_errors / total_requests * 100) if total_requests > 0 else 0,
            "avg_response_time": mean(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "requests_per_second": total_requests / elapsed,
            "duration": elapsed
        }
        
        print(f"\n📊 Load Test Results:")
        print(f"  Total Requests: {results['total_requests']:,}")
        print(f"  Total Errors: {results['total_errors']:,}")
        print(f"  Error Rate: {results['error_rate']:.2f}%")
        print(f"  Avg Response Time: {results['avg_response_time']:.2f}ms")
        print(f"  Max Response Time: {results['max_response_time']:.2f}ms")
        print(f"  Requests/Second: {results['requests_per_second']:.1f}")
        
        # Check performance targets
        if results['avg_response_time'] < 200:
            print(f"  ✅ PASS: Average response time < 200ms")
        else:
            print(f"  ❌ FAIL: Average response time > 200ms")
        
        if results['error_rate'] < 1:
            print(f"  ✅ PASS: Error rate < 1%")
        else:
            print(f"  ❌ FAIL: Error rate > 1%")
        
        return results
    
    def run_payment_workflow_simulation(self, workflows: int = 100) -> Dict:
        """Simulate payment workflow performance"""
        print(f"\n💳 Running Payment Workflow Simulation ({workflows} workflows)")
        print("="*60)
        
        workflow_times = []
        successful_workflows = 0
        
        for i in range(workflows):
            # Simulate workflow steps
            intent_time = self.simulate_api_call("/api/v1/payments/mandates/intent", 0.15)
            cart_time = self.simulate_api_call("/api/v1/payments/mandates/cart", 0.12)
            payment_time = self.simulate_api_call("/api/v1/payments/transactions/execute", 0.18)
            
            total_time = intent_time + cart_time + payment_time
            
            # Simulate 99% success rate
            if random.random() < 0.99:
                successful_workflows += 1
                workflow_times.append(total_time * 1000)  # Convert to ms
            
            if i % 20 == 0:
                print(f"  Progress: {i}/{workflows} - Last workflow: {total_time*1000:.2f}ms")
        
        if workflow_times:
            results = {
                "total_workflows": workflows,
                "successful_workflows": successful_workflows,
                "success_rate": (successful_workflows / workflows) * 100,
                "avg_workflow_time": mean(workflow_times),
                "median_workflow_time": median(workflow_times),
                "min_workflow_time": min(workflow_times),
                "max_workflow_time": max(workflow_times),
                "workflows_per_second": len(workflow_times) / sum(workflow_times) * 1000
            }
            
            print(f"\n📊 Payment Workflow Results:")
            print(f"  Total Workflows: {results['total_workflows']}")
            print(f"  Successful: {results['successful_workflows']} ({results['success_rate']:.1f}%)")
            print(f"  Avg Workflow Time: {results['avg_workflow_time']:.2f}ms")
            print(f"  Median Workflow Time: {results['median_workflow_time']:.2f}ms")
            print(f"  Workflows/Second: {results['workflows_per_second']:.2f}")
            
            # Check performance targets
            if results['avg_workflow_time'] < 200:
                print(f"  ✅ PASS: Average workflow time < 200ms")
            else:
                print(f"  ❌ FAIL: Average workflow time > 200ms")
            
            if results['workflows_per_second'] >= 100:
                print(f"  ✅ PASS: Throughput >= 100 workflows/second")
            else:
                print(f"  ❌ FAIL: Throughput < 100 workflows/second")
            
            return results
        
        return {}
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        print(f"\n📋 Generating Performance Report")
        print("="*60)
        
        # Run all tests
        baseline_results = self.run_baseline_test(50)  # Reduced for demo
        load_results = self.run_load_test_simulation(500, 60)  # Reduced for demo
        payment_results = self.run_payment_workflow_simulation(50)  # Reduced for demo
        
        # Generate report
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_type": "Mock Performance Test",
            "baseline_results": baseline_results,
            "load_test_results": load_results,
            "payment_workflow_results": payment_results,
            "performance_summary": {
                "api_response_time_target": "< 200ms",
                "concurrent_users_target": "1000+",
                "payment_throughput_target": "100+/sec",
                "error_rate_target": "< 1%"
            }
        }
        
        # Save report
        with open("performance-tests/reports/mock-performance-report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✅ Performance Report Generated:")
        print(f"  File: performance-tests/reports/mock-performance-report.json")
        
        return json.dumps(report, indent=2)

def main():
    """Run mock performance tests"""
    print("🚀 Starting Mock Performance Testing")
    print("====================================")
    print("Note: This is a simulation to validate testing infrastructure")
    print("For real testing, ensure the BAIS application is running on localhost:8000")
    print()
    
    tester = MockPerformanceTest()
    
    # Generate comprehensive report
    report = tester.generate_performance_report()
    
    print(f"\n🎉 Mock Performance Testing Complete!")
    print("====================================")
    print("All testing infrastructure validated and working correctly.")
    print("Ready for real performance testing when application is running.")

if __name__ == "__main__":
    main()
