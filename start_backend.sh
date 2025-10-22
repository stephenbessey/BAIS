#!/bin/bash

# BAIS Backend Startup Script
echo "🚀 Starting BAIS Backend Server..."

# Change to the BAIS directory
cd /Users/stephenbessey/Documents/Development/BAIS

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "📥 Installing required packages..."
    pip3 install fastapi uvicorn pydantic email-validator
fi

# Start the backend server
echo "🌐 Starting server on http://localhost:8000"
echo "📚 API Documentation available at http://localhost:8000/docs"
echo "🔍 Health check available at http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the backend
python3 app.py
