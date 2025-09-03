import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { createLogger } from '../utils/logger.js';

const logger = createLogger('Security');

export function configureHelmet(app) {
    app.use(helmet({
        contentSecurityPolicy: {
            directives: {
                defaultSrc: ["'self'"],
                styleSrc: ["'self'", "'unsafe-inline'"],
                scriptSrc: ["'self'"],
                imgSrc: ["'self'", "data:", "https:"]
            }
        },
        crossOriginEmbedderPolicy: false
    }));
    
    logger.info('Helmet security middleware configured');
}

export function configureRateLimit(app) {
    const generalLimiter = rateLimit({
        windowMs: 15 * 60 * 1000,
        max: 100,
        message: {
            success: false,
            error: 'Too many requests from this IP, please try again later',
            retryAfter: '15 minutes'
        },
        standardHeaders: true,
        legacyHeaders: false,
        handler: (req, res) => {
            logger.warn(`Rate limit exceeded for IP: ${req.ip}`);
            res.status(429).json({
                success: false,
                error: 'Too many requests',
                retryAfter: '15 minutes'
            });
        }
    });

    const chatLimiter = rateLimit({
        windowMs: 10 * 60 * 1000,
        max: 20,
        message: {
            success: false,
            error: 'Too many chat requests, please slow down',
            retryAfter: '10 minutes'
        },
        standardHeaders: true,
        legacyHeaders: false,
        handler: (req, res) => {
            logger.warn(`Chat rate limit exceeded for IP: ${req.ip}`);
            res.status(429).json({
                success: false,
                error: 'Too many chat requests',
                retryAfter: '10 minutes'
            });
        }
    });

    app.use(generalLimiter);
    
    app.use('/api/v1/agent/chat', chatLimiter);
    
    logger.info('Rate limiting middleware configured');
}

export function validateApiKey(req, res, next) {
    const apiKey = req.headers['x-api-key'];
    
    if (!apiKey) {
        return res.status(401).json({
            success: false,
            error: 'API key required'
        });
    }
    
    const validApiKeys = process.env.API_KEYS?.split(',') || [];
    
    if (!validApiKeys.includes(apiKey)) {
        logger.warn(`Invalid API key attempt from IP: ${req.ip}`);
        return res.status(401).json({
            success: false,
            error: 'Invalid API key'
        });
    }
    
    next();
}