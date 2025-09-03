import { VALIDATION_MESSAGES } from '../config/constants.js';
import { isValidBusinessType } from '../data/business-registry.js';

export class FormValidator {
    constructor(domElements) {
        this.dom = domElements;
    }

    validateAgentRequest() {
        const validationChecks = [
            this.validateBusinessSelection,
            this.validateRequestType,
            this.validateSpecificRequest
        ];

        for (const check of validationChecks) {
            const result = check.call(this);
            if (!result.isValid) {
                return result;
            }
        }

        return this.createValidationResult(true);
    }

    validateBusinessSelection() {
        const businessType = this.getBusinessType();
        
        if (!businessType) {
            return this.createValidationResult(false, VALIDATION_MESSAGES.MISSING_BUSINESS);
        }

        if (!isValidBusinessType(businessType)) {
            return this.createValidationResult(false, VALIDATION_MESSAGES.INVALID_BUSINESS_TYPE);
        }

        return this.createValidationResult(true);
    }

    validateRequestType() {
        const requestType = this.getRequestType();
        
        if (!requestType) {
            return this.createValidationResult(false, VALIDATION_MESSAGES.MISSING_REQUEST_TYPE);
        }

        return this.createValidationResult(true);
    }

    validateSpecificRequest() {
        const specificRequest = this.getSpecificRequest();
        
        if (!specificRequest || specificRequest.trim().length === 0) {
            return this.createValidationResult(false, VALIDATION_MESSAGES.MISSING_DETAILS);
        }

        if (specificRequest.trim().length > 0 && specificRequest.trim().length < 10) {
            return this.createValidationResult(false, 'Please provide more detailed request information (at least 10 characters)');
        }

        return this.createValidationResult(true);
    }

    createValidationResult(isValid, errorMessage = '') {
        return {
            isValid,
            errorMessage
        };
    }

    getValidatedFormData() {
        return {
            businessType: this.getBusinessType(),
            requestType: this.getRequestType(),
            userPreferences: this.getUserPreferences(),
            specificRequest: this.getSpecificRequest()
        };
    }

    getBusinessType() {
        return this.dom.businessSelect.value.trim();
    }

    getRequestType() {
        return this.dom.requestType.value.trim();
    }

    getUserPreferences() {
        return this.dom.userPreferences.value.trim();
    }

    getSpecificRequest() {
        return this.dom.specificRequest.value.trim();
    }

    hasUserInput() {
        const formData = this.getValidatedFormData();
        return Object.values(formData).some(value => value && value.length > 0);
    }

    clearForm() {
        this.dom.businessSelect.value = '';
        this.dom.requestType.value = '';
        this.dom.userPreferences.value = '';
        this.dom.specificRequest.value = '';
    }

    setFormData(formData) {
        if (formData.businessType) {
            this.dom.businessSelect.value = formData.businessType;
        }
        if (formData.requestType) {
            this.dom.requestType.value = formData.requestType;
        }
        if (formData.userPreferences) {
            this.dom.userPreferences.value = formData.userPreferences;
        }
        if (formData.specificRequest) {
            this.dom.specificRequest.value = formData.specificRequest;
        }
    }

    validateField(fieldName) {
        switch (fieldName) {
            case 'businessType':
                return this.validateBusinessSelection();
            case 'requestType':
                return this.validateRequestType();
            case 'specificRequest':
                return this.validateSpecificRequest();
            default:
                return this.createValidationResult(true);
        }
    }
}