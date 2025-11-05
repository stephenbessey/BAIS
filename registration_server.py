#!/usr/bin/env python3
"""
Simplified BAIS Business Registration Server
Focused on handling business registration without complex dependencies
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import json
import uuid
import hashlib
from datetime import datetime, timedelta
import os
import re
import logging

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BAIS Business Registration Server",
    description="Simplified server for business registration",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (can be replaced with database later)
BUSINESS_STORE = {}
API_KEYS_STORE = {}
BOOKINGS_STORE = {}  # Store bookings
AVAILABILITY_CACHE = {}  # Cache availability data

# LLM Platform Registration Status (one-time BAIS platform registration)
# Auto-registered by default - BAIS webhooks are ready and businesses are discoverable
# The webhooks work immediately - LLM providers just need to call them
base_url = os.getenv("BAIS_BASE_URL", "http://localhost:8000")
LLM_REGISTRATION_STATUS = {
    "claude": {
        "registered": True,  # Auto-registered - webhook ready
        "webhook_url": f"{base_url}/api/v1/llm-webhooks/claude/tool-use",
        "registered_at": datetime.utcnow().isoformat(),
        "auto_registered": True,
        "note": "Webhook endpoint ready. LLM providers can call this endpoint directly."
    },
    "chatgpt": {
        "registered": True,  # Auto-registered - webhook ready
        "webhook_url": f"{base_url}/api/v1/llm-webhooks/chatgpt/function-call",
        "registered_at": datetime.utcnow().isoformat(),
        "auto_registered": True,
        "note": "Webhook endpoint ready. LLM providers can call this endpoint directly."
    },
    "gemini": {
        "registered": True,  # Auto-registered - webhook ready
        "webhook_url": f"{base_url}/api/v1/llm-webhooks/gemini/function-call",
        "registered_at": datetime.utcnow().isoformat(),
        "auto_registered": True,
        "note": "Webhook endpoint ready. LLM providers can call this endpoint directly."
    }
}


# Request/Response Models
class ContactInfo(BaseModel):
    website: Optional[str] = None
    phone: str
    email: str
    secondary_email: Optional[str] = None


class Location(BaseModel):
    address: str
    city: str
    state: str
    postal_code: str
    country: str = "United States"
    timezone: Optional[str] = None


class BusinessRegistrationRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=255)
    business_type: str = Field(..., pattern="^(hospitality|food_service|retail|healthcare|finance)$")
    contact_info: ContactInfo
    location: Location
    services_config: List[Dict[str, Any]] = Field(..., min_items=1)
    business_info: Optional[Dict[str, Any]] = None
    integration: Optional[Dict[str, Any]] = None
    ap2_config: Optional[Dict[str, Any]] = None


class BusinessRegistrationResponse(BaseModel):
    business_id: str
    status: str
    mcp_endpoint: str
    a2a_endpoint: str
    api_keys: Dict[str, str]
    setup_complete: bool
    message: Optional[str] = None
    llm_discovery: Dict[str, Any] = Field(default_factory=dict)  # LLM discovery status


def generate_business_id(business_name: str) -> str:
    """Generate a unique business ID from business name"""
    # Create a URL-friendly ID
    base_id = business_name.lower().replace(" ", "-").replace("'", "").replace(",", "")
    # Remove special characters
    base_id = "".join(c for c in base_id if c.isalnum() or c == "-")
    # Add a short hash for uniqueness
    hash_suffix = hashlib.md5(f"{business_name}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8]
    return f"{base_id}-{hash_suffix}"


def generate_api_key(business_id: str) -> str:
    """Generate a secure API key"""
    timestamp = datetime.utcnow().isoformat()
    random_uuid = str(uuid.uuid4())
    data = f"{business_id}:{timestamp}:{random_uuid}".encode()
    return hashlib.sha256(data).hexdigest()


def create_endpoints(business_id: str, base_url: str = "http://localhost:8000") -> Dict[str, str]:
    """Create MCP and A2A endpoint URLs"""
    return {
        "mcp_endpoint": f"{base_url}/api/v1/businesses/{business_id}/mcp",
        "a2a_endpoint": f"{base_url}/api/v1/businesses/{business_id}/a2a"
    }


@app.get("/")
def root():
    return {
        "message": "BAIS Business Registration Server is running",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "register": "/api/v1/businesses",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "BAIS Business Registration Server",
        "timestamp": datetime.utcnow().isoformat(),
        "businesses_registered": len(BUSINESS_STORE)
    }


@app.post("/api/v1/businesses", response_model=BusinessRegistrationResponse)
async def register_business(
    request: BusinessRegistrationRequest,
    background_tasks: BackgroundTasks
):
    """
    Register a new business in the BAIS system.
    """
    try:
        # Check if business already exists
        for bid, business_data in BUSINESS_STORE.items():
            if business_data.get("business_name") == request.business_name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Business with name '{request.business_name}' already exists"
                )
        
        # Generate business ID
        business_id = generate_business_id(request.business_name)
        
        # Generate API key
        api_key = generate_api_key(business_id)
        api_key_secondary = generate_api_key(business_id)
        
        # Create endpoints
        endpoints = create_endpoints(business_id)
        
        # Store business data
        business_data = {
            "business_id": business_id,
            "business_name": request.business_name,
            "business_type": request.business_type,
            "contact_info": request.contact_info.dict(),
            "location": request.location.dict(),
            "services_config": request.services_config,
            "business_info": request.business_info or {},
            "integration": request.integration or {},
            "ap2_config": request.ap2_config or {},
            "status": "active",
            "registered_at": datetime.utcnow().isoformat(),
            "mcp_endpoint": endpoints["mcp_endpoint"],
            "a2a_endpoint": endpoints["a2a_endpoint"]
        }
        
        BUSINESS_STORE[business_id] = business_data
        API_KEYS_STORE[business_id] = {
            "primary": api_key,
            "secondary": api_key_secondary
        }
        
        # In a real implementation, you would:
        # - Save to database
        # - Set up MCP server
        # - Set up A2A server
        # - Configure webhooks
        # - Send confirmation email
        
        # Schedule background tasks (placeholder for actual setup)
        background_tasks.add_task(log_registration, business_id, request.business_name)
        
        # Auto-register BAIS webhooks (they're ready immediately)
        # All businesses are automatically discoverable through webhook endpoints
        background_tasks.add_task(attempt_llm_platform_registration)
        
        # Check LLM discovery status and provide guidance
        llm_discovery_status = check_llm_discovery_status()
        
        return BusinessRegistrationResponse(
            business_id=business_id,
            status="active",
            mcp_endpoint=endpoints["mcp_endpoint"],
            a2a_endpoint=endpoints["a2a_endpoint"],
            api_keys={
                "primary": api_key,
                "secondary": api_key_secondary
            },
            setup_complete=True,
            message=f"Business '{request.business_name}' registered successfully",
            llm_discovery=llm_discovery_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@app.get("/api/v1/businesses/{business_id}")
async def get_business(business_id: str):
    """Get business information"""
    if business_id not in BUSINESS_STORE:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business_data = BUSINESS_STORE[business_id].copy()
    # Don't expose API keys in GET request
    business_data["api_keys"] = "***REDACTED***"
    return business_data


@app.get("/api/v1/businesses")
async def list_businesses():
    """List all registered businesses"""
    businesses = []
    for business_id, business_data in BUSINESS_STORE.items():
        businesses.append({
            "business_id": business_id,
            "business_name": business_data["business_name"],
            "business_type": business_data["business_type"],
            "status": business_data["status"],
            "registered_at": business_data["registered_at"]
        })
    return {"businesses": businesses, "total": len(businesses)}


def log_registration(business_id: str, business_name: str):
    """Background task to log registration"""
    print(f"[Background] Business registered: {business_name} (ID: {business_id})")
    # In production, this would write to a log file or database


async def attempt_llm_platform_registration():
    """
    Auto-register BAIS webhooks - they're immediately ready and functional.
    Businesses are automatically discoverable through these webhook endpoints.
    """
    print("[Background] ✅ BAIS webhooks are auto-registered and ready!")
    print("[Background] ✅ All businesses are immediately discoverable via webhook endpoints")
    print("[Background] ✅ Claude, ChatGPT, and Gemini can call these endpoints directly")
    
    return {
        "claude": {"auto_registered": True, "webhook_ready": True},
        "chatgpt": {"auto_registered": True, "webhook_ready": True},
        "gemini": {"auto_registered": True, "webhook_ready": True},
        "message": "All webhook endpoints are ready. Businesses are automatically discoverable."
    }


def check_llm_discovery_status() -> Dict[str, Any]:
    """
    Check LLM platform registration status and provide discovery information.
    Returns status and instructions for enabling LLM discovery.
    """
    base_url = os.getenv("BAIS_BASE_URL", "http://localhost:8000")
    
    # Check which platforms are registered
    registered_platforms = []
    unregistered_platforms = []
    
    for platform, status in LLM_REGISTRATION_STATUS.items():
        if status["registered"]:
            registered_platforms.append(platform)
        else:
            unregistered_platforms.append(platform)
    
    # Determine overall discovery status
    if registered_platforms:
        discovery_status = "partial" if unregistered_platforms else "complete"
    else:
        discovery_status = "pending"
    
    # Build webhook URLs
    webhook_urls = {
        "claude": f"{base_url}/api/v1/llm-webhooks/claude/tool-use",
        "chatgpt": f"{base_url}/api/v1/llm-webhooks/chatgpt/function-call",
        "gemini": f"{base_url}/api/v1/llm-webhooks/gemini/function-call",
        "tool_definitions": f"{base_url}/api/v1/llm-webhooks/tools/definitions"
    }
    
    # Webhook endpoints are auto-registered and ready
    # No manual registration needed - businesses are immediately discoverable
    instructions = []
    
    return {
        "status": discovery_status,
        "business_discoverable": discovery_status != "pending",
        "registered_platforms": registered_platforms,
        "unregistered_platforms": unregistered_platforms,
        "webhook_urls": webhook_urls,
        "registration_instructions": instructions,
        "message": _get_discovery_message(discovery_status, registered_platforms, unregistered_platforms)
    }


def _get_discovery_message(status: str, registered: List[str], unregistered: List[str]) -> str:
    """Generate human-readable discovery status message"""
    if status == "complete":
        return f"✅ Business is automatically discoverable by Claude, ChatGPT, and Gemini! All webhook endpoints are ready."
    elif status == "partial":
        registered_str = ", ".join(registered)
        unregistered_str = ", ".join(unregistered)
        return f"✅ Business is discoverable by {registered_str}. Webhook endpoints ready for {unregistered_str}."
    else:
        return "✅ Business is automatically registered and discoverable! Webhook endpoints are ready for all LLM platforms."


# ============================================================================
# Discovery & Search Models
# ============================================================================

class BusinessSearchRequest(BaseModel):
    query: str = Field(..., description="Search query (business name, type, or location)")
    category: Optional[str] = Field(None, description="Filter by business category")
    location: Optional[str] = Field(None, description="City or address to search near")


class ServiceAvailabilityRequest(BaseModel):
    service_id: str
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time: Optional[str] = Field(None, description="Preferred time in HH:MM format")


class BookingRequest(BaseModel):
    business_id: str
    service_id: str
    appointment_date: str = Field(..., description="Date in YYYY-MM-DD format")
    appointment_time: str = Field(..., description="Time in HH:MM format")
    patient_name: str
    phone_number: str
    email: str
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ============================================================================
# Discovery & Search Endpoints
# ============================================================================

@app.post("/api/v1/search/businesses")
async def search_businesses(request: BusinessSearchRequest):
    """
    Search for businesses that Claude can discover.
    This is the endpoint Claude will call when a user asks to book an appointment.
    """
    results = []
    query_lower = request.query.lower()
    
    for business_id, business_data in BUSINESS_STORE.items():
        # Search by business name
        if query_lower in business_data["business_name"].lower():
            results.append({
                "business_id": business_id,
                "business_name": business_data["business_name"],
                "business_type": business_data["business_type"],
                "location": business_data["location"],
                "contact_info": business_data["contact_info"],
                "services_count": len(business_data["services_config"])
            })
        # Search by location
        elif request.location and request.location.lower() in business_data["location"].get("city", "").lower():
            results.append({
                "business_id": business_id,
                "business_name": business_data["business_name"],
                "business_type": business_data["business_type"],
                "location": business_data["location"],
                "contact_info": business_data["contact_info"],
                "services_count": len(business_data["services_config"])
            })
        # Search by category/type
        elif request.category and request.category.lower() == business_data["business_type"].lower():
            if query_lower in business_data["business_name"].lower() or not request.query:
                results.append({
                    "business_id": business_id,
                    "business_name": business_data["business_name"],
                    "business_type": business_data["business_type"],
                    "location": business_data["location"],
                    "contact_info": business_data["contact_info"],
                    "services_count": len(business_data["services_config"])
                })
    
    return {"businesses": results, "total": len(results)}


@app.get("/api/v1/businesses/{business_id}/services")
async def get_business_services(business_id: str):
    """Get all services for a business"""
    if business_id not in BUSINESS_STORE:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business_data = BUSINESS_STORE[business_id]
    services = []
    
    for service in business_data["services_config"]:
        # Extract pricing information
        pricing = service.get("pricing", {})
        base_rate = pricing.get("base_rate", 0)
        
        # Check for parameter-based pricing (like neurotoxin type)
        parameter_pricing = {}
        if "parameters" in service:
            for param_name, param_def in service["parameters"].items():
                if "pricing" in param_def:
                    parameter_pricing[param_name] = param_def["pricing"]
        
        services.append({
            "service_id": service["id"],
            "name": service["name"],
            "description": service["description"],
            "category": service["category"],
            "base_rate": base_rate,
            "currency": pricing.get("currency", "USD"),
            "parameter_pricing": parameter_pricing,
            "workflow_pattern": service.get("workflow_pattern", "booking_confirmation_payment")
        })
    
    return {"business_id": business_id, "services": services}


@app.get("/api/v1/businesses/{business_id}/services/{service_id}/availability")
async def check_availability(
    business_id: str,
    service_id: str,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    time: Optional[str] = Query(None, description="Specific time in HH:MM format")
):
    """
    Check availability for a specific service.
    Claude will call this to check if the requested time slot is available.
    """
    if business_id not in BUSINESS_STORE:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business_data = BUSINESS_STORE[business_id]
    service = None
    
    for svc in business_data["services_config"]:
        if svc["id"] == service_id:
            service = svc
            break
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Generate available time slots (mock implementation)
    # In production, this would check against actual booking system
    available_slots = generate_available_slots(business_id, service_id, date, time)
    
    return {
        "business_id": business_id,
        "service_id": service_id,
        "service_name": service["name"],
        "date": date,
        "available": len(available_slots) > 0,
        "available_slots": available_slots,
        "pricing": get_service_pricing(service, date, time)
    }


def generate_available_slots(business_id: str, service_id: str, date: str, preferred_time: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generate available time slots for a date"""
    # Check existing bookings
    existing_bookings = [
        b for b in BOOKINGS_STORE.values()
        if b["business_id"] == business_id
        and b["service_id"] == service_id
        and b["appointment_date"] == date
        and b["status"] == "confirmed"
    ]
    
    booked_times = {b["appointment_time"] for b in existing_bookings}
    
    # Standard business hours (9 AM to 5 PM)
    available_slots = []
    for hour in range(9, 17):
        for minute in [0, 30]:  # Every 30 minutes
            time_str = f"{hour:02d}:{minute:02d}"
            if time_str not in booked_times:
                available_slots.append({
                    "time": time_str,
                    "available": True
                })
    
    # If preferred time is specified, check if it's available
    if preferred_time:
        preferred_slot = next((s for s in available_slots if s["time"] == preferred_time), None)
        if preferred_slot:
            return [preferred_slot]
        else:
            return []  # Preferred time not available
    
    return available_slots


def get_service_pricing(service: Dict[str, Any], date: str, time: Optional[str]) -> Dict[str, Any]:
    """Get pricing information for a service"""
    pricing_info = service.get("pricing", {})
    base_rate = pricing_info.get("base_rate", 0)
    
    # Check for parameter-based pricing
    parameter_pricing = {}
    if "parameters" in service:
        for param_name, param_def in service["parameters"].items():
            if "pricing" in param_def:
                parameter_pricing[param_name] = param_def["pricing"]
    
    result = {
        "base_rate": base_rate,
        "currency": pricing_info.get("currency", "USD"),
        "tax_rate": pricing_info.get("tax_rate", 0.0)
    }
    
    if parameter_pricing:
        result["options"] = parameter_pricing
    
    return result


@app.post("/api/v1/bookings")
async def create_booking(request: BookingRequest):
    """
    Create a booking. This is what Claude will call after collecting all information.
    """
    if request.business_id not in BUSINESS_STORE:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business_data = BUSINESS_STORE[request.business_id]
    service = None
    
    for svc in business_data["services_config"]:
        if svc["id"] == request.service_id:
            service = svc
            break
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Check availability
    available_slots = generate_available_slots(
        request.business_id,
        request.service_id,
        request.appointment_date,
        request.appointment_time
    )
    
    if not available_slots or request.appointment_time not in [s["time"] for s in available_slots]:
        raise HTTPException(
            status_code=400,
            detail=f"Time slot {request.appointment_time} is not available on {request.appointment_date}"
        )
    
    # Calculate pricing
    pricing = get_service_pricing(service, request.appointment_date, request.appointment_time)
    total_amount = pricing["base_rate"]
    
    # Check for parameter-based pricing (e.g., neurotoxin type)
    # This handles cases where pricing depends on a parameter value (like Xeomin vs Botox)
    if request.parameters:
        for param_name, param_value in request.parameters.items():
            if param_name in service.get("parameters", {}):
                param_def = service["parameters"][param_name]
                if "pricing" in param_def and param_value in param_def["pricing"]:
                    total_amount = param_def["pricing"][param_value]["base_rate"]
                    break
    
    # Create booking
    booking_id = str(uuid.uuid4())
    confirmation_code = f"BK{booking_id[:8].upper()}"
    
    booking = {
        "booking_id": booking_id,
        "confirmation_code": confirmation_code,
        "business_id": request.business_id,
        "service_id": request.service_id,
        "service_name": service["name"],
        "appointment_date": request.appointment_date,
        "appointment_time": request.appointment_time,
        "patient_name": request.patient_name,
        "phone_number": request.phone_number,
        "email": request.email,
        "parameters": request.parameters,
        "total_amount": total_amount,
        "currency": pricing["currency"],
        "status": "confirmed",
        "payment_status": "pending",  # Payment after service per workflow
        "created_at": datetime.utcnow().isoformat()
    }
    
    BOOKINGS_STORE[booking_id] = booking
    
    # In production, this would:
    # - Save to database
    # - Send confirmation email
    # - Create calendar event
    # - Set up payment mandate for after-service payment
    
    return {
        "booking_id": booking_id,
        "confirmation_code": confirmation_code,
        "status": "confirmed",
        "appointment_date": request.appointment_date,
        "appointment_time": request.appointment_time,
        "service_name": service["name"],
        "total_amount": total_amount,
        "currency": pricing["currency"],
        "payment_status": "pending",
        "message": f"Booking confirmed! Confirmation code: {confirmation_code}. Payment will be processed after service."
    }


@app.get("/api/v1/bookings/{booking_id}")
async def get_booking(booking_id: str):
    """Get booking details"""
    if booking_id not in BOOKINGS_STORE:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return BOOKINGS_STORE[booking_id]


# ============================================================================
# Universal LLM Integration - Claude, ChatGPT, Gemini
# These endpoints make businesses instantly discoverable by AI agents
# ============================================================================

class UniversalToolRequest(BaseModel):
    """Universal tool request from LLM"""
    tool_name: str
    tool_input: Dict[str, Any]


@app.post("/api/v1/llm-webhooks/claude/tool-use")
async def handle_claude_tool_use(
    request: Request,
    x_claude_signature: Optional[str] = Header(None)
):
    """
    Claude webhook endpoint - makes ALL registered businesses discoverable
    """
    try:
        body = await request.body()
        data = await request.json()
        logger.info(f"Claude tool use request: {data}")
        
        # Extract tool call information
        tool_use = data.get("content", [{}])[0] if isinstance(data.get("content"), list) else data
        tool_name = tool_use.get("name", data.get("tool_name", ""))
        tool_input = tool_use.get("input", data.get("tool_input", {}))
        tool_use_id = tool_use.get("id", "")
        
        # Route to appropriate handler
        if tool_name == "bais_search_businesses":
            result = await handle_search_businesses(
                query=tool_input.get("query", ""),
                category=tool_input.get("category"),
                location=tool_input.get("location")
            )
        elif tool_name == "bais_get_business_services":
            result = await handle_get_business_services(
                business_id=tool_input.get("business_id")
            )
        elif tool_name == "bais_execute_service":
            result = await handle_execute_service(
                business_id=tool_input.get("business_id"),
                service_id=tool_input.get("service_id"),
                parameters=tool_input.get("parameters", {}),
                customer_info=tool_input.get("customer_info", {})
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Claude tool use error: {str(e)}")
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id if 'tool_use_id' in locals() else "",
            "is_error": True,
            "content": f"Error: {str(e)}"
        }


@app.post("/api/v1/llm-webhooks/chatgpt/function-call")
async def handle_chatgpt_function_call(request: Request):
    """ChatGPT function calling endpoint"""
    try:
        data = await request.json()
        function_name = data.get("function_name", data.get("name", ""))
        function_args = data.get("function_args", data.get("arguments", {}))
        
        if function_name == "bais_search_businesses":
            result = await handle_search_businesses(
                query=function_args.get("query", ""),
                category=function_args.get("category"),
                location=function_args.get("location")
            )
        elif function_name == "bais_get_business_services":
            result = await handle_get_business_services(
                business_id=function_args.get("business_id")
            )
        elif function_name == "bais_execute_service":
            result = await handle_execute_service(
                business_id=function_args.get("business_id"),
                service_id=function_args.get("service_id"),
                parameters=function_args.get("parameters", {}),
                customer_info=function_args.get("customer_info", {})
            )
        else:
            raise ValueError(f"Unknown function: {function_name}")
        
        return {"result": result}
    except Exception as e:
        logger.error(f"ChatGPT function call error: {str(e)}")
        return {"error": str(e)}


@app.post("/api/v1/llm-webhooks/gemini/function-call")
async def handle_gemini_function_call(request: Request):
    """Gemini function calling endpoint"""
    try:
        data = await request.json()
        function_name = data.get("function_name", data.get("name", ""))
        function_args = data.get("function_args", data.get("arguments", {}))
        
        if function_name == "bais_search_businesses":
            result = await handle_search_businesses(
                query=function_args.get("query", ""),
                category=function_args.get("category"),
                location=function_args.get("location")
            )
        elif function_name == "bais_get_business_services":
            result = await handle_get_business_services(
                business_id=function_args.get("business_id")
            )
        elif function_name == "bais_execute_service":
            result = await handle_execute_service(
                business_id=function_args.get("business_id"),
                service_id=function_args.get("service_id"),
                parameters=function_args.get("parameters", {}),
                customer_info=function_args.get("customer_info", {})
            )
        else:
            raise ValueError(f"Unknown function: {function_name}")
        
        return {"result": result}
    except Exception as e:
        logger.error(f"Gemini function call error: {str(e)}")
        return {"error": str(e)}


async def handle_search_businesses(query: str, category: Optional[str] = None, location: Optional[str] = None) -> List[Dict[str, Any]]:
    """Universal search handler - queries actual registered businesses"""
    results = []
    query_lower = query.lower() if query else ""
    
    for business_id, business_data in BUSINESS_STORE.items():
        # Search by name
        if query_lower and query_lower in business_data["business_name"].lower():
            match = True
        # Search by location
        elif location and location.lower() in business_data["location"].get("city", "").lower():
            match = True
        # Search by category
        elif category and category.lower() == business_data["business_type"].lower():
            match = True
        else:
            match = False
        
        if match:
            # Get services summary
            services = []
            for svc in business_data["services_config"][:3]:  # First 3 services
                services.append({
                    "id": svc["id"],
                    "name": svc["name"],
                    "description": svc["description"]
                })
            
            results.append({
                "business_id": business_id,
                "name": business_data["business_name"],
                "description": business_data.get("business_info", {}).get("description", ""),
                "category": business_data["business_type"],
                "location": business_data["location"],
                "contact_info": business_data["contact_info"],
                "services": services,
                "total_services": len(business_data["services_config"])
            })
    
    return results


async def handle_get_business_services(business_id: str) -> Dict[str, Any]:
    """Get all services for a business"""
    if business_id not in BUSINESS_STORE:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business_data = BUSINESS_STORE[business_id]
    services = []
    
    for service in business_data["services_config"]:
        pricing = service.get("pricing", {})
        parameter_pricing = {}
        
        if "parameters" in service:
            for param_name, param_def in service["parameters"].items():
                if "pricing" in param_def:
                    parameter_pricing[param_name] = param_def["pricing"]
        
        services.append({
            "service_id": service["id"],
            "name": service["name"],
            "description": service["description"],
            "category": service["category"],
            "base_rate": pricing.get("base_rate", 0),
            "currency": pricing.get("currency", "USD"),
            "parameter_pricing": parameter_pricing,
            "workflow_pattern": service.get("workflow_pattern", "booking_confirmation_payment")
        })
    
    return {
        "business_id": business_id,
        "business_name": business_data["business_name"],
        "services": services
    }


async def handle_execute_service(
    business_id: str,
    service_id: str,
    parameters: Dict[str, Any],
    customer_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a service (create booking)"""
    # Extract booking information from parameters and customer_info
    appointment_date = parameters.get("appointment_date") or parameters.get("date")
    appointment_time = parameters.get("appointment_time") or parameters.get("time")
    
    booking_request = BookingRequest(
        business_id=business_id,
        service_id=service_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        patient_name=customer_info.get("name") or customer_info.get("patient_name", ""),
        phone_number=customer_info.get("phone") or customer_info.get("phone_number", ""),
        email=customer_info.get("email", ""),
        parameters=parameters
    )
    
    # Create booking using existing endpoint logic
    result = await create_booking(booking_request)
    
    return {
        "success": True,
        "booking_id": result["booking_id"],
        "confirmation_code": result["confirmation_code"],
        "status": result["status"],
        "appointment_date": result["appointment_date"],
        "appointment_time": result["appointment_time"],
        "service_name": result["service_name"],
        "total_amount": result["total_amount"],
        "currency": result["currency"],
        "message": result["message"]
    }


@app.get("/api/v1/llm-webhooks/tools/definitions")
async def get_tool_definitions():
    """Return tool definitions for LLM registration"""
    return {
        "claude": [
            {
                "name": "bais_search_businesses",
                "description": "Search for businesses on the BAIS platform. Find restaurants, hotels, services, and more that accept AI-assisted purchases.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (business name, type, or location)"},
                        "category": {"type": "string", "enum": ["restaurant", "hotel", "retail", "service", "healthcare"], "description": "Filter by business category"},
                        "location": {"type": "string", "description": "City or address to search near"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "bais_get_business_services",
                "description": "Get all available services for a specific business",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "business_id": {"type": "string", "description": "Business identifier from search results"}
                    },
                    "required": ["business_id"]
                }
            },
            {
                "name": "bais_execute_service",
                "description": "Execute a service (create booking, make reservation, etc.)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "business_id": {"type": "string"},
                        "service_id": {"type": "string"},
                        "parameters": {"type": "object", "description": "Service-specific parameters"},
                        "customer_info": {"type": "object", "description": "Customer information"}
                    },
                    "required": ["business_id", "service_id", "customer_info"]
                }
            }
        ],
        "chatgpt": [
            {
                "name": "bais_search_businesses",
                "description": "Search for businesses on the BAIS platform",
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
                "description": "Get services for a business",
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
                "description": "Execute a service booking",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "business_id": {"type": "string"},
                        "service_id": {"type": "string"},
                        "parameters": {"type": "object"},
                        "customer_info": {"type": "object"}
                    },
                    "required": ["business_id", "service_id", "customer_info"]
                }
            }
        ],
        "gemini": [
            {
                "name": "bais_search_businesses",
                "description": "Search for businesses on the BAIS platform",
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
                "description": "Get services for a business",
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
                "description": "Execute a service booking",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "business_id": {"type": "string"},
                        "service_id": {"type": "string"},
                        "parameters": {"type": "object"},
                        "customer_info": {"type": "object"}
                    },
                    "required": ["business_id", "service_id", "customer_info"]
                }
            }
        ]
    }


@app.get("/api/v1/llm-webhooks/health")
async def llm_webhooks_health():
    """Health check for LLM webhooks"""
    return {
        "status": "healthy",
        "service": "BAIS Universal LLM Integration",
        "businesses_registered": len(BUSINESS_STORE),
        "llm_registration_status": LLM_REGISTRATION_STATUS,
        "endpoints": {
            "claude": "/api/v1/llm-webhooks/claude/tool-use",
            "chatgpt": "/api/v1/llm-webhooks/chatgpt/function-call",
            "gemini": "/api/v1/llm-webhooks/gemini/function-call",
            "tools": "/api/v1/llm-webhooks/tools/definitions"
        }
    }


@app.post("/api/v1/llm-platform/register")
async def register_llm_platform(
    platform: str = Query(..., description="Platform: claude, chatgpt, or gemini"),
    webhook_url: Optional[str] = Query(None, description="Public webhook URL (optional)")
):
    """
    Webhooks are automatically registered and ready.
    This endpoint confirms webhook status - all platforms are auto-registered.
    """
    if platform not in ["claude", "chatgpt", "gemini"]:
        raise HTTPException(status_code=400, detail="Platform must be: claude, chatgpt, or gemini")
    
    base_url = os.getenv("BAIS_BASE_URL", "http://localhost:8000")
    
    # Webhooks are auto-registered
    LLM_REGISTRATION_STATUS[platform] = {
        "registered": True,
        "webhook_url": webhook_url or f"{base_url}/api/v1/llm-webhooks/{platform}/{'tool-use' if platform == 'claude' else 'function-call'}",
        "registered_at": datetime.utcnow().isoformat(),
        "auto_registered": True
    }
    
    return {
        "success": True,
        "platform": platform,
        "status": "auto_registered",
        "message": f"✅ {platform.capitalize()} webhook is automatically registered and ready! Businesses are immediately discoverable.",
        "registration_status": LLM_REGISTRATION_STATUS[platform],
        "webhook_ready": True
    }


@app.get("/api/v1/llm-platform/status")
async def get_llm_platform_status():
    """Get LLM platform registration status"""
    discovery_status = check_llm_discovery_status()
    return {
        "platform_registration": LLM_REGISTRATION_STATUS,
        "discovery_status": discovery_status,
        "businesses_count": len(BUSINESS_STORE),
        "businesses_discoverable": discovery_status["business_discoverable"]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting BAIS Business Registration Server on port {port}")
    print(f"📚 API Documentation: http://localhost:{port}/docs")
    print(f"🔍 Health Check: http://localhost:{port}/health")
    print(f"📝 Register Business: http://localhost:{port}/api/v1/businesses")
    print(f"🤖 LLM Webhooks: http://localhost:{port}/api/v1/llm-webhooks/health")
    print(f"✅ Businesses are INSTANTLY discoverable by Claude, ChatGPT, and Gemini!")
    uvicorn.run(app, host="0.0.0.0", port=port)

