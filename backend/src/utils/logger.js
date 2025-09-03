import winston from 'winston';

export function createLogger(label) {
    return winston.createLogger({
        level: process.env.LOG_LEVEL || 'info',
        format: winston.format.combine(
            winston.format.timestamp(),
            winston.format.label({ label }),
            winston.format.errors({ stack: true }),
            winston.format.json()
        ),
        defaultMeta: { service: 'bais-api' },
        transports: [
            new winston.transports.Console({
                format: winston.format.combine(
                    winston.format.colorize(),
                    winston.format.timestamp({ format: 'HH:mm:ss' }),
                    winston.format.printf(({ timestamp, level, label, message, ...meta }) => {
                        let output = `${timestamp} [${label}] ${level}: ${message}`;
                        
                        if (Object.keys(meta).length > 0) {
                            output += ` ${JSON.stringify(meta, null, 2)}`;
                        }
                        
                        return output;
                    })
                )
            })
        ]
    });
}

if (process.env.NODE_ENV === 'production') {
    const loggers = winston.loggers;
    
    loggers.add('default', {
        transports: [
            new winston.transports.File({
                filename: 'logs/error.log',
                level: 'error',
                maxsize: 5242880,
                maxFiles: 5
            }),
            new winston.transports.File({
                filename: 'logs/combined.log',
                maxsize: 5242880,
                maxFiles: 5
            })
        ]
    });
}