# BAIS ACP Migration Guide

## Overview

This guide outlines the migration from the custom ACP implementation to the official **Agentic Commerce Protocol (ACP)** specification as defined by the ACP consortium and OpenAI standards.

## 🔍 **Analysis Summary**

### Current State (Custom ACP)
- ✅ Well-structured service layer
- ✅ Proper error handling for commerce operations
- ✅ Session management with expiration
- ✅ Webhook infrastructure
- ✅ Payment token abstraction
- ❌ Custom protocol instead of official ACP specification
- ❌ Non-compliant data models and endpoints
- ❌ Missing official ACP manifest endpoint

### Target State (Official ACP)
- ✅ Full ACP 1.0.0 specification compliance
- ✅ Official data models and schemas
- ✅ Standardized endpoints and responses
- ✅ Proper commerce manifest for agent discovery
- ✅ Webhook signature verification
- ✅ Schema.org alignment for product data

## 🚀 **Migration Steps**

### Phase 1: Add Official ACP Implementation (COMPLETED)

#### ✅ 1.1 Create Official ACP Service
**File**: `backend/production/services/commerce/acp_official_compliance.py`

```python
class OfficialACPIntegrationService:
    """Official ACP Integration Service implementing ACP 1.0.0 specification"""
    
    async def get_commerce_manifest(self, merchant_id: str) -> ACPCommerceManifest
    async def initialize_checkout(self, merchant_id: str, line_items: List[Dict]) -> ACPCheckoutSession
    async def update_checkout_session(self, session_id: str, updates: Dict) -> ACPCheckoutSession
    async def create_delegated_payment_token(self, merchant_id: str, amount: ACPMoney, payment_method: ACPPaymentMethod) -> ACPDelegatedPaymentToken
    async def complete_checkout(self, session_id: str, payment_token: ACPDelegatedPaymentToken) -> ACPOrder
    async def get_product_catalog(self, merchant_id: str) -> List[ACPProduct]
    async def handle_webhook_event(self, event: ACPWebhookEvent) -> None
```

#### ✅ 1.2 Implement Official ACP Data Models
**Key Changes from Custom to Official:**

| Custom ACP | Official ACP | Change Required |
|------------|--------------|-----------------|
| `CheckoutSession` | `ACPCheckoutSession` | ✅ Updated |
| `SharedPaymentToken` | `ACPDelegatedPaymentToken` | ✅ Updated |
| `AcpWebhookEvent` | `ACPWebhookEvent` | ✅ Updated (uses `type` not `event_type`) |
| `Product` | `ACPProduct` | ✅ Updated (requires `images` array) |
| `Money` | `ACPMoney` | ✅ Updated |

#### ✅ 1.3 Create Official API Endpoints
**File**: `backend/production/api/v1/acp_commerce.py`

```python
# Official ACP endpoints
POST /v1/commerce/checkout/initialize
GET  /v1/commerce/checkout/{session_id}
PUT  /v1/commerce/checkout/{session_id}
POST /v1/commerce/payment-tokens
POST /v1/commerce/checkout/{session_id}/complete
GET  /v1/commerce/orders/{order_id}
GET  /v1/commerce/products
POST /v1/commerce/webhooks
```

#### ✅ 1.4 Create Commerce Manifest Endpoint
**File**: `backend/production/api/v1/acp_manifest.py`

```python
GET /.well-known/commerce-manifest
GET /.well-known/commerce-manifest/{merchant_id}
```

### Phase 2: Update Demo Template System (IN PROGRESS)

#### 🔄 2.1 Update ACP Config Builder
**File**: `backend/production/services/demo_templates/generator/acp_config_builder.py`

**Changes Made:**
- ✅ Updated imports to use official ACP models
- 🔄 Update method signatures to use official ACP types
- 🔄 Update configuration generation for ACP compliance

#### 🔄 2.2 Update Demo Orchestrator
**File**: `backend/production/services/demo_templates/orchestrator/demo_workflow.py`

**Required Changes:**
- Update ACP service instantiation
- Update demo generation to use official ACP
- Update documentation generation

### Phase 3: Testing and Validation (NEXT)

#### 📋 3.1 ACP Compliance Test Suite
**File**: `backend/production/tests/test_acp_compliance.py`

**Test Coverage:**
- ✅ Data model compliance
- ✅ Service method compliance
- ✅ API endpoint compliance
- ✅ Webhook event handling
- ✅ Session and token expiration
- ✅ Amount validation
- ✅ Error handling

#### 📋 3.2 Integration Tests
**Required Tests:**
- End-to-end checkout flow
- Webhook signature verification
- Product catalog compliance
- Manifest endpoint validation

### Phase 4: Production Deployment (FUTURE)

#### 📋 4.1 Gradual Migration Strategy
1. Deploy official ACP alongside custom implementation
2. Update client integrations to use official endpoints
3. Monitor usage and performance
4. Deprecate custom ACP endpoints
5. Remove custom implementation

#### 📋 4.2 Documentation Updates
- Update API documentation
- Update integration guides
- Update demo templates documentation
- Create migration guide for existing clients

## 📊 **Compliance Checklist**

### ✅ Data Models
- [x] `ACPCheckoutSession` with official fields
- [x] `ACPDelegatedPaymentToken` with proper structure
- [x] `ACPWebhookEvent` using `type` field (not `event_type`)
- [x] `ACPProduct` with required `images` array
- [x] `ACPMoney` with amount and currency
- [x] `ACPOrder` with complete order structure

### ✅ API Endpoints
- [x] `/v1/commerce/checkout/initialize` - Initialize checkout
- [x] `/v1/commerce/checkout/{session_id}` - Get/update checkout
- [x] `/v1/commerce/checkout/{session_id}/complete` - Complete checkout
- [x] `/v1/commerce/payment-tokens` - Create payment tokens
- [x] `/v1/commerce/orders/{order_id}` - Get order details
- [x] `/v1/commerce/products` - Get product catalog
- [x] `/v1/commerce/webhooks` - Handle webhook events

### ✅ Commerce Manifest
- [x] `/.well-known/commerce-manifest` - Merchant discovery
- [x] Capabilities advertisement
- [x] Endpoint documentation
- [x] Authentication methods
- [x] Schema references

### ✅ Webhook Events
- [x] `payment.completed` - Payment successful
- [x] `payment.failed` - Payment failed
- [x] `order.created` - Order created
- [x] `order.updated` - Order updated
- [x] `order.cancelled` - Order cancelled
- [x] `order.fulfilled` - Order fulfilled

### ✅ Error Handling
- [x] Proper HTTP status codes
- [x] Descriptive error messages
- [x] Session expiration handling
- [x] Token expiration handling
- [x] Amount validation
- [x] Input validation

## 🔧 **Key Differences: Custom vs Official ACP**

### Data Model Changes

#### Checkout Session
```python
# Custom ACP
class CheckoutSession(BaseModel):
    session_id: str
    merchant_id: str
    products: List[Product]
    # ...

# Official ACP
class ACPCheckoutSession(BaseModel):
    id: str  # Changed from session_id
    merchant_id: str
    line_items: List[Dict[str, Any]]  # Changed from products
    # ...
```

#### Webhook Events
```python
# Custom ACP
class AcpWebhookEvent(BaseModel):
    event_type: str  # Wrong field name
    merchant_id: str
    session_id: str
    # ...

# Official ACP
class ACPWebhookEvent(BaseModel):
    type: str  # Correct field name
    id: str
    created: int  # Unix timestamp
    data: Dict[str, Any]
    merchant_id: str
    # ...
```

#### Products
```python
# Custom ACP
class Product(BaseModel):
    id: str
    name: str
    price: Money
    image_url: Optional[str]  # Single image
    # ...

# Official ACP
class ACPProduct(BaseModel):
    id: str
    name: str
    price: ACPMoney
    images: List[str]  # Required array of images
    availability: str  # Required: "in_stock" | "out_of_stock" | "preorder"
    # ...
```

### API Endpoint Changes

#### Checkout Initialization
```python
# Custom ACP
POST /acp/checkout/initialize
{
    "session_id": "uuid",
    "products": [...]
}

# Official ACP
POST /v1/commerce/checkout/initialize
{
    "merchant_id": "merchant-id",
    "line_items": [...],
    "customer_id": "optional"
}
```

#### Payment Token Creation
```python
# Custom ACP
POST /acp/payment-tokens
{
    "payment_method": "credit_card",
    "amount": {"amount": 100, "currency": "USD"}
}

# Official ACP
POST /v1/commerce/payment-tokens
{
    "merchant_id": "merchant-id",
    "amount": {"amount": 100, "currency": "USD"},
    "payment_method": "credit_card",
    "metadata": {}
}
```

## 🧪 **Testing Strategy**

### Unit Tests
```bash
# Run ACP compliance tests
python -m pytest backend/production/tests/test_acp_compliance.py -v

# Run specific test categories
python -m pytest backend/production/tests/test_acp_compliance.py::TestACPDataModels -v
python -m pytest backend/production/tests/test_acp_compliance.py::TestACPServiceCompliance -v
python -m pytest backend/production/tests/test_acp_compliance.py::TestACPAPIEndpoints -v
```

### Integration Tests
```bash
# Test end-to-end ACP flow
python -m pytest backend/production/tests/test_integration_workflows.py -v

# Test demo generation with ACP
python scripts/generate_demo.py generate https://example.com --enable-acp
```

### Compliance Validation
```bash
# Validate commerce manifest
curl http://localhost:8000/.well-known/commerce-manifest

# Test checkout flow
curl -X POST http://localhost:8000/v1/commerce/checkout/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant",
    "line_items": [
      {
        "id": "product-1",
        "name": "Test Product",
        "price": {"amount": 100, "currency": "USD"},
        "quantity": 1
      }
    ]
  }'
```

## 📈 **Performance Considerations**

### Session Management
- **Custom ACP**: In-memory storage
- **Official ACP**: Database-backed with proper indexing
- **Impact**: Better scalability and persistence

### Token Expiration
- **Custom ACP**: 30-minute timeout
- **Official ACP**: 15-minute timeout (ACP standard)
- **Impact**: Improved security, faster cleanup

### Webhook Processing
- **Custom ACP**: Basic signature verification
- **Official ACP**: Proper HMAC verification
- **Impact**: Enhanced security compliance

## 🚨 **Breaking Changes**

### For Existing Clients
1. **Endpoint URLs**: Changed from `/acp/*` to `/v1/commerce/*`
2. **Field Names**: `session_id` → `id`, `event_type` → `type`
3. **Data Structures**: `products` → `line_items`, `image_url` → `images[]`
4. **Response Formats**: Updated to match ACP specification

### Migration Path for Clients
```python
# Old client code
response = await client.initialize_checkout(
    session_id="uuid",
    products=[...]
)

# New client code
response = await client.initialize_checkout(
    merchant_id="merchant-id",
    line_items=[...],
    customer_id="optional"
)
```

## 📚 **Documentation Updates**

### API Documentation
- [ ] Update OpenAPI specs for ACP endpoints
- [ ] Update request/response examples
- [ ] Update authentication methods
- [ ] Update error codes and messages

### Integration Guides
- [ ] Update client SDK examples
- [ ] Update webhook integration guide
- [ ] Update product catalog setup
- [ ] Update payment flow documentation

### Demo Templates
- [ ] Update demo generation to use official ACP
- [ ] Update demo documentation
- [ ] Update example scenarios
- [ ] Update CLI help text

## 🎯 **Success Metrics**

### Compliance Metrics
- [ ] 100% ACP 1.0.0 specification compliance
- [ ] All required endpoints implemented
- [ ] All webhook events supported
- [ ] Commerce manifest properly configured

### Quality Metrics
- [ ] 90%+ test coverage for ACP components
- [ ] All integration tests passing
- [ ] Performance benchmarks met
- [ ] Security audit passed

### Adoption Metrics
- [ ] Existing clients migrated successfully
- [ ] New integrations using official ACP
- [ ] Demo generation working with ACP
- [ ] Documentation usage increased

## 🔮 **Future Enhancements**

### ACP 1.1 Features (Future)
- Enhanced inventory management
- Multi-currency support
- Advanced tax calculation
- Subscription billing support
- Refund and chargeback handling

### Integration Improvements
- Real-time inventory updates
- Dynamic pricing support
- Customer preference learning
- Fraud detection integration
- Analytics and reporting

---

## 📞 **Support**

For questions about the ACP migration:

- **Documentation**: https://docs.bais.io/acp
- **ACP Specification**: https://specs.bais.io/acp
- **Support**: support@bais.io
- **Migration Help**: migration@bais.io

---

*This migration guide ensures BAIS remains at the forefront of AI agent commerce integration while maintaining backward compatibility and providing a smooth transition path for existing clients.*
