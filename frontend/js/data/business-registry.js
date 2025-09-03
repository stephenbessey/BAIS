import { BUSINESS_TYPES } from '../../frontend/js/config/constants.js';

export const BUSINESS_REGISTRY = {
    [BUSINESS_TYPES.HOTEL]: {
        businessInfo: {
            name: 'Zion Adventure Lodge',
            type: 'hospitality',
            location: {
                address: '123 Canyon View Dr, Springdale, UT',
                city: 'Springdale',
                state: 'UT',
                coordinates: [37.1889, -112.9856]
            }
        },
        serviceType: 'Hospitality',
        services: 'Rooms, Restaurant, Activities',
        availableOperations: ['search', 'book', 'modify', 'cancel'],
        baisCompliant: true
    },
    
    [BUSINESS_TYPES.RESTAURANT]: {
        businessInfo: {
            name: 'Red Canyon Brewing',
            type: 'food_service',
            location: {
                address: '456 Brewery Lane, Springdale, UT',
                city: 'Springdale',
                state: 'UT',
                coordinates: [37.1901, -112.9834]
            }
        },
        serviceType: 'Food Service',
        services: 'Dining, Catering, Events',
        availableOperations: ['search', 'book', 'modify', 'cancel'],
        baisCompliant: true
    },
    
    [BUSINESS_TYPES.RETAIL]: {
        businessInfo: {
            name: 'Desert Pearl Gifts',
            type: 'retail',
            location: {
                address: '789 Merchant Square, Springdale, UT',
                city: 'Springdale',
                state: 'UT',
                coordinates: [37.1876, -112.9845]
            }
        },
        serviceType: 'Retail',
        services: 'Gifts, Souvenirs, Local Crafts',
        availableOperations: ['search', 'book'],
        baisCompliant: true
    }
};

export function getBusinessByType(businessType) {
    return BUSINESS_REGISTRY[businessType] || null;
}

export function isValidBusinessType(businessType) {
    return businessType && BUSINESS_REGISTRY.hasOwnProperty(businessType);
}

export function getAllBusinessTypes() {
    return Object.keys(BUSINESS_REGISTRY);
}

export function getBusinessDisplayName(businessType) {
    const business = getBusinessByType(businessType);
    return business ? business.businessInfo.name : '';
}