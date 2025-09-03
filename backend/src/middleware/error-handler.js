import { createLogger } from '../utils/logger.js';

const logger = createLogger('ErrorHandler');

export function errorHandler(error, req, res, next) {
    logger.error(`Error in ${req.method} ${req.path}:`, {
        message: error.message,
        stack: error.stack,
        ip: req.ip,
        userAgent: req.get('User-Agent')
    });

    const errorResponse = categorizeError(error);
    
    res.status(errorResponse.statusCode).json({
        success: false,
        error: errorResponse.message,
        ...(process.env.NODE_ENV === 'development' && {
            details: error.message,
            stack: error.stack
        })
    });
}

function categorizeError(error) {
    if (error.name === 'ValidationError') {
        return {
            statusCode: 400,
            message: 'Validation failed'
        };
    }

    if (error.message.includes('Ollama service')) {
        return {
            statusCode: 503,
            message: 'AI service temporarily unavailable'
        };
    }

    if (error.message.includes('model not found')) {
        return {
            statusCode: 503,
            message: 'AI model not available'
        };
    }

    if (error.message.includes('connection refused')) {
        return {
            statusCode: 503,
            message: 'AI service is not running'
        };
    }

    if (error.message.includes('timeout')) {
        return {
            statusCode: 504,
            message: 'Request timed out - please try again'
        };
    }

    if (error.statusCode === 429) {
        return {
            statusCode: 429,
            message: 'Too many requests - please slow down'
        };
    }

    if (error.statusCode === 401) {
        return {
            statusCode: 401,
            message: 'Authentication required'
        };
    }

    if (error.statusCode === 403) {
        return {
            statusCode: 403,
            message: 'Access denied'
        };
    }

    if (error.statusCode === 404) {
        return {
            statusCode: 404,
            message: 'Resource not found'
        };
    }

    if (error.message.includes('required field') || 
        error.message.includes('invalid') ||
        error.message.includes('must be')) {
        return {
            statusCode: 400,
            message: 'Invalid request data'
        };
    }

    if (error.code === 'ECONNREFUSED' && error.port) {
        return {
            statusCode: 503,
            message: 'Database service unavailable'
        };
    }

    if (error.code === 'ENOTFOUND' || error.code === 'ECONNRESET') {
        return {
            statusCode: 503,
            message: 'External service unavailable'
        };
    }

    return {
        statusCode: 500,
        message: 'Internal server error'
    };
}

export function notFoundHandler(req, res) {
    logger.warn(`404 - Route not found: ${req.method} ${req.path} from ${req.ip}`);
    
    res.status(404).json({
        success: false,
        error: 'API endpoint not found',
        path: req.originalUrl,
        method: req.method
    });
}

export function asyncHandler(fn) {
    return (req, res, next) => {
        Promise.resolve(fn(req, res, next)).catch(next);
    };
}