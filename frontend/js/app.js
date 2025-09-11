import { DOMElements } from './utils/dom-elements.js';
import { BusinessDetailsManager } from './managers/business-details-manager.js';
import { FormValidator } from './managers/form-validator.js';
import { UIStateManager } from './managers/ui-state-manager.js';
import { BAISPromptBuilder } from './services/prompt-builder.js';
import { BAISApiClient } from './services/api-client.js';

export class BAISTestingInterface {
    constructor(
        dom,
        businessDetailsManager,
        formValidator,
        uiManager,
        promptBuilder,
        apiClient
    ) {
        this.dom = dom;
        this.businessDetailsManager = businessDetailsManager;
        this.formValidator = formValidator;
        this.uiManager = uiManager;
        this.promptBuilder = promptBuilder;
        this.apiClient = apiClient;

        this.initializeEventHandlers();
        this.performInitialSetup();
    }

    initializeEventHandlers() {
        // ... same as before
    }

    // ... rest of the class is the same
}

function initializeApplication() {
    try {
        const dom = new DOMElements();
        const businessDetailsManager = new BusinessDetailsManager(dom);
        const formValidator = new FormValidator(dom);
        const uiManager = new UIStateManager(dom);
        const promptBuilder = new BAISPromptBuilder();
        const apiClient = new BAISApiClient();

        new BAISTestingInterface(
            dom,
            businessDetailsManager,
            formValidator,
            uiManager,
            promptBuilder,
            apiClient
        );
    } catch (error) {
        console.error('Failed to start BAIS Testing Interface:', error);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApplication);
} else {
    initializeApplication();
}