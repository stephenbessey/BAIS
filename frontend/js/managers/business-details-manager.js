import { getBusinessByType, isValidBusinessType } from '../data/business-registry.js';
import { BAIS_CONFIG } from '../config/constants.js';

export class BusinessDetailsManager {
    constructor(domElements) {
        this.dom = domElements;
    }

    updateBusinessDetails(selectedBusinessType) {
        if (this.isValidBusinessSelection(selectedBusinessType)) {
            this.displayBusinessDetails(selectedBusinessType);
        } else {
            this.hideBusinessDetails();
        }
    }

    isValidBusinessSelection(businessType) {
        return isValidBusinessType(businessType);
    }

    displayBusinessDetails(businessType) {
        const businessData = getBusinessByType(businessType);
        if (!businessData) {
            console.error(`Business data not found for type: ${businessType}`);
            this.hideBusinessDetails();
            return;
        }

        this.populateBusinessFields(businessData);
        this.showBusinessDetailsContainer();
    }

    populateBusinessFields(businessData) {
        this.dom.serviceType.textContent = businessData.serviceType;
        this.dom.location.textContent = this.formatLocation(businessData.businessInfo.location);
        this.dom.services.textContent = businessData.services;
        this.dom.baisVersion.textContent = BAIS_CONFIG.VERSION;
    }

    formatLocation(location) {
        if (location.city && location.state) {
            return `${location.city}, ${location.state}`;
        }
        return location.address || 'Location not specified';
    }

    showBusinessDetailsContainer() {
        this.dom.businessDetails.style.display = 'block';
        this.addShowAnimation();
    }

    hideBusinessDetails() {
        this.dom.businessDetails.style.display = 'none';
        this.clearBusinessFields();
    }

    clearBusinessFields() {
        this.dom.serviceType.textContent = '-';
        this.dom.location.textContent = '-';
        this.dom.services.textContent = '-';
        this.dom.baisVersion.textContent = BAIS_CONFIG.VERSION;
    }

    addShowAnimation() {
        this.dom.businessDetails.style.opacity = '0';
        this.dom.businessDetails.style.transform = 'translateY(-10px)';

        this.dom.businessDetails.offsetHeight;
        
        this.dom.businessDetails.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        this.dom.businessDetails.style.opacity = '1';
        this.dom.businessDetails.style.transform = 'translateY(0)';
    }

    getCurrentBusinessInfo() {
        const selectedType = this.dom.businessSelect.value;
        return selectedType ? getBusinessByType(selectedType) : null;
    }

    isOperationSupported(operation) {
        const currentBusiness = this.getCurrentBusinessInfo();
        return currentBusiness && 
               currentBusiness.availableOperations && 
               currentBusiness.availableOperations.includes(operation);
    }

    getAvailableOperations() {
        const currentBusiness = this.getCurrentBusinessInfo();
        return currentBusiness ? currentBusiness.availableOperations || [] : [];
    }
}