"""
MCP Prompts Implementation - Clean Code Implementation
Comprehensive prompt templates and management for MCP protocol following Clean Code principles
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """Types of MCP prompts"""
    BUSINESS_SEARCH = "business_search"
    BOOKING_CREATION = "booking_creation"
    PAYMENT_PROCESSING = "payment_processing"
    CUSTOMER_SUPPORT = "customer_support"
    BUSINESS_ANALYTICS = "business_analytics"
    A2A_COORDINATION = "a2a_coordination"
    AP2_PAYMENT_FLOW = "ap2_payment_flow"


class PromptCategory(Enum):
    """Categories of prompts for organization"""
    OPERATIONAL = "operational"
    ANALYTICAL = "analytical"
    COORDINATION = "coordination"
    SUPPORT = "support"
    INTEGRATION = "integration"


@dataclass
class PromptVariable:
    """Variable definition for prompt templates"""
    name: str
    description: str
    type: str  # "string", "number", "boolean", "object", "array"
    required: bool = True
    default_value: Any = None
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    examples: List[Any] = field(default_factory=list)


@dataclass
class PromptTemplate:
    """MCP prompt template following Clean Code principles"""
    name: str
    description: str
    prompt_type: PromptType
    category: PromptCategory
    template: str
    variables: List[PromptVariable] = field(default_factory=list)
    output_format: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def render(self, variables: Dict[str, Any]) -> str:
        """Render the prompt template with provided variables"""
        try:
            # Validate required variables
            missing_vars = []
            for var in self.variables:
                if var.required and var.name not in variables:
                    missing_vars.append(var.name)
            
            if missing_vars:
                raise ValueError(f"Missing required variables: {missing_vars}")
            
            # Apply default values
            rendered_vars = {}
            for var in self.variables:
                if var.name in variables:
                    rendered_vars[var.name] = variables[var.name]
                elif var.default_value is not None:
                    rendered_vars[var.name] = var.default_value
            
            # Simple template rendering (could be enhanced with Jinja2)
            rendered_prompt = self.template
            for var_name, var_value in rendered_vars.items():
                placeholder = f"{{{var_name}}}"
                rendered_prompt = rendered_prompt.replace(placeholder, str(var_value))
            
            return rendered_prompt
            
        except Exception as e:
            logger.error(f"Error rendering prompt template {self.name}: {e}")
            raise


class MCPPromptManager:
    """Manages MCP prompt templates following Clean Code principles"""
    
    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default prompt templates"""
        
        # Business Search Prompt
        self._templates["business_search"] = PromptTemplate(
            name="business_search",
            description="Search for available business services",
            prompt_type=PromptType.BUSINESS_SEARCH,
            category=PromptCategory.OPERATIONAL,
            template="""
You are a business service search assistant for {business_name}.

Context:
- Business Type: {business_type}
- Location: {location}
- Service Category: {service_category}
- Customer Requirements: {customer_requirements}

Instructions:
1. Search for available services matching the customer requirements
2. Filter results based on location, availability, and pricing
3. Provide detailed information about each service option
4. Include pricing, availability, and booking options

Output Format:
- List of available services with details
- Pricing information for each service
- Availability status and booking options
- Recommendations based on customer preferences

Customer Requirements: {customer_requirements}
Search Criteria: {search_criteria}
""",
            variables=[
                PromptVariable("business_name", "Name of the business", "string", True),
                PromptVariable("business_type", "Type of business (hotel, restaurant, etc.)", "string", True),
                PromptVariable("location", "Geographic location", "string", True),
                PromptVariable("service_category", "Category of services to search", "string", True),
                PromptVariable("customer_requirements", "Specific customer requirements", "string", True),
                PromptVariable("search_criteria", "Additional search criteria", "string", False, "")
            ],
            output_format={
                "type": "object",
                "properties": {
                    "services": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "service_id": {"type": "string"},
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "price": {"type": "number"},
                                "availability": {"type": "string"},
                                "booking_url": {"type": "string"}
                            }
                        }
                    },
                    "recommendations": {"type": "string"},
                    "total_found": {"type": "integer"}
                }
            }
        )
        
        # Booking Creation Prompt
        self._templates["booking_creation"] = PromptTemplate(
            name="booking_creation",
            description="Create a booking for a business service",
            prompt_type=PromptType.BOOKING_CREATION,
            category=PromptCategory.OPERATIONAL,
            template="""
You are a booking assistant for {business_name}.

Context:
- Service: {service_name}
- Customer: {customer_name} ({customer_email})
- Booking Details: {booking_details}
- Special Requirements: {special_requirements}

Instructions:
1. Validate the booking request against business policies
2. Check availability for the requested dates/times
3. Calculate pricing including taxes and fees
4. Process the booking with proper confirmation details
5. Send confirmation to customer

Booking Details:
- Service: {service_name}
- Date/Time: {booking_datetime}
- Duration: {duration}
- Guests/Quantity: {quantity}
- Special Requirements: {special_requirements}

Customer Information:
- Name: {customer_name}
- Email: {customer_email}
- Phone: {customer_phone}
- Payment Method: {payment_method}

Output Format:
- Booking confirmation details
- Confirmation number
- Payment summary
- Cancellation policy information
""",
            variables=[
                PromptVariable("business_name", "Name of the business", "string", True),
                PromptVariable("service_name", "Name of the service being booked", "string", True),
                PromptVariable("customer_name", "Customer's full name", "string", True),
                PromptVariable("customer_email", "Customer's email address", "string", True),
                PromptVariable("customer_phone", "Customer's phone number", "string", False, ""),
                PromptVariable("booking_datetime", "Date and time of booking", "string", True),
                PromptVariable("duration", "Duration of the service", "string", True),
                PromptVariable("quantity", "Number of guests or quantity", "integer", True),
                PromptVariable("special_requirements", "Any special requirements", "string", False, ""),
                PromptVariable("payment_method", "Payment method for booking", "string", True)
            ],
            output_format={
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string"},
                    "confirmation_number": {"type": "string"},
                    "status": {"type": "string"},
                    "total_amount": {"type": "number"},
                    "payment_status": {"type": "string"},
                    "confirmation_details": {"type": "string"}
                }
            }
        )
        
        # AP2 Payment Flow Prompt
        self._templates["ap2_payment_flow"] = PromptTemplate(
            name="ap2_payment_flow",
            description="Process AP2 payment workflow",
            prompt_type=PromptType.AP2_PAYMENT_FLOW,
            category=PromptCategory.INTEGRATION,
            template="""
You are an AP2 payment processing assistant for {business_name}.

Context:
- Payment Intent: {payment_intent}
- Amount: {amount} {currency}
- Customer: {customer_id}
- Agent: {agent_id}
- Payment Method: {payment_method_id}

Instructions:
1. Create intent mandate for the payment
2. Validate payment constraints and limits
3. Process cart mandate with itemized breakdown
4. Execute payment with proper authorization
5. Handle payment completion or failure scenarios

Payment Details:
- Intent Description: {payment_intent}
- Total Amount: {amount} {currency}
- Payment Constraints: {payment_constraints}
- Mandate Expiry: {mandate_expiry}

Customer Information:
- Customer ID: {customer_id}
- Agent ID: {agent_id}
- Payment Method ID: {payment_method_id}

Output Format:
- Payment workflow status
- Mandate IDs (intent and cart)
- Transaction ID
- Payment status and details
""",
            variables=[
                PromptVariable("business_name", "Name of the business", "string", True),
                PromptVariable("payment_intent", "Description of payment intent", "string", True),
                PromptVariable("amount", "Payment amount", "number", True),
                PromptVariable("currency", "Payment currency", "string", True, "USD"),
                PromptVariable("customer_id", "Customer identifier", "string", True),
                PromptVariable("agent_id", "Agent identifier", "string", True),
                PromptVariable("payment_method_id", "Payment method identifier", "string", True),
                PromptVariable("payment_constraints", "Payment constraints and limits", "string", False, "{}"),
                PromptVariable("mandate_expiry", "Mandate expiry time", "string", False, "")
            ],
            output_format={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "intent_mandate_id": {"type": "string"},
                    "cart_mandate_id": {"type": "string"},
                    "transaction_id": {"type": "string"},
                    "payment_status": {"type": "string"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string"}
                }
            }
        )
        
        # A2A Coordination Prompt
        self._templates["a2a_coordination"] = PromptTemplate(
            name="a2a_coordination",
            description="Coordinate multi-agent workflows",
            prompt_type=PromptType.A2A_COORDINATION,
            category=PromptCategory.COORDINATION,
            template="""
You are an A2A coordination assistant for {business_name}.

Context:
- Workflow Type: {workflow_type}
- Participating Agents: {participating_agents}
- Coordination Requirements: {coordination_requirements}
- Business Context: {business_context}

Instructions:
1. Discover and validate participating agents
2. Coordinate task distribution among agents
3. Monitor workflow progress and handle failures
4. Aggregate results from all participating agents
5. Provide comprehensive workflow completion report

Workflow Details:
- Type: {workflow_type}
- Agents: {participating_agents}
- Requirements: {coordination_requirements}
- Business Context: {business_context}

Output Format:
- Workflow coordination status
- Agent task assignments
- Progress tracking information
- Final workflow results
""",
            variables=[
                PromptVariable("business_name", "Name of the business", "string", True),
                PromptVariable("workflow_type", "Type of workflow to coordinate", "string", True),
                PromptVariable("participating_agents", "List of participating agents", "string", True),
                PromptVariable("coordination_requirements", "Specific coordination requirements", "string", True),
                PromptVariable("business_context", "Business context for coordination", "string", True)
            ],
            output_format={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "coordination_status": {"type": "string"},
                    "agent_assignments": {"type": "object"},
                    "progress_tracking": {"type": "object"},
                    "final_results": {"type": "object"}
                }
            }
        )
        
        # Customer Support Prompt
        self._templates["customer_support"] = PromptTemplate(
            name="customer_support",
            description="Handle customer support inquiries",
            prompt_type=PromptType.CUSTOMER_SUPPORT,
            category=PromptCategory.SUPPORT,
            template="""
You are a customer support assistant for {business_name}.

Context:
- Customer: {customer_name} ({customer_email})
- Inquiry Type: {inquiry_type}
- Issue Description: {issue_description}
- Business Context: {business_context}

Instructions:
1. Analyze the customer inquiry and determine the appropriate response
2. Access relevant customer and business information
3. Provide accurate and helpful information
4. Escalate complex issues when necessary
5. Follow up on any required actions

Customer Information:
- Name: {customer_name}
- Email: {customer_email}
- Previous Interactions: {previous_interactions}

Issue Details:
- Type: {inquiry_type}
- Description: {issue_description}
- Priority: {priority_level}
- Business Context: {business_context}

Output Format:
- Response to customer inquiry
- Recommended actions
- Escalation requirements (if any)
- Follow-up information
""",
            variables=[
                PromptVariable("business_name", "Name of the business", "string", True),
                PromptVariable("customer_name", "Customer's name", "string", True),
                PromptVariable("customer_email", "Customer's email", "string", True),
                PromptVariable("inquiry_type", "Type of customer inquiry", "string", True),
                PromptVariable("issue_description", "Description of the issue", "string", True),
                PromptVariable("business_context", "Business context for support", "string", True),
                PromptVariable("previous_interactions", "Previous customer interactions", "string", False, ""),
                PromptVariable("priority_level", "Priority level of the inquiry", "string", False, "medium")
            ],
            output_format={
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "recommended_actions": {"type": "array"},
                    "escalation_required": {"type": "boolean"},
                    "follow_up_required": {"type": "boolean"},
                    "ticket_id": {"type": "string"}
                }
            }
        )
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name"""
        return self._templates.get(name)
    
    def list_templates(self, category: Optional[PromptCategory] = None) -> List[PromptTemplate]:
        """List available prompt templates"""
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        return sorted(templates, key=lambda t: t.name)
    
    def create_template(self, template: PromptTemplate) -> bool:
        """Create a new prompt template"""
        try:
            self._templates[template.name] = template
            logger.info(f"Created prompt template: {template.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create prompt template {template.name}: {e}")
            return False
    
    def update_template(self, name: str, template: PromptTemplate) -> bool:
        """Update an existing prompt template"""
        try:
            if name not in self._templates:
                return False
            
            template.updated_at = datetime.now()
            self._templates[name] = template
            logger.info(f"Updated prompt template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update prompt template {name}: {e}")
            return False
    
    def delete_template(self, name: str) -> bool:
        """Delete a prompt template"""
        try:
            if name not in self._templates:
                return False
            
            del self._templates[name]
            logger.info(f"Deleted prompt template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete prompt template {name}: {e}")
            return False
    
    def render_prompt(self, name: str, variables: Dict[str, Any]) -> str:
        """Render a prompt template with variables"""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Prompt template not found: {name}")
        
        return template.render(variables)


class MCPPromptExecutor:
    """Executes MCP prompts and handles responses following Clean Code principles"""
    
    def __init__(self, prompt_manager: MCPPromptManager):
        self._prompt_manager = prompt_manager
        self._execution_history: List[Dict[str, Any]] = []
    
    async def execute_prompt(
        self, 
        prompt_name: str, 
        variables: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a prompt template with variables"""
        try:
            # Get the template
            template = self._prompt_manager.get_template(prompt_name)
            if not template:
                raise ValueError(f"Prompt template not found: {prompt_name}")
            
            # Render the prompt
            rendered_prompt = self._prompt_manager.render_prompt(prompt_name, variables)
            
            # Execute the prompt (this would integrate with your AI/LLM service)
            execution_result = await self._execute_rendered_prompt(
                rendered_prompt, 
                template, 
                context or {}
            )
            
            # Record execution
            execution_record = {
                "prompt_name": prompt_name,
                "execution_id": str(uuid.uuid4()),
                "variables": variables,
                "rendered_prompt": rendered_prompt,
                "result": execution_result,
                "timestamp": datetime.now().isoformat(),
                "template_version": template.version
            }
            
            self._execution_history.append(execution_record)
            
            return {
                "success": True,
                "execution_id": execution_record["execution_id"],
                "result": execution_result,
                "template_used": prompt_name,
                "timestamp": execution_record["timestamp"]
            }
            
        except Exception as e:
            logger.error(f"Failed to execute prompt {prompt_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "template_attempted": prompt_name,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_rendered_prompt(
        self, 
        rendered_prompt: str, 
        template: PromptTemplate,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the rendered prompt (placeholder for AI/LLM integration)"""
        # This is a placeholder implementation
        # In a real system, this would integrate with your AI/LLM service
        
        # Simulate execution based on prompt type
        if template.prompt_type == PromptType.BUSINESS_SEARCH:
            return await self._simulate_business_search(rendered_prompt, context)
        elif template.prompt_type == PromptType.BOOKING_CREATION:
            return await self._simulate_booking_creation(rendered_prompt, context)
        elif template.prompt_type == PromptType.AP2_PAYMENT_FLOW:
            return await self._simulate_payment_flow(rendered_prompt, context)
        elif template.prompt_type == PromptType.A2A_COORDINATION:
            return await self._simulate_a2a_coordination(rendered_prompt, context)
        elif template.prompt_type == PromptType.CUSTOMER_SUPPORT:
            return await self._simulate_customer_support(rendered_prompt, context)
        else:
            return {"message": "Prompt executed successfully", "type": template.prompt_type.value}
    
    async def _simulate_business_search(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate business search execution"""
        return {
            "services": [
                {
                    "service_id": "service_1",
                    "name": "Sample Service",
                    "description": "A sample service for demonstration",
                    "price": 100.0,
                    "availability": "available",
                    "booking_url": "/book/service_1"
                }
            ],
            "recommendations": "Based on your requirements, we recommend the sample service.",
            "total_found": 1
        }
    
    async def _simulate_booking_creation(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate booking creation execution"""
        return {
            "booking_id": str(uuid.uuid4()),
            "confirmation_number": f"CONF-{uuid.uuid4().hex[:8].upper()}",
            "status": "confirmed",
            "total_amount": 100.0,
            "payment_status": "pending",
            "confirmation_details": "Booking confirmed successfully"
        }
    
    async def _simulate_payment_flow(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate AP2 payment flow execution"""
        return {
            "workflow_id": str(uuid.uuid4()),
            "intent_mandate_id": f"intent-{uuid.uuid4().hex[:8]}",
            "cart_mandate_id": f"cart-{uuid.uuid4().hex[:8]}",
            "transaction_id": f"txn-{uuid.uuid4().hex[:8]}",
            "payment_status": "processing",
            "amount": 100.0,
            "currency": "USD"
        }
    
    async def _simulate_a2a_coordination(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate A2A coordination execution"""
        return {
            "workflow_id": str(uuid.uuid4()),
            "coordination_status": "active",
            "agent_assignments": {
                "agent_1": "search_task",
                "agent_2": "booking_task"
            },
            "progress_tracking": {
                "total_tasks": 2,
                "completed_tasks": 0,
                "failed_tasks": 0
            },
            "final_results": {}
        }
    
    async def _simulate_customer_support(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate customer support execution"""
        return {
            "response": "Thank you for contacting us. We're here to help with your inquiry.",
            "recommended_actions": ["Review customer account", "Check booking history"],
            "escalation_required": False,
            "follow_up_required": True,
            "ticket_id": f"TICKET-{uuid.uuid4().hex[:8].upper()}"
        }
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self._execution_history[-limit:] if limit else self._execution_history


# Global prompt manager instance
_prompt_manager: Optional[MCPPromptManager] = None
_prompt_executor: Optional[MCPPromptExecutor] = None


def get_prompt_manager() -> MCPPromptManager:
    """Get global prompt manager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = MCPPromptManager()
    return _prompt_manager


def get_prompt_executor() -> MCPPromptExecutor:
    """Get global prompt executor instance"""
    global _prompt_executor
    if _prompt_executor is None:
        _prompt_executor = MCPPromptExecutor(get_prompt_manager())
    return _prompt_executor


if __name__ == "__main__":
    # Example usage
    async def main():
        manager = get_prompt_manager()
        executor = get_prompt_executor()
        
        # List available templates
        templates = manager.list_templates()
        print(f"Available templates: {[t.name for t in templates]}")
        
        # Execute a business search prompt
        variables = {
            "business_name": "Sample Hotel",
            "business_type": "hotel",
            "location": "New York",
            "service_category": "accommodation",
            "customer_requirements": "Single room for 2 nights",
            "search_criteria": "Near city center, under $200/night"
        }
        
        result = await executor.execute_prompt("business_search", variables)
        print(f"Search result: {result}")
        
        # Execute a booking creation prompt
        booking_variables = {
            "business_name": "Sample Hotel",
            "service_name": "Deluxe Room",
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "customer_phone": "+1234567890",
            "booking_datetime": "2024-12-01 15:00:00",
            "duration": "2 nights",
            "quantity": 1,
            "special_requirements": "High floor, city view",
            "payment_method": "credit_card"
        }
        
        booking_result = await executor.execute_prompt("booking_creation", booking_variables)
        print(f"Booking result: {booking_result}")
    
    asyncio.run(main())
