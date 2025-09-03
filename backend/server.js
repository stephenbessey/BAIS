import app from './src/app.js';
import { createLogger } from './src/utils/logger.js';

const logger = createLogger('Server');
const PORT = process.env.PORT || 3001;

function startServer() {
    try {
        app.listen(PORT, () => {
            logger.info(`BAIS API Server running on port ${PORT}`);
            logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
            logger.info('Ready to accept requests from BAIS frontend');
        });
    } catch (error) {
        logger.error('Failed to start server:', error);
        process.exit(1);
    }
}

function setupGracefulShutdown() {
    const shutdownHandler = (signal) => {
        logger.info(`Received ${signal}. Starting graceful shutdown...`);
        
        setTimeout(() => {
            logger.info('Server shut down successfully');
            process.exit(0);
        }, 5000);
    };

    process.on('SIGTERM', () => shutdownHandler('SIGTERM'));
    process.on('SIGINT', () => shutdownHandler('SIGINT'));
}

function setupErrorHandlers() {
    process.on('uncaughtException', (error) => {
        logger.error('Uncaught Exception:', error);
        process.exit(1);
    });

    process.on('unhandledRejection', (reason, promise) => {
        logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
        process.exit(1);
    });
}

setupErrorHandlers();
setupGracefulShutdown();
startServer();