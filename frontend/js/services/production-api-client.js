export const PRODUCTION_API_CONFIG = {
    BASE_URL: process.env.NODE_ENV === 'production' 
        ? 'https://api.baintegrate.com/api/v1' 
        : 'http://localhost:8000/api/v1',
    OAUTH_URL: process.env.NODE_ENV === 'production'
        ? 'https://auth.baintegrate.com/oauth'
        : 'http://localhost:8003/oauth',
    TIMEOUT: 30000,
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000
};

// Business Registration Service
export class BusinessRegistrationService {
    constructor() {
        this.apiClient = new ProductionAPIClient();
    }

    async registerBusiness(businessData) {
        const registrationRequest = {
            business_name: businessData.name,
            business_type: businessData.type,
            contact_info: {
                website: businessData.website,
                phone: businessData.phone,
                email: businessData.email
            },
            location: {
                address: businessData.address,
                city: businessData.city,
                state: businessData.state,
                postal_code: businessData.postalCode,
                country: businessData.country || 'US'
            },
            services_config: businessData.services.map(service => ({
                id: service.id,
                name: service.name,
                description: service.description,
                category: service.category,
                workflow_pattern: service.workflowPattern || 'booking_confirmation_payment',
                parameters: service.parameters || {}
            }))
        };

        try {
            const response = await this.apiClient.post('/businesses', registrationRequest);
            return {
                success: true,
                data: response.data,
                businessId: response.data.business_id,
                apiKey: response.data.api_keys.primary,
                mcpEndpoint: response.data.mcp_endpoint,
                a2aEndpoint: response.data.a2a_endpoint
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                details: error.response?.data
            };
        }
    }

    async getBusinessStatus(businessId, apiKey) {
        try {
            const response = await this.apiClient.get(`/businesses/${businessId}`, {
                headers: { 'Authorization': `Bearer ${apiKey}` }
            });
            
            return {
                success: true,
                data: response.data
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async validateSchema(schemaData) {
        try {
            const response = await this.apiClient.post('/schemas/validate', {
                schema_data: schemaData
            });
            
            return {
                success: true,
                isValid: response.data.is_valid,
                issues: response.data.issues,
                warnings: response.data.warnings || []
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
}

// Production API Client with OAuth 2.0 Support
export class ProductionAPIClient {
    constructor() {
        this.baseURL = PRODUCTION_API_CONFIG.BASE_URL;
        this.oauthURL = PRODUCTION_API_CONFIG.OAUTH_URL;
        this.accessToken = localStorage.getItem('bais_access_token');
        this.refreshToken = localStorage.getItem('bais_refresh_token');
    }

    async authenticate(clientId, clientSecret, scope = 'read search book') {
        try {
            const response = await fetch(`${this.oauthURL}/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    grant_type: 'client_credentials',
                    client_id: clientId,
                    client_secret: clientSecret,
                    scope: scope
                })
            });

            if (!response.ok) {
                throw new Error(`Authentication failed: ${response.status}`);
            }

            const tokenData = await response.json();
            
            this.accessToken = tokenData.access_token;
            this.refreshToken = tokenData.refresh_token;
            
            // Store tokens securely
            localStorage.setItem('bais_access_token', this.accessToken);
            if (this.refreshToken) {
                localStorage.setItem('bais_refresh_token', this.refreshToken);
            }

            return {
                success: true,
                accessToken: this.accessToken,
                expiresIn: tokenData.expires_in,
                scope: tokenData.scope
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async refreshAccessToken() {
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }

        try {
            const response = await fetch(`${this.oauthURL}/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    grant_type: 'refresh_token',
                    refresh_token: this.refreshToken,
                    client_id: 'bais_ai_agent',  // Should be configurable
                    client_secret: 'bais_agent_secret_2024'  // Should be from env
                })
            });

            if (!response.ok) {
                throw new Error(`Token refresh failed: ${response.status}`);
            }

            const tokenData = await response.json();
            
            this.accessToken = tokenData.access_token;
            localStorage.setItem('bais_access_token', this.accessToken);

            return tokenData;
        } catch (error) {
            // Clear tokens on refresh failure
            this.clearTokens();
            throw error;
        }
    }

    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        localStorage.removeItem('bais_access_token');
        localStorage.removeItem('bais_refresh_token');
    }

    async makeRequest(method, endpoint, data = null, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Add authorization header if we have a token
        if (this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }

        const config = {
            method,
            headers,
            ...options
        };

        if (data && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
            config.body = JSON.stringify(data);
        }

        try {
            let response = await fetch(url, config);

            // Handle token expiration
            if (response.status === 401 && this.refreshToken) {
                await this.refreshAccessToken();
                headers['Authorization'] = `Bearer ${this.accessToken}`;
                config.headers = headers;
                response = await fetch(url, config);
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            throw new Error(`API request failed: ${error.message}`);
        }
    }

    async get(endpoint, options = {}) {
        return this.makeRequest('GET', endpoint, null, options);
    }

    async post(endpoint, data, options = {}) {
        return this.makeRequest('POST', endpoint, data, options);
    }

    async put(endpoint, data, options = {}) {
        return this.makeRequest('PUT', endpoint, data, options);
    }

    async delete(endpoint, options = {}) {
        return this.makeRequest('DELETE', endpoint, null, options);
    }
}

// Agent Interaction Service
export class AgentInteractionService {
    constructor() {
        this.apiClient = new ProductionAPIClient();
    }

    async processAgentRequest(businessId, interactionData) {
        const requestPayload = {
            business_id: businessId,
            agent_id: interactionData.agentId || 'web-interface-agent',
            interaction_type: interactionData.type,
            parameters: {
                service_id: interactionData.serviceId,
                ...interactionData.parameters
            }
        };

        try {
            const response = await this.apiClient.post('/agents/interact', requestPayload);
            
            return {
                success: true,
                interactionId: response.data.interaction_id,
                status: response.data.status,
                responseData: response.data.response_data,
                processingTime: response.data.processing_time_ms
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async searchServices(businessId, searchParams) {
        return this.processAgentRequest(businessId, {
            type: 'search',
            serviceId: searchParams.serviceId || 'room_booking',
            parameters: searchParams
        });
    }

    async createBooking(businessId, bookingParams) {
        return this.processAgentRequest(businessId, {
            type: 'book',
            serviceId: bookingParams.serviceId || 'room_booking',
            parameters: bookingParams
        });
    }

    async getBusinessInfo(businessId) {
        return this.processAgentRequest(businessId, {
            type: 'info',
            parameters: {}
        });
    }
}

// Business Discovery Service
export class BusinessDiscoveryService {
    constructor() {
        this.apiClient = new ProductionAPIClient();
    }

    async discoverAgents() {
        try {
            const response = await this.apiClient.get('/a2a/discover');
            
            return {
                success: true,
                agents: response.data.agents,
                totalFound: response.data.total_found,
                discoveryTimestamp: response.data.discovery_timestamp
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async getBusinessesByType(businessType) {
        const discovery = await this.discoverAgents();
        if (!discovery.success) {
            return discovery;
        }

        const filteredAgents = discovery.agents.filter(
            agent => agent.business_type === businessType
        );

        return {
            success: true,
            businesses: filteredAgents,
            totalFound: filteredAgents.length
        };
    }
}

// Updated Business Management Component
export class BusinessManagementComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.registrationService = new BusinessRegistrationService();
        this.interactionService = new AgentInteractionService();
        this.discoveryService = new BusinessDiscoveryService();
        
        this.currentBusiness = null;
        this.apiKey = localStorage.getItem('bais_business_api_key');
        
        this.init();
    }

    init() {
        this.render();
        this.setupEventListeners();
        this.loadExistingBusiness();
    }

    render() {
        this.container.innerHTML = `
            <div class="bais-business-management">
                <div class="header">
                    <h1>BAIS Business Management Portal</h1>
                    <p>Manage your business integration with the AI agent ecosystem</p>
                </div>

                <div class="tabs">
                    <button class="tab-button active" data-tab="registration">Business Registration</button>
                    <button class="tab-button" data-tab="status">Status & Monitoring</button>
                    <button class="tab-button" data-tab="testing">Agent Testing</button>
                    <button class="tab-button" data-tab="discovery">Agent Discovery</button>
                </div>

                <div class="tab-content">
                    <div id="registration-tab" class="tab-panel active">
                        ${this.renderRegistrationPanel()}
                    </div>
                    
                    <div id="status-tab" class="tab-panel">
                        ${this.renderStatusPanel()}
                    </div>
                    
                    <div id="testing-tab" class="tab-panel">
                        ${this.renderTestingPanel()}
                    </div>
                    
                    <div id="discovery-tab" class="tab-panel">
                        ${this.renderDiscoveryPanel()}
                    </div>
                </div>

                <div id="notifications" class="notifications"></div>
            </div>
        `;
    }

    renderRegistrationPanel() {
        return `
            <div class="registration-panel">
                <h2>Register Your Business with BAIS</h2>
                
                <form id="business-registration-form" class="registration-form">
                    <div class="form-section">
                        <h3>Business Information</h3>
                        
                        <div class="form-group">
                            <label for="business-name">Business Name *</label>
                            <input type="text" id="business-name" name="name" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="business-type">Business Type *</label>
                            <select id="business-type" name="type" required>
                                <option value="">Select business type...</option>
                                <option value="hospitality">Hospitality</option>
                                <option value="food_service">Food Service</option>
                                <option value="retail">Retail</option>
                                <option value="healthcare">Healthcare</option>
                                <option value="finance">Finance</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="business-website">Website</label>
                            <input type="url" id="business-website" name="website">
                        </div>
                    </div>

                    <div class="form-section">
                        <h3>Location</h3>
                        
                        <div class="form-group">
                            <label for="business-address">Address *</label>
                            <input type="text" id="business-address" name="address" required>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="business-city">City *</label>
                                <input type="text" id="business-city" name="city" required>
                            </div>
                            
                            <div class="form-group">
                                <label for="business-state">State *</label>
                                <input type="text" id="business-state" name="state" required>
                            </div>
                            
                            <div class="form-group">
                                <label for="business-postal-code">Postal Code</label>
                                <input type="text" id="business-postal-code" name="postalCode">
                            </div>
                        </div>
                    </div>

                    <div class="form-section">
                        <h3>Contact Information</h3>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="business-email">Email *</label>
                                <input type="email" id="business-email" name="email" required>
                            </div>
                            
                            <div class="form-group">
                                <label for="business-phone">Phone</label>
                                <input type="tel" id="business-phone" name="phone">
                            </div>
                        </div>
                    </div>

                    <div class="form-section">
                        <h3>Services</h3>
                        
                        <div id="services-container">
                            <div class="service-config">
                                <div class="form-group">
                                    <label>Service Name *</label>
                                    <input type="text" name="services[0][name]" placeholder="e.g., Room Booking" required>
                                </div>
                                
                                <div class="form-group">
                                    <label>Service ID *</label>
                                    <input type="text" name="services[0][id]" placeholder="e.g., room_booking" required>
                                </div>
                                
                                <div class="form-group">
                                    <label>Description</label>
                                    <textarea name="services[0][description]" rows="2" placeholder="Brief service description"></textarea>
                                </div>
                            </div>
                        </div>
                        
                        <button type="button" id="add-service" class="btn-secondary">Add Another Service</button>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn-primary" id="register-business">Register Business</button>
                        <button type="button" class="btn-secondary" id="validate-schema">Validate Schema First</button>
                    </div>
                </form>
            </div>
        `;
    }

    renderStatusPanel() {
        return `
            <div class="status-panel">
                <h2>Business Status & Monitoring</h2>
                
                <div id="business-status" class="status-cards">
                    <div class="status-card">
                        <h3>Integration Status</h3>
                        <div id="integration-status" class="status-value">Loading...</div>
                    </div>
                    
                    <div class="status-card">
                        <h3>Services Active</h3>
                        <div id="services-count" class="status-value">-</div>
                    </div>
                    
                    <div class="status-card">
                        <h3>MCP Server</h3>
                        <div id="mcp-status" class="status-value">-</div>
                    </div>
                    
                    <div class="status-card">
                        <h3>A2A Server</h3>
                        <div id="a2a-status" class="status-value">-</div>
                    </div>
                </div>

                <div class="metrics-section">
                    <h3>Recent Metrics</h3>
                    <div id="business-metrics" class="metrics-grid">
                        <!-- Metrics will be populated dynamically -->
                    </div>
                </div>

                <div class="endpoints-section">
                    <h3>Integration Endpoints</h3>
                    <div id="integration-endpoints" class="endpoints-list">
                        <!-- Endpoints will be populated dynamically -->
                    </div>
                </div>
            </div>
        `;
    }

    renderTestingPanel() {
        return `
            <div class="testing-panel">
                <h2>Agent Interaction Testing</h2>
                
                <div class="test-configuration">
                    <div class="form-group">
                        <label for="test-business-id">Business ID</label>
                        <input type="text" id="test-business-id" placeholder="Enter business ID">
                    </div>
                    
                    <div class="form-group">
                        <label for="test-interaction-type">Interaction Type</label>
                        <select id="test-interaction-type">
                            <option value="search">Search Services</option>
                            <option value="book">Create Booking</option>
                            <option value="info">Get Business Info</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="test-parameters">Parameters (JSON)</label>
                        <textarea id="test-parameters" rows="6" placeholder='{"check_in": "2024-03-15", "check_out": "2024-03-17", "guests": 2}'></textarea>
                    </div>
                    
                    <button id="run-test" class="btn-primary">Run Test</button>
                </div>

                <div id="test-results" class="test-results">
                    <h3>Test Results</h3>
                    <div id="test-output" class="test-output">
                        Run a test to see results here...
                    </div>
                </div>
            </div>
        `;
    }

    renderDiscoveryPanel() {
        return `
            <div class="discovery-panel">
                <h2>Agent Discovery</h2>
                
                <div class="discovery-controls">
                    <button id="discover-agents" class="btn-primary">Discover Available Agents</button>
                    
                    <div class="filter-controls">
                        <label for="filter-business-type">Filter by Business Type:</label>
                        <select id="filter-business-type">
                            <option value="">All Types</option>
                            <option value="hospitality">Hospitality</option>
                            <option value="food_service">Food Service</option>
                            <option value="retail">Retail</option>
                        </select>
                    </div>
                </div>

                <div id="discovered-agents" class="agents-grid">
                    <!-- Discovered agents will be displayed here -->
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        // Tab switching
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('tab-button')) {
                this.switchTab(e.target.dataset.tab);
            }
        });

        // Business registration
        const registrationForm = this.container.querySelector('#business-registration-form');
        if (registrationForm) {
            registrationForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleBusinessRegistration();
            });
        }

        // Test agent interaction
        const runTestButton = this.container.querySelector('#run-test');
        if (runTestButton) {
            runTestButton.addEventListener('click', () => {
                this.runAgentTest();
            });
        }

        // Discover agents
        const discoverButton = this.container.querySelector('#discover-agents');
        if (discoverButton) {
            discoverButton.addEventListener('click', () => {
                this.discoverAgents();
            });
        }

        // Add service button
        const addServiceButton = this.container.querySelector('#add-service');
        if (addServiceButton) {
            addServiceButton.addEventListener('click', () => {
                this.addServiceField();
            });
        }
    }

    switchTab(tabName) {
        // Update tab buttons
        this.container.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        this.container.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab panels
        this.container.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        this.container.querySelector(`#${tabName}-tab`).classList.add('active');

        // Load tab-specific data
        if (tabName === 'status') {
            this.loadBusinessStatus();
        } else if (tabName === 'discovery') {
            this.loadDiscoveredAgents();
        }
    }

    async handleBusinessRegistration() {
        const formData = new FormData(this.container.querySelector('#business-registration-form'));
        const businessData = Object.fromEntries(formData.entries());

        // Parse services data
        businessData.services = this.parseServicesFromForm();

        try {
            this.showNotification('Registering business...', 'info');
            
            const result = await this.registrationService.registerBusiness(businessData);
            
            if (result.success) {
                this.currentBusiness = result.data;
                this.apiKey = result.apiKey;
                localStorage.setItem('bais_business_api_key', this.apiKey);
                localStorage.setItem('bais_business_id', result.businessId);
                
                this.showNotification('Business registered successfully!', 'success');
                this.switchTab('status');
            } else {
                this.showNotification(`Registration failed: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Registration error: ${error.message}`, 'error');
        }
    }

    parseServicesFromForm() {
        const services = [];
        const serviceElements = this.container.querySelectorAll('.service-config');
        
        serviceElements.forEach((element, index) => {
            const nameInput = element.querySelector(`input[name="services[${index}][name]"]`);
            const idInput = element.querySelector(`input[name="services[${index}][id]"]`);
            const descInput = element.querySelector(`textarea[name="services[${index}][description]"]`);
            
            if (nameInput?.value && idInput?.value) {
                services.push({
                    name: nameInput.value,
                    id: idInput.value,
                    description: descInput?.value || '',
                    category: 'general'
                });
            }
        });
        
        return services;
    }

    async loadBusinessStatus() {
        const businessId = localStorage.getItem('bais_business_id');
        if (!businessId || !this.apiKey) {
            this.showNotification('No business registered', 'warning');
            return;
        }

        try {
            const result = await this.registrationService.getBusinessStatus(businessId, this.apiKey);
            
            if (result.success) {
                this.updateStatusDisplay(result.data);
            } else {
                this.showNotification(`Failed to load status: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Status error: ${error.message}`, 'error');
        }
    }

    updateStatusDisplay(businessData) {
        const statusElements = {
            integrationStatus: this.container.querySelector('#integration-status'),
            servicesCount: this.container.querySelector('#services-count'),
            mcpStatus: this.container.querySelector('#mcp-status'),
            a2aStatus: this.container.querySelector('#a2a-status')
        };

        if (statusElements.integrationStatus) {
            statusElements.integrationStatus.textContent = businessData.status;
            statusElements.integrationStatus.className = `status-value status-${businessData.status}`;
        }

        if (statusElements.servicesCount) {
            statusElements.servicesCount.textContent = businessData.services_enabled;
        }

        if (statusElements.mcpStatus) {
            statusElements.mcpStatus.textContent = businessData.mcp_server_active ? 'Active' : 'Inactive';
            statusElements.mcpStatus.className = `status-value ${businessData.mcp_server_active ? 'status-active' : 'status-inactive'}`;
        }

        if (statusElements.a2aStatus) {
            statusElements.a2aStatus.textContent = businessData.a2a_server_active ? 'Active' : 'Inactive';
            statusElements.a2aStatus.className = `status-value ${businessData.a2a_server_active ? 'status-active' : 'status-inactive'}`;
        }

        // Update metrics
        this.updateMetricsDisplay(businessData.metrics);
    }

    updateMetricsDisplay(metrics) {
        const metricsContainer = this.container.querySelector('#business-metrics');
        if (!metricsContainer || !metrics) return;

        metricsContainer.innerHTML = `
            <div class="metric-item">
                <label>Total Interactions</label>
                <value>${metrics.total_interactions || 0}</value>
            </div>
            <div class="metric-item">
                <label>Successful Bookings</label>
                <value>${metrics.successful_bookings || 0}</value>
            </div>
            <div class="metric-item">
                <label>Revenue Today</label>
                <value>$${(metrics.revenue_today || 0).toFixed(2)}</value>
            </div>
            <div class="metric-item">
                <label>Avg Response Time</label>
                <value>${metrics.avg_response_time_ms || 0}ms</value>
            </div>
        `;
    }

    async runAgentTest() {
        const businessId = this.container.querySelector('#test-business-id').value || localStorage.getItem('bais_business_id');
        const interactionType = this.container.querySelector('#test-interaction-type').value;
        const parametersText = this.container.querySelector('#test-parameters').value;

        if (!businessId) {
            this.showNotification('Business ID required for testing', 'warning');
            return;
        }

        let parameters = {};
        try {
            parameters = parametersText ? JSON.parse(parametersText) : {};
        } catch (error) {
            this.showNotification('Invalid JSON in parameters', 'error');
            return;
        }

        try {
            this.showNotification('Running agent test...', 'info');
            
            const result = await this.interactionService.processAgentRequest(businessId, {
                type: interactionType,
                parameters: parameters
            });

            this.displayTestResults(result);
            
            if (result.success) {
                this.showNotification('Test completed successfully', 'success');
            } else {
                this.showNotification(`Test failed: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Test error: ${error.message}`, 'error');
        }
    }

    displayTestResults(result) {
        const outputElement = this.container.querySelector('#test-output');
        if (!outputElement) return;

        outputElement.innerHTML = `
            <div class="test-result ${result.success ? 'success' : 'error'}">
                <h4>Test Result: ${result.success ? 'SUCCESS' : 'FAILED'}</h4>
                
                ${result.success ? `
                    <div class="result-details">
                        <p><strong>Interaction ID:</strong> ${result.interactionId}</p>
                        <p><strong>Status:</strong> ${result.status}</p>
                        <p><strong>Processing Time:</strong> ${result.processingTime}ms</p>
                        
                        <div class="response-data">
                            <h5>Response Data:</h5>
                            <pre>${JSON.stringify(result.responseData, null, 2)}</pre>
                        </div>
                    </div>
                ` : `
                    <div class="error-details">
                        <p><strong>Error:</strong> ${result.error}</p>
                    </div>
                `}
            </div>
        `;
    }

    async discoverAgents() {
        try {
            this.showNotification('Discovering agents...', 'info');
            
            const result = await this.discoveryService.discoverAgents();
            
            if (result.success) {
                this.displayDiscoveredAgents(result.agents);
                this.showNotification(`Found ${result.totalFound} agents`, 'success');
            } else {
                this.showNotification(`Discovery failed: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Discovery error: ${error.message}`, 'error');
        }
    }

    displayDiscoveredAgents(agents) {
        const agentsContainer = this.container.querySelector('#discovered-agents');
        if (!agentsContainer) return;

        agentsContainer.innerHTML = agents.map(agent => `
            <div class="agent-card">
                <h4>${agent.business_name}</h4>
                <p class="business-type">${agent.business_type}</p>
                <p class="location">${agent.location.city}, ${agent.location.state}</p>
                
                <div class="capabilities">
                    <strong>Capabilities:</strong>
                    <ul>
                        ${agent.capabilities.map(cap => `<li>${cap}</li>`).join('')}
                    </ul>
                </div>
                
                <div class="endpoints">
                    <a href="${agent.agent_card_url}" target="_blank" class="btn-secondary">View Agent Card</a>
                </div>
            </div>
        `).join('');
    }

    addServiceField() {
        const servicesContainer = this.container.querySelector('#services-container');
        const serviceCount = servicesContainer.querySelectorAll('.service-config').length;
        
        const serviceDiv = document.createElement('div');
        serviceDiv.className = 'service-config';
        serviceDiv.innerHTML = `
            <div class="form-group">
                <label>Service Name *</label>
                <input type="text" name="services[${serviceCount}][name]" required>
            </div>
            
            <div class="form-group">
                <label>Service ID *</label>
                <input type="text" name="services[${serviceCount}][id]" required>
            </div>
            
            <div class="form-group">
                <label>Description</label>
                <textarea name="services[${serviceCount}][description]" rows="2"></textarea>
            </div>
            
            <button type="button" class="remove-service btn-danger">Remove</button>
        `;
        
        servicesContainer.appendChild(serviceDiv);
        
        // Add remove functionality
        serviceDiv.querySelector('.remove-service').addEventListener('click', () => {
            serviceDiv.remove();
        });
    }

    async loadExistingBusiness() {
        const businessId = localStorage.getItem('bais_business_id');
        if (businessId && this.apiKey) {
            await this.loadBusinessStatus();
        }
    }

    showNotification(message, type = 'info') {
        const notificationsContainer = this.container.querySelector('#notifications');
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        notificationsContainer.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize the business management interface
document.addEventListener('DOMContentLoaded', () => {
    const managementInterface = new BusinessManagementComponent('business-management-container');
});

// Export for module use
export { BusinessManagementComponent, ProductionAPIClient, BusinessRegistrationService, AgentInteractionService, BusinessDiscoveryService };