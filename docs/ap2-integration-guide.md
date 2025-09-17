# AP2 (Agent Payments Protocol) Integration Guide

This guide explains how to integrate and use the Agent Payments Protocol (AP2) with the BAIS (Business-Agent Integration Standard) system.

## Overview

The Agent Payments Protocol (AP2) is an open protocol that enables secure, agent-led payments across platforms. It provides a payment-agnostic framework for users, merchants, and payment providers to transact with confidence.

## Key Concepts

### Mandates
AP2 uses cryptographically-signed mandates to establish trust and authorization:

- **Intent Mandate**: Authorizes an agent to make purchases within specified constraints
- **Cart Mandate**: Specifies exact items and pricing for a transaction

### Payment Workflow
The complete AP2 payment flow consists of:
1. Intent Mandate creation (user authorization)
2. Cart Mandate creation (specific items and pricing)
3. Payment execution (transaction processing)

## Configuration

### Environment Variables

Configure AP2 settings using the following environment variables:

```bash
# AP2 Network Configuration
AP2_BASE_URL=https://ap2-network.example.com
AP2_CLIENT_ID=your-ap2-client-id
AP2_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nYour private key\n-----END PRIVATE KEY-----
AP2_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\nYour public key\n-----END PUBLIC KEY-----

# AP2 Protocol Settings
AP2_VERSION=1.0
AP2_TIMEOUT=30
AP2_DEFAULT_MANDATE_EXPIRY_HOURS=24
AP2_SUPPORTED_PAYMENT_METHODS=credit_card,debit_card,bank_transfer,digital_wallet
AP2_DEFAULT_CURRENCY=USD
AP2_VERIFICATION_REQUIRED=true
```

### Database Schema Updates

The database models have been updated to support AP2:

#### Business Model
```python
# AP2 Payment Protocol configuration
ap2_enabled = Column(Boolean, default=False, index=True)
ap2_client_id = Column(String(255))
ap2_public_key = Column(Text)  # PEM format public key
ap2_supported_payment_methods = Column(JSONB, default=list)
ap2_webhook_endpoint = Column(String(255))
ap2_verification_required = Column(Boolean, default=True)
```

#### Booking Model
```python
# AP2 Payment Protocol fields
ap2_intent_mandate_id = Column(String(255), index=True)
ap2_cart_mandate_id = Column(String(255), index=True)
ap2_transaction_id = Column(String(255), index=True)
ap2_payment_workflow_id = Column(String(255), index=True)
ap2_payment_method_id = Column(String(255))
ap2_verification_status = Column(String(20), default="pending")
```

## API Endpoints

### Mandate Management

#### Create Intent Mandate
```http
POST /api/v1/payments/mandates/intent
Content-Type: application/json

{
  "user_id": "user_123",
  "business_id": "business_456",
  "intent_description": "Book a hotel room for weekend trip",
  "constraints": {
    "max_amount": 500.00,
    "payment_methods": ["credit_card", "debit_card"],
    "expiry_time": "2024-12-31T23:59:59Z"
  },
  "expiry_hours": 24
}
```

#### Create Cart Mandate
```http
POST /api/v1/payments/mandates/cart
Content-Type: application/json

{
  "intent_mandate_id": "mandate_123",
  "cart_items": [
    {
      "service_id": "hotel_room_001",
      "name": "Deluxe Room",
      "price": 299.00,
      "quantity": 1,
      "currency": "USD"
    }
  ],
  "pricing_validation": true
}
```

#### Get Mandate
```http
GET /api/v1/payments/mandates/{mandate_id}
```

#### Revoke Mandate
```http
POST /api/v1/payments/mandates/{mandate_id}/revoke
Content-Type: application/json

{
  "reason": "user_requested"
}
```

### Transaction Management

#### Initiate Payment Workflow
```http
POST /api/v1/payments/transactions/workflows
Content-Type: application/json

{
  "user_id": "user_123",
  "business_id": "business_456",
  "agent_id": "agent_789",
  "intent_description": "Book a hotel room",
  "cart_items": [
    {
      "service_id": "hotel_room_001",
      "name": "Deluxe Room",
      "price": 299.00,
      "quantity": 1,
      "currency": "USD"
    }
  ],
  "payment_constraints": {
    "max_amount": 500.00
  },
  "payment_method_id": "pm_123"
}
```

#### Get Payment Workflow Status
```http
GET /api/v1/payments/transactions/workflows/{workflow_id}
```

#### Get Transaction Details
```http
GET /api/v1/payments/transactions/{transaction_id}
```

## MCP Server Integration

The MCP server generator has been updated to support AP2 payment workflows:

### AP2-Enabled Booking Tool

When creating MCP servers, businesses can now use AP2-enabled booking tools:

```python
# Tool name: book_with_ap2_payment_{service_id}
{
  "name": "book_with_ap2_payment_hotel_room_001",
  "description": "Create a booking for Deluxe Room with AP2 payment integration",
  "inputSchema": {
    "type": "object",
    "properties": {
      "check_in": {"type": "string", "format": "date"},
      "check_out": {"type": "string", "format": "date"},
      "guests": {"type": "integer", "minimum": 1},
      "customer_info": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "email": {"type": "string"},
          "phone": {"type": "string"}
        },
        "required": ["name", "email"]
      },
      "ap2_payment": {
        "type": "object",
        "properties": {
          "user_id": {"type": "string"},
          "agent_id": {"type": "string"},
          "payment_method_id": {"type": "string"},
          "intent_description": {"type": "string"},
          "constraints": {
            "type": "object",
            "properties": {
              "max_amount": {"type": "number"},
              "payment_methods": {"type": "array", "items": {"type": "string"}},
              "expiry_time": {"type": "string"}
            }
          }
        },
        "required": ["user_id", "agent_id", "payment_method_id"]
      }
    },
    "required": ["check_in", "check_out", "guests", "customer_info", "ap2_payment"]
  }
}
```

## Authentication Middleware

AP2 authentication middleware provides secure mandate verification:

### Usage in FastAPI

```python
from api.middleware.ap2_auth import require_ap2_auth, require_ap2_intent_mandate

@app.post("/secure-endpoint")
async def secure_endpoint(
    auth_context: dict = Depends(require_ap2_auth)
):
    user_id = auth_context["user_id"]
    business_id = auth_context["business_id"]
    mandate = auth_context["mandate"]
    # Process request with verified mandate
```

### Mandate Verification

The middleware automatically:
- Verifies cryptographic signatures
- Checks mandate expiry
- Validates mandate types
- Extracts user and business context

## Error Handling

AP2 integration includes comprehensive error handling:

### Common Error Responses

```json
{
  "detail": "AP2 authentication failed: Invalid mandate signature",
  "status_code": 401
}
```

```json
{
  "detail": "Business business_123 is not AP2-enabled",
  "status_code": 400
}
```

```json
{
  "detail": "AP2 mandate has expired",
  "status_code": 400
}
```

## Testing

### Unit Tests

Run AP2 unit tests:

```bash
pytest tests/integration/test_ap2_integration.py -v
```

### Integration Tests

Test complete AP2 workflows:

```bash
pytest tests/integration/test_ap2_integration.py::TestAP2Integration -v
```

## Security Considerations

1. **Private Key Management**: Store AP2 private keys securely using environment variables or secret management systems
2. **Mandate Expiry**: Always set appropriate expiry times for mandates
3. **Signature Verification**: All mandates must be cryptographically verified
4. **Rate Limiting**: Implement rate limiting for AP2 endpoints
5. **Audit Logging**: Log all AP2 transactions for compliance

## Monitoring and Observability

AP2 integration includes monitoring capabilities:

- Payment workflow status tracking
- Mandate lifecycle monitoring
- Transaction success/failure rates
- Performance metrics for AP2 operations

## Troubleshooting

### Common Issues

1. **AP2 Service Not Enabled**
   - Check `AP2_CLIENT_ID`, `AP2_PRIVATE_KEY`, and `AP2_PUBLIC_KEY` environment variables
   - Verify `is_ap2_enabled()` returns `True`

2. **Mandate Validation Errors**
   - Ensure business is AP2-enabled in database
   - Check mandate constraints are valid
   - Verify mandate hasn't expired

3. **Payment Workflow Failures**
   - Check AP2 network connectivity
   - Verify payment method configuration
   - Review transaction logs for specific errors

### Debug Mode

Enable debug logging for AP2 operations:

```bash
LOG_LEVEL=DEBUG
AP2_MOCK_RESPONSES=true
```

## Future Enhancements

Planned improvements for AP2 integration:

1. **Webhook Support**: Real-time payment status updates
2. **Multi-Currency**: Enhanced currency support
3. **Payment Method Management**: User payment method storage
4. **Advanced Analytics**: Payment flow analytics and reporting
5. **Compliance Tools**: Enhanced audit and compliance features

## Support

For AP2 integration support:

1. Check the [AP2 Protocol Specification](https://github.com/google/agent-payments-protocol)
2. Review BAIS documentation
3. Contact the development team for assistance
