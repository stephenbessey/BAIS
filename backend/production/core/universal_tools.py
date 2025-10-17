"""
BAIS Universal Tools Architecture
Universal Business Access Through Any AI Platform

This architecture enables ANY consumer to buy from ANY BAIS business
through Claude, ChatGPT, or Gemini with NO per-business setup required.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum


# ============================================================================
# CRITICAL INSIGHT: BAIS registers as ONE tool with each LLM provider
# All businesses are accessible through this single integration
# ============================================================================


class BAISUniversalTool:
    """
    Universal BAIS tool definition that works for ALL businesses.
    This is what gets registered with Claude, ChatGPT, and Gemini.
    """
    
    @staticmethod
    def get_tool_definitions() -> Dict[str, List[Dict[str, Any]]]:
        """
        Returns the tool definitions that BAIS registers with each LLM.
        These are the ONLY tools needed - they work for ALL businesses.
        """
        return {
            "claude": [
                {
                    "name": "bais_search_businesses",
                    "description": """Search for businesses on the BAIS platform. 
                    Find restaurants, hotels, services, and more that accept AI-assisted purchases.
                    Returns business information and available services.""",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (business name, type, or location)"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["restaurant", "hotel", "retail", "service", "healthcare"],
                                "description": "Filter by business category"
                            },
                            "location": {
                                "type": "string",
                                "description": "City or address to search near"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "bais_get_business_services",
                    "description": """Get detailed information about services offered by a specific business.
                    Returns available services, pricing, and booking requirements.""",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "business_id": {
                                "type": "string",
                                "description": "Unique identifier for the business"
                            }
                        },
                        "required": ["business_id"]
                    }
                },
                {
                    "name": "bais_execute_service",
                    "description": """Execute a business service (booking, purchase, reservation, etc.).
                    Handles the complete transaction including payment if required.""",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "business_id": {
                                "type": "string",
                                "description": "Business identifier from search results"
                            },
                            "service_id": {
                                "type": "string",
                                "description": "Service identifier from business services"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Service-specific parameters (date, time, quantity, etc.)"
                            },
                            "customer_info": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string"},
                                    "phone": {"type": "string"}
                                },
                                "required": ["name", "email"]
                            }
                        },
                        "required": ["business_id", "service_id", "parameters", "customer_info"]
                    }
                }
            ],
            "chatgpt": [
                {
                    "name": "bais_search_businesses",
                    "description": "Search for businesses on BAIS platform that accept AI purchases",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "category": {
                                "type": "string",
                                "enum": ["restaurant", "hotel", "retail", "service", "healthcare"]
                            },
                            "location": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "bais_get_business_services",
                    "description": "Get services offered by a specific business",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "business_id": {"type": "string"}
                        },
                        "required": ["business_id"]
                    }
                },
                {
                    "name": "bais_execute_service",
                    "description": "Execute a business service (booking, purchase, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "business_id": {"type": "string"},
                            "service_id": {"type": "string"},
                            "parameters": {"type": "object"},
                            "customer_info": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string"},
                                    "phone": {"type": "string"}
                                }
                            }
                        },
                        "required": ["business_id", "service_id", "parameters", "customer_info"]
                    }
                }
            ],
            "gemini": [
                {
                    "name": "bais_search_businesses",
                    "description": "Search BAIS platform for businesses",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "category": {"type": "string"},
                            "location": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "bais_get_business_services",
                    "description": "Get business service details",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "business_id": {"type": "string"}
                        },
                        "required": ["business_id"]
                    }
                },
                {
                    "name": "bais_execute_service",
                    "description": "Execute a business service",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "business_id": {"type": "string"},
                            "service_id": {"type": "string"},
                            "parameters": {"type": "object"},
                            "customer_info": {"type": "object"}
                        },
                        "required": ["business_id", "service_id", "parameters", "customer_info"]
                    }
                }
            ]
        }


class BAISUniversalToolHandler:
    """
    Handles execution of universal BAIS tools.
    All businesses are accessible through these handlers.
    """
    
    def __init__(self, db_manager=None):
        """Initialize with database manager for business operations"""
        self.db_manager = db_manager
    
    async def search_businesses(
        self,
        query: str,
        category: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for businesses across the entire BAIS platform.
        Returns list of matching businesses with their services.
        """
        try:
            # Use existing business registry/search functionality
            from ..services.business_registry_service import BusinessRegistryService
            from ..core.database_models import Business, BusinessService
            
            # Create search parameters
            search_params = {
                "query": query,
                "category": category,
                "location": location,
                "limit": 10
            }
            
            # For now, return mock data that integrates with your existing structure
            # In production, this would query your actual business database
            mock_businesses = [
                {
                    "business_id": "hotel_001",
                    "name": "Zion Adventure Lodge",
                    "description": "Luxury lodge near Zion National Park with restaurant and activities",
                    "category": "hospitality",
                    "location": {
                        "city": "Springdale",
                        "state": "UT",
                        "address": "123 Canyon View Dr, Springdale, UT"
                    },
                    "rating": 4.8,
                    "services": [
                        {
                            "id": "room_booking",
                            "name": "Room Reservation",
                            "description": "Book a room for your stay"
                        },
                        {
                            "id": "restaurant_booking", 
                            "name": "Restaurant Reservation",
                            "description": "Reserve a table at our restaurant"
                        },
                        {
                            "id": "activity_booking",
                            "name": "Activity Booking",
                            "description": "Book outdoor activities and tours"
                        }
                    ]
                },
                {
                    "business_id": "restaurant_001",
                    "name": "Red Canyon Brewing",
                    "description": "Local brewery and restaurant with craft beer and dining",
                    "category": "food_service",
                    "location": {
                        "city": "Springdale",
                        "state": "UT", 
                        "address": "456 Brewery Lane, Springdale, UT"
                    },
                    "rating": 4.6,
                    "services": [
                        {
                            "id": "table_reservation",
                            "name": "Table Reservation",
                            "description": "Reserve a table for dining"
                        },
                        {
                            "id": "takeout_order",
                            "name": "Takeout Order",
                            "description": "Order food for takeout"
                        },
                        {
                            "id": "event_booking",
                            "name": "Event Booking",
                            "description": "Book private events and parties"
                        }
                    ]
                },
                {
                    "business_id": "retail_001",
                    "name": "Desert Pearl Gifts",
                    "description": "Gift shop with local crafts, souvenirs, and outdoor gear",
                    "category": "retail",
                    "location": {
                        "city": "Springdale",
                        "state": "UT",
                        "address": "789 Merchant Square, Springdale, UT"
                    },
                    "rating": 4.4,
                    "services": [
                        {
                            "id": "product_search",
                            "name": "Product Search",
                            "description": "Search for products and availability"
                        },
                        {
                            "id": "special_order",
                            "name": "Special Order",
                            "description": "Place special orders for items"
                        }
                    ]
                }
            ]
            
            # Filter results based on search criteria
            filtered_businesses = []
            for business in mock_businesses:
                # Simple text matching for now
                if query.lower() in business.get("name", "").lower() or query.lower() in business.get("description", "").lower():
                    if category and business.get("category") != category:
                        continue
                    if location and location.lower() not in business.get("location", {}).get("city", "").lower():
                        continue
                    filtered_businesses.append(business)
            
            return filtered_businesses[:10]  # Limit to 10 results
            
        except Exception as e:
            # Return error information
            return [{
                "error": f"Search failed: {str(e)}",
                "businesses": []
            }]
    
    async def get_business_services(
        self,
        business_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed service information for a specific business.
        """
        try:
            # Mock data - in production, query your actual business database
            business_services = {
                "hotel_001": {
                    "business_id": "hotel_001",
                    "business_name": "Zion Adventure Lodge",
                    "services": [
                        {
                            "service_id": "room_booking",
                            "name": "Room Reservation",
                            "description": "Book a room for your stay at Zion Adventure Lodge",
                            "parameters": {
                                "check_in_date": "date",
                                "check_out_date": "date", 
                                "room_type": "string",
                                "guests": "integer"
                            },
                            "pricing": {
                                "base_price": 299.00,
                                "currency": "USD"
                            },
                            "availability": "available"
                        },
                        {
                            "service_id": "restaurant_booking",
                            "name": "Restaurant Reservation", 
                            "description": "Reserve a table at our on-site restaurant",
                            "parameters": {
                                "date": "date",
                                "time": "time",
                                "party_size": "integer",
                                "special_requests": "string"
                            },
                            "pricing": {
                                "deposit_required": True,
                                "deposit_amount": 25.00,
                                "currency": "USD"
                            },
                            "availability": "available"
                        }
                    ]
                },
                "restaurant_001": {
                    "business_id": "restaurant_001", 
                    "business_name": "Red Canyon Brewing",
                    "services": [
                        {
                            "service_id": "table_reservation",
                            "name": "Table Reservation",
                            "description": "Reserve a table for dining",
                            "parameters": {
                                "date": "date",
                                "time": "time",
                                "party_size": "integer",
                                "special_requests": "string"
                            },
                            "pricing": {
                                "deposit_required": True,
                                "deposit_amount": 15.00,
                                "currency": "USD"
                            },
                            "availability": "available"
                        }
                    ]
                }
            }
            
            if business_id not in business_services:
                raise ValueError(f"Business not found: {business_id}")
            
            return business_services[business_id]
            
        except Exception as e:
            return {
                "error": f"Failed to get business services: {str(e)}",
                "business_id": business_id
            }
    
    async def execute_service(
        self,
        business_id: str,
        service_id: str,
        parameters: Dict[str, Any],
        customer_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a service for any business on the platform.
        Handles booking, payment, and confirmation.
        """
        try:
            # Generate a mock confirmation ID
            import uuid
            confirmation_id = str(uuid.uuid4())[:8].upper()
            
            # Mock execution result
            result = {
                "success": True,
                "confirmation_id": f"BAIS-{confirmation_id}",
                "status": "confirmed",
                "details": {
                    "business_id": business_id,
                    "service_id": service_id,
                    "customer": customer_info,
                    "parameters": parameters,
                    "executed_at": "2025-01-27T12:00:00Z"
                },
                "confirmation_message": f"Your {service_id} has been confirmed! Confirmation ID: BAIS-{confirmation_id}",
                "receipt_url": f"https://api.baintegrate.com/receipts/BAIS-{confirmation_id}",
                "contact_info": {
                    "business_phone": "+1-555-0123",
                    "business_email": "support@business.com"
                }
            }
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Service execution failed: {str(e)}",
                "business_id": business_id,
                "service_id": service_id
            }
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat()


# ============================================================================
# BAIS Platform Registration (One-time setup)
# ============================================================================

class BAISPlatformRegistration:
    """
    BAIS platform registers ONCE with each LLM provider.
    After this, ALL businesses are automatically accessible.
    """
    
    async def register_with_all_providers(self):
        """
        One-time registration of BAIS with Claude, ChatGPT, and Gemini.
        This is done by BAIS platform admins, NOT by individual businesses.
        """
        tools = BAISUniversalTool.get_tool_definitions()
        
        results = {
            "claude": await self._register_with_claude(tools["claude"]),
            "chatgpt": await self._register_with_chatgpt(tools["chatgpt"]),
            "gemini": await self._register_with_gemini(tools["gemini"])
        }
        
        return results
    
    async def _register_with_claude(self, tools: List[Dict]) -> Dict:
        """Register BAIS tools with Anthropic/Claude"""
        # This would use Anthropic's developer console or API
        # to register BAIS as a custom tool provider
        return {
            "status": "registered",
            "tool_count": len(tools),
            "webhook_url": "https://api.baintegrate.com/api/v1/llm-webhooks/claude/tool-use"
        }
    
    async def _register_with_chatgpt(self, tools: List[Dict]) -> Dict:
        """Register BAIS functions with OpenAI/ChatGPT"""
        # This would use OpenAI's GPT Actions or Plugin API
        return {
            "status": "registered",
            "function_count": len(tools),
            "webhook_url": "https://api.baintegrate.com/api/v1/llm-webhooks/chatgpt/function-call"
        }
    
    async def _register_with_gemini(self, tools: List[Dict]) -> Dict:
        """Register BAIS functions with Google/Gemini"""
        # This would use Google's Function Calling API
        return {
            "status": "registered",
            "function_count": len(tools),
            "webhook_url": "https://api.baintegrate.com/api/v1/llm-webhooks/gemini/function-call"
        }
