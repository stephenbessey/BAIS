import { DOMElements } from './utils/dom-elements.js';
import { BusinessDetailsManager } from './managers/business-details-manager.js';
import { FormValidator } from './managers/form-validator.js';
import { UIStateManager } from './managers/ui-state-manager.js';
import { BAISPromptBuilder } from './services/prompt-builder.js';
import { BAISApiClient } from './services/api-client.js';

export class BAISTestingInterface {
    constructor() {
        this.initializeComponents();
        this.initializeEventHandlers();
        this.performInitialSetup();
    }

    initializeComponents() {
        try {
            this.dom = new DOMElements();
            this.businessDetailsManager = new BusinessDetailsManager(this.dom);
            this.formValidator = new FormValidator(this.dom);
            this.uiManager = new UIStateManager(this.dom);
            this.promptBuilder = new BAISPromptBuilder();
            this.apiClient = new BAISApiClient();
        } catch (error) {
            console.error('Failed to initialize components:', error);
            this.handleInitializationError(error);
        }
    }

    initializeEventHandlers() {
        this.dom.businessSelect.addEventListener('change', (event) => {
            this.handleBusinessSelectionChange(event.target.value);
        });

        this.dom.testButton.addEventListener('click', () => {
            this.handleAgentTestRequest();
        });

        this.dom.specificRequest.addEventListener('blur', () => {
            if (this.dom.specificRequest.value.trim().length > 0) {
                this.handleFieldValidation('specificRequest');
            }
        });

        this.dom.specificRequest.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && event.ctrlKey) {
                this.handleAgentTestRequest();
            }
        });
    }

    performInitialSetup() {
        this.uiManager.showIdleState();
        console.log('BAIS Testing Interface initialized successfully');
    }

    handleBusinessSelectionChange(selectedBusinessType) {
        try {
            this.businessDetailsManager.updateBusinessDetails(selectedBusinessType);
        } catch (error) {
            console.error('Error updating business details:', error);
            this.uiManager.displayErrorMessage('Failed to load business details');
        }
    }

    async handleAgentTestRequest() {
        if (!this.uiManager.isReadyForRequest()) {
            return;
        }

        const validationResult = this.validateRequest();
        if (!validationResult.isValid) {
            this.uiManager.displayErrorMessage(validationResult.errorMessage);
            return;
        }

        await this.processAgentRequest();
    }

    validateRequest() {
        try {
            return this.formValidator.validateAgentRequest();
        } catch (error) {
            console.error('Validation error:', error);
            return {
                isValid: false,
                errorMessage: 'Form validation failed'
            };
        }
    }

    async processAgentRequest() {
        this.uiManager.showLoadingState();

        try {
            const formData = this.formValidator.getValidatedFormData();
            const agentPrompt = this.promptBuilder.buildAgentPrompt(formData);
            const apiResponse = await this.apiClient.sendAgentRequest(agentPrompt, formData);
            const responseContent = this.apiClient.extractResponseContent(apiResponse);
            
            this.uiManager.displayAgentResponse(responseContent);
            
        } catch (error) {
            console.error('Agent request failed:', error);
            const errorMessage = this.buildUserFriendlyErrorMessage(error);
            this.uiManager.displayErrorMessage(errorMessage);
            
        } finally {
            if (!this.uiManager.getCurrentState() === 'success') {
                this.uiManager.showErrorState();
            }
        }
    }

    handleFieldValidation(fieldName) {
        try {
            const validationResult = this.formValidator.validateField(fieldName);
            if (!validationResult.isValid) {
                console.warn(`Validation warning for ${fieldName}:`, validationResult.errorMessage);
            }
        } catch (error) {
            console.error(`Field validation error for ${fieldName}:`, error);
        }
    }

    buildUserFriendlyErrorMessage(error) {
        const baseMessage = error.message || 'An unexpected error occurred';
        
        return `${baseMessage}\n\nThis demonstrates how BAIS would handle error scenarios and provide fallback responses to maintain user experience.`;
    }

    handleInitializationError(error) {
        const errorMessage = `Application failed to initialize: ${error.message}`;
        console.error(errorMessage);
        
        const container = document.querySelector('.container');
        if (container) {
            container.innerHTML = `
                <div style="background: #f8d7da; color: #721c24; padding: 20px; border-radius: 8px; margin: 20px;">
                    <h3>Initialization Error</h3>
                    <p>${errorMessage}</p>
                    <p>Please refresh the page and try again.</p>
                </div>
            `;
        }
    }

    getApplicationState() {
        return {
            uiState: this.uiManager.getCurrentState(),
            hasUserInput: this.formValidator.hasUserInput(),
            currentBusiness: this.businessDetailsManager.getCurrentBusinessInfo(),
            timestamp: new Date().toISOString()
        };
    }

    reset() {
        this.formValidator.clearForm();
        this.businessDetailsManager.hideBusinessDetails();
        this.uiManager.reset();
    }

    healthCheck() {
        const results = {
            dom: false,
            api: false,
            components: false
        };

        try {
            results.dom = this.dom.validateElements();
            
            results.apiCheck = this.apiClient.checkApiHealth();
            
            results.components = !!(this.businessDetailsManager && 
                                  this.formValidator && 
                                  this.uiManager && 
                                  this.promptBuilder);
            
        } catch (error) {
            console.error('Health check failed:', error);
        }

        return results;
    }
}

function initializeApplication() {
    try {
        new BAISTestingInterface();
    } catch (error) {
        console.error('Failed to start BAIS Testing Interface:', error);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApplication);
} else {
    initializeApplication();
}