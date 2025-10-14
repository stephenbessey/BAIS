import { validationResult } from 'express-validator';
import { OllamaService } from '../services/ollama-service.js';
import { PromptService } from '../services/prompt-service.js';
import { createLogger } from '../utils/logger.js';

const logger = createLogger('AgentController');

export class AgentController {
    constructor() {
        this.ollamaService = new OllamaService();
        this.promptService = new PromptService();
        // Universal AI router will be initialized when needed
        this.universalAIRouter = null;
    }

    async processChat(req, res, next) {
        try {
            const errors = validationResult(req);
            if (!errors.isEmpty()) {
                return this.sendValidationError(res, errors.array());
            }

            const { prompt, businessType, requestType, userPreferences, aiProvider, model } = req.body;
            
            logger.info(`Processing BAIS agent request for business type: ${businessType} with provider: ${aiProvider || 'auto'}`);
            
            // Try universal AI router first, fallback to Ollama
            let response;
            try {
                if (this.universalAIRouter) {
                    response = await this.universalAIRouter.processRequest({
                        prompt,
                        businessType,
                        requestType,
                        userPreferences,
                        provider: aiProvider,
                        model
                    });
                } else {
                    // Fallback to Ollama service
                    const baisPrompt = this.promptService.buildBAISPrompt({
                        prompt,
                        businessType,
                        requestType,
                        userPreferences
                    });
                    response = await this.ollamaService.sendChatMessage(baisPrompt);
                }
            } catch (aiError) {
                logger.warn(`Universal AI router failed, falling back to Ollama: ${aiError.message}`);
                const baisPrompt = this.promptService.buildBAISPrompt({
                    prompt,
                    businessType,
                    requestType,
                    userPreferences
                });
                response = await this.ollamaService.sendChatMessage(baisPrompt);
            }
            
            this.sendSuccessResponse(res, {
                response: response.content,
                metadata: {
                    model: response.model || response.model_used,
                    businessType,
                    requestType,
                    processingTime: response.total_duration,
                    aiProvider: response.ai_provider || 'ollama',
                    timestamp: new Date().toISOString()
                }
            });
            
        } catch (error) {
            logger.error('Agent chat processing failed:', error.message);
            next(error);
        }
    }

    async getStatus(req, res, next) {
        try {
            const isOllamaAvailable = await this.ollamaService.isAvailable();
            const ollamaStatus = this.ollamaService.getStatus();
            
            this.sendSuccessResponse(res, {
                status: 'operational',
                ollama: {
                    available: isOllamaAvailable,
                    ...ollamaStatus
                },
                api: {
                    version: '1.0.0',
                    environment: process.env.NODE_ENV || 'development'
                },
                timestamp: new Date().toISOString()
            });
            
        } catch (error) {
            logger.error('Status check failed:', error.message);
            next(error);
        }
    }

    async listModels(req, res, next) {
        try {
            const models = await this.ollamaService.listModels();
            
            this.sendSuccessResponse(res, {
                models: models.map(model => ({
                    name: model.name,
                    size: model.size,
                    modified_at: model.modified_at
                })),
                count: models.length,
                timestamp: new Date().toISOString()
            });
            
        } catch (error) {
            logger.error('Failed to list models:', error.message);
            next(error);
        }
    }

    async checkHealth(req, res, next) {
        try {
            const isOllamaAvailable = await this.ollamaService.isAvailable();
            
            const healthStatus = {
                status: isOllamaAvailable ? 'healthy' : 'degraded',
                services: {
                    api: 'healthy',
                    ollama: isOllamaAvailable ? 'healthy' : 'unhealthy'
                },
                timestamp: new Date().toISOString()
            };
            
            const statusCode = isOllamaAvailable ? 200 : 503;
            res.status(statusCode).json({
                success: isOllamaAvailable,
                data: healthStatus
            });
            
        } catch (error) {
            logger.error('Health check failed:', error.message);
            next(error);
        }
    }

    sendSuccessResponse(res, data) {
        res.json({
            success: true,
            data
        });
    }

    sendValidationError(res, errors) {
        res.status(400).json({
            success: false,
            error: 'Validation failed',
            details: errors.map(error => ({
                field: error.param,
                message: error.msg,
                value: error.value
            }))
        });
    }
}

const agentController = new AgentController();

export const processChat = (req, res, next) => agentController.processChat(req, res, next);
export const getStatus = (req, res, next) => agentController.getStatus(req, res, next);
export const listModels = (req, res, next) => agentController.listModels(req, res, next);
export const checkHealth = (req, res, next) => agentController.checkHealth(req, res, next);