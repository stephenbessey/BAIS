#!/usr/bin/env python3
"""
BAIS Platform - Acceptance Test Suite
Comprehensive testing for pilot users and production readiness
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration_ms: float
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None


class AcceptanceTestSuite:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_auth_token(self) -> str:
        """Get authentication token for testing"""
        # Register a test user with unique email
        timestamp = int(time.time())
        random_id = str(uuid.uuid4())[:8]
        register_payload = {
            "email": f"test+{timestamp}+{random_id}@example.com",
            "password": "TestPass123!",
            "business_name": "Test Business",
            "contact_name": "Test User",
            "phone": "+1-555-0123"
        }
        
        # Register user
        register_response = await self.execute_request(
            "POST",
            "/api/v1/auth/register",
            authenticated=False,
            json=register_payload
        )
        
        assert register_response["status"] == 201, "User registration failed for auth token"
        
        # Login to get token
        auth_payload = {
            "email": register_payload["email"],
            "password": register_payload["password"]
        }
        
        auth_response = await self.execute_request(
            "POST",
            "/api/v1/auth/login",
            authenticated=False,
            json=auth_payload
        )
        
        assert auth_response["status"] == 200, "Authentication failed for token"
        return auth_response["data"]["access_token"]

    async def execute_request(self, method: str, endpoint: str, authenticated: bool = True, **kwargs) -> Dict:
        """Execute HTTP request with proper error handling"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "BAIS-AcceptanceTests/1.0"
        }
        
        # Add authentication if requested
        if authenticated:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Merge with any additional headers
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            del kwargs['headers']
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(
                method, 
                url, 
                headers=headers, 
                timeout=aiohttp.ClientTimeout(total=30),
                **kwargs
            ) as response:
                response_data = None
                try:
                    response_data = await response.json()
                except aiohttp.ContentTypeError:
                    response_data = await response.text()
                
                return {
                    "status": response.status,
                    "data": response_data,
                    "headers": dict(response.headers)
                }
        except asyncio.TimeoutError:
            raise AssertionError(f"Request timeout for {method} {endpoint}")
        except aiohttp.ClientError as e:
            raise AssertionError(f"Request failed: {str(e)}")

    async def run_test(self, test_func):
        """Execute a test function and record results"""
        test_name = test_func.__name__
        start_time = time.time()
        
        try:
            await test_func()
            duration = (time.time() - start_time) * 1000
            
            result = TestResult(
                name=test_name,
                status=TestStatus.PASSED,
                duration_ms=duration
            )
            logger.info(f"✓ {test_name} passed in {duration:.2f}ms")
            
        except AssertionError as e:
            duration = (time.time() - start_time) * 1000
            result = TestResult(
                name=test_name,
                status=TestStatus.FAILED,
                duration_ms=duration,
                error_message=str(e)
            )
            logger.error(f"✗ {test_name} failed: {e}")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            result = TestResult(
                name=test_name,
                status=TestStatus.FAILED,
                duration_ms=duration,
                error_message=f"Unexpected error: {str(e)}"
            )
            logger.error(f"✗ {test_name} error: {e}")
        
        self.results.append(result)
        return result

    async def test_health_endpoint(self):
        """Test health endpoint is accessible and responsive"""
        response = await self.execute_request("GET", "/health")
        
        assert response["status"] == 200, f"Expected 200, got {response['status']}"
        assert "status" in response["data"], "Response missing status field"
        assert response["data"]["status"] == "healthy", "Health check not healthy"

    async def test_user_registration(self):
        """Test user can successfully register"""
        timestamp = int(time.time())
        payload = {
            "email": f"pilot+{timestamp}@test.com",
            "password": "SecurePass123!",
            "business_name": "Test Business",
            "contact_name": "Test User",
            "phone": "+1-555-0123"
        }
        
        response = await self.execute_request(
            "POST", 
            "/api/v1/auth/register",
            json=payload
        )
        
        assert response["status"] == 201, f"Expected 201, got {response['status']}"
        assert "user_id" in response["data"], "Response missing user_id"
        assert "verification_token" in response["data"], "Missing verification token"

    async def test_user_authentication(self):
        """Test user can authenticate and receive token"""
        # First register a user
        timestamp = int(time.time())
        register_payload = {
            "email": f"auth+{timestamp}@test.com",
            "password": "TestPass123!",
            "business_name": "Auth Test Business",
            "contact_name": "Auth Test User",
            "phone": "+1-555-0123"
        }
        
        register_response = await self.execute_request(
            "POST",
            "/api/v1/auth/register",
            json=register_payload
        )
        
        assert register_response["status"] == 201, "User registration failed"
        
        # Then authenticate
        auth_payload = {
            "email": register_payload["email"],
            "password": register_payload["password"]
        }
        
        response = await self.execute_request(
            "POST",
            "/api/v1/auth/login",
            json=auth_payload
        )
        
        assert response["status"] == 200, "Authentication failed"
        assert "access_token" in response["data"], "Missing access token"
        assert "refresh_token" in response["data"], "Missing refresh token"
        assert "expires_in" in response["data"], "Missing token expiration"

    async def test_payment_workflow_creation(self):
        """Test creating a payment workflow"""
        # Get authentication token
        auth_token = await self.get_auth_token()
        
        workflow_config = {
            "name": "Test Payment Flow",
            "description": "Acceptance test payment workflow",
            "payment_provider": "stripe",
            "amount": 100.00,
            "currency": "USD",
            "webhook_url": "https://test-webhook.example.com/callback",
            "metadata": {"test": True, "environment": "staging"}
        }
        
        response = await self.execute_request(
            "POST",
            "/api/v1/workflows/payment",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=workflow_config
        )
        
        assert response["status"] == 201, "Workflow creation failed"
        assert "workflow_id" in response["data"], "Missing workflow_id"
        assert "public_key" in response["data"], "Missing public key"
        assert response["data"]["status"] == "active", "Workflow not active"

    async def test_payment_processing(self):
        """Test end-to-end payment processing"""
        # Create a test workflow first
        workflow_config = {
            "name": "Test Payment Processing",
            "description": "Test payment processing workflow",
            "payment_provider": "stripe",
            "amount": 50.00,
            "currency": "USD",
            "webhook_url": "https://test-webhook.example.com/payment"
        }
        
        # Get authentication token
        auth_token = await self.get_auth_token()
        
        workflow_response = await self.execute_request(
            "POST",
            "/api/v1/workflows/payment",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=workflow_config
        )
        
        assert workflow_response["status"] == 201, "Workflow creation failed"
        workflow_id = workflow_response["data"]["workflow_id"]
        
        # Process a test payment
        payment_data = {
            "workflow_id": workflow_id,
            "payment_method": {
                "type": "card",
                "card_number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2025,
                "cvc": "123",
                "name": "Test User"
            },
            "amount": 50.00,
            "currency": "USD",
            "customer_email": "test@example.com"
        }
        
        response = await self.execute_request(
            "POST",
            "/api/v1/payments/process",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=payment_data
        )
        
        assert response["status"] in [200, 201], "Payment processing failed"
        assert "payment_id" in response["data"], "Missing payment ID"
        assert "status" in response["data"], "Missing payment status"
        assert response["data"]["status"] in ["completed", "pending", "processing"], "Invalid payment status"

    async def test_webhook_delivery(self):
        """Test webhook event delivery"""
        webhook_config = {
            "url": "https://test-webhook.example.com/callback",
            "events": ["payment.completed", "payment.failed", "workflow.updated"],
            "secret": "test_secret_key_123",
            "active": True
        }
        
        # Get authentication token
        auth_token = await self.get_auth_token()
        
        response = await self.execute_request(
            "POST",
            "/api/v1/webhooks/configure",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=webhook_config
        )
        
        assert response["status"] == 201, "Webhook configuration failed"
        assert "webhook_id" in response["data"], "Missing webhook ID"
        assert "signature_secret" in response["data"], "Missing signature secret"

    async def test_analytics_dashboard_data(self):
        """Test analytics data retrieval"""
        # Get authentication token
        auth_token = await self.get_auth_token()
        
        response = await self.execute_request(
            "GET",
            "/api/v1/analytics/dashboard?period=7d",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response["status"] == 200, "Analytics retrieval failed"
        data = response["data"]
        
        # Check for required metrics
        required_metrics = ["total_payments", "success_rate", "total_volume", "average_amount"]
        for metric in required_metrics:
            assert metric in data, f"Missing metric: {metric}"
        
        # Validate metric types
        assert isinstance(data["total_payments"], (int, float)), "total_payments should be numeric"
        assert isinstance(data["success_rate"], (int, float)), "success_rate should be numeric"
        assert 0 <= data["success_rate"] <= 100, "success_rate should be percentage"

    async def test_rate_limiting(self):
        """Test API rate limiting enforcement"""
        responses = []
        
        # Make requests to trigger rate limiting (more aggressive)
        for i in range(150):  # Increased from 105 to 150
            response = await self.execute_request("GET", "/health", authenticated=False)
            responses.append(response["status"])
            
            # Minimal delay to trigger rate limiting faster
            if i % 20 == 0:
                await asyncio.sleep(0.05)
        
        # Check if rate limiting was enforced
        rate_limited = any(status == 429 for status in responses)
        assert rate_limited, "Rate limiting not enforced after 150 requests"
        
        # Reset rate limiting for subsequent tests
        try:
            reset_response = await self.execute_request(
                "POST",
                "/api/v1/test/reset-rate-limit",
                authenticated=False
            )
        except:
            pass  # Ignore reset errors

    async def test_error_handling(self):
        """Test proper error responses"""
        # Test invalid data
        response = await self.execute_request(
            "POST",
            "/api/v1/test/validation",
            authenticated=False,
            json={"invalid": "data", "missing_required": True}
        )
        
        assert response["status"] == 400, "Should return 400 for invalid data"
        assert "error" in response["data"], "Missing error information"
        # Check nested error structure
        assert "message" in response["data"]["error"] or "type" in response["data"]["error"], "Missing error details"
        
        # Test unauthorized access
        response = await self.execute_request(
            "GET",
            "/api/v1/analytics/dashboard",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response["status"] == 401, "Should return 401 for invalid token"

    async def test_performance_response_time(self):
        """Test response time meets SLA"""
        start = time.time()
        
        response = await self.execute_request("GET", "/health", authenticated=False)
        
        duration_ms = (time.time() - start) * 1000
        
        assert duration_ms < 200, f"Response time {duration_ms:.2f}ms exceeds 200ms SLA"
        assert response["status"] == 200, "Health check failed"

    async def test_database_connectivity(self):
        """Test database connectivity and basic operations"""
        response = await self.execute_request("GET", "/api/v1/system/status", authenticated=False)
        
        assert response["status"] == 200, "System status check failed"
        assert "database" in response["data"], "Missing database status"
        assert response["data"]["database"]["status"] == "connected", "Database not connected"

    async def test_cache_functionality(self):
        """Test Redis cache functionality"""
        # Test cache write
        cache_data = {"test_key": "test_value", "timestamp": time.time()}
        response = await self.execute_request(
            "POST",
            "/api/v1/cache/test",
            authenticated=False,
            json=cache_data
        )
        
        assert response["status"] == 200, "Cache write failed"
        
        # Test cache read
        response = await self.execute_request("GET", "/api/v1/cache/test", authenticated=False)
        
        assert response["status"] == 200, "Cache read failed"
        assert response["data"]["test_key"] == "test_value", "Cache data mismatch"

    async def test_concurrent_requests(self):
        """Test system handles concurrent requests properly"""
        async def make_request():
            return await self.execute_request("GET", "/health", authenticated=False)
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response["status"] == 200, "Concurrent request failed"

    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        
        avg_duration = sum(r.duration_ms for r in self.results) / total if total > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "test_suite": "BAIS Platform Acceptance Tests",
            "environment": "staging",
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "success_rate": (passed / total * 100) if total > 0 else 0,
                "average_duration_ms": avg_duration
            },
            "results": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "duration_ms": round(r.duration_ms, 2),
                    "error": r.error_message
                }
                for r in self.results
            ],
            "recommendations": self._generate_recommendations(passed, failed)
        }

    def _generate_recommendations(self, passed: int, failed: int) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        total = passed + failed
        
        if failed == 0:
            recommendations.append("✅ All tests passed - Ready for production deployment")
            recommendations.append("🎯 Proceed with monitoring setup and on-call rotation")
        else:
            recommendations.append(f"⚠️ {failed} test(s) failed - Review and fix issues before production")
            recommendations.append("🔧 Run tests again after fixes")
            
            if failed > total * 0.3:
                recommendations.append("🚨 High failure rate - Consider delaying production deployment")

        return recommendations

    async def run_all_tests(self):
        """Execute all acceptance tests"""
        test_methods = [
            self.test_health_endpoint,
            self.test_user_registration,
            self.test_user_authentication,
            self.test_payment_workflow_creation,
            self.test_payment_processing,
            self.test_webhook_delivery,
            self.test_analytics_dashboard_data,
            self.test_rate_limiting,
            self.test_error_handling,
            self.test_performance_response_time,
            self.test_database_connectivity,
            self.test_cache_functionality,
            self.test_concurrent_requests
        ]
        
        logger.info("Starting BAIS Platform acceptance test suite...")
        logger.info(f"Target URL: {self.base_url}")
        
        for test in test_methods:
            await self.run_test(test)
        
        report = self.generate_report()
        
        # Display results
        logger.info("\n" + "="*60)
        logger.info("BAIS PLATFORM ACCEPTANCE TEST REPORT")
        logger.info("="*60)
        logger.info(f"Total Tests: {report['summary']['total_tests']}")
        logger.info(f"Passed: {report['summary']['passed']}")
        logger.info(f"Failed: {report['summary']['failed']}")
        logger.info(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        logger.info(f"Average Duration: {report['summary']['average_duration_ms']:.2f}ms")
        logger.info("="*60)
        
        # Display recommendations
        logger.info("\nRecommendations:")
        for rec in report['recommendations']:
            logger.info(rec)
        
        # Save report
        report_filename = f"acceptance_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\nDetailed report saved to: {report_filename}")
        
        return report


async def main():
    """Main entry point for acceptance tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BAIS Platform Acceptance Test Suite")
    parser.add_argument("--url", default="http://staging-api.bais.io", help="Base URL for testing")
    parser.add_argument("--api-key", default="test_api_key_123", help="API key for authentication")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    async with AcceptanceTestSuite(args.url, args.api_key) as test_suite:
        report = await test_suite.run_all_tests()
        
        # Exit with error code if tests failed
        if report["summary"]["failed"] > 0:
            exit(1)


if __name__ == "__main__":
    asyncio.run(main())
