"""
Shared in-memory storage for BAIS businesses
This ensures BUSINESS_STORE is accessible across all modules
"""
from typing import Dict, Any

# Global in-memory storage for businesses
# This is shared across all BAIS modules (routes_simple, universal_tools, etc.)
BUSINESS_STORE: Dict[str, Dict[str, Any]] = {}

def get_business_store() -> Dict[str, Dict[str, Any]]:
    """Get the shared business store"""
    return BUSINESS_STORE

def register_business(business_id: str, business_data: Dict[str, Any]) -> None:
    """Register a business in the shared store"""
    BUSINESS_STORE[business_id] = business_data

def get_business(business_id: str) -> Dict[str, Any]:
    """Get a business from the shared store"""
    return BUSINESS_STORE.get(business_id)

def list_businesses() -> Dict[str, Dict[str, Any]]:
    """List all businesses in the shared store"""
    return BUSINESS_STORE.copy()

def clear_business_store() -> None:
    """Clear all businesses (for testing)"""
    BUSINESS_STORE.clear()

def count_businesses() -> int:
    """Get the count of registered businesses"""
    return len(BUSINESS_STORE)

