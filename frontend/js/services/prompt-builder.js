import { getBusinessByType } from '../data/business-registry.js';
import { BAIS_CONFIG } from '../config/constants.js';

export class BAISPromptBuilder {

    buildAgentPrompt(formData) {
        this.validateFormData(formData);
        
        const businessInfo = getBusinessByType(formData.businessType);
        if (!businessInfo) {
            throw new Error(`Invalid business type: ${formData.businessType}`);
        }

        return this.constructPrompt(formData, businessInfo);
    }

    validateFormData(formData) {
        const requiredFields = ['businessType', 'requestType', 'specificRequest'];
        
        for (const field of requiredFields) {
            if (!formData[field] || formData[field].trim() === '') {
                throw new Error(`Missing required field: ${field}`);
            }
        }
    }

    constructPrompt(formData, businessInfo) {
        const sections = [
            this.buildIntroduction(formData, businessInfo),
            this.buildBAISContext(formData, businessInfo),
            this.buildInstructions(),
            this.buildResponseFormat()
        ];

        return sections.join('\n\n');
    }

    buildIntroduction(formData, businessInfo) {
        return `As an AI agent using the ${BAIS_CONFIG.PROTOCOL_NAME} (BAIS), interact with ${businessInfo.serviceType} business "${businessInfo.businessInfo.name}" located in ${businessInfo.businessInfo.location.city}, ${businessInfo.businessInfo.location.state}.`;
    }

    buildBAISContext(formData, businessInfo) {
        const userPrefs = formData.userPreferences || 'None specified';
        
        return `BAIS Context:
- Protocol Version: ${BAIS_CONFIG.VERSION}
- Business Name: ${businessInfo.businessInfo.name}
- Business Type: ${businessInfo.businessInfo.type}
- Service Category: ${businessInfo.serviceType}
- Available Services: ${businessInfo.services}
- Request Type: ${formData.requestType}
- User Preferences: ${userPrefs}
- Specific Request: ${formData.specificRequest}
- BAIS Compliant: ${businessInfo.baisCompliant ? 'Yes' : 'No'}`;
    }

    buildInstructions() {
        return `Please process this request as if you're communicating through standardized BAIS protocols. Provide a realistic response that demonstrates:
1. How you would parse the business service schema (BSS)
2. What API calls you would make through the Agent-Business Protocol (ABP)
3. The expected business response and next steps
4. Any error handling or fallback scenarios`;
    }

    buildResponseFormat() {
        return `Format your response as a structured agent interaction log showing:
- Schema Discovery Phase
- Request Validation Phase  
- Business Service Interaction
- Response Processing
- User Communication

Include realistic timestamps, request/response examples, and demonstrate how BAIS standardization improves the interaction compared to custom integrations.`;
    }

    buildSimplePrompt(businessType, request) {
        const businessInfo = getBusinessByType(businessType);
        if (!businessInfo) {
            throw new Error(`Invalid business type: ${businessType}`);
        }

        return `Using BAIS ${BAIS_CONFIG.VERSION}, help with this request for ${businessInfo.businessInfo.name}: ${request}`;
    }

    buildErrorSimulationPrompt(errorType) {
        return `Demonstrate how BAIS ${BAIS_CONFIG.VERSION} handles a ${errorType} error scenario. Show the error detection, logging, fallback procedures, and user communication that would occur in a production BAIS implementation.`;
    }
}