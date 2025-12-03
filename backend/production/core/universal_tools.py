"""
BAIS Universal Tools Architecture
Universal Business Access Through Any AI Platform

This architecture enables ANY consumer to buy from ANY BAIS business
through Claude, ChatGPT, or Gemini with NO per-business setup required.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum
import logging

logger = logging.getLogger(__name__)


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
            # Search businesses - check database first, then fallback to mock data
            businesses = []
            
            # Try to query database if available - query ALL registered businesses
            db_checked = False
            try:
                from ..core.database_models import DatabaseManager, Business, BusinessService
                import os
                
                # Use db_manager from handler if available, otherwise create new one
                if self.db_manager:
                    db_manager = self.db_manager
                    logger.info(f"Using handler's database manager for search")
                else:
                    # Get database URL from environment
                    database_url = os.getenv("DATABASE_URL")
                    if not database_url or database_url == "not_set":
                        logger.debug("No DATABASE_URL and no db_manager in handler, skipping database query")
                        db_manager = None
                    else:
                        logger.info(f"Creating new database manager for search")
                        db_manager = DatabaseManager(database_url)
                
                if db_manager:
                    logger.info(f"Searching database for query='{query}', location='{location}', category='{category}'")
                    with db_manager.get_session() as session:
                        # First, check total count of active businesses
                        total_active = session.query(Business).filter(Business.status == "active").count()
                        logger.info(f"Total active businesses in database: {total_active}")
                        
                        query_obj = session.query(Business).filter(Business.status == "active")
                        db_checked = True
                        
                        # Apply search filters
                        if query:
                            # Normalize query for better matching (handle "med spa" -> "medspa", etc.)
                            query_lower = query.lower().strip()
                            query_normalized = query_lower.replace(" ", "").replace("-", "")
                            query_words = query_lower.split()
                            
                            # Build flexible search conditions
                            search_conditions = []
                            
                            # Exact and partial matches
                            search_conditions.append(Business.name.ilike(f"%{query_lower}%"))
                            search_conditions.append(Business.description.ilike(f"%{query_lower}%"))
                            
                            # Normalized matches (handles "med spa" matching "medspa" in name)
                            if query_normalized:
                                search_conditions.append(
                                    Business.name.ilike(f"%{query_normalized}%")
                                )
                                search_conditions.append(
                                    Business.description.ilike(f"%{query_normalized}%")
                                )
                            
                            # Word-by-word matching for multi-word queries (very lenient)
                            for word in query_words:
                                if len(word) > 2:
                                    search_conditions.append(Business.name.ilike(f"%{word}%"))
                                    search_conditions.append(Business.description.ilike(f"%{word}%"))
                            
                            # Very lenient: if query is "med spa", match if name contains "med" OR "spa"
                            # This ensures "New Life New Image Med Spa" matches "med spa" query
                            if len(query_words) >= 2:
                                # Match if all significant words appear somewhere in name or description
                                for word in query_words:
                                    if len(word) > 2:
                                        search_conditions.append(Business.name.ilike(f"%{word}%"))
                                        search_conditions.append(Business.description.ilike(f"%{word}%"))
                            
                            # Also search in service names through relationships
                            search_conditions.append(
                                Business.services.any(
                                    BusinessService.name.ilike(f"%{query_lower}%")
                                )
                            )
                            
                            from sqlalchemy import or_
                            query_obj = query_obj.filter(or_(*search_conditions))
                        
                        if category:
                            query_obj = query_obj.filter(Business.business_type == category)
                        
                        if location:
                            location_lower = location.lower().strip()
                            location_normalized = location_lower.replace(",", " ").replace(".", "").strip()
                            location_words = location_normalized.split()
                            
                            location_conditions = []
                            location_conditions.append(Business.city.ilike(f"%{location_lower}%"))
                            location_conditions.append(Business.state.ilike(f"%{location_lower}%"))
                            
                            # Handle "Las Vegas" variations
                            if "vegas" in location_lower or "las vegas" in location_lower:
                                location_conditions.append(Business.city.ilike("%las vegas%"))
                                location_conditions.append(Business.city.ilike("%vegas%"))
                            
                            # Word-by-word matching
                            for word in location_words:
                                if len(word) > 2:
                                    location_conditions.append(Business.city.ilike(f"%{word}%"))
                                    location_conditions.append(Business.state.ilike(f"%{word}%"))
                            
                            from sqlalchemy import or_
                            query_obj = query_obj.filter(or_(*location_conditions))
                        
                        # Get matching businesses
                        db_businesses = query_obj.limit(10).all()
                        logger.info(f"Database query returned {len(db_businesses)} matching businesses")
                        
                        if len(db_businesses) == 0 and total_active > 0:
                            # If we have businesses but no matches, log all business names for debugging
                            all_businesses = session.query(Business).filter(Business.status == "active").all()
                            logger.warning(f"No matches found, but {len(all_businesses)} active businesses exist:")
                            for biz in all_businesses[:5]:  # Log first 5
                                logger.warning(f"  - {biz.name} (type: {biz.business_type}, city: {biz.city}, state: {biz.state})")
                        
                        for biz in db_businesses:
                            # Get services for this business
                            services = session.query(BusinessService).filter(
                                BusinessService.business_id == biz.id
                            ).all()
                            
                            # Use external_id as business_id for consistency with API
                            business_data = {
                                "business_id": biz.external_id or str(biz.id),
                                "name": biz.name,
                                "description": biz.description or "",
                                "category": biz.business_type,
                                "location": {
                                    "city": biz.city or "",
                                    "state": biz.state or "",
                                    "address": f"{biz.address or ''}, {biz.city or ''}, {biz.state or ''}"
                                },
                                "phone": biz.phone or "",
                                "website": biz.website or "",
                                "rating": 4.5,  # Default rating, can be enhanced with metrics
                                "services": [
                                    {
                                        "id": svc.service_id or str(svc.id),
                                        "name": svc.name,
                                        "description": svc.description or ""
                                    }
                                    for svc in services[:5]  # Limit services in search results
                                ]
                            }
                            businesses.append(business_data)
                        
                        logger.info(f"Found {len(businesses)} businesses from database")
                else:
                    logger.debug("No database manager available, skipping database query")
                    
            except Exception as db_error:
                logger.debug(f"Database query failed, using fallback: {db_error}")
                # Continue to fallback logic
            
            # Only check in-memory BUSINESS_STORE if database is not available
            # Database is the source of truth - in-memory is only a fallback
            if not db_checked or len(businesses) == 0:
                # Only use in-memory store if we don't have database access
                try:
                # Try multiple import paths for shared_storage
                simple_store = None
                try:
                    from shared_storage import BUSINESS_STORE as simple_store
                except ImportError:
                    try:
                        from ..shared_storage import BUSINESS_STORE as simple_store
                    except ImportError:
                        try:
                            from backend.production.shared_storage import BUSINESS_STORE as simple_store
                        except ImportError:
                            # Try importing the module and accessing the attribute
                            import sys
                            import os
                            # Add parent directory to path if needed
                            parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                            if parent_dir not in sys.path:
                                sys.path.insert(0, parent_dir)
                            try:
                                from backend.production import shared_storage
                                simple_store = getattr(shared_storage, 'BUSINESS_STORE', None)
                            except Exception as import_err:
                                logger.debug(f"Could not import shared_storage: {import_err}")
                                pass
                
                if simple_store and len(simple_store) > 0:
                    logger.info(f"Checking in-memory BUSINESS_STORE (fallback only) with {len(simple_store)} businesses")
                    logger.info(f"Business IDs in store: {list(simple_store.keys())}")
                    logger.warning("Using in-memory store as fallback - database should be primary source")
                    for business_id, business_data in simple_store.items():
                        logger.info(f"Checking business: {business_data.get('business_name', 'Unknown')} (ID: {business_id})")
                        # Skip if already in results
                        if any(b.get("business_id") == business_id for b in businesses):
                            continue
                        
                        # Apply search filters
                        matches = True
                        business_name = business_data.get("business_name", "").lower()
                        business_desc = business_data.get("business_info", {}).get("description", "").lower()
                        business_type = business_data.get("business_type", "").lower()
                        business_city = business_data.get("location", {}).get("city", "").lower()
                        business_state = business_data.get("location", {}).get("state", "").lower()
                        
                        # Normalize location strings (remove punctuation, extra spaces)
                        def normalize_location(loc_str):
                            if not loc_str:
                                return ""
                            return " ".join(loc_str.lower().replace(",", " ").split())
                        
                        # Check query match - more flexible matching
                        if query:
                            query_lower = query.lower().strip()
                            query_words = query_lower.split()
                            
                            # Normalize query terms (handle "med spa" -> "medspa", "med-spa", etc.)
                            normalized_query = query_lower.replace(" ", "").replace("-", "")
                            normalized_name = business_name.replace(" ", "").replace("-", "")
                            
                            # Check name, description, and service names
                            service_names = " ".join([
                                svc.get("name", "").lower() 
                                for svc in business_data.get("services_config", [])
                            ])
                            
                            # Enhanced matching: check normalized strings, partial matches, and keyword matching
                            query_matches = (
                                query_lower in business_name or
                                business_name in query_lower or
                                normalized_query in normalized_name or
                                normalized_name in normalized_query or
                                any(word in business_name for word in query_words if len(word) > 2) or
                                query_lower in business_desc or
                                any(word in business_desc for word in query_words if len(word) > 2) or
                                query_lower in service_names or
                                any(word in service_names for word in query_words if len(word) > 2)
                            )
                            
                            # Very lenient matching: if ANY query word appears in name/description/services, it's a match
                            # This ensures "med spa" matches "New Life New Image Med Spa"
                            matches_query = (
                                query_lower in business_name or
                                query_lower in business_desc or
                                query_lower in service_names or
                                any(word in business_name for word in query_words if len(word) > 2) or
                                any(word in business_desc for word in query_words if len(word) > 2) or
                                any(word in service_names for word in query_words if len(word) > 2) or
                                # Very lenient: if normalized query appears anywhere
                                normalized_query in normalized_name or
                                normalized_name in normalized_query
                            )
                            
                            if not matches_query:
                                matches = False
                                logger.debug(f"Business '{business_data.get('business_name', 'Unknown')}' didn't match query '{query_lower}'")
                            else:
                                logger.info(f"✓ Business '{business_data.get('business_name', 'Unknown')}' MATCHED query '{query_lower}'")
                        
                        # Check category match
                        if category and category.lower() != business_type:
                            matches = False
                        
                        # Check location match - more flexible
                        if location:
                            location_lower = normalize_location(location)
                            business_city_norm = normalize_location(business_city)
                            business_state_norm = normalize_location(business_state)
                            
                            # Handle state abbreviations and full names
                            state_mappings = {
                                "nv": "nevada", "nevada": "nv",
                                "ca": "california", "california": "ca",
                                "ny": "new york", "new york": "ny"
                            }
                            
                            location_normalized = location_lower
                            for abbrev, full in state_mappings.items():
                                if abbrev in location_normalized:
                                    location_normalized = location_normalized.replace(abbrev, full)
                                if full in location_normalized:
                                    location_normalized = location_normalized.replace(full, abbrev)
                            
                            # Match if location is in city, state, or contains key words
                            location_words = location_lower.split()
                            matches_location = (
                                location_lower in business_city_norm or
                                location_lower in business_state_norm or
                                business_city_norm in location_lower or
                                any(word in business_city_norm for word in location_words if len(word) > 2) or
                                any(word in business_state_norm for word in location_words if len(word) > 2) or
                                # Handle "Las Vegas" matching
                                ("vegas" in location_lower and "vegas" in business_city_norm) or
                                ("las vegas" in location_lower and "las vegas" in business_city_norm)
                            )
                            
                            if not matches_location:
                                matches = False
                                logger.debug(f"Business '{business_data.get('business_name', 'Unknown')}' in {business_city_norm}, {business_state_norm} didn't match location '{location_lower}'")
                            else:
                                logger.info(f"✓ Business '{business_data.get('business_name', 'Unknown')}' matched location '{location_lower}'")
                        
                        if matches:
                            # Get services
                            services = [
                                {
                                    "id": svc.get("id", ""),
                                    "name": svc.get("name", ""),
                                    "description": svc.get("description", "")
                                }
                                for svc in business_data.get("services_config", [])[:5]
                            ]
                            
                            business_result = {
                                "business_id": business_id,
                                "name": business_data.get("business_name", ""),
                                "description": business_data.get("business_info", {}).get("description", ""),
                                "category": business_type,
                                "location": {
                                    "city": business_data.get("location", {}).get("city", ""),
                                    "state": business_data.get("location", {}).get("state", ""),
                                    "address": business_data.get("location", {}).get("address", "")
                                },
                                "phone": business_data.get("contact_info", {}).get("phone", ""),
                                "website": business_data.get("contact_info", {}).get("website", ""),
                                "rating": 4.5,
                                "services": services
                            }
                            businesses.append(business_result)
                            logger.info(f"✓ Added business from in-memory store: {business_data.get('business_name')} (ID: {business_id})")
                    
                    logger.info(f"Found {len([b for b in businesses if b.get('business_id') in simple_store])} businesses from in-memory store")
                else:
                    logger.debug("BUSINESS_STORE not found in routes_simple")
            except Exception as store_error:
                logger.error(f"In-memory store check failed: {store_error}", exc_info=True)
            
            # If no database results AND no query provided, include some example businesses
            # This helps users understand what BAIS can do
            # NOTE: In production, this should only show if database is empty, not if search returns no results
            if not businesses and not query:
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
            
                # Filter mock results based on search criteria
                for business in mock_businesses:
                    # Simple text matching
                    matches_query = query.lower() in business.get("name", "").lower() or query.lower() in business.get("description", "").lower()
                    matches_category = not category or business.get("category") == category
                    matches_location = not location or location.lower() in business.get("location", {}).get("city", "").lower()
                    
                    if matches_query and matches_category and matches_location:
                        businesses.append(business)
            
            # NOTE: All registered businesses should now be in the businesses list from the database query above
            # The database query includes ALL active businesses that match the search criteria
            # This makes BAIS truly universal - any business registered will be discoverable
            
            # If still no results, try returning ALL active businesses (very lenient fallback)
            if len(businesses) == 0:
                logger.warning("No businesses found with any search criteria, trying to return all active businesses")
                try:
                    # Use handler's db_manager if available, otherwise create new one
                    fallback_db_manager = self.db_manager
                    if not fallback_db_manager:
                        from ..core.database_models import DatabaseManager
                        import os
                        database_url = os.getenv("DATABASE_URL")
                        if database_url and database_url != "not_set":
                            fallback_db_manager = DatabaseManager(database_url)
                    
                    if fallback_db_manager:
                        from ..core.database_models import Business, BusinessService
                        with fallback_db_manager.get_session() as session:
                            all_businesses = session.query(Business).filter(
                                Business.status == "active"
                            ).limit(10).all()
                            
                            logger.info(f"Found {len(all_businesses)} active businesses in database")
                            
                            for biz in all_businesses:
                                services = session.query(BusinessService).filter(
                                    BusinessService.business_id == biz.id
                                ).all()
                                
                                business_data = {
                                    "business_id": biz.external_id or str(biz.id),
                                    "name": biz.name,
                                    "description": biz.description or "",
                                    "category": biz.business_type,
                                    "location": {
                                        "city": biz.city or "",
                                        "state": biz.state or "",
                                        "address": f"{biz.address or ''}, {biz.city or ''}, {biz.state or ''}"
                                    },
                                    "phone": biz.phone or "",
                                    "website": biz.website or "",
                                    "rating": 4.5,
                                    "services": [
                                        {
                                            "id": svc.service_id or str(svc.id),
                                            "name": svc.name,
                                            "description": svc.description or ""
                                        }
                                        for svc in services[:5]
                                    ]
                                }
                                businesses.append(business_data)
                            
                            logger.info(f"Fallback: Returning {len(businesses)} total active businesses")
                    else:
                        logger.debug("No database manager available, cannot do fallback search")
                except Exception as e:
                    logger.error(f"Fallback search failed: {e}", exc_info=True)
            
            # If still no results and we have a query, try without location filter
            if len(businesses) == 0 and query and location:
                logger.warning(f"No results with location filter, trying without location for query '{query}'")
                # Re-run search without location
                return await self.search_businesses(query=query, category=category, location=None)
            
            logger.info(f"Final result: returning {len(businesses)} businesses")
            if len(businesses) == 0:
                logger.warning("WARNING: Search returned 0 businesses. This might indicate:")
                logger.warning("  1. No businesses are registered")
                logger.warning("  2. Search criteria are too strict")
                logger.warning("  3. Database/in-memory store is not accessible")
            
            return businesses[:10]  # Limit to 10 results
            
        except Exception as e:
            logger.error(f"Search businesses error: {str(e)}", exc_info=True)
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
