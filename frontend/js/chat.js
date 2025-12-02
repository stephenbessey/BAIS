const API_BASE_URL = window.location.origin;
const CHAT_ENDPOINT = `${API_BASE_URL}/api/v1/chat/message`;
const CONFIG_STORAGE_KEY = 'baisChatConfig';
const MAX_TEXTAREA_HEIGHT = 120;
const NOTIFICATION_DURATION = 3000;
const LOADING_DOTS_COUNT = 3;
const DEFAULT_OLLAMA_HOST = 'http://golem:11434';
const DEFAULT_OLLAMA_MODEL = 'gpt-oss:120b';

let messages = [];
let isProcessing = false;

const configPanel = document.getElementById('configPanel');
const settingsButton = document.getElementById('settingsButton');
const closeConfigBtn = document.getElementById('closeConfigBtn');
const saveConfigBtn = document.getElementById('saveConfigBtn');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const statusText = document.getElementById('statusText');
const apiStatus = document.getElementById('apiStatus');
const ollamaHostInput = document.getElementById('ollamaHost');
const ollamaModelInput = document.getElementById('ollamaModel');

document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadConfiguration();
    checkApiStatus();
    injectNotificationStyles();
});

function initializeEventListeners() {
    settingsButton.addEventListener('click', toggleSettings);
    closeConfigBtn.addEventListener('click', toggleSettings);
    saveConfigBtn.addEventListener('click', handleSaveConfig);
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', handleInputKeydown);
    messageInput.addEventListener('input', handleInputResize);
    attachExampleQueryListeners();
}

function toggleSettings() {
    const isVisible = configPanel.style.display !== 'none';
    configPanel.style.display = isVisible ? 'none' : 'block';
}

function handleSaveConfig() {
    saveConfiguration();
    showNotification('Settings saved');
    toggleSettings();
}

function handleInputKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function handleInputResize() {
    messageInput.style.height = 'auto';
    messageInput.style.height = `${Math.min(messageInput.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
}

function attachExampleQueryListeners() {
    document.querySelectorAll('.example-queries li').forEach(li => {
        li.addEventListener('click', () => {
            messageInput.value = li.textContent.trim();
            messageInput.focus();
        });
    });
}

function loadConfiguration() {
    const saved = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!saved) {
        ollamaHostInput.value = DEFAULT_OLLAMA_HOST;
        ollamaModelInput.value = DEFAULT_OLLAMA_MODEL;
        return;
    }
    
    try {
        const config = JSON.parse(saved);
        ollamaHostInput.value = config.ollamaHost || DEFAULT_OLLAMA_HOST;
        ollamaModelInput.value = config.ollamaModel || DEFAULT_OLLAMA_MODEL;
    } catch (e) {
        console.error('Error loading configuration:', e);
        ollamaHostInput.value = DEFAULT_OLLAMA_HOST;
        ollamaModelInput.value = DEFAULT_OLLAMA_MODEL;
    }
}

function saveConfiguration() {
    const config = {
        ollamaHost: ollamaHostInput.value.trim() || DEFAULT_OLLAMA_HOST,
        ollamaModel: ollamaModelInput.value.trim() || DEFAULT_OLLAMA_MODEL
    };
    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isProcessing) return;
    
    const ollamaHost = ollamaHostInput.value.trim() || DEFAULT_OLLAMA_HOST;
    const ollamaModel = ollamaModelInput.value.trim() || DEFAULT_OLLAMA_MODEL;
    
    if (!ollamaHost || !ollamaModel) {
        showNotification('Please configure Ollama settings', 'error');
        toggleSettings();
        return;
    }
    
    addMessage('user', message);
    clearInput();
    
    const loadingId = addLoadingIndicator();
    setProcessingState(true);
    
    try {
        const response = await fetchChatResponse(ollamaHost, ollamaModel);
        removeLoadingIndicator(loadingId);
        
        if (!response.ok) {
            throw await createErrorFromResponse(response);
        }
        
        const data = await response.json();
        addMessage('assistant', data.message, data.tool_calls);
        statusText.textContent = '';
    } catch (error) {
        removeLoadingIndicator(loadingId);
        const errorMessage = formatErrorMessage(error.message);
        addMessage('assistant', errorMessage, null, true);
        statusText.textContent = '';
        console.error('Chat error:', error);
    } finally {
        setProcessingState(false);
    }
}

function formatErrorMessage(errorMessage) {
    if (errorMessage.includes('Connection refused') || errorMessage.includes('Failed to establish')) {
        return 'Unable to connect to Ollama server. Please check your settings and ensure the server is running and accessible.';
    }
    if (errorMessage.includes('Max retries exceeded')) {
        return 'Connection to Ollama server timed out. Please verify the host address and network connection.';
    }
    return `Error: ${errorMessage}`;
}

function clearInput() {
    messageInput.value = '';
    messageInput.style.height = 'auto';
}

function setProcessingState(processing) {
    isProcessing = processing;
    sendButton.disabled = processing;
    statusText.textContent = processing ? 'Processing' : '';
}

async function fetchChatResponse(ollamaHost, ollamaModel) {
    const requestBody = {
        model: 'ollama',
        messages: messages.map(msg => ({
            role: msg.role,
            content: msg.content
        })),
        ollama_host: ollamaHost,
        ollama_model_name: ollamaModel
    };
    
    return fetch(CHAT_ENDPOINT, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
    });
}

async function createErrorFromResponse(response) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    return new Error(error.detail || `HTTP ${response.status}`);
}

function addMessage(role, content, toolCalls = null, isError = false) {
    removeWelcomeMessage();
    messages.push({ role, content });
    
    const messageDiv = createMessageElement(role, content, toolCalls, isError);
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function removeWelcomeMessage() {
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
}

function createMessageElement(role, content, toolCalls, isError) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}${isError ? ' error' : ''}`;
    
    const avatar = createAvatar(role);
    const messageContent = createMessageContent(role, content, toolCalls, isError);
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);
    
    return messageDiv;
}

function createAvatar(role) {
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'U' : 'AI';
    avatar.setAttribute('aria-label', role === 'user' ? 'User' : 'Assistant');
    return avatar;
}

function createMessageContent(role, content, toolCalls, isError) {
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    const messageHeader = createMessageHeader(role);
    const messageText = createMessageText(content, isError);
    
    messageContent.appendChild(messageHeader);
    messageContent.appendChild(messageText);
    
    if (toolCalls && toolCalls.length > 0 && role === 'assistant') {
        toolCalls.forEach(toolCall => {
            messageContent.appendChild(createToolCallElement(toolCall));
        });
    }
    
    return messageContent;
}

function createMessageHeader(role) {
    const messageHeader = document.createElement('div');
    messageHeader.className = 'message-header';
    
    const roleSpan = document.createElement('span');
    roleSpan.className = 'message-role';
    roleSpan.textContent = role === 'user' ? 'You' : 'Assistant';
    
    const timeSpan = document.createElement('span');
    timeSpan.className = 'message-time';
    timeSpan.textContent = new Date().toLocaleTimeString();
    
    messageHeader.appendChild(roleSpan);
    messageHeader.appendChild(timeSpan);
    
    return messageHeader;
}

function createMessageText(content, isError) {
    const messageText = document.createElement('div');
    messageText.className = 'message-text';
    
    if (isError) {
        messageText.style.background = '#fee';
        messageText.style.color = '#c33';
        messageText.textContent = content;
    } else {
        if (typeof marked !== 'undefined') {
            messageText.innerHTML = marked.parse(content);
        } else {
            messageText.textContent = content;
        }
    }
    
    return messageText;
}

function createToolCallElement(toolCall) {
    const toolCallDiv = document.createElement('div');
    toolCallDiv.className = 'tool-call';
    
    const toolHeader = document.createElement('div');
    toolHeader.className = 'tool-call-header';
    toolHeader.textContent = `Used: ${toolCall.name}`;
    toolHeader.addEventListener('click', () => {
        toolCallDiv.classList.toggle('expanded');
    });
    
    const toolDetails = document.createElement('div');
    toolDetails.className = 'tool-call-details';
    toolDetails.textContent = JSON.stringify(toolCall.input, null, 2);
    
    toolCallDiv.appendChild(toolHeader);
    toolCallDiv.appendChild(toolDetails);
    
    return toolCallDiv;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addLoadingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = `loading-${Date.now()}`;
    
    const avatar = createAvatar('assistant');
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-indicator';
    
    for (let i = 0; i < LOADING_DOTS_COUNT; i++) {
        const dot = document.createElement('div');
        dot.className = 'loading-dot';
        loadingDiv.appendChild(dot);
    }
    
    messageContent.appendChild(loadingDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
    
    return messageDiv.id;
}

function removeLoadingIndicator(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

async function checkApiStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/llm-webhooks/health`);
        if (response.ok) {
            apiStatus.textContent = 'Connected';
            apiStatus.className = 'api-status';
        } else {
            throw new Error('API not available');
        }
    } catch (error) {
        apiStatus.textContent = 'Disconnected';
        apiStatus.className = 'api-status error';
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const bgColor = type === 'error' ? 'var(--color-error)' : 'var(--color-success)';
    
    notification.style.cssText = `
        position: fixed;
        top: 24px;
        right: 24px;
        background: ${bgColor};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1000;
        font-size: 14px;
        font-weight: 500;
        max-width: 400px;
        animation: slideInRight 0.3s ease-out;
    `;
    
    notification.textContent = message;
    notification.setAttribute('role', 'alert');
    notification.setAttribute('aria-live', 'polite');
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, NOTIFICATION_DURATION);
}

function injectNotificationStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}
