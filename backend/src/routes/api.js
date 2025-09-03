import express from 'express';
import { body } from 'express-validator';
import { processChat, getStatus, listModels, checkHealth } from '../controllers/agent-controller.js';

const router = express.Router();

const chatValidationRules = [
    body('prompt')
        .isString()
        .isLength({ min: 1, max: 50000 })
        .withMessage('Prompt must be between 1 and 50,000 characters'),
    
    body('businessType')
        .isIn(['hotel', 'restaurant', 'retail'])
        .withMessage('Business type must be hotel, restaurant, or retail'),
    
    body('requestType')
        .isIn(['search', 'book', 'modify', 'cancel'])
        .withMessage('Request type must be search, book, modify, or cancel'),
    
    body('userPreferences')
        .optional()
        .isString()
        .isLength({ max: 5000 })
        .withMessage('User preferences must be less than 5,000 characters')
];


router.post('/agent/chat', chatValidationRules, processChat);

router.get('/agent/status', getStatus);

router.get('/agent/models', listModels);

router.get('/agent/health', checkHealth);

router.get('/', (req, res) => {
    res.json({
        success: true,
        data: {
            service: 'BAIS API Server',
            version: '1.0.0',
            description: 'Business-Agent Integration Standard API',
            endpoints: {
                'POST /agent/chat': 'Process BAIS agent requests',
                'GET /agent/status': 'Get service status',
                'GET /agent/models': 'List available models',
                'GET /agent/health': 'Health check'
            },
            documentation: 'https://github.com/stephenbessey/BAIS',
            timestamp: new Date().toISOString()
        }
    });
});

export default router;