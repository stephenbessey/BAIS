export const API_CONFIG = {
    BASE_URL: 'http://localhost:3001/api/v1/agent/chat',
    STATUS_URL: 'http://localhost:3001/api/v1/agent/status',
    HEALTH_URL: 'http://localhost:3001/api/v1/agent/health',
    TIMEOUT: 240000,
    MAX_RETRIES: 2,
    RETRY_DELAY: 2000
};

export const BAIS_CONFIG = {
    VERSION: '1.0',
    PROTOCOL_NAME: 'Business-Agent Integration Standard'
};

export const VALIDATION_MESSAGES = {
    MISSING_BUSINESS: 'Please select a business service',
    MISSING_REQUEST_TYPE: 'Please select a request type',
    MISSING_DETAILS: 'Please provide specific request details',
    INVALID_BUSINESS_TYPE: 'Invalid business type selected'
};

export const ERROR_MESSAGES = {
    API_FAILURE: 'Failed to communicate with AI agent service',
    NETWORK_ERROR: 'Network connection error. Please check your internet connection',
    TIMEOUT_ERROR: 'Request timed out. The AI model may be busy processing other requests',
    UNEXPECTED_ERROR: 'An unexpected error occurred',
    SERVER_ERROR: 'Server error on the AI service. Please try again in a few moments',
    CLIENT_ERROR: 'Request error. Please check your input and try again'
};

export const UI_STATES = {
    LOADING: 'loading',
    IDLE: 'idle',
    ERROR: 'error',
    SUCCESS: 'success'
};

export const BUSINESS_TYPES = {
    HOTEL: 'hotel',
    RESTAURANT: 'restaurant',
    RETAIL: 'retail'
};

export const REQUEST_TYPES = {
    SEARCH: 'search',
    BOOK: 'book',
    MODIFY: 'modify',
    CANCEL: 'cancel'
};