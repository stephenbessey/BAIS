# BAIS Platform - Demo Template System

## Overview

The BAIS Demo Template System is a revolutionary tool that automatically generates complete, interactive demonstrations of AI agent integration with any business website. This system enables you to:

- **Input any business website URL**
- **Automatically extract business intelligence**
- **Generate complete BAIS demonstrations** including MCP server, ACP integration, and interactive UI
- **Deploy demos instantly** to show prospective clients how BAIS would work for their specific business

## 🚀 **Quick Start**

### Using the CLI

```bash
# Generate a full-stack demo
python scripts/generate_demo.py generate https://grandhotelstgeorge.com

# Generate a backend-only demo with ACP
python scripts/generate_demo.py generate https://restaurant.com --type backend_only --enable-acp

# Analyze a website first
python scripts/generate_demo.py analyze https://business.com
```

### Using the API

```bash
# Generate demo via API
curl -X POST http://localhost:8000/api/v1/demo-generation/generate \
  -H "Content-Type: application/json" \
  -d '{
    "website_url": "https://grandhotelstgeorge.com",
    "demo_type": "full_stack",
    "enable_acp": true
  }'

# Check deployment status
curl http://localhost:8000/api/v1/demo-generation/status/deployment-id
```

## 🏗️ **Architecture**

### Core Components

```
demo-templates/
├── scraper/                    # Website intelligence extraction
│   ├── website_analyzer.py     # Main analyzer
│   ├── service_extractor.py    # Service extraction
│   └── schema_inferencer.py    # Schema inference
├── generator/                  # Code generation
│   ├── schema_generator.py     # BAIS schema generation
│   ├── mcp_server_builder.py   # MCP server generation
│   ├── demo_ui_creator.py      # React UI generation
│   └── acp_config_builder.py   # ACP configuration
├── orchestrator/               # Deployment orchestration
│   ├── demo_workflow.py        # Main orchestrator
│   └── deployment_manager.py   # Deployment management
├── commerce/                   # Commerce integration
│   └── acp_integration_service.py  # ACP implementation
└── templates/                  # Business templates
    ├── hotel_template.json
    ├── restaurant_template.json
    ├── retail_template.json
    └── service_template.json
```

### Integration Points

1. **Website Analyzer**: Extracts business intelligence from any website
2. **Schema Generator**: Creates BAIS-compliant schemas from extracted data
3. **MCP Server Builder**: Generates working MCP protocol servers
4. **Demo UI Creator**: Creates interactive React applications
5. **ACP Config Builder**: Configures Agentic Commerce Protocol integration
6. **Demo Orchestrator**: Coordinates the entire generation pipeline

## 📋 **Demo Types**

### Full Stack Demo
- **Components**: MCP server + Demo UI + ACP config
- **Features**: Complete interactive demonstration
- **Time**: 3-5 minutes
- **Best For**: Sales presentations, client demonstrations

### Backend Only Demo
- **Components**: MCP server only
- **Features**: API endpoints, MCP protocol, health checks
- **Time**: 2-3 minutes
- **Best For**: Technical validation, API testing

### Frontend Only Demo
- **Components**: Demo UI only
- **Features**: Interactive interface, mock data, scenarios
- **Time**: 1-2 minutes
- **Best For**: UI/UX demonstrations, static showcases

### Commerce Enabled Demo
- **Components**: Full stack + ACP commerce integration
- **Features**: Payment processing, order management, commerce flows
- **Time**: 4-6 minutes
- **Best For**: E-commerce businesses, payment-enabled services

## 🔍 **Website Analysis**

The system automatically extracts:

### Business Information
- Business name and type
- Description and branding
- Contact information (phone, email, address)
- Operational hours
- Social media links

### Services & Products
- Service catalog
- Pricing information
- Service categories
- Booking requirements
- Product specifications

### Technical Details
- Website structure
- Navigation patterns
- Form configurations
- Media content
- Structured data

### Example Analysis Output

```json
{
  "business_name": "Grand Hotel St. George",
  "business_type": "hotel",
  "description": "Luxury hotel in downtown with premium amenities",
  "services": [
    {
      "id": "room_booking",
      "name": "Room Booking",
      "description": "Book luxury rooms and suites",
      "category": "accommodation",
      "service_type": "booking",
      "price": 299.0,
      "currency": "USD"
    }
  ],
  "contact_info": {
    "phone": "+1-555-123-4567",
    "email": "reservations@grandhotelstgeorge.com",
    "address": "123 Main St, Downtown, NY 10001"
  }
}
```

## 🛠️ **Generated Components**

### MCP Server
- **FastAPI-based server** implementing MCP protocol
- **Resource handlers** for business data
- **Tool definitions** for agent interactions
- **Health checks** and metrics
- **Docker configuration** for deployment

### Demo UI
- **React application** with modern UI
- **Interactive service cards** and booking forms
- **Agent chat interface** for live demonstrations
- **Analytics dashboard** with real-time metrics
- **Admin panel** for service management

### ACP Integration
- **Commerce configuration** for payment processing
- **Product feed generation** from services
- **Webhook handlers** for payment events
- **Checkout flow** configuration
- **Tax and shipping** setup

## 🎯 **Demo Scenarios**

### Scenario 1: Service Discovery
1. **User asks**: "What services do you offer?"
2. **Agent responds**: "I can help you explore our services"
3. **Agent lists**: Available services with descriptions
4. **User selects**: A specific service
5. **Agent confirms**: "Great choice! Let me help you book that"

### Scenario 2: Booking Process
1. **User requests**: "I want to book a room"
2. **Agent searches**: Available dates and rooms
3. **Agent collects**: Guest details and preferences
4. **Agent processes**: Booking confirmation
5. **Agent provides**: Confirmation number and details

### Scenario 3: Customer Support
1. **User asks**: "Can I modify my booking?"
2. **Agent accesses**: Booking history and status
3. **Agent provides**: Modification options
4. **Agent processes**: Requested changes
5. **Agent confirms**: Updated booking details

## 🔧 **Configuration**

### Demo Configuration

```python
config = DemoConfig(
    environment="staging",
    include_mock_data=True,
    enable_analytics=True,
    enable_acp=True,
    custom_domain="demo.business.com",
    infrastructure={
        "provider": "docker",
        "auto_cleanup": True,
        "resource_limits": {
            "cpu": "1",
            "memory": "2Gi"
        }
    }
)
```

### Business Templates

Templates are automatically selected based on business type:

- **Hotel**: Room booking, availability checking, guest management
- **Restaurant**: Table reservations, menu browsing, order management
- **Retail**: Product catalog, shopping cart, checkout process
- **Service**: Appointment booking, consultation scheduling, service delivery

## 📊 **Monitoring & Analytics**

### Deployment Metrics
- Generation time and success rates
- Resource usage and performance
- User interactions and engagement
- Error rates and debugging info

### Business Analytics
- Service discovery patterns
- Booking completion rates
- Customer satisfaction scores
- Revenue and conversion metrics

## 🚀 **Deployment Options**

### Local Development
```bash
# Generate and run locally
python scripts/generate_demo.py generate https://business.com
cd generated_demo/
docker-compose up
```

### Cloud Deployment
```bash
# Deploy to cloud
python scripts/generate_demo.py generate https://business.com --output-dir ./cloud-deploy
# Upload to cloud provider
```

### Kubernetes Deployment
```bash
# Deploy to Kubernetes
kubectl apply -f generated_demo/k8s/
```

## 🔒 **Security Considerations**

### API Security
- API key authentication
- Rate limiting and throttling
- Input validation and sanitization
- HTTPS enforcement

### Demo Security
- Isolated demo environments
- Temporary credentials and tokens
- Auto-cleanup after demo sessions
- No production data exposure

## 🧪 **Testing**

### Unit Tests
```bash
# Run component tests
python -m pytest backend/production/services/demo_templates/tests/
```

### Integration Tests
```bash
# Run full pipeline tests
python -m pytest backend/production/tests/test_demo_generation.py
```

### Demo Validation
```bash
# Validate generated demo
python scripts/validate_demo.py deployment-id
```

## 📚 **API Reference**

### Demo Generation API

#### POST `/api/v1/demo-generation/generate`
Generate a new demo from a website URL.

**Request Body:**
```json
{
  "website_url": "https://business.com",
  "demo_type": "full_stack",
  "enable_acp": true,
  "custom_domain": "demo.business.com"
}
```

**Response:**
```json
{
  "success": true,
  "deployment_id": "uuid-here",
  "demo_url": "https://demo-uuid.bais.io",
  "admin_panel": "https://demo-uuid.bais.io/admin",
  "api_endpoints": {
    "mcp": "https://demo-uuid.bais.io/mcp",
    "api": "https://demo-uuid.bais.io/api/v1"
  }
}
```

#### GET `/api/v1/demo-generation/status/{deployment_id}`
Get the status of a demo deployment.

#### DELETE `/api/v1/demo-generation/deployments/{deployment_id}`
Cleanup a demo deployment.

## 🎯 **Use Cases**

### Sales Demonstrations
- **Client meetings**: Show live demos tailored to client's business
- **Proposal presentations**: Generate demos during sales calls
- **Pilot programs**: Create pilot environments for testing

### Technical Validation
- **API testing**: Validate MCP protocol integration
- **Performance testing**: Test system under load
- **Security auditing**: Validate security implementations

### Training & Education
- **Team training**: Demonstrate BAIS capabilities
- **Client onboarding**: Show integration possibilities
- **Developer education**: Learn BAIS implementation patterns

## 🔮 **Future Enhancements**

### Planned Features
- **Multi-language support**: Generate demos in multiple languages
- **Custom branding**: Apply client branding to demos
- **Advanced analytics**: Deeper insights into demo performance
- **AI-powered optimization**: Automatically optimize demo configurations

### Integration Roadmap
- **More payment providers**: PayPal, Square, custom processors
- **Additional business types**: Healthcare, education, professional services
- **Enhanced UI components**: More interactive elements and animations
- **Real-time collaboration**: Multi-user demo sessions

## 📞 **Support & Resources**

### Documentation
- **API Documentation**: https://docs.bais.io/demo-templates
- **Integration Guide**: https://docs.bais.io/integration
- **Best Practices**: https://docs.bais.io/best-practices

### Community
- **GitHub**: https://github.com/bais-io/demo-templates
- **Discord**: https://discord.gg/bais
- **Stack Overflow**: Tag questions with `bais-demo-templates`

### Support
- **Email**: support@bais.io
- **Slack**: #demo-templates channel
- **Enterprise**: enterprise@bais.io

---

*Generated by BAIS Platform Demo Template System v1.0.0*
