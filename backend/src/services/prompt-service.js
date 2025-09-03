import { createLogger } from '../utils/logger.js';

const logger = createLogger('PromptService');

export class PromptService {
    constructor() {
        this.baisVersion = '1.0';
        this.businessRegistry = this.initializeBusinessRegistry();
    }

    initializeBusinessRegistry() {
        return {
            hotel: {
                name: 'Zion Adventure Lodge',
                type: 'hospitality',
                serviceType: 'Hospitality',
                location: 'Springdale, UT',
                services: 'Rooms, Restaurant, Activities',
                capabilities: ['search', 'book', 'modify', 'cancel']
            },
            restaurant: {
                name: 'Red Canyon Brewing',
                type: 'food_service',
                serviceType: 'Food Service',
                location: 'Springdale, UT',
                services: 'Dining, Catering, Events',
                capabilities: ['search', 'book', 'modify', 'cancel']
            },
            retail: {
                name: 'Desert Pearl Gifts',
                type: 'retail',
                serviceType: 'Retail',
                location: 'Springdale, UT',
                services: 'Gifts, Souvenirs, Local Crafts',
                capabilities: ['search', 'book']
            }
        };
    }

    buildBAISPrompt(requestData) {
        this.validateRequestData(requestData);
        
        const business = this.getBusinessInfo(requestData.businessType);
        const sections = [
            this.buildIntroSection(business),
            this.buildContextSection(requestData, business),
            this.buildInstructionsSection(),
            this.buildResponseFormatSection()
        ];

        const fullPrompt = sections.join('\n\n');
        
        logger.info(`Built BAIS prompt for ${business.name} (${requestData.requestType})`);
        return fullPrompt;
    }

    validateRequestData(requestData) {
        const required = ['prompt', 'businessType', 'requestType'];
        
        for (const field of required) {
            if (!requestData[field]) {
                throw new Error(`Missing required field: ${field}`);
            }
        }

        if (!this.businessRegistry[requestData.businessType]) {
            throw new Error(`Invalid business type: ${requestData.businessType}`);
        }

        if (typeof requestData.prompt !== 'string' || requestData.prompt.trim().length === 0) {
            throw new Error('Prompt must be a non-empty string');
        }
    }

    getBusinessInfo(businessType) {
        const business = this.businessRegistry[businessType];
        if (!business) {
            throw new Error(`Business type not found: ${businessType}`);
        }
        return business;
    }

    buildIntroSection(business) {
        return `As an AI agent using the Business-Agent Integration Standard (BAIS) v${this.baisVersion}, you are interacting with ${business.serviceType} business "${business.name}" located in ${business.location}.`;
    }

    buildContextSection(requestData, business) {
        const userPrefs = requestData.userPreferences || 'None specified';
        
        return `BAIS Context:
- Protocol Version: ${this.baisVersion}
- Business Name: ${business.name}
- Business Type: ${business.type}
- Service Category: ${business.serviceType}
- Available Services: ${business.services}
- Supported Operations: ${business.capabilities.join(', ')}
- Request Type: ${requestData.requestType}
- User Preferences: ${userPrefs}
- Specific Request: ${requestData.prompt}`;
    }

    buildInstructionsSection() {
        return `Please process this request as if you're communicating through standardized BAIS protocols. Demonstrate:
1. Business Service Schema (BSS) parsing and validation
2. Agent-Business Protocol (ABP) API calls and workflow
3. Real-time availability checking and constraint validation
4. Expected business system responses and data flows
5. Error handling and fallback procedures when applicable`;
    }

    buildResponseFormatSection() {
        return `Format your response as a structured agent interaction log with:
- Schema Discovery Phase: How you parse the business service description
- Request Validation Phase: Input validation and constraint checking  
- Business Service Interaction: API calls and data exchange patterns
- Response Processing: How you handle and validate business responses
- User Communication: Final response to the user with actionable information

Include realistic timestamps, request/response examples, and demonstrate how BAIS standardization improves reliability compared to custom integrations.`;
    }

    buildSimplePrompt(businessType, request) {
        const business = this.getBusinessInfo(businessType);
        return `Using BAIS v${this.baisVersion}, help with this ${business.serviceType} request for ${business.name}: ${request}`;
    }

    buildErrorSimulationPrompt(errorType) {
        return `Demonstrate how BAIS v${this.baisVersion} handles a ${errorType} error scenario. Show error detection, logging, fallback procedures, and user communication patterns.`;
    }

    getAvailableBusinessTypes() {
        return Object.keys(this.businessRegistry);
    }

    getBusinessCapabilities(businessType) {
        const business = this.getBusinessInfo(businessType);
        return business.capabilities;
    }

    supportsOperation(businessType, operation) {
        const business = this.getBusinessInfo(businessType);
        return business.capabilities.includes(operation);
    }
}