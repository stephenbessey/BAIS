"""
Contact API Router for BAIS Platform
Handles contact form submissions and demo requests
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from ...core.database_models import DatabaseManager
from ...services.business_service import BusinessService

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for contact form
class ContactFormRequest(BaseModel):
    """Contact form submission request"""
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    business_name: Optional[str] = Field(None, max_length=255, description="Business name")
    business_type: Optional[str] = Field(None, max_length=50, description="Business type")
    message: str = Field(..., min_length=10, max_length=1000, description="Message content")
    hear_about: Optional[str] = Field(None, max_length=100, description="How they heard about us")
    demo_requested: bool = Field(default=False, description="Whether they want a demo")

class BusinessRegistrationRequest(BaseModel):
    """Business registration form submission request"""
    business_name: str = Field(..., min_length=1, max_length=255, description="Business name")
    business_type: str = Field(..., min_length=1, max_length=50, description="Business type")
    first_name: str = Field(..., min_length=1, max_length=100, description="Contact first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Contact last name")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    state: str = Field(..., min_length=1, max_length=100, description="State/Province")
    business_description: str = Field(..., min_length=10, max_length=1000, description="Business description")
    hear_about: Optional[str] = Field(None, max_length=100, description="How they heard about us")

class ContactResponse(BaseModel):
    """Contact form response"""
    success: bool
    message: str
    contact_id: Optional[str] = None
    demo_scheduled: bool = False

class BusinessRegistrationResponse(BaseModel):
    """Business registration response"""
    success: bool
    message: str
    business_id: Optional[str] = None
    next_steps: Optional[Dict[str, Any]] = None

# Database models for contact submissions
class ContactSubmission:
    """Contact submission model"""
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def create_contact_submission(self, contact_data: Dict[str, Any]) -> str:
        """Create a new contact submission"""
        try:
            contact_id = str(uuid.uuid4())
            
            # Store in database (you can implement this based on your database setup)
            # For now, we'll log it and return success
            logger.info(f"Contact submission received: {contact_id}")
            logger.info(f"Contact data: {contact_data}")
            
            return contact_id
        except Exception as e:
            logger.error(f"Error creating contact submission: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process contact submission")

    async def create_business_registration(self, business_data: Dict[str, Any]) -> str:
        """Create a new business registration"""
        try:
            business_id = str(uuid.uuid4())
            
            # Store in database
            logger.info(f"Business registration received: {business_id}")
            logger.info(f"Business data: {business_data}")
            
            return business_id
        except Exception as e:
            logger.error(f"Error creating business registration: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process business registration")

# Dependency injection
def get_contact_service(db: DatabaseManager = Depends(lambda: DatabaseManager("sqlite:///bais.db"))) -> ContactSubmission:
    """Get contact service dependency"""
    return ContactSubmission(db)

@router.post("/contact", response_model=ContactResponse, tags=["Contact"])
async def submit_contact_form(
    request: ContactFormRequest,
    contact_service: ContactSubmission = Depends(get_contact_service),
    background_tasks: BackgroundTasks = None
):
    """
    Submit contact form
    
    This endpoint handles general contact form submissions and demo requests.
    """
    try:
        # Convert request to dict
        contact_data = request.dict()
        contact_data['submitted_at'] = datetime.utcnow().isoformat()
        contact_data['type'] = 'contact_form'
        
        # Create contact submission
        contact_id = await contact_service.create_contact_submission(contact_data)
        
        # Schedule demo if requested
        demo_scheduled = False
        if request.demo_requested:
            # Here you would integrate with your demo scheduling system
            demo_scheduled = True
            logger.info(f"Demo requested for contact: {contact_id}")
        
        return ContactResponse(
            success=True,
            message="Thank you for your message! We'll get back to you within 24 hours.",
            contact_id=contact_id,
            demo_scheduled=demo_scheduled
        )
        
    except Exception as e:
        logger.error(f"Contact form submission error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to submit contact form. Please try again later."
        )

@router.post("/business-registration", response_model=BusinessRegistrationResponse, tags=["Business Registration"])
async def submit_business_registration(
    request: BusinessRegistrationRequest,
    contact_service: ContactSubmission = Depends(get_contact_service),
    business_service: BusinessService = Depends(lambda: BusinessService(DatabaseManager("sqlite:///bais.db"), BackgroundTasks()))
):
    """
    Submit business registration form
    
    This endpoint handles business registration for the launch partner program.
    """
    try:
        # Convert request to dict
        business_data = request.dict()
        business_data['submitted_at'] = datetime.utcnow().isoformat()
        business_data['type'] = 'business_registration'
        business_data['status'] = 'pending_review'
        
        # Create business registration
        business_id = await contact_service.create_business_registration(business_data)
        
        # Prepare next steps
        next_steps = {
            "review_timeline": "24-48 hours",
            "contact_method": "email",
            "demo_scheduling": "We'll contact you to schedule a live demo",
            "onboarding": "Complete setup guide will be provided"
        }
        
        return BusinessRegistrationResponse(
            success=True,
            message="Thank you for your interest in joining BAIS Launch Partners! We'll review your application and contact you within 24-48 hours.",
            business_id=business_id,
            next_steps=next_steps
        )
        
    except Exception as e:
        logger.error(f"Business registration submission error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to submit business registration. Please try again later."
        )

@router.get("/contact/{contact_id}", tags=["Contact"])
async def get_contact_status(contact_id: str):
    """
    Get contact submission status
    
    This endpoint allows checking the status of a contact submission.
    """
    try:
        # Here you would implement actual status checking
        return {
            "contact_id": contact_id,
            "status": "received",
            "message": "Your submission has been received and is being processed."
        }
    except Exception as e:
        logger.error(f"Error getting contact status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get contact status")

@router.get("/business-registration/{business_id}", tags=["Business Registration"])
async def get_business_registration_status(business_id: str):
    """
    Get business registration status
    
    This endpoint allows checking the status of a business registration.
    """
    try:
        # Here you would implement actual status checking
        return {
            "business_id": business_id,
            "status": "under_review",
            "message": "Your business registration is under review. We'll contact you soon."
        }
    except Exception as e:
        logger.error(f"Error getting business registration status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get business registration status")
