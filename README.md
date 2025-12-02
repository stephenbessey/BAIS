# BAIS - Business-Agent Integration Standard

BAIS is a universal platform that makes businesses discoverable and bookable through AI agents. Once a business registers with BAIS, it becomes instantly accessible to users through any AI assistant (Claude, ChatGPT, Gemini, or local LLMs like Ollama) without requiring per-business integrations.

## What is BAIS?

BAIS solves a critical problem: **fragmentation in AI-powered business discovery and booking**. Instead of each business needing custom AI integrations, BAIS provides a single, universal standard that works across all AI platforms.

### Key Benefits

- **For Businesses**: Submit your business information once, become discoverable by all AI platforms automatically
- **For AI Platforms**: Register BAIS once, gain access to all registered businesses
- **For Consumers**: Use any AI assistant to find and book with any BAIS business

## Architecture

BAIS uses a **universal tools architecture**:

1. **Three Universal Tools**: All businesses are accessible through three standardized tools:
   - `bais_search_businesses` - Search for businesses by query, category, or location
   - `bais_get_business_services` - Get available services for a specific business
   - `bais_execute_service` - Execute a service (book appointment, make reservation, etc.)

2. **Single Integration**: BAIS registers these three tools once with each LLM provider (Claude, ChatGPT, Gemini). All businesses become accessible through this single integration.

3. **Database Persistence**: Businesses are stored in PostgreSQL (with SQLite fallback) for reliable persistence across server restarts.

## Features

### Chat Interface
- Modern, responsive chat UI that adapts to light/dark mode
- Direct integration with Ollama (local LLM support)
- Real-time business discovery and booking
- Tool call visualization
- Settings panel for Ollama configuration

### Business Registration
- Simple JSON-based registration
- Automatic service discovery
- Database persistence
- Instant discoverability after registration

### LLM Integration
- Universal webhook endpoints for Claude, ChatGPT, and Gemini
- Tool definitions automatically provided
- Works with local LLMs (Ollama) via Tailscale
- No per-business setup required

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (optional, SQLite fallback available)
- Ollama server (for local LLM support)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd BAIS
   ```

2. **Install dependencies**
   ```bash
   pip install -r backend/production/requirements.txt
   ```

3. **Start the server**
   ```bash
   ./start_bais.sh
   ```

   Or manually:
   ```bash
   python3 -m uvicorn backend.production.main_railway_final:app --host 0.0.0.0 --port 8000
   ```

4. **Access the chat interface**
   - Open http://localhost:8000/chat in your browser

### Configuration

#### Ollama Setup (for local LLM)

1. Click the settings icon (⚙️) in the chat interface header
2. Enter your Ollama host address (e.g., `http://100.x.x.x:11434` for Tailscale)
3. Enter your model name (e.g., `gpt-oss:120b` or `llama3`)
4. Click Save

#### Database Setup (optional)

Set the `DATABASE_URL` environment variable:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/bais"
```

If not set, BAIS will use in-memory storage (data lost on restart).

## Usage

### Chat Interface

1. Open http://localhost:8000/chat
2. Configure Ollama settings if needed (click ⚙️ icon)
3. Start chatting! Try queries like:
   - "Find a med spa in Las Vegas"
   - "What services does New Life New Image Med Spa offer?"
   - "Book me a Botox appointment"

### Register a Business

Use the registration script:
```bash
python3 scripts/submit_customer.py customers/your-business.json https://bais-production.up.railway.app
```

Or use the API directly:
```bash
curl -X POST http://localhost:8000/api/v1/businesses \
  -H "Content-Type: application/json" \
  -d @customers/your-business.json
```

### Example Business JSON

```json
{
  "name": "Your Business Name",
  "business_type": "healthcare",
  "description": "Business description",
  "address": "123 Main St",
  "city": "Las Vegas",
  "state": "NV",
  "postal_code": "89101",
  "services": [
    {
      "id": "service-1",
      "name": "Service Name",
      "description": "Service description",
      "price": 100.00
    }
  ]
}
```

## API Endpoints

### Core Endpoints

- `GET /` - Server status
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation (Swagger UI)

### Business Management

- `POST /api/v1/businesses` - Register a new business
- `GET /api/v1/businesses/{business_id}` - Get business details
- `GET /api/v1/businesses/{business_id}/services` - Get business services

### LLM Integration

- `GET /api/v1/llm-webhooks/tools/definitions` - Get tool definitions for LLM providers
- `POST /api/v1/llm-webhooks/claude/tool-use` - Claude webhook endpoint
- `POST /api/v1/llm-webhooks/chatgpt/function-call` - ChatGPT webhook endpoint
- `POST /api/v1/llm-webhooks/gemini/function-call` - Gemini webhook endpoint
- `GET /api/v1/llm-webhooks/health` - LLM webhooks health check

### Chat Interface

- `POST /api/v1/chat/message` - Send chat message
- `GET /api/v1/chat/models` - Get available models
- `GET /chat` - Chat interface (HTML)

## Project Structure

```
BAIS/
├── backend/
│   └── production/
│       ├── api/v1/          # API endpoints
│       │   ├── universal_webhooks.py  # LLM webhook handlers
│       │   └── chat_endpoint.py       # Chat interface backend
│       ├── core/
│       │   ├── universal_tools.py      # Universal BAIS tools
│       │   └── database_models.py     # Database schema
│       ├── routes_simple.py           # Business registration routes
│       └── main_railway_final.py      # Main application entry point
├── frontend/
│   ├── chat.html            # Chat interface
│   ├── assets/
│   │   └── chat-styles.css  # Styles (with dark mode support)
│   └── js/
│       └── chat.js          # Chat interface logic
├── scripts/
│   ├── submit_customer.py   # Business registration script
│   ├── claude_with_bais.py  # Claude integration example
│   └── ollama_with_bais.py  # Ollama integration example
├── customers/               # Customer business data
└── start_bais.sh           # Startup script
```

## Deployment

### Railway Deployment

BAIS is configured for Railway deployment:

1. Connect your repository to Railway
2. Set environment variables:
   - `DATABASE_URL` - PostgreSQL connection string (Railway auto-provides)
   - `PORT` - Server port (Railway auto-provides)
3. Railway will automatically deploy using `backend/production/main_railway_final.py`

### Local Deployment

```bash
./start_bais.sh
```

The script will:
- Check prerequisites
- Install dependencies if needed
- Start the FastAPI server
- Serve the frontend at http://localhost:8000/chat

## How It Works

### Universal Discovery

1. **Business Registration**: A business submits their information via JSON
2. **Database Storage**: Business is stored in PostgreSQL with all services
3. **Instant Discovery**: Business becomes immediately searchable through BAIS tools
4. **AI Access**: Any AI agent using BAIS tools can discover and interact with the business

### Example Flow

1. User asks AI: "Find a med spa in Las Vegas"
2. AI calls `bais_search_businesses` with query="med spa", location="Las Vegas"
3. BAIS searches database and returns matching businesses
4. AI presents results to user
5. User asks: "Book a Botox appointment"
6. AI calls `bais_get_business_services` to get available services
7. AI calls `bais_execute_service` to create the booking
8. Booking is processed and confirmed

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string (optional, uses SQLite fallback)
- `PORT` - Server port (default: 8000)
- `ANTHROPIC_API_KEY` - For Claude integration (if using Claude directly)
- `OLLAMA_HOST` - Ollama server address (default: http://localhost:11434)
- `OLLAMA_MODEL` - Ollama model name (default: llama3)

## Troubleshooting

### Chat Interface Not Loading

- Verify backend is running: `curl http://localhost:8000/health`
- Check browser console for errors
- Ensure frontend files exist in `frontend/` directory

### Ollama Connection Errors

- Verify Ollama server is running and accessible
- Check Tailscale connection if using remote server
- Test connection: `curl http://your-ollama-host:11434/api/tags`
- Verify host address in settings (include `http://` prefix)

### Business Not Found

- Verify business is registered: Check database or re-register
- Test search endpoint directly using API documentation at `/docs`
- Check business data includes proper location and service information

## License

Proprietary software. All rights reserved.
