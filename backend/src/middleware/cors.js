import cors from 'cors';
import { createLogger } from '../utils/logger.js';

const logger = createLogger('CORS');

const corsOptions = {
    origin: function (origin, callback) {
        const allowedOrigins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:8080',
            'http://127.0.0.1:8080',
            process.env.FRONTEND_URL
        ].filter(Boolean);

        if (!origin) {
            return callback(null, true);
        }

        if (allowedOrigins.indexOf(origin) !== -1) {
            callback(null, true);
        } else {
            logger.warn(`CORS blocked request from origin: ${origin}`);
            callback(new Error('Not allowed by CORS policy'));
        }
    },
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: [
        'Content-Type',
        'Authorization',
        'X-Requested-With',
        'Accept',
        'Origin'
    ],
    credentials: false,
    maxAge: 86400
};

export function configureCors(app) {
    app.use(cors(corsOptions));
    
    app.options('*', cors(corsOptions));
    
    logger.info('CORS middleware configured');
}