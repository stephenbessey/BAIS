import express from 'express';
import dotenv from 'dotenv';
import { configureCors } from './middleware/cors.js';
import { configureHelmet } from './middleware/auth.js';
import { configureRateLimit } from './middleware/auth.js';
import { errorHandler } from './middleware/error-handler.js';
import apiRoutes from './routes/api.js';
import { createLogger } from './utils/logger.js';

dotenv.config();

const logger = createLogger('App');
const app = express();

function configureMiddleware() {
    configureHelmet(app);
    configureCors(app);
    configureRateLimit(app);
    
    app.use(express.json({ limit: '10mb' }));
    app.use(express.urlencoded({ extended: true, limit: '10mb' }));
    
    app.use((req, res, next) => {
        logger.info(`${req.method} ${req.path} - ${req.ip}`);
        next();
    });
}

function configureRoutes() {
    app.get('/health', (req, res) => {
        res.json({
            status: 'healthy',
            timestamp: new Date().toISOString(),
            service: 'BAIS API Server'
        });
    });
    
    app.use('/api/v1', apiRoutes);
    
    app.use('*', (req, res) => {
        res.status(404).json({
            success: false,
            error: 'API endpoint not found',
            path: req.originalUrl
        });
    });
}

function configureErrorHandling() {
    app.use(errorHandler);
}

function initializeApp() {
    try {
        configureMiddleware();
        configureRoutes();
        configureErrorHandling();
        
        logger.info('BAIS API application configured successfully');
    } catch (error) {
        logger.error('Failed to initialize application:', error);
        throw error;
    }
}

initializeApp();

export default app;