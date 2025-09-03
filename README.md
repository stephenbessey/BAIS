# BAIS Testing Interface - Full Stack Application

A clean, modular full-stack application for testing Business-Agent Integration Standard (BAIS) protocols with AI agents through Express.js API and Ollama.

**Architecture: Frontend → Express API → Ollama.js → Language Model**

## 🚀 Quick Start

### **1. Prerequisites**
- **Node.js 18+** 
- **Ollama** installed and running
- **Python 3** (for frontend server)

### **2. Install Ollama and Model**
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull the required model
ollama pull gpt-oss:120b
```

### **3. Backend Setup**
```bash
# Navigate to backend directory
cd backend

# Install dependencies
npm install

# Create environment file
cp .env.example .env
# Edit .env if needed (default values should work for local development)

# Start development server
npm run dev
```
Backend will run on `http://localhost:3001`

### **4. Frontend Setup**
```bash
# In a new terminal, navigate to frontend directory
cd frontend

# Start static file server (choose one option)

# Option A: Python 3
python -m http.server 3000

# Option B: Python 2
python -m SimpleHTTPServer 3000

# Option C: Node.js serve
npx serve . -p 3000

# Option D: VS Code Live Server
# Right-click index.html → "Open with Live Server"
```
Frontend will run on `http://localhost:3000`

### **5. Test the Application**
1. Open `http://localhost:3000` in your browser
2. Select "Zion Adventure Lodge (Hotel)"
3. Choose "Search Available Services"
4. Enter: "Looking for a room for 2 guests from Dec 15-17 with mountain views"
5. Click "Test Agent Integration"

## 📁 Project Structure

```
bais-testing-interface/
├── frontend/                    # Static frontend files
│   ├── assets/styles.css       # Application styles
│   ├── js/                     # JavaScript modules
│   │   ├── config/constants.js # Configuration
│   │   ├── services/           # API communication
│   │   ├── managers/           # Business logic
│   │   └── utils/              # Utilities
│   └── index.html              # Entry point
├── backend/                    # Express.js API server
│   ├── src/
│   │   ├── controllers/        # Request handlers
│   │   ├── services/           # Business services
│   │   ├── middleware/         # Express middleware
│   │   ├── routes/             # API routes
│   │   └── utils/              # Utilities
│   ├── server.js               # Server entry point
│   └── package.json            # Dependencies
└── README.md                   # This file
```

## 🏗️ Clean Architecture

### **Layer Separation**
- **Frontend**: UI logic and user interaction only
- **Express API**: Business logic, validation, and orchestration
- **Ollama Service**: Clean interface to AI language model
- **Ollama.js**: Official Ollama client library

### **Single Responsibility Classes**
- `OllamaService`: Handles all Ollama communication
- `PromptService`: Constructs BAIS-specific prompts
- `AgentController`: Manages HTTP request/response
- `ErrorHandler`: Centralized error processing

### **Dependency Inversion**
- Frontend depends on API contracts, not implementation
- API depends on service interfaces, not concrete implementations
- Easy to swap Ollama for other LLM providers

## 🔧 API Endpoints

### **POST** `/api/v1/agent/chat`
Process BAIS agent requests
```json
{
  "prompt": "Looking for a hotel room",
  "businessType": "hotel",
  "requestType": "search",
  "userPreferences": "Mountain view preferred"
}
```

### **GET** `/api/v1/agent/status`
Get service status and configuration

### **GET** `/api/v1/agent/health` 
Health check endpoint

### **GET** `/api/v1/agent/models`
List available Ollama models

## 🛡️ Security Features

- **Helmet.js**: Security headers
- **CORS**: Configured for frontend origins
- **Rate Limiting**: 100 requests/15min general, 20 chat requests/10min
- **Input Validation**: Server-side validation with express-validator
- **Error Handling**: Secure error messages that don't leak information

## 🧪 Development

### **Backend Development**
```bash
cd backend

# Development with auto-restart
npm run dev

# Run tests (when implemented)
npm test

# Lint code
npm run lint

# Format code
npm run format
```

### **Frontend Development**
The frontend uses vanilla JavaScript ES6 modules. Any static file server will work for development.

### **Environment Variables**
Configure backend behavior in `backend/.env`:
```env
NODE_ENV=development
PORT=3001
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gpt-oss:120b
LOG_LEVEL=info
```

## 🚨 Troubleshooting

### **"Connection refused" errors**
- Ensure Ollama is running: `ollama serve`
- Check Ollama is on correct port: `curl http://localhost:11434`

### **"Model not found" errors**
- Pull the model: `ollama pull gpt-oss:120b`
- List available models: `ollama list`

### **CORS errors**
- Make sure frontend is running on port 3000
- Backend CORS is configured for `http://localhost:3000`

### **Module loading errors (frontend)**
- Must use HTTP server (not file:// protocol)
- Python HTTP server is the easiest: `python -m http.server 3000`

## 🎯 Key Features

- **Clean Code Architecture**: Follows Robert Martin's principles
- **Type Safety**: Input validation and error handling
- **Retry Logic**: Automatic retry for failed requests
- **Streaming Disabled**: As recommended for Ollama.js
- **Comprehensive Logging**: Winston-based logging
- **Rate Limiting**: Prevents API abuse
- **Security Headers**: Helmet.js protection
- **CORS Configuration**: Proper cross-origin setup

## 📚 Technology Stack

### **Frontend**
- **Vanilla JavaScript ES6+** with modules
- **Modern CSS3** with CSS Grid and Flexbox
- **Fetch API** for HTTP requests

### **Backend**
- **Node.js 18+** runtime
- **Express.js** web framework
- **Ollama.js** official client library
- **Winston** structured logging
- **Helmet** security middleware
- **express-validator** input validation

### **AI Integration**
- **Ollama** local AI runtime
- **gpt-oss:120b** language model
- **Non-streaming** responses as recommended

This architecture provides a solid foundation for enterprise-grade AI applications while maintaining clean code principles and separation of concerns.