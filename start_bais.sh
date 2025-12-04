#!/bin/bash

# BAIS Complete Startup Script
# Starts both backend and serves frontend in one command
# Works with Claude, ChatGPT, Gemini, and Ollama (via Tailscale)

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     BAIS Platform - Complete Startup Script            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}❌ Python3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

# Check if uvicorn is available
if ! python3 -c "import uvicorn" &> /dev/null; then
    echo -e "${YELLOW}📦 Installing required packages...${NC}"
    pip3 install -q fastapi uvicorn[standard] pydantic requests anthropic
fi

# Check if frontend exists
if [ ! -d "frontend" ]; then
    echo -e "${YELLOW}❌ Frontend directory not found${NC}"
    exit 1
fi

# Check if chat.html exists
if [ ! -f "frontend/chat.html" ]; then
    echo -e "${YELLOW}❌ Frontend chat.html not found${NC}"
    exit 1
fi

# Set default port
PORT=${PORT:-8000}

echo -e "${GREEN}✓${NC} Prerequisites checked"
echo ""

# Shutdown any running BAIS services
echo -e "${YELLOW}🔄 Checking for running BAIS services...${NC}"

# Find and kill processes running uvicorn with main_railway_final
RUNNING_UVICORN=$(pgrep -f "uvicorn.*main_railway_final" 2>/dev/null || true)
if [ -n "$RUNNING_UVICORN" ]; then
    echo -e "   Found running uvicorn processes (PIDs: $RUNNING_UVICORN)"
    echo -e "   ${YELLOW}Stopping existing BAIS server...${NC}"
    pkill -f "uvicorn.*main_railway_final" 2>/dev/null || true
    sleep 2
    echo -e "   ${GREEN}✓${NC} Stopped existing BAIS server"
fi

# Check if port is in use and kill the process using it
PORT_IN_USE=$(lsof -ti:$PORT 2>/dev/null || true)
if [ -n "$PORT_IN_USE" ]; then
    echo -e "   Port $PORT is in use by process(es): $PORT_IN_USE"
    echo -e "   ${YELLOW}Freeing port $PORT...${NC}"
    kill -9 $PORT_IN_USE 2>/dev/null || true
    sleep 1
    echo -e "   ${GREEN}✓${NC} Port $PORT is now available"
fi

# Also check for any Python processes running main_railway_final
RUNNING_PYTHON=$(pgrep -f "python.*main_railway_final" 2>/dev/null || true)
if [ -n "$RUNNING_PYTHON" ]; then
    echo -e "   Found running Python BAIS processes (PIDs: $RUNNING_PYTHON)"
    echo -e "   ${YELLOW}Stopping...${NC}"
    pkill -f "python.*main_railway_final" 2>/dev/null || true
    sleep 1
    echo -e "   ${GREEN}✓${NC} Stopped Python BAIS processes"
fi

if [ -z "$RUNNING_UVICORN" ] && [ -z "$PORT_IN_USE" ] && [ -z "$RUNNING_PYTHON" ]; then
    echo -e "   ${GREEN}✓${NC} No running BAIS services found"
fi

echo ""

# Display configuration info
echo -e "${BLUE}📋 Configuration:${NC}"
echo "   Backend: backend/production/main_railway_final.py"
echo "   Frontend: frontend/chat.html"
echo "   Port: $PORT"
echo ""

# Check for environment variables
echo -e "${YELLOW}⚠️  Configuration Notes:${NC}"

# Check DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "   • Database: Using in-memory storage (data lost on restart)"
    echo "     To persist data, set DATABASE_URL (see DATABASE_SETUP.md)"
else
    # Check if using internal Railway URL locally
    if echo "$DATABASE_URL" | grep -q "postgres.railway.internal"; then
        echo "   • Database: ⚠️  Using Railway INTERNAL URL - will not work locally!"
        echo "     Get PUBLIC URL from Railway dashboard or use local database"
        echo "     See DATABASE_SETUP.md for configuration options"
    else
        echo "   • Database: Using configured DATABASE_URL"
    fi
fi

# Check LLM API keys
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OLLAMA_HOST" ]; then
    echo "   • LLM: Not configured"
    echo "     - For Claude: Set ANTHROPIC_API_KEY environment variable"
    echo "     - For Ollama: Configure host in the chat interface"
fi
echo ""

# Display URLs
echo -e "${GREEN}🚀 Starting BAIS Server...${NC}"
echo ""
echo -e "${BLUE}📍 Access Points:${NC}"
echo -e "   ${GREEN}Chat Interface:${NC}  http://localhost:$PORT/chat"
echo -e "   ${GREEN}API Docs:${NC}        http://localhost:$PORT/docs"
echo -e "   ${GREEN}Health Check:${NC}     http://localhost:$PORT/health"
echo ""
echo -e "${BLUE}🤖 LLM Integration:${NC}"
echo "   • Claude: Configure API key in chat interface"
echo "   • Ollama: Set host (e.g., http://your-tailscale-ip:11434)"
echo "   • ChatGPT/Gemini: Coming soon"
echo ""
echo -e "${BLUE}💡 Demo Queries:${NC}"
echo "   • 'Find a med spa in Las Vegas'"
echo "   • 'What services does New Life New Image Med Spa offer?'"
echo "   • 'Book me a Botox appointment'"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the server
cd "$SCRIPT_DIR"
python3 -m uvicorn backend.production.main_railway_final:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --reload

