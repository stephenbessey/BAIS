"""
Locust Load Testing Configuration
Tests system behavior under 1000+ concurrent connections
"""

from locust import HttpUser, task, between
import json
import random

class BAISUser(HttpUser):
    """Simulated BAIS platform user"""
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Setup - authenticate user"""
        # Mock authentication
        self.token = "test_token_" + str(random.randint(1000, 9999))
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def list_mcp_resources(self):
        """List MCP resources - common operation"""
        self.client.get(
            "/mcp/resources/list",
            headers=self.headers,
            name="MCP: List Resources"
        )
    
    @task(3)
    def list_mcp_tools(self):
        """List MCP tools - common operation"""
        self.client.get(
            "/mcp/tools/list",
            headers=self.headers,
            name="MCP: List Tools"
        )
    
    @task(2)
    def call_mcp_tool(self):
        """Call MCP tool - medium frequency"""
        self.client.post(
            "/mcp/tools/call",
            headers=self.headers,
            json={
                "name": "search_hotel_rooms",
                "arguments": {
                    "check_in": "2024-12-01",
                    "check_out": "2024-12-03",
                    "guests": 2
                }
            },
            name="MCP: Call Tool"
        )
    
    @task(2)
    def a2a_discover(self):
        """A2A agent discovery"""
        self.client.get(
            "/a2a/v1/discover",
            headers=self.headers,
            params={
                "capabilities": "booking",
                "type": "hotel"
            },
            name="A2A: Discover Agents"
        )
    
    @task(1)
    def create_intent_mandate(self):
        """Create AP2 intent mandate - less frequent"""
        self.client.post(
            "/api/v1/payments/mandates/intent",
            headers=self.headers,
            json={
                "user_id": f"user_{random.randint(1, 1000)}",
                "business_id": "hotel_123",
                "intent_description": "Book hotel room",
                "constraints": {
                    "max_amount": 500.0,
                    "currency": "USD"
                }
            },
            name="AP2: Create Intent Mandate"
        )
    
    @task(1)
    def payment_workflow(self):
        """Complete payment workflow - least frequent"""
        # Create intent mandate
        intent_response = self.client.post(
            "/api/v1/payments/mandates/intent",
            headers=self.headers,
            json={
                "user_id": f"user_{random.randint(1, 1000)}",
                "business_id": "hotel_123",
                "intent_description": "Book hotel room",
                "constraints": {"max_amount": 500.0}
            },
            catch_response=True,
            name="Workflow: Intent Mandate"
        )
        
        if intent_response.status_code == 201:
            intent_id = intent_response.json().get("id")
            
            # Create cart mandate
            self.client.post(
                "/api/v1/payments/mandates/cart",
                headers=self.headers,
                json={
                    "intent_mandate_id": intent_id,
                    "cart_items": [
                        {
                            "service_id": "room_001",
                            "name": "Deluxe Room",
                            "price": 299.0,
                            "quantity": 1
                        }
                    ]
                },
                name="Workflow: Cart Mandate"
            )
