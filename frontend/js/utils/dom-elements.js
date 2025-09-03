export class DOMElements {
    constructor() {
        this.initializeElements();
    }

    initializeElements() {
        this.businessSelect = this.getRequiredElement('businessSelect');
        this.requestType = this.getRequiredElement('requestType');
        this.userPreferences = this.getRequiredElement('userPreferences');
        this.specificRequest = this.getRequiredElement('specificRequest');
        
        this.testButton = this.getRequiredElement('testButton');
        this.loading = this.getRequiredElement('loading');
        
        this.results = this.getRequiredElement('results');
        this.agentResponse = this.getRequiredElement('agentResponse');
        this.errorContainer = this.getRequiredElement('errorContainer');
        
        this.businessDetails = this.getRequiredElement('businessDetails');
        this.serviceType = this.getRequiredElement('serviceType');
        this.location = this.getRequiredElement('location');
        this.services = this.getRequiredElement('services');
        this.baisVersion = this.getRequiredElement('baisVersion');
    }

    getRequiredElement(elementId) {
        const element = document.getElementById(elementId);
        if (!element) {
            throw new Error(`Required DOM element not found: ${elementId}`);
        }
        return element;
    }

    validateElements() {
        try {
            const elementProperties = Object.getOwnPropertyNames(this);
            return elementProperties.every(prop => {
                const element = this[prop];
                return element instanceof HTMLElement && 
                       document.contains(element);
            });
        } catch (error) {
            console.error('DOM validation error:', error);
            return false;
        }
    }
 
    refresh() {
        this.initializeElements();
    }
}