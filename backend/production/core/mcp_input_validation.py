"""
MCP Input Validation - Clean Code Implementation
Comprehensive input validation for all MCP endpoints following security best practices
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date, time
from dataclasses import dataclass
from enum import Enum
import re
import json
from pydantic import BaseModel, Field, validator, root_validator

from .mcp_error_handler import ValidationError


class ServiceType(Enum):
    """Service types for validation"""
    HOSPITALITY = "hospitality"
    RESTAURANT = "restaurant"
    RETAIL = "retail"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"


class PaymentMethod(Enum):
    """Payment methods for validation"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    DIGITAL_WALLET = "digital_wallet"
    BANK_TRANSFER = "bank_transfer"
    CRYPTOCURRENCY = "cryptocurrency"


# Base validation schemas
class BaseMCPSchema(BaseModel):
    """Base schema for MCP requests with common validation"""
    
    class Config:
        extra = "forbid"  # Reject extra fields
        validate_assignment = True  # Validate on assignment
        use_enum_values = True


# Resource validation schemas
class ResourceURIValidation(BaseModel):
    """Validate resource URIs"""
    uri: str = Field(..., min_length=1, max_length=500)
    
    @validator('uri')
    def validate_uri_format(cls, v):
        """Validate URI format"""
        valid_schemes = ['availability', 'service', 'business']
        
        try:
            scheme, path = v.split('://', 1)
            if scheme not in valid_schemes:
                raise ValueError(f"Invalid scheme '{scheme}'. Must be one of: {', '.join(valid_schemes)}")
            
            if not path or len(path) < 1:
                raise ValueError("URI path cannot be empty")
            
            # Validate path format (alphanumeric, hyphens, underscores)
            if not re.match(r'^[a-zA-Z0-9_-]+$', path):
                raise ValueError("URI path can only contain alphanumeric characters, hyphens, and underscores")
            
            return v
        except ValueError as e:
            if "Invalid scheme" in str(e) or "cannot be empty" in str(e) or "can only contain" in str(e):
                raise ValueError(str(e))
            raise ValueError("Invalid URI format")
    
    @validator('uri')
    def validate_uri_length(cls, v):
        """Validate URI length"""
        if len(v) > 500:
            raise ValueError("URI too long (max 500 characters)")
        return v


# Tool validation schemas
class ServiceSearchParameters(BaseModel):
    """Validated search parameters for service discovery"""
    location: Optional[str] = Field(None, max_length=100, description="Location filter")
    service_type: Optional[ServiceType] = Field(None, description="Type of service")
    date_range: Optional[Dict[str, date]] = Field(None, description="Date range for availability")
    price_range: Optional[Dict[str, float]] = Field(None, description="Price range filter")
    capacity: Optional[int] = Field(None, ge=1, le=100, description="Required capacity")
    features: Optional[List[str]] = Field(None, max_items=10, description="Required features")
    
    @validator('location')
    def validate_location(cls, v):
        """Validate location format"""
        if v is not None:
            # Remove extra whitespace
            v = v.strip()
            if len(v) == 0:
                raise ValueError("Location cannot be empty")
            
            # Check for valid characters (letters, numbers, spaces, commas, hyphens)
            if not re.match(r'^[a-zA-Z0-9\s,.-]+$', v):
                raise ValueError("Location contains invalid characters")
        
        return v
    
    @validator('date_range')
    def validate_date_range(cls, v):
        """Validate date range"""
        if v is not None:
            if 'start_date' not in v or 'end_date' not in v:
                raise ValueError("Date range must include start_date and end_date")
            
            start_date = v['start_date']
            end_date = v['end_date']
            
            if start_date >= end_date:
                raise ValueError("End date must be after start date")
            
            # Check date is not too far in the past or future
            today = date.today()
            if start_date < today:
                raise ValueError("Start date cannot be in the past")
            
            if end_date > date(today.year + 1, today.month, today.day):
                raise ValueError("End date cannot be more than 1 year in the future")
        
        return v
    
    @validator('price_range')
    def validate_price_range(cls, v):
        """Validate price range"""
        if v is not None:
            if 'min_price' not in v or 'max_price' not in v:
                raise ValueError("Price range must include min_price and max_price")
            
            min_price = v['min_price']
            max_price = v['max_price']
            
            if min_price < 0:
                raise ValueError("Minimum price cannot be negative")
            
            if max_price <= min_price:
                raise ValueError("Maximum price must be greater than minimum price")
            
            if max_price > 1000000:  # $1M limit
                raise ValueError("Maximum price cannot exceed $1,000,000")
        
        return v
    
    @validator('features')
    def validate_features(cls, v):
        """Validate features list"""
        if v is not None:
            # Remove duplicates while preserving order
            seen = set()
            unique_features = []
            for feature in v:
                feature = feature.strip().lower()
                if feature and feature not in seen:
                    seen.add(feature)
                    unique_features.append(feature)
            
            # Validate feature names (alphanumeric, spaces, hyphens)
            for feature in unique_features:
                if not re.match(r'^[a-zA-Z0-9\s-]+$', feature):
                    raise ValueError(f"Invalid feature name: '{feature}'")
            
            return unique_features
        
        return v


class BookingParameters(BaseModel):
    """Validated booking parameters"""
    service_id: str = Field(..., min_length=1, max_length=100, description="Service identifier")
    date: date = Field(..., description="Booking date")
    time: Optional[time] = Field(None, description="Booking time")
    duration_hours: Optional[float] = Field(None, ge=0.5, le=24, description="Duration in hours")
    guests: int = Field(..., ge=1, le=50, description="Number of guests")
    special_requests: Optional[str] = Field(None, max_length=500, description="Special requests")
    contact_info: Dict[str, str] = Field(..., description="Contact information")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    
    @validator('service_id')
    def validate_service_id(cls, v):
        """Validate service ID format"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Service ID can only contain alphanumeric characters, hyphens, and underscores")
        return v
    
    @validator('date')
    def validate_booking_date(cls, v):
        """Validate booking date"""
        today = date.today()
        
        if v < today:
            raise ValueError("Booking date cannot be in the past")
        
        if v > date(today.year + 1, today.month, today.day):
            raise ValueError("Booking date cannot be more than 1 year in the future")
        
        return v
    
    @validator('special_requests')
    def validate_special_requests(cls, v):
        """Validate special requests"""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            
            # Check for potentially malicious content
            suspicious_patterns = [
                r'<script[^>]*>',
                r'javascript:',
                r'on\w+\s*=',
                r'data:',
                r'vbscript:'
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, v, re.IGNORECASE):
                    raise ValueError("Special requests contain potentially unsafe content")
        
        return v
    
    @validator('contact_info')
    def validate_contact_info(cls, v):
        """Validate contact information"""
        required_fields = ['email', 'phone']
        
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Contact information missing required field: {field}")
        
        # Validate email format
        email = v['email']
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")
        
        # Validate phone format (basic international format)
        phone = v['phone']
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        if not re.match(phone_pattern, phone):
            raise ValueError("Invalid phone number format")
        
        return v


class PaymentParameters(BaseModel):
    """Validated payment parameters"""
    amount: float = Field(..., gt=0, le=1000000, description="Payment amount")
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    payment_details: Dict[str, Any] = Field(..., description="Payment method specific details")
    description: Optional[str] = Field(None, max_length=200, description="Payment description")
    
    @validator('currency')
    def validate_currency(cls, v):
        """Validate currency code"""
        valid_currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CHF']
        if v.upper() not in valid_currencies:
            raise ValueError(f"Unsupported currency: {v}. Supported currencies: {', '.join(valid_currencies)}")
        return v.upper()
    
    @validator('payment_details')
    def validate_payment_details(cls, v, values):
        """Validate payment method specific details"""
        payment_method = values.get('payment_method')
        
        if payment_method == PaymentMethod.CREDIT_CARD:
            required_fields = ['card_number', 'expiry_date', 'cvv', 'cardholder_name']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Credit card payment requires field: {field}")
            
            # Validate card number (basic Luhn algorithm check)
            card_number = v['card_number'].replace(' ', '').replace('-', '')
            if not cls._is_valid_card_number(card_number):
                raise ValueError("Invalid credit card number")
            
            # Validate expiry date format
            expiry = v['expiry_date']
            if not re.match(r'^\d{2}/\d{2}$', expiry):
                raise ValueError("Expiry date must be in MM/YY format")
            
            # Validate CVV
            cvv = v['cvv']
            if not re.match(r'^\d{3,4}$', cvv):
                raise ValueError("CVV must be 3 or 4 digits")
            
            # Validate cardholder name
            cardholder_name = v['cardholder_name']
            if len(cardholder_name.strip()) < 2:
                raise ValueError("Cardholder name must be at least 2 characters")
        
        elif payment_method == PaymentMethod.DIGITAL_WALLET:
            required_fields = ['wallet_type', 'wallet_id']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Digital wallet payment requires field: {field}")
            
            # Validate wallet type
            valid_wallets = ['paypal', 'apple_pay', 'google_pay', 'stripe']
            if v['wallet_type'].lower() not in valid_wallets:
                raise ValueError(f"Unsupported wallet type: {v['wallet_type']}")
        
        return v
    
    @staticmethod
    def _is_valid_card_number(card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm"""
        if not card_number.isdigit():
            return False
        
        # Luhn algorithm
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10
        
        return luhn_checksum(card_number) == 0


# Prompt validation schemas
class PromptParameters(BaseModel):
    """Validated prompt parameters"""
    prompt_type: str = Field(..., min_length=1, max_length=50, description="Type of prompt")
    context: Optional[Dict[str, Any]] = Field(None, description="Prompt context")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="Maximum tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature setting")
    
    @validator('prompt_type')
    def validate_prompt_type(cls, v):
        """Validate prompt type"""
        valid_types = ['question', 'summary', 'translation', 'generation', 'analysis']
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid prompt type: {v}. Valid types: {', '.join(valid_types)}")
        return v.lower()
    
    @validator('context')
    def validate_context(cls, v):
        """Validate prompt context"""
        if v is not None:
            # Check context size
            context_str = json.dumps(v)
            if len(context_str) > 10000:  # 10KB limit
                raise ValueError("Prompt context too large (max 10KB)")
            
            # Check for potentially malicious content
            suspicious_patterns = [
                r'<script[^>]*>',
                r'javascript:',
                r'on\w+\s*=',
                r'eval\s*\(',
                r'function\s*\('
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, context_str, re.IGNORECASE):
                    raise ValueError("Prompt context contains potentially unsafe content")
        
        return v


# MCP request validation schemas
class MCPInitializeRequest(BaseMCPSchema):
    """Validated MCP initialization request"""
    protocolVersion: str = Field(..., description="MCP protocol version")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Client capabilities")
    clientInfo: Dict[str, str] = Field(..., description="Client information")
    
    @validator('protocolVersion')
    def validate_protocol_version(cls, v):
        """Validate protocol version"""
        supported_versions = ["2025-06-18", "2024-11-05"]
        if v not in supported_versions:
            raise ValueError(f"Unsupported protocol version: {v}. Supported versions: {', '.join(supported_versions)}")
        return v
    
    @validator('clientInfo')
    def validate_client_info(cls, v):
        """Validate client information"""
        required_fields = ['name', 'version']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Client info missing required field: {field}")
        
        # Validate name format
        name = v['name']
        if not re.match(r'^[a-zA-Z0-9\s-]+$', name):
            raise ValueError("Client name contains invalid characters")
        
        # Validate version format
        version = v['version']
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            raise ValueError("Version must be in semantic version format (e.g., 1.0.0)")
        
        return v


class MCPCallToolRequest(BaseMCPSchema):
    """Validated MCP tool call request"""
    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    
    @validator('name')
    def validate_tool_name(cls, v):
        """Validate tool name format"""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Tool name must start with letter or underscore and contain only alphanumeric characters and underscores")
        return v
    
    @validator('arguments')
    def validate_arguments_size(cls, v):
        """Validate arguments size"""
        args_str = json.dumps(v)
        if len(args_str) > 50000:  # 50KB limit
            raise ValueError("Tool arguments too large (max 50KB)")
        return v


class MCPReadResourceRequest(BaseMCPSchema):
    """Validated MCP resource read request"""
    uri: str = Field(..., min_length=1, max_length=500, description="Resource URI")
    
    @validator('uri')
    def validate_uri(cls, v):
        """Validate resource URI using ResourceURIValidation"""
        validator = ResourceURIValidation(uri=v)
        return validator.uri


# Validation service
class MCPInputValidator:
    """Service for validating MCP inputs following Clean Code principles"""
    
    @staticmethod
    def validate_initialize_request(data: Dict[str, Any]) -> MCPInitializeRequest:
        """Validate MCP initialization request"""
        try:
            return MCPInitializeRequest(**data)
        except Exception as e:
            raise ValidationError(f"Invalid initialization request: {str(e)}")
    
    @staticmethod
    def validate_tool_request(data: Dict[str, Any]) -> MCPCallToolRequest:
        """Validate MCP tool request"""
        try:
            return MCPCallToolRequest(**data)
        except Exception as e:
            raise ValidationError(f"Invalid tool request: {str(e)}")
    
    @staticmethod
    def validate_resource_request(data: Dict[str, Any]) -> MCPReadResourceRequest:
        """Validate MCP resource request"""
        try:
            return MCPReadResourceRequest(**data)
        except Exception as e:
            raise ValidationError(f"Invalid resource request: {str(e)}")
    
    @staticmethod
    def validate_service_search_params(data: Dict[str, Any]) -> ServiceSearchParameters:
        """Validate service search parameters"""
        try:
            return ServiceSearchParameters(**data)
        except Exception as e:
            raise ValidationError(f"Invalid search parameters: {str(e)}")
    
    @staticmethod
    def validate_booking_params(data: Dict[str, Any]) -> BookingParameters:
        """Validate booking parameters"""
        try:
            return BookingParameters(**data)
        except Exception as e:
            raise ValidationError(f"Invalid booking parameters: {str(e)}")
    
    @staticmethod
    def validate_payment_params(data: Dict[str, Any]) -> PaymentParameters:
        """Validate payment parameters"""
        try:
            return PaymentParameters(**data)
        except Exception as e:
            raise ValidationError(f"Invalid payment parameters: {str(e)}")
    
    @staticmethod
    def validate_prompt_params(data: Dict[str, Any]) -> PromptParameters:
        """Validate prompt parameters"""
        try:
            return PromptParameters(**data)
        except Exception as e:
            raise ValidationError(f"Invalid prompt parameters: {str(e)}")
    
    @staticmethod
    def sanitize_string_input(input_str: str, max_length: int = 1000) -> str:
        """Sanitize string input for security"""
        if not isinstance(input_str, str):
            raise ValidationError("Input must be a string")
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in input_str if ord(char) >= 32)
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_json_input(json_str: str, max_size_kb: int = 100) -> Dict[str, Any]:
        """Validate and parse JSON input"""
        try:
            # Check size limit
            if len(json_str.encode('utf-8')) > max_size_kb * 1024:
                raise ValidationError(f"JSON input too large (max {max_size_kb}KB)")
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Ensure it's a dictionary
            if not isinstance(data, dict):
                raise ValidationError("JSON input must be an object")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValidationError(f"JSON validation error: {str(e)}")


# Global validator instance
_input_validator: Optional[MCPInputValidator] = None


def get_input_validator() -> MCPInputValidator:
    """Get the global input validator instance"""
    global _input_validator
    if _input_validator is None:
        _input_validator = MCPInputValidator()
    return _input_validator
