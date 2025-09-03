import { Ollama } from 'ollama';
import { createLogger } from '../utils/logger.js';

const logger = createLogger('OllamaService');

export class OllamaService {
    constructor() {
        this.client = new Ollama({
            host: process.env.OLLAMA_HOST || 'http://golem:11434'
        });
        this.defaultModel = process.env.OLLAMA_MODEL || 'gpt-oss:120b';
        this.defaultOptions = {
            stream: false,
            temperature: 0.7,
            top_p: 0.9
        };
    }

    async sendChatMessage(prompt, options = {}) {
        this.validatePrompt(prompt);
        
        const requestConfig = this.buildRequestConfig(prompt, options);
        
        try {
            logger.info(`Sending request to Ollama model: ${requestConfig.model}`);
            const startTime = Date.now();
            
            const response = await this.client.chat(requestConfig);
            
            const duration = Date.now() - startTime;
            logger.info(`Ollama response received in ${duration}ms`);
            
            return this.processResponse(response);
            
        } catch (error) {
            logger.error('Ollama request failed:', error.message);
            throw this.handleOllamaError(error);
        }
    }

    validatePrompt(prompt) {
        if (!prompt || typeof prompt !== 'string') {
            throw new Error('Prompt is required and must be a string');
        }
        
        if (prompt.trim().length === 0) {
            throw new Error('Prompt cannot be empty');
        }
        
        if (prompt.length > 50000) {
            throw new Error('Prompt is too long (maximum 50,000 characters)');
        }
    }

    buildRequestConfig(prompt, options) {
        return {
            model: options.model || this.defaultModel,
            messages: [
                {
                    role: 'user',
                    content: prompt.trim()
                }
            ],
            stream: false,
            options: {
                temperature: options.temperature || this.defaultOptions.temperature,
                top_p: options.top_p || this.defaultOptions.top_p,
                ...options.modelOptions
            }
        };
    }

    processResponse(response) {
        if (!response) {
            throw new Error('No response received from Ollama');
        }

        const content = this.extractContent(response);
        
        return {
            success: true,
            content: content,
            model: response.model,
            created_at: response.created_at,
            done: response.done,
            total_duration: response.total_duration,
            load_duration: response.load_duration,
            prompt_eval_duration: response.prompt_eval_duration,
            eval_duration: response.eval_duration
        };
    }

    extractContent(response) {
        if (response.message && response.message.content) {
            return response.message.content;
        }
        
        if (response.response) {
            return response.response;
        }
        
        if (response.content) {
            return response.content;
        }
        
        logger.warn('Unknown response format from Ollama:', Object.keys(response));
        throw new Error('Could not extract content from Ollama response');
    }

    handleOllamaError(error) {
        if (error.message.includes('connection refused')) {
            return new Error('Ollama service is not running. Please start Ollama.');
        }
        
        if (error.message.includes('model not found')) {
            return new Error(`Model ${this.defaultModel} not found. Please pull the model first.`);
        }
        
        if (error.message.includes('timeout')) {
            return new Error('Request timed out. The model may be busy or the prompt too complex.');
        }
        
        if (error.code === 'ECONNRESET') {
            return new Error('Connection to Ollama was reset. Please try again.');
        }
        
        return new Error(`Ollama service error: ${error.message}`);
    }

    async isAvailable() {
        try {
            await this.client.list();
            return true;
        } catch (error) {
            logger.warn('Ollama health check failed:', error.message);
            return false;
        }
    }

    async listModels() {
        try {
            const response = await this.client.list();
            return response.models || [];
        } catch (error) {
            logger.error('Failed to list models:', error.message);
            throw this.handleOllamaError(error);
        }
    }

    getStatus() {
        return {
            host: this.client.config?.host || 'Unknown',
            defaultModel: this.defaultModel,
            defaultOptions: this.defaultOptions,
            timestamp: new Date().toISOString()
        };
    }
}