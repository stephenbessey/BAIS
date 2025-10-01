"""
BAIS Platform - Demo UI Creator

This module generates React-based demo applications with interactive
interfaces for showcasing BAIS agent interactions.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from pydantic import BaseModel, Field

from ...core.bais_schema_validator import BAISBusinessSchema
from ..scraper.website_analyzer import BusinessIntelligence


@dataclass
class ReactComponent:
    """React component definition"""
    name: str
    component_type: str
    props: Dict[str, Any]
    children: List['ReactComponent']
    styles: Dict[str, Any]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DemoScenario:
    """Demo scenario definition"""
    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    expected_outcome: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MockData:
    """Mock data for demo"""
    services: List[Dict[str, Any]]
    bookings: List[Dict[str, Any]]
    customers: List[Dict[str, Any]]
    analytics: Dict[str, Any]


@dataclass
class DemoApplication:
    """Complete demo application"""
    frontend: str
    mock_data: MockData
    scenarios: List[DemoScenario]
    package_json: str
    readme: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DemoUiCreator:
    """
    Demo UI Creator for BAIS Platform
    
    Generates React-based demo applications with interactive interfaces
    for showcasing BAIS agent interactions.
    """
    
    def __init__(self):
        self.component_templates = self._load_component_templates()
        self.scenario_templates = self._load_scenario_templates()
    
    def create_interactive_demo(
        self, 
        schema: BAISBusinessSchema,
        intelligence: BusinessIntelligence
    ) -> DemoApplication:
        """
        Generate React-based demo application
        
        Args:
            schema: BAIS business schema
            intelligence: Business intelligence data
            
        Returns:
            DemoApplication: Complete demo application
        """
        try:
            # Generate UI components
            components = self._generate_ui_components(schema, intelligence)
            
            # Create agent chat interface
            agent_interface = self._create_agent_chat_interface(schema)
            
            # Create business dashboard
            business_dashboard = self._create_business_dashboard(schema)
            
            # Bundle React app
            frontend = self._bundle_react_app(components, agent_interface, business_dashboard)
            
            # Generate mock data
            mock_data = self._generate_realistic_mock_data(intelligence)
            
            # Create demo scenarios
            scenarios = self._create_demo_scenarios(schema)
            
            # Generate package.json
            package_json = self._generate_package_json()
            
            # Generate README
            readme = self._generate_demo_readme(schema, intelligence)
            
            return DemoApplication(
                frontend=frontend,
                mock_data=mock_data,
                scenarios=scenarios,
                package_json=package_json,
                readme=readme,
                metadata={
                    "business_name": schema.business_info.name,
                    "business_type": schema.business_info.business_type,
                    "components_count": len(components),
                    "scenarios_count": len(scenarios),
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            raise Exception(f"Demo UI creation failed: {str(e)}")
    
    def _generate_ui_components(
        self, 
        schema: BAISBusinessSchema,
        intelligence: BusinessIntelligence
    ) -> List[ReactComponent]:
        """Generate service-specific UI components"""
        components = []
        
        # Main app component
        app_component = ReactComponent(
            name="App",
            component_type="functional",
            props={
                "businessName": schema.business_info.name,
                "businessType": schema.business_info.business_type
            },
            children=[],
            styles={
                "container": "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                "header": "bg-white shadow-sm border-b border-gray-200"
            }
        )
        components.append(app_component)
        
        # Service cards
        for service in schema.services:
            service_card = self._create_service_card(service, intelligence)
            components.append(service_card)
            
            # Booking form for each service
            booking_form = self._create_booking_form(service)
            components.append(booking_form)
        
        # Agent chat interface
        chat_interface = self._create_agent_chat_interface(schema)
        components.append(chat_interface)
        
        # Analytics dashboard
        analytics_dashboard = self._create_analytics_dashboard()
        components.append(analytics_dashboard)
        
        return components
    
    def _create_service_card(self, service: Any, intelligence: BusinessIntelligence) -> ReactComponent:
        """Create service card component"""
        return ReactComponent(
            name=f"{service.name.replace(' ', '')}Card",
            component_type="functional",
            props={
                "service": {
                    "id": service.id,
                    "name": service.name,
                    "description": service.description,
                    "category": service.category,
                    "enabled": service.enabled
                },
                "businessInfo": {
                    "name": intelligence.business_name,
                    "type": intelligence.business_type.value
                }
            },
            children=[
                ReactComponent(
                    name="ServiceHeader",
                    component_type="div",
                    props={"className": "flex items-center justify-between"},
                    children=[],
                    styles={}
                ),
                ReactComponent(
                    name="ServiceDescription",
                    component_type="p",
                    props={"className": "text-gray-600 mt-2"},
                    children=[],
                    styles={}
                ),
                ReactComponent(
                    name="ServiceActions",
                    component_type="div",
                    props={"className": "mt-4 flex space-x-2"},
                    children=[],
                    styles={}
                )
            ],
            styles={
                "card": "bg-white rounded-lg shadow-md p-6 border border-gray-200",
                "title": "text-xl font-semibold text-gray-900",
                "button": "bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            }
        )
    
    def _create_booking_form(self, service: Any) -> ReactComponent:
        """Create booking form component"""
        return ReactComponent(
            name=f"{service.name.replace(' ', '')}BookingForm",
            component_type="functional",
            props={
                "service": {
                    "id": service.id,
                    "name": service.name,
                    "parameters": service.parameters
                }
            },
            children=[
                ReactComponent(
                    name="FormFields",
                    component_type="div",
                    props={"className": "space-y-4"},
                    children=[],
                    styles={}
                ),
                ReactComponent(
                    name="SubmitButton",
                    component_type="button",
                    props={
                        "type": "submit",
                        "className": "w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
                    },
                    children=[],
                    styles={}
                )
            ],
            styles={
                "form": "bg-white p-6 rounded-lg shadow-md",
                "field": "mb-4",
                "label": "block text-sm font-medium text-gray-700 mb-1",
                "input": "w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            }
        )
    
    def _create_agent_chat_interface(self, schema: BAISBusinessSchema) -> ReactComponent:
        """Create agent chat interface"""
        return ReactComponent(
            name="AgentChatInterface",
            component_type="functional",
            props={
                "businessName": schema.business_info.name,
                "services": [
                    {
                        "id": service.id,
                        "name": service.name,
                        "description": service.description
                    }
                    for service in schema.services
                ]
            },
            children=[
                ReactComponent(
                    name="ChatHeader",
                    component_type="div",
                    props={"className": "bg-blue-600 text-white p-4 rounded-t-lg"},
                    children=[],
                    styles={}
                ),
                ReactComponent(
                    name="ChatMessages",
                    component_type="div",
                    props={"className": "h-96 overflow-y-auto p-4 space-y-2"},
                    children=[],
                    styles={}
                ),
                ReactComponent(
                    name="ChatInput",
                    component_type="div",
                    props={"className": "p-4 border-t border-gray-200"},
                    children=[],
                    styles={}
                )
            ],
            styles={
                "container": "bg-white rounded-lg shadow-lg",
                "message": "bg-gray-100 p-3 rounded-lg",
                "input": "w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            }
        )
    
    def _create_business_dashboard(self, schema: BAISBusinessSchema) -> ReactComponent:
        """Create business dashboard"""
        return ReactComponent(
            name="BusinessDashboard",
            component_type="functional",
            props={
                "business": {
                    "name": schema.business_info.name,
                    "type": schema.business_info.business_type,
                    "description": schema.business_info.description
                },
                "services": schema.services
            },
            children=[
                ReactComponent(
                    name="DashboardHeader",
                    component_type="div",
                    props={"className": "mb-6"},
                    children=[],
                    styles={}
                ),
                ReactComponent(
                    name="MetricsGrid",
                    component_type="div",
                    props={"className": "grid grid-cols-1 md:grid-cols-3 gap-6 mb-6"},
                    children=[],
                    styles={}
                ),
                ReactComponent(
                    name="ServicesList",
                    component_type="div",
                    props={"className": "bg-white rounded-lg shadow p-6"},
                    children=[],
                    styles={}
                )
            ],
            styles={
                "container": "bg-gray-50 min-h-screen py-8",
                "card": "bg-white rounded-lg shadow p-6",
                "metric": "text-center",
                "metricValue": "text-3xl font-bold text-blue-600",
                "metricLabel": "text-gray-600 mt-1"
            }
        )
    
    def _create_analytics_dashboard(self) -> ReactComponent:
        """Create analytics dashboard"""
        return ReactComponent(
            name="AnalyticsDashboard",
            component_type="functional",
            props={},
            children=[
                ReactComponent(
                    name="AnalyticsHeader",
                    component_type="div",
                    props={"className": "mb-6"},
                    children=[],
                    styles={}
                ),
                ReactComponent(
                    name="ChartsGrid",
                    component_type="div",
                    props={"className": "grid grid-cols-1 lg:grid-cols-2 gap-6"},
                    children=[],
                    styles={}
                )
            ],
            styles={
                "container": "bg-white rounded-lg shadow p-6",
                "chart": "h-64",
                "title": "text-lg font-semibold text-gray-900 mb-4"
            }
        )
    
    def _bundle_react_app(
        self, 
        components: List[ReactComponent],
        agent_interface: ReactComponent,
        business_dashboard: ReactComponent
    ) -> str:
        """Bundle React application"""
        # Generate main App.jsx
        app_jsx = self._generate_app_jsx(components, agent_interface, business_dashboard)
        
        # Generate component files
        component_files = self._generate_component_files(components)
        
        # Generate styles
        styles = self._generate_styles()
        
        # Combine into complete frontend
        frontend = f"""
{app_jsx}

{component_files}

{styles}
"""
        
        return frontend
    
    def _generate_app_jsx(
        self, 
        components: List[ReactComponent],
        agent_interface: ReactComponent,
        business_dashboard: ReactComponent
    ) -> str:
        """Generate main App.jsx"""
        return '''import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <Router>
      <div className="App">
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-xl font-bold text-gray-900">BAIS Demo</h1>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link
                    to="/dashboard"
                    className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/services"
                    className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                  >
                    Services
                  </Link>
                  <Link
                    to="/agent"
                    className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                  >
                    Agent Chat
                  </Link>
                  <Link
                    to="/analytics"
                    className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                  >
                    Analytics
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/services" element={<Services />} />
            <Route path="/agent" element={<AgentChat />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;'''
    
    def _generate_component_files(self, components: List[ReactComponent]) -> str:
        """Generate component files"""
        files = []
        
        for component in components:
            if component.name != "App":
                file_content = f'''
// {component.name}.jsx
import React from 'react';

function {component.name}({{ {', '.join(component.props.keys())} }}) {{
  return (
    <div className="{component.styles.get('container', '')}">
      {/* Component implementation */}
    </div>
  );
}}

export default {component.name};'''
                files.append(file_content)
        
        return '\n\n'.join(files)
    
    def _generate_styles(self) -> str:
        """Generate CSS styles"""
        return '''/* App.css */
@import 'tailwindcss/base';
@import 'tailwindcss/components';
@import 'tailwindcss/utilities';

.App {
  text-align: center;
}

.App-logo {
  height: 40vmin;
  pointer-events: none;
}

@media (prefers-reduced-motion: no-preference) {
  .App-logo {
    animation: App-logo-spin infinite 20s linear;
  }
}

.App-header {
  background-color: #282c34;
  padding: 20px;
  color: white;
}

.App-link {
  color: #61dafb;
}

@keyframes App-logo-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Custom styles */
.chat-message {
  margin-bottom: 1rem;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background-color: #f3f4f6;
}

.chat-message.user {
  background-color: #dbeafe;
  margin-left: 2rem;
}

.chat-message.agent {
  background-color: #f0fdf4;
  margin-right: 2rem;
}

.service-card {
  transition: transform 0.2s ease-in-out;
}

.service-card:hover {
  transform: translateY(-2px);
}

.booking-form {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.analytics-chart {
  background: white;
  border-radius: 0.5rem;
  padding: 1rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
}'''
    
    def _generate_realistic_mock_data(self, intelligence: BusinessIntelligence) -> MockData:
        """Generate realistic mock data"""
        services = []
        bookings = []
        customers = []
        
        # Generate mock services based on intelligence
        for i, service in enumerate(intelligence.services):
            services.append({
                "id": service.id,
                "name": service.name,
                "description": service.description,
                "price": service.price or 100.0,
                "currency": service.currency,
                "available": True,
                "category": service.category
            })
        
        # Generate mock bookings
        for i in range(10):
            bookings.append({
                "id": f"booking_{i}",
                "service_id": services[i % len(services)]["id"],
                "customer_name": f"Customer {i+1}",
                "customer_email": f"customer{i+1}@example.com",
                "date": f"2024-01-{15+i}",
                "time": "10:00",
                "status": "confirmed",
                "total_amount": 100.0,
                "currency": "USD"
            })
        
        # Generate mock customers
        for i in range(5):
            customers.append({
                "id": f"customer_{i}",
                "name": f"Customer {i+1}",
                "email": f"customer{i+1}@example.com",
                "phone": f"+1-555-{1000+i}",
                "bookings_count": i + 1,
                "total_spent": (i + 1) * 100.0
            })
        
        # Generate mock analytics
        analytics = {
            "total_bookings": len(bookings),
            "total_revenue": sum(booking["total_amount"] for booking in bookings),
            "average_booking_value": sum(booking["total_amount"] for booking in bookings) / len(bookings),
            "conversion_rate": 0.15,
            "customer_satisfaction": 4.5,
            "popular_services": [
                {"service_id": service["id"], "bookings": i+5}
                for i, service in enumerate(services[:3])
            ]
        }
        
        return MockData(
            services=services,
            bookings=bookings,
            customers=customers,
            analytics=analytics
        )
    
    def _create_demo_scenarios(self, schema: BAISBusinessSchema) -> List[DemoScenario]:
        """Create demo scenarios"""
        scenarios = []
        
        # Scenario 1: Service Discovery
        scenarios.append(DemoScenario(
            id="service_discovery",
            name="Service Discovery",
            description="Agent helps user discover available services",
            steps=[
                {"step": 1, "action": "User asks about available services", "agent_response": "I can help you explore our services"},
                {"step": 2, "action": "Agent lists available services", "agent_response": "Here are our available services..."},
                {"step": 3, "action": "User selects a service", "agent_response": "Great choice! Let me help you book that service"}
            ],
            expected_outcome="User discovers and selects appropriate service"
        ))
        
        # Scenario 2: Booking Process
        scenarios.append(DemoScenario(
            id="booking_process",
            name="Booking Process",
            description="Agent guides user through booking process",
            steps=[
                {"step": 1, "action": "User wants to book a service", "agent_response": "I'll help you book that service"},
                {"step": 2, "action": "Agent checks availability", "agent_response": "Let me check availability for you"},
                {"step": 3, "action": "Agent collects booking details", "agent_response": "I need some details to complete your booking"},
                {"step": 4, "action": "Agent confirms booking", "agent_response": "Your booking has been confirmed!"}
            ],
            expected_outcome="Successful booking completion"
        ))
        
        # Scenario 3: Customer Support
        scenarios.append(DemoScenario(
            id="customer_support",
            name="Customer Support",
            description="Agent provides customer support",
            steps=[
                {"step": 1, "action": "User has a question", "agent_response": "I'm here to help with any questions"},
                {"step": 2, "action": "Agent provides information", "agent_response": "Here's the information you need"},
                {"step": 3, "action": "User needs modification", "agent_response": "I can help you modify your booking"}
            ],
            expected_outcome="User receives helpful support"
        ))
        
        return scenarios
    
    def _generate_package_json(self) -> str:
        """Generate package.json"""
        return '''{
  "name": "bais-demo-frontend",
  "version": "1.0.0",
  "description": "BAIS Demo Frontend Application",
  "main": "src/App.js",
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "react-scripts": "5.0.1",
    "axios": "^1.3.0",
    "chart.js": "^4.2.0",
    "react-chartjs-2": "^5.2.0",
    "tailwindcss": "^3.2.0",
    "@headlessui/react": "^1.7.0",
    "@heroicons/react": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "typescript": "^4.9.0"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}'''
    
    def _generate_demo_readme(
        self, 
        schema: BAISBusinessSchema, 
        intelligence: BusinessIntelligence
    ) -> str:
        """Generate demo README"""
        business_name = schema.business_info.name
        
        return f'''# BAIS Demo Frontend - {business_name}

Interactive demo application showcasing AI agent interactions with {business_name} services.

## Overview

This React application demonstrates how AI agents can interact with business services through the BAIS platform. It includes:

- **Service Discovery**: Browse available services
- **Booking Interface**: Interactive booking forms
- **Agent Chat**: Real-time chat with AI agents
- **Analytics Dashboard**: Business metrics and insights
- **Admin Panel**: Service management interface

## Features

### 🎯 Service Management
- View all available services
- Interactive service cards
- Real-time availability checking

### 🤖 Agent Integration
- Live chat interface with AI agents
- Natural language service queries
- Automated booking assistance

### 📊 Analytics
- Real-time booking metrics
- Revenue tracking
- Customer satisfaction scores
- Popular service analysis

### ⚙️ Admin Features
- Service configuration
- Booking management
- Customer support tools

## Quick Start

### Prerequisites
- Node.js 16+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm start
```

The application will be available at `http://localhost:3000`.

### Building for Production

```bash
# Build the application
npm run build

# Serve the built application
npx serve -s build
```

## Demo Scenarios

### 1. Service Discovery
1. Navigate to Services tab
2. Browse available services
3. Click on a service to see details
4. Use agent chat to ask questions

### 2. Booking Process
1. Select a service from the catalog
2. Fill out the booking form
3. Use agent chat for assistance
4. Confirm your booking

### 3. Agent Interaction
1. Go to Agent Chat tab
2. Ask questions about services
3. Request booking assistance
4. Get real-time responses

### 4. Analytics Review
1. Visit Analytics tab
2. Review booking metrics
3. Check revenue reports
4. Analyze customer data

## API Integration

The frontend integrates with the BAIS MCP server:

- **Base URL**: `http://localhost:8000`
- **MCP Endpoint**: `/mcp`
- **REST API**: `/api/v1`

### Example API Calls

```javascript
// Get available services
const services = await fetch('/api/v1/services').then(r => r.json());

// Search availability
const availability = await fetch('/api/v1/availability/search', {{
  method: 'POST',
  headers: {{ 'Content-Type': 'application/json' }},
  body: JSON.stringify({{ date: '2024-01-15' }})
}}).then(r => r.json());

// Create booking
const booking = await fetch('/api/v1/bookings', {{
  method: 'POST',
  headers: {{ 'Content-Type': 'application/json' }},
  body: JSON.stringify(bookingData)
}}).then(r => r.json());
```

## Customization

### Styling
The application uses Tailwind CSS for styling. Customize the appearance by modifying:
- `src/App.css` - Global styles
- Component-specific Tailwind classes
- Color scheme in `tailwind.config.js`

### Business Logic
Modify the following files to customize business logic:
- `src/components/ServiceCard.jsx` - Service display
- `src/components/BookingForm.jsx` - Booking process
- `src/components/AgentChat.jsx` - Chat interface

### Mock Data
Update mock data in:
- `src/data/services.js` - Service definitions
- `src/data/bookings.js` - Sample bookings
- `src/data/customers.js` - Customer data

## Deployment

### Docker Deployment

```bash
# Build Docker image
docker build -t bais-demo-frontend .

# Run container
docker run -p 3000:3000 bais-demo-frontend
```

### Static Hosting

Build the application and deploy to any static hosting service:

```bash
npm run build
# Upload build/ directory to your hosting service
```

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure the backend server is running and CORS is configured
2. **API Connection**: Check that the MCP server is accessible at the configured URL
3. **Build Errors**: Ensure all dependencies are installed and Node.js version is compatible

### Development Tips

- Use browser dev tools to inspect network requests
- Check the console for JavaScript errors
- Verify API endpoints are responding correctly

## Generated By

This demo application was generated by the BAIS Platform Demo Template System on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}.

For more information about BAIS, visit: https://bais.io

## Support

For questions about this demo:
- **Documentation**: https://docs.bais.io
- **Support**: support@bais.io
- **GitHub**: https://github.com/bais-io/demo-templates
'''
    
    def _load_component_templates(self) -> Dict[str, Any]:
        """Load component templates"""
        return {
            "service_card": {
                "template": "service_card_template",
                "props": ["service", "businessInfo"],
                "styles": ["card", "title", "button"]
            },
            "booking_form": {
                "template": "booking_form_template", 
                "props": ["service"],
                "styles": ["form", "field", "input"]
            },
            "chat_interface": {
                "template": "chat_interface_template",
                "props": ["businessName", "services"],
                "styles": ["container", "message", "input"]
            }
        }
    
    def _load_scenario_templates(self) -> Dict[str, Any]:
        """Load scenario templates"""
        return {
            "service_discovery": {
                "steps": 3,
                "focus": "discovery",
                "outcome": "service_selected"
            },
            "booking_process": {
                "steps": 4,
                "focus": "booking",
                "outcome": "booking_confirmed"
            },
            "customer_support": {
                "steps": 3,
                "focus": "support",
                "outcome": "issue_resolved"
            }
        }
