"""
BAIS Platform - ACP Configuration Builder

This module generates ACP (Agentic Commerce Protocol) configurations for
commerce-enabled demo applications, handling checkout flows and payment processing.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from pydantic import BaseModel, Field

from ...core.bais_schema_validator import BAISBusinessSchema
from ..scraper.website_analyzer import BusinessIntelligence, Service
from ..commerce.acp_integration_service import (
    CheckoutConfiguration, PaymentMethod, PaymentTiming, 
    TaxConfig, ReturnsPolicy, ShippingOption, Money
)


@dataclass
class Product:
    """Product for ACP integration"""
    id: str
    name: str
    description: str
    price: Money
    image_url: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProductFeed:
    """Product feed configuration"""
    url: str
    format: str  # 'json', 'rss', 'xml'
    update_frequency: int  # minutes
    products: List[Product]


@dataclass
class WebhookHandler:
    """Webhook handler configuration"""
    event_type: str
    endpoint: str
    secret: str
    retry_count: int = 3
    timeout_seconds: int = 30


@dataclass
class PaymentConfig:
    """Payment configuration for ACP"""
    provider: str  # 'stripe', 'paypal', 'bais_internal'
    api_key: str
    webhook_secret: str
    supported_methods: List[PaymentMethod]
    currency: str = "USD"


@dataclass
class AcpConfiguration:
    """Complete ACP configuration"""
    checkout_endpoint: CheckoutConfiguration
    product_feed: ProductFeed
    webhook_handlers: List[WebhookHandler]
    payment_config: PaymentConfig
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AcpConfigBuilder:
    """
    ACP Configuration Builder for BAIS Demo Templates
    
    Generates ACP configurations for commerce-enabled demo applications,
    handling checkout flows, payment processing, and webhook management.
    """
    
    def __init__(self):
        self.payment_providers = {
            "stripe": {
                "api_key_format": "sk_test_...",
                "webhook_secret_format": "whsec_...",
                "supported_methods": [
                    PaymentMethod.CREDIT_CARD,
                    PaymentMethod.DEBIT_CARD,
                    PaymentMethod.DIGITAL_WALLET
                ]
            },
            "paypal": {
                "api_key_format": "client_id_...",
                "webhook_secret_format": "webhook_secret_...",
                "supported_methods": [
                    PaymentMethod.CREDIT_CARD,
                    PaymentMethod.DIGITAL_WALLET
                ]
            },
            "bais_internal": {
                "api_key_format": "bais_demo_...",
                "webhook_secret_format": "demo_secret_...",
                "supported_methods": [
                    PaymentMethod.CREDIT_CARD,
                    PaymentMethod.DEBIT_CARD
                ]
            }
        }
        
        self.business_type_configs = {
            "hotel": {
                "payment_timing": PaymentTiming.AT_BOOKING,
                "shipping_required": False,
                "tax_rate": 0.08,
                "returns_enabled": False
            },
            "restaurant": {
                "payment_timing": PaymentTiming.AT_BOOKING,
                "shipping_required": False,
                "tax_rate": 0.08,
                "returns_enabled": False
            },
            "retail": {
                "payment_timing": PaymentTiming.AT_CHECKOUT,
                "shipping_required": True,
                "tax_rate": 0.08,
                "returns_enabled": True
            },
            "service": {
                "payment_timing": PaymentTiming.AT_BOOKING,
                "shipping_required": False,
                "tax_rate": 0.08,
                "returns_enabled": False
            }
        }
    
    def build_acp_integration(
        self, 
        schema: BAISBusinessSchema,
        products: List[Service]
    ) -> AcpConfiguration:
        """
        Generate ACP configuration for commerce demos
        
        Args:
            schema: BAIS business schema
            products: List of products/services
            
        Returns:
            AcpConfiguration: Complete ACP configuration
        """
        try:
            # Create checkout configuration
            checkout_config = self._create_checkout_config(schema)
            
            # Generate product feed
            product_feed = self._generate_product_feed(products, schema)
            
            # Create webhook handlers
            webhook_handlers = self._create_webhook_handlers(schema)
            
            # Create payment configuration
            payment_config = self._create_payment_config(schema)
            
            return AcpConfiguration(
                checkout_endpoint=checkout_config,
                product_feed=product_feed,
                webhook_handlers=webhook_handlers,
                payment_config=payment_config,
                metadata={
                    "business_name": schema.business_info.name,
                    "business_type": schema.business_info.business_type,
                    "generated_at": datetime.utcnow().isoformat(),
                    "acp_version": "1.0.0"
                }
            )
            
        except Exception as e:
            raise Exception(f"ACP configuration generation failed: {str(e)}")
    
    def _create_checkout_config(self, schema: BAISBusinessSchema) -> CheckoutConfiguration:
        """Create checkout configuration"""
        business_type = schema.business_info.business_type
        business_config = self.business_type_configs.get(business_type, self.business_type_configs["service"])
        
        # Extract payment methods from schema
        payment_methods = []
        for service in schema.services:
            for method in service.policies.payment.methods:
                if method.value not in [m.value for m in payment_methods]:
                    payment_methods.append(PaymentMethod(method.value))
        
        # Add default payment methods if none found
        if not payment_methods:
            payment_methods = [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]
        
        # Create tax configuration
        tax_config = TaxConfig(
            enabled=True,
            rate=business_config["tax_rate"],
            exempt_categories=[]
        )
        
        # Create returns policy
        returns_policy = ReturnsPolicy(
            enabled=business_config["returns_enabled"],
            days_to_return=30 if business_config["returns_enabled"] else 0,
            restocking_fee=0.0,
            description="Standard return policy" if business_config["returns_enabled"] else "No returns"
        )
        
        # Create shipping options if required
        shipping_options = []
        if business_config["shipping_required"]:
            shipping_options = [
                ShippingOption(
                    id="standard",
                    name="Standard Shipping",
                    price=Money(amount=9.99, currency="USD"),
                    estimated_days=5,
                    description="Standard shipping (5-7 business days)"
                ),
                ShippingOption(
                    id="express",
                    name="Express Shipping",
                    price=Money(amount=19.99, currency="USD"),
                    estimated_days=2,
                    description="Express shipping (2-3 business days)"
                )
            ]
        
        # Generate webhook URL
        safe_name = schema.business_info.name.lower().replace(' ', '-').strip()
        webhook_url = f"https://api.{safe_name}.com/acp/webhooks"
        
        return CheckoutConfiguration(
            merchant_id=schema.business_info.external_id,
            supported_payment_methods=payment_methods,
            payment_timing=business_config["payment_timing"],
            shipping_options=shipping_options,
            tax_config=tax_config,
            returns_policy=returns_policy,
            webhook_url=webhook_url,
            metadata={
                "business_type": business_type,
                "checkout_flow": "standard",
                "guest_checkout": True,
                "save_payment_methods": True
            }
        )
    
    def _generate_product_feed(self, products: List[Service], schema: BAISBusinessSchema) -> ProductFeed:
        """Generate product feed from services"""
        acp_products = []
        
        for service in products:
            # Convert service to product
            product = Product(
                id=service.id,
                name=service.name,
                description=service.description,
                price=Money(
                    amount=service.price or 100.0,
                    currency=service.currency or "USD"
                ),
                category=service.category,
                metadata={
                    "service_type": service.service_type.value if hasattr(service, 'service_type') else "booking",
                    "availability": "available",
                    "booking_required": True
                }
            )
            acp_products.append(product)
        
        # Generate product feed URL
        safe_name = schema.business_info.name.lower().replace(' ', '-').strip()
        feed_url = f"https://api.{safe_name}.com/acp/products.json"
        
        return ProductFeed(
            url=feed_url,
            format="json",
            update_frequency=15,  # Update every 15 minutes
            products=acp_products
        )
    
    def _create_webhook_handlers(self, schema: BAISBusinessSchema) -> List[WebhookHandler]:
        """Create webhook handlers"""
        handlers = []
        
        # Generate webhook secret
        webhook_secret = f"whsec_{uuid.uuid4().hex[:32]}"
        
        # Generate webhook URL
        safe_name = schema.business_info.name.lower().replace(' ', '-').strip()
        base_url = f"https://api.{safe_name}.com/acp/webhooks"
        
        # Define webhook events
        webhook_events = [
            {
                "event_type": "payment.completed",
                "endpoint": f"{base_url}/payment-completed",
                "description": "Payment completed successfully"
            },
            {
                "event_type": "payment.failed",
                "endpoint": f"{base_url}/payment-failed",
                "description": "Payment failed"
            },
            {
                "event_type": "order.created",
                "endpoint": f"{base_url}/order-created",
                "description": "New order created"
            },
            {
                "event_type": "order.cancelled",
                "endpoint": f"{base_url}/order-cancelled",
                "description": "Order cancelled"
            },
            {
                "event_type": "order.fulfilled",
                "endpoint": f"{base_url}/order-fulfilled",
                "description": "Order fulfilled"
            },
            {
                "event_type": "customer.created",
                "endpoint": f"{base_url}/customer-created",
                "description": "New customer created"
            }
        ]
        
        for event in webhook_events:
            handler = WebhookHandler(
                event_type=event["event_type"],
                endpoint=event["endpoint"],
                secret=webhook_secret,
                retry_count=3,
                timeout_seconds=30
            )
            handlers.append(handler)
        
        return handlers
    
    def _create_payment_config(self, schema: BAISBusinessSchema) -> PaymentConfig:
        """Create payment configuration"""
        business_type = schema.business_info.business_type
        
        # Select appropriate payment provider
        if business_type == "retail":
            provider = "stripe"
        elif business_type in ["hotel", "restaurant"]:
            provider = "bais_internal"
        else:
            provider = "bais_internal"  # Default to internal for demos
        
        provider_config = self.payment_providers[provider]
        
        # Generate demo API keys
        api_key = provider_config["api_key_format"].replace("...", uuid.uuid4().hex[:20])
        webhook_secret = provider_config["webhook_secret_format"].replace("...", uuid.uuid4().hex[:20])
        
        return PaymentConfig(
            provider=provider,
            api_key=api_key,
            webhook_secret=webhook_secret,
            supported_methods=provider_config["supported_methods"],
            currency="USD"
        )
    
    def generate_acp_documentation(self, config: AcpConfiguration) -> str:
        """Generate ACP configuration documentation"""
        business_name = config.metadata.get("business_name", "Demo Business")
        
        doc = f'''# ACP Configuration - {business_name}

## Overview

This document describes the Agentic Commerce Protocol (ACP) configuration for {business_name}. ACP enables AI agents to complete purchases directly within conversational interfaces while keeping merchants in control.

## Configuration Details

### Business Information
- **Name**: {business_name}
- **Type**: {config.metadata.get("business_type", "service")}
- **ACP Version**: {config.metadata.get("acp_version", "1.0.0")}
- **Generated**: {config.metadata.get("generated_at", "unknown")}

### Checkout Configuration

#### Payment Methods
'''
        
        for method in config.checkout_endpoint.supported_payment_methods:
            doc += f"- {method.value.replace('_', ' ').title()}\n"
        
        doc += f'''
#### Payment Timing
- **Timing**: {config.checkout_endpoint.payment_timing.value.replace('_', ' ').title()}

#### Tax Configuration
- **Enabled**: {config.checkout_endpoint.tax_config.enabled}
- **Rate**: {config.checkout_endpoint.tax_config.rate * 100:.1f}%
- **Tax ID**: {config.checkout_endpoint.tax_config.tax_id or "Not configured"}

#### Returns Policy
- **Enabled**: {config.checkout_endpoint.returns_policy.enabled}
- **Days to Return**: {config.checkout_endpoint.returns_policy.days_to_return}
- **Restocking Fee**: {config.checkout_endpoint.returns_policy.restocking_fee}%

### Shipping Options

'''
        
        if config.checkout_endpoint.shipping_options:
            for option in config.checkout_endpoint.shipping_options:
                doc += f'''#### {option.name}
- **ID**: {option.id}
- **Price**: ${option.price.amount:.2f} {option.price.currency}
- **Estimated Days**: {option.estimated_days}
- **Description**: {option.description or "No description"}

'''
        else:
            doc += "No shipping options configured (digital/physical services only)\n\n"
        
        doc += f'''### Product Feed

- **URL**: {config.product_feed.url}
- **Format**: {config.product_feed.format.upper()}
- **Update Frequency**: Every {config.product_feed.update_frequency} minutes
- **Products Count**: {len(config.product_feed.products)}

#### Products

'''
        
        for product in config.product_feed.products:
            doc += f'''#### {product.name}
- **ID**: {product.id}
- **Price**: ${product.price.amount:.2f} {product.price.currency}
- **Category**: {product.category or "General"}
- **Description**: {product.description}

'''
        
        doc += f'''### Payment Configuration

- **Provider**: {config.payment_config.provider.title()}
- **Currency**: {config.payment_config.currency}
- **API Key**: {config.payment_config.api_key[:20]}... (masked)
- **Webhook Secret**: {config.payment_config.webhook_secret[:20]}... (masked)

#### Supported Payment Methods
'''
        
        for method in config.payment_config.supported_methods:
            doc += f"- {method.value.replace('_', ' ').title()}\n"
        
        doc += f'''
### Webhook Handlers

The following webhook events are configured:

'''
        
        for handler in config.webhook_handlers:
            doc += f'''#### {handler.event_type.replace('.', ' ').title()}
- **Endpoint**: {handler.endpoint}
- **Retry Count**: {handler.retry_count}
- **Timeout**: {handler.timeout_seconds} seconds
- **Secret**: {handler.secret[:20]}... (masked)

'''
        
        doc += '''## Integration Guide

### 1. Checkout Flow

The ACP checkout flow follows these steps:

1. **Initialize Checkout**: Agent initiates checkout session
2. **Collect Information**: Agent gathers customer details
3. **Process Payment**: Agent processes payment using delegated tokens
4. **Confirm Order**: Agent confirms order and provides confirmation

### 2. Payment Processing

Payments are processed using delegated payment tokens:

```javascript
// Example payment processing
const paymentToken = await createDelegatedToken({
  paymentMethod: 'credit_card',
  amount: { amount: 100.00, currency: 'USD' },
  merchantId: 'merchant_id'
});

const result = await processPayment({
  sessionId: 'session_id',
  paymentToken: paymentToken,
  orderDetails: orderDetails
});
```

### 3. Webhook Handling

Webhook events are sent to configured endpoints:

```javascript
// Example webhook handler
app.post('/acp/webhooks/payment-completed', (req, res) => {
  const event = req.body;
  
  // Verify webhook signature
  const signature = req.headers['x-acp-signature'];
  if (!verifySignature(event, signature)) {
    return res.status(401).send('Invalid signature');
  }
  
  // Process payment completed event
  handlePaymentCompleted(event);
  
  res.status(200).send('OK');
});
```

### 4. Product Feed

The product feed is available at the configured URL:

```bash
# Get product feed
curl {config.product_feed.url}

# Example response
{
  "products": [
    {{
      "id": "product_1",
      "name": "Service Name",
      "description": "Service description",
      "price": {{ "amount": 100.00, "currency": "USD" }},
      "category": "service",
      "metadata": {{
        "service_type": "booking",
        "availability": "available"
      }}
    }}
  ],
  "updated_at": "2024-01-15T10:00:00Z"
}
```

## Testing

### Test Payment Processing

Use the following test data for payment processing:

```javascript
const testPaymentToken = {
  provider: 'stripe',
  token: 'tok_test_visa',
  amount: { amount: 100.00, currency: 'USD' }
};

const testOrderDetails = {
  sessionId: 'test_session',
  merchantId: 'test_merchant',
  customerEmail: 'test@example.com',
  customerName: 'Test Customer',
  billingAddress: {
    line1: '123 Test St',
    city: 'Test City',
    state: 'TS',
    postalCode: '12345',
    country: 'US'
  },
  products: [/* test products */],
  total: { amount: 100.00, currency: 'USD' }
};
```

### Test Webhook Events

Test webhook events using webhook testing tools:

```bash
# Test payment completed webhook
curl -X POST {config.webhook_handlers[0].endpoint} \\
  -H "Content-Type: application/json" \\
  -H "X-ACP-Signature: test_signature" \\
  -d '{{
    "event_type": "payment.completed",
    "merchant_id": "test_merchant",
    "session_id": "test_session",
    "order_id": "test_order",
    "timestamp": "2024-01-15T10:00:00Z",
    "data": {{
      "amount": {{ "amount": 100.00, "currency": "USD" }},
      "payment_method": "credit_card"
    }}
  }}'
```

## Security Considerations

1. **API Key Security**: Keep API keys secure and rotate regularly
2. **Webhook Verification**: Always verify webhook signatures
3. **HTTPS Only**: Use HTTPS for all webhook endpoints
4. **Rate Limiting**: Implement rate limiting for webhook endpoints
5. **Error Handling**: Implement proper error handling and logging

## Monitoring

Monitor the following metrics:

- Payment success/failure rates
- Webhook delivery success rates
- Checkout completion rates
- Average order values
- Customer satisfaction scores

## Support

For questions about this ACP configuration:

- **Documentation**: https://docs.bais.io/acp
- **Support**: support@bais.io
- **ACP Specification**: https://specs.bais.io/acp

---
*Generated by BAIS Platform Demo Template System*
'''
        
        return doc
    
    def export_configuration(self, config: AcpConfiguration, format: str = "json") -> str:
        """Export ACP configuration in various formats"""
        if format.lower() == "json":
            return json.dumps(config.__dict__, indent=2, default=str)
        elif format.lower() == "yaml":
            import yaml
            return yaml.dump(config.__dict__, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def validate_configuration(self, config: AcpConfiguration) -> List[str]:
        """Validate ACP configuration"""
        issues = []
        
        # Validate checkout configuration
        if not config.checkout_endpoint.supported_payment_methods:
            issues.append("No payment methods configured")
        
        if config.checkout_endpoint.tax_config.enabled and config.checkout_endpoint.tax_config.rate <= 0:
            issues.append("Tax rate must be greater than 0 when tax is enabled")
        
        # Validate product feed
        if not config.product_feed.products:
            issues.append("No products in product feed")
        
        for product in config.product_feed.products:
            if product.price.amount <= 0:
                issues.append(f"Product {product.id} has invalid price")
        
        # Validate webhook handlers
        if not config.webhook_handlers:
            issues.append("No webhook handlers configured")
        
        # Validate payment configuration
        if not config.payment_config.api_key:
            issues.append("Payment API key not configured")
        
        if not config.payment_config.webhook_secret:
            issues.append("Webhook secret not configured")
        
        return issues
