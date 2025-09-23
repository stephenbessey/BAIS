"""
Business Validator - Clean Code Implementation
Extracts business validation logic from PaymentCoordinator to follow SRP
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..business_query_repository import BusinessQueryRepository
from ..exceptions import ValidationError, NotFoundError


@dataclass
class BusinessValidationResult:
    """Result of business validation"""
    is_valid: bool
    business_id: str
    business_name: str
    ap2_enabled: bool
    supported_payment_methods: list
    validation_errors: list = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


class PaymentBusinessValidator:
    """
    Validates business requirements for payment processing.
    Follows Single Responsibility Principle by focusing only on business validation.
    """
    
    def __init__(self, business_repository: BusinessQueryRepository):
        self._business_repository = business_repository
    
    def validate_business_for_payment(self, business_id: str) -> BusinessValidationResult:
        """
        Validate that a business can process payments.
        
        Args:
            business_id: ID of the business to validate
            
        Returns:
            BusinessValidationResult with validation status and details
            
        Raises:
            ValidationError: If business validation fails
        """
        validation_errors = []
        
        # Check if business exists
        business = self._business_repository.find_by_id(business_id)
        if not business:
            raise NotFoundError(f"Business {business_id} not found")
        
        # Validate AP2 enablement
        if not business.ap2_enabled:
            validation_errors.append("Business does not have AP2 payments enabled")
        
        # Validate business status
        if business.status != "active":
            validation_errors.append(f"Business status is '{business.status}', must be 'active'")
        
        # Validate payment configuration
        if not self._validate_payment_configuration(business):
            validation_errors.append("Business payment configuration is invalid")
        
        # Get supported payment methods
        supported_methods = self._get_supported_payment_methods(business)
        if not supported_methods:
            validation_errors.append("No payment methods configured for business")
        
        return BusinessValidationResult(
            is_valid=len(validation_errors) == 0,
            business_id=business.id,
            business_name=business.name,
            ap2_enabled=business.ap2_enabled,
            supported_payment_methods=supported_methods,
            validation_errors=validation_errors
        )
    
    def validate_payment_constraints(self, 
                                   business_id: str, 
                                   constraints: Dict[str, Any]) -> None:
        """
        Validate payment constraints against business capabilities.
        
        Args:
            business_id: ID of the business
            constraints: Payment constraints to validate
            
        Raises:
            ValidationError: If constraints are invalid
        """
        business = self._business_repository.find_by_id(business_id)
        if not business:
            raise NotFoundError(f"Business {business_id} not found")
        
        # Validate amount constraints
        if "max_amount" in constraints:
            max_amount = constraints["max_amount"]
            if not isinstance(max_amount, (int, float)) or max_amount <= 0:
                raise ValidationError("Invalid max_amount constraint")
            
            # Check against business limits
            business_max = getattr(business, 'max_payment_amount', float('inf'))
            if max_amount > business_max:
                raise ValidationError(f"Payment amount exceeds business limit of {business_max}")
        
        # Validate currency constraints
        if "currency" in constraints:
            currency = constraints["currency"]
            supported_currencies = getattr(business, 'supported_currencies', ['USD'])
            if currency not in supported_currencies:
                raise ValidationError(f"Currency {currency} not supported by business")
        
        # Validate payment method constraints
        if "payment_method" in constraints:
            payment_method = constraints["payment_method"]
            supported_methods = self._get_supported_payment_methods(business)
            if payment_method not in supported_methods:
                raise ValidationError(f"Payment method {payment_method} not supported by business")
        
        # Validate time constraints
        if "expiry_hours" in constraints:
            expiry_hours = constraints["expiry_hours"]
            if not isinstance(expiry_hours, int) or expiry_hours <= 0 or expiry_hours > 168:
                raise ValidationError("Invalid expiry_hours constraint (must be 1-168)")
    
    def validate_cart_items(self, business_id: str, cart_items: list) -> None:
        """
        Validate cart items against business inventory and pricing.
        
        Args:
            business_id: ID of the business
            cart_items: List of cart items to validate
            
        Raises:
            ValidationError: If cart items are invalid
        """
        if not cart_items:
            raise ValidationError("Cart cannot be empty")
        
        business = self._business_repository.find_by_id(business_id)
        if not business:
            raise NotFoundError(f"Business {business_id} not found")
        
        for item in cart_items:
            # Validate item structure
            if not isinstance(item, dict):
                raise ValidationError("Cart items must be dictionaries")
            
            required_fields = ["id", "name", "price", "quantity"]
            for field in required_fields:
                if field not in item:
                    raise ValidationError(f"Cart item missing required field: {field}")
            
            # Validate item data types
            if not isinstance(item["price"], (int, float)) or item["price"] <= 0:
                raise ValidationError(f"Invalid price for item {item.get('id', 'unknown')}")
            
            if not isinstance(item["quantity"], int) or item["quantity"] <= 0:
                raise ValidationError(f"Invalid quantity for item {item.get('id', 'unknown')}")
            
            # Business-specific validation
            self._validate_item_against_business(business, item)
    
    def _validate_payment_configuration(self, business) -> bool:
        """Validate business payment configuration"""
        # Check for required payment configuration fields
        required_fields = ["ap2_enabled"]
        
        for field in required_fields:
            if not hasattr(business, field):
                return False
        
        # Additional validation logic based on business type
        business_type = getattr(business, 'type', 'unknown')
        
        if business_type == "hospitality":
            # Hospitality businesses need specific payment configuration
            return self._validate_hospitality_payment_config(business)
        elif business_type == "restaurant":
            # Restaurant businesses need specific payment configuration
            return self._validate_restaurant_payment_config(business)
        elif business_type == "retail":
            # Retail businesses need specific payment configuration
            return self._validate_retail_payment_config(business)
        
        return True  # Default validation for unknown business types
    
    def _validate_hospitality_payment_config(self, business) -> bool:
        """Validate hospitality-specific payment configuration"""
        # Check for hospitality-specific payment settings
        required_settings = ["deposit_required", "cancellation_policy"]
        
        for setting in required_settings:
            if not hasattr(business, setting):
                return False
        
        return True
    
    def _validate_restaurant_payment_config(self, business) -> bool:
        """Validate restaurant-specific payment configuration"""
        # Check for restaurant-specific payment settings
        required_settings = ["gratuity_enabled", "split_bill_supported"]
        
        for setting in required_settings:
            if not hasattr(business, setting):
                return False
        
        return True
    
    def _validate_retail_payment_config(self, business) -> bool:
        """Validate retail-specific payment configuration"""
        # Check for retail-specific payment settings
        required_settings = ["inventory_tracking", "return_policy"]
        
        for setting in required_settings:
            if not hasattr(business, setting):
                return False
        
        return True
    
    def _get_supported_payment_methods(self, business) -> list:
        """Get supported payment methods for a business"""
        # Get from business configuration or use defaults
        supported_methods = getattr(business, 'supported_payment_methods', [])
        
        if not supported_methods:
            # Default payment methods based on business type
            business_type = getattr(business, 'type', 'unknown')
            
            if business_type in ["hospitality", "restaurant"]:
                supported_methods = ["credit_card", "debit_card", "digital_wallet"]
            elif business_type == "retail":
                supported_methods = ["credit_card", "debit_card", "digital_wallet", "buy_now_pay_later"]
            else:
                supported_methods = ["credit_card", "debit_card"]
        
        return supported_methods
    
    def _validate_item_against_business(self, business, item: Dict[str, Any]) -> None:
        """Validate individual item against business rules"""
        business_type = getattr(business, 'type', 'unknown')
        
        if business_type == "hospitality":
            self._validate_hospitality_item(business, item)
        elif business_type == "restaurant":
            self._validate_restaurant_item(business, item)
        elif business_type == "retail":
            self._validate_retail_item(business, item)
    
    def _validate_hospitality_item(self, business, item: Dict[str, Any]) -> None:
        """Validate hospitality item"""
        # Check for required hospitality item fields
        required_fields = ["check_in", "check_out", "room_type"]
        
        for field in required_fields:
            if field in item:
                # Additional validation for date fields
                if field in ["check_in", "check_out"]:
                    # Validate date format and logic
                    pass  # Implement date validation
    
    def _validate_restaurant_item(self, business, item: Dict[str, Any]) -> None:
        """Validate restaurant item"""
        # Check for required restaurant item fields
        required_fields = ["menu_item_id", "quantity"]
        
        for field in required_fields:
            if field in item:
                # Additional validation for menu items
                pass  # Implement menu item validation
    
    def _validate_retail_item(self, business, item: Dict[str, Any]) -> None:
        """Validate retail item"""
        # Check for required retail item fields
        required_fields = ["product_id", "quantity"]
        
        for field in required_fields:
            if field in item:
                # Additional validation for products
                pass  # Implement product validation
