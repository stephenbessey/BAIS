/**
 * Refactored API Client following best practices
 * 
 * This module provides a clean, testable API client with proper error handling,
 * retry logic, and separation of concerns.
 */

import { API_CONFIG, ERROR_MESSAGES } from '../config/constants.js';

/**
 * Configuration for retry behavior
 */
const RETRY_CONFIG = {
    MAX_ATTEMPTS: 3,
    BASE_DELAY_MS: 1000,
    MAX_DELAY_MS: 5000,
    BACKOFF_MULTIPLIER: 2
};

/**
 * HTTP status codes that should not be retried
 */
const NON_RETRYABLE_STATUS_CODES = [400, 401, 403, 404, 422];

/**
 * Error types for better error handling
 */
export class APIError extends Error {
    constructor(message, statusCode = null, isRetryable = true) {
        super(message);
        this.name = 'APIError';
        this.statusCode = statusCode;
        this.isRetryable = isRetryable;
    }
}

export class NetworkError extends APIError {
    constructor(message) {
        super(message, null, true);
        this.name = 'NetworkError';
    }
}

export class ValidationError extends APIError {
    constructor(message) {
        super(message, 400, false);
        this.name = 'ValidationError';
    }
}

/**
 * Main API Client class
 */
export class BAISApiClient {
    /**
     * Initialize the API client with configuration
     * 
     * @param {Object} config - Configuration object
     */
    constructor(config = {}) {
        this.baseUrl = config.baseUrl || API_CONFIG.BASE_URL;
        this.model = config.model || API_CONFIG.MODEL;
        this.timeout = config.timeout || API_CONFIG.TIMEOUT;
        this.retryConfig = { ...RETRY_CONFIG, ...config.retryConfig };
    }

    /**
     * Send an agent request with automatic retry logic
     * 
     * @param {string} prompt - The prompt to send
     * @param {Object} formData - Additional form data
     * @returns {Promise<Object>} API response
     * @throws {ValidationError} If prompt validation fails
     * @throws {APIError} If API request fails after all retries
     */
    async sendAgentRequest(prompt, formData = {}) {
        this.validatePrompt(prompt);
        
        const requestPayload = this.buildRequestPayload(prompt, formData);
        
        return await this.executeWithRetry(async () => {
            return await this.makeRequest(requestPayload);
        });
    }

    /**
     * Execute a request with exponential backoff retry logic
     * 
     * @param {Function} requestFn - Function that makes the request
     * @returns {Promise<Object>} Request result
     */
    async executeWithRetry(requestFn) {
        let lastError;
        
        for (let attempt = 1; attempt <= this.retryConfig.MAX_ATTEMPTS; attempt++) {
            try {
                console.log(`API attempt ${attempt}/${this.retryConfig.MAX_ATTEMPTS}`);
                return await requestFn();
                
            } catch (error) {
                lastError = error;
                console.warn(`Attempt ${attempt} failed:`, error.message);
                
                if (!this.shouldRetry(error) || attempt === this.retryConfig.MAX_ATTEMPTS) {
                    throw this.transformError(error);
                }
                
                const delay = this.calculateRetryDelay(attempt);
                await this.delay(delay);
            }
        }
        
        throw this.transformError(lastError);
    }

    /**
     * Make a single HTTP request
     * 
     * @param {Object} payload - Request payload
     * @returns {Promise<Object>} Response data
     */
    async makeRequest(payload) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(this.baseUrl, {
                method: 'POST',
                headers: this.buildHeaders(),
                body: JSON.stringify(payload),
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new APIError(
                    `HTTP ${response.status}: ${response.statusText}`,
                    response.status,
                    !NON_RETRYABLE_STATUS_CODES.includes(response.status)
                );
            }

            return await this.parseResponse(response);
            
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    /**
     * Determine if an error should trigger a retry
     * 
     * @param {Error} error - The error to check
     * @returns {boolean} True if the request should be retried
     */
    shouldRetry(error) {
        if (error instanceof ValidationError) {
            return false;
        }
        
        if (error instanceof APIError) {
            return error.isRetryable;
        }
        
        // Network errors are generally retryable
        if (error.name === 'AbortError' || 
            error.message.includes('Failed to fetch') ||
            error.message.includes('NetworkError')) {
            return true;
        }
        
        return false;
    }

    /**
     * Calculate delay for retry attempts using exponential backoff
     * 
     * @param {number} attempt - Current attempt number (1-based)
     * @returns {number} Delay in milliseconds
     */
    calculateRetryDelay(attempt) {
        const delay = this.retryConfig.BASE_DELAY_MS * 
                     Math.pow(this.retryConfig.BACKOFF_MULTIPLIER, attempt - 1);
        return Math.min(delay, this.retryConfig.MAX_DELAY_MS);
    }

    /**
     * Validate the prompt parameter
     * 
     * @param {string} prompt - The prompt to validate
     * @throws {ValidationError} If validation fails
     */
    validatePrompt(prompt) {
        if (!prompt || typeof prompt !== 'string') {
            throw new ValidationError('Prompt is required and must be a string');
        }
        
        const trimmedPrompt = prompt.trim();
        if (trimmedPrompt.length === 0) {
            throw new ValidationError('Prompt cannot be empty');
        }
        
        if (trimmedPrompt.length > 50000) {
            throw new ValidationError('Prompt is too long (max 50,000 characters)');
        }
    }

    /**
     * Build the request payload
     * 
     * @param {string} prompt - The prompt
     * @param {Object} formData - Additional form data
     * @returns {Object} Request payload
     */
    buildRequestPayload(prompt, formData = {}) {
        return {
            prompt: prompt.trim(),
            businessType: formData.businessType,
            requestType: formData.requestType,
            userPreferences: formData.userPreferences
        };
    }

    /**
     * Build HTTP headers for the request
     * 
     * @returns {Object} HTTP headers
     */
    buildHeaders() {
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
    }

    /**
     * Parse the HTTP response
     * 
     * @param {Response} response - Fetch response object
     * @returns {Promise<Object>} Parsed response data
     * @throws {APIError} If response parsing fails
     */
    async parseResponse(response) {
        try {
            return await response.json();
        } catch (error) {
            throw new APIError('Failed to parse API response as JSON', null, false);
        }
    }

    /**
     * Extract content from API response
     * 
     * @param {Object} apiResponse - Raw API response
     * @returns {string} Extracted content
     */
    extractResponseContent(apiResponse) {
        if (!apiResponse) {
            return 'No response received from API';
        }

        if (apiResponse.success && apiResponse.data?.response) {
            return apiResponse.data.response;
        }

        if (!apiResponse.success && apiResponse.error) {
            return `Error: ${apiResponse.error}`;
        }

        console.warn('Unknown response format:', apiResponse);
        return `Received response but couldn't extract content. Available keys: ${Object.keys(apiResponse).join(', ')}`;
    }

    /**
     * Transform errors into user-friendly messages
     * 
     * @param {Error} error - Original error
     * @returns {Error} Transformed error
     */
    transformError(error) {
        if (error instanceof ValidationError || error instanceof APIError) {
            return error;
        }

        if (error.name === 'AbortError') {
            return new APIError(
                `${ERROR_MESSAGES.TIMEOUT_ERROR}. The AI model may be processing a heavy load. Try a shorter request.`,
                null,
                true
            );
        }

        if (error.message.includes('Failed to fetch') || 
            error.message.includes('NetworkError') ||
            error.message.includes('net::')) {
            return new NetworkError(ERROR_MESSAGES.NETWORK_ERROR);
        }

        return new APIError(`${ERROR_MESSAGES.UNEXPECTED_ERROR}: ${error.message}`);
    }

    /**
     * Utility method to delay execution
     * 
     * @param {number} ms - Delay in milliseconds
     * @returns {Promise<void>}
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Check API health by sending a test request
     * 
     * @returns {Promise<boolean>} True if API is healthy
     */
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