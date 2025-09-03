import { UI_STATES } from '../config/constants.js';

export class UIStateManager {
    constructor(domElements) {
        this.dom = domElements;
        this.currentState = UI_STATES.IDLE;
    }

    showLoadingState() {
        this.currentState = UI_STATES.LOADING;
        this.disableTestButton();
        this.showLoadingIndicator();
        this.hideResults();
        this.clearErrorMessage();
    }

    showResultsState() {
        this.currentState = UI_STATES.SUCCESS;
        this.enableTestButton();
        this.hideLoadingIndicator();
        this.showResults();
    }

    showErrorState() {
        this.currentState = UI_STATES.ERROR;
        this.enableTestButton();
        this.hideLoadingIndicator();
        this.showResults();
    }

    showIdleState() {
        this.currentState = UI_STATES.IDLE;
        this.enableTestButton();
        this.hideLoadingIndicator();
        this.hideResults();
        this.clearErrorMessage();
    }

    displayAgentResponse(responseContent) {
        this.dom.agentResponse.textContent = responseContent;
        this.showResultsState();
    }

    displayErrorMessage(errorMessage) {
        const errorElement = this.createErrorElement(errorMessage);
        this.dom.errorContainer.innerHTML = '';
        this.dom.errorContainer.appendChild(errorElement);
        this.showErrorState();
    }

    createErrorElement(errorMessage) {
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.textContent = errorMessage;
        return errorElement;
    }

    clearErrorMessage() {
        this.dom.errorContainer.innerHTML = '';
    }

    disableTestButton() {
        this.dom.testButton.disabled = true;
        this.dom.testButton.textContent = 'Processing...';
    }

    enableTestButton() {
        this.dom.testButton.disabled = false;
        this.dom.testButton.textContent = 'Test Agent Integration';
    }

    showLoadingIndicator() {
        this.dom.loading.classList.add('active');
    }

    hideLoadingIndicator() {
        this.dom.loading.classList.remove('active');
    }

    showResults() {
        this.dom.results.classList.add('active');
        this.scrollToResults();
    }

    hideResults() {
        this.dom.results.classList.remove('active');
    }

    scrollToResults() {
        setTimeout(() => {
            this.dom.results.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }, 100);
    }

    getCurrentState() {
        return this.currentState;
    }

    isLoading() {
        return this.currentState === UI_STATES.LOADING;
    }

    isReadyForRequest() {
        return this.currentState === UI_STATES.IDLE || 
               this.currentState === UI_STATES.SUCCESS || 
               this.currentState === UI_STATES.ERROR;
    }

    displaySuccessMessage(message) {
        const successElement = document.createElement('div');
        successElement.className = 'success-message';
        successElement.textContent = message;
        successElement.style.cssText = `
            color: #27ae60;
            background: #d5f4e6;
            border: 1px solid #27ae60;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 14px;
        `;
        
        this.dom.errorContainer.innerHTML = '';
        this.dom.errorContainer.appendChild(successElement);
    }

    updateButtonText(text) {
        this.dom.testButton.textContent = text;
    }

    reset() {
        this.showIdleState();
        this.dom.agentResponse.textContent = '';
        this.updateButtonText('Test Agent Integration');
    }
}