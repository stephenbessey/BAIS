import { API_CONFIG, ERROR_MESSAGES } from '../config/constants.js';

export class BAISApiClient {
    constructor() {
        this.baseUrl = API_CONFIG.BASE_URL;
        this.model = API_CONFIG.MODEL;
        this.timeout = API_CONFIG.TIMEOUT;
        this.maxRetries = API_CONFIG.MAX_RETRIES || 2;
        this.retryDelay = API_CONFIG.RETRY_DELAY || 2000;
    }

    async sendAgentRequest(prompt, formData = {}) {
        this.validatePrompt(prompt);
        
        for (let attempt = 1; attempt <= this.maxRetries + 1; attempt++) {
            try {
                console.log(`API attempt ${attempt}/${this.maxRetries + 1}`);
                return await this.makeRequest(prompt, formData);
                
            } catch (error) {
                console.warn(`Attempt ${attempt} failed:`, error.message);
                
                if (this.isNonRetryableError(error) || attempt === this.maxRetries + 1) {
                    throw this.handleRequestError(error);
                }
                
                await this.delay(this.retryDelay * attempt);
            }
        }
    }

    async makeRequest(prompt, formData) {
        const requestPayload = this.buildRequestPayload(prompt, formData);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(this.baseUrl, {
                method: 'POST',
                headers: this.buildHeaders(),
                body: JSON.stringify(requestPayload),
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`API Error: ${response.status} - ${errorData.error || response.statusText}`);
            }

            return await this.parseResponse(response);
            
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }
    
    isNonRetryableError(error) {
        const nonRetryableMessages = [
            'Prompt is required',
            'Failed to parse',
            'Invalid request',
            'API Error: 4'
        ];
        
        return nonRetryableMessages.some(msg => 
            error.message.includes(msg)
        );
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    validatePrompt(prompt) {
        if (!prompt || typeof prompt !== 'string' || prompt.trim().length === 0) {
            throw new Error('Prompt is required and must be a non-empty string');
        }
        
        if (prompt.trim().length > 50000) {
            throw new Error('Prompt is too long (max 50,000 characters)');
        }
    }

    buildRequestPayload(prompt, formData = {}) {
        return {
            prompt: prompt.trim(),
            businessType: formData.businessType,
            requestType: formData.requestType,
            userPreferences: formData.userPreferences
        };
    }

    buildHeaders() {
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
    }

    async parseResponse(response) {
        try {
            return await response.json();
        } catch (error) {
            throw new Error('Failed to parse API response as JSON');
        }
    }

    extractResponseContent(apiResponse) {
        if (!apiResponse) {
            return 'No response received from API';
        }

        if (apiResponse.success && apiResponse.data && apiResponse.data.response) {
            return apiResponse.data.response;
        }

        if (!apiResponse.success && apiResponse.error) {
            return `Error: ${apiResponse.error}`;
        }

        console.warn('Unknown response format:', apiResponse);
        return `Received response but couldn't extract content. Available keys: ${Object.keys(apiResponse).join(', ')}`;
    }

    handleRequestError(error) {
        if (error.name === 'AbortError') {
            return new Error(`${ERROR_MESSAGES.TIMEOUT_ERROR}. The AI model may be processing a heavy load. Try a shorter request.`);
        }

        if (error.message.includes('Failed to fetch') || 
            error.message.includes('NetworkError') ||
            error.message.includes('net::')) {
            return new Error(ERROR_MESSAGES.NETWORK_ERROR);
        }

        if (error.message.includes('API Error: 5')) {
            return new Error(ERROR_MESSAGES.SERVER_ERROR);
        }

        if (error.message.includes('API Error: 4')) {
            return new Error(ERROR_MESSAGES.CLIENT_ERROR);
        }

        return new Error(`${ERROR_MESSAGES.UNEXPECTED_ERROR}: ${error.message}`);
    }

    async checkApiHealth() {
        try {
            const testPrompt = "Test connection";
            await this.sendAgentRequest(testPrompt);
            return true;
        } catch (error) {
            console.warn('API health check failed:', error.message);
            return false;
        }
    }
}