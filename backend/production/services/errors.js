export class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ValidationError';
    }
}

export class BusinessNotFoundError extends Error {
    constructor(businessType) {
        super(`Business type not found: ${businessType}`);
        this.name = 'BusinessNotFoundError';
    }
}