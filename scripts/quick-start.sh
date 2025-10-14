#!/bin/bash

# BA Integrate - Quick Start Script
# Sets up the development environment and initializes the database

set -e  # Exit on any error

echo "🚀 BA Integrate - Quick Start Setup"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found. Please run this script from the BAIS directory."
    exit 1
fi

# Check Python version
echo "🐍 Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp env.production.example .env
    echo "⚠️  Please edit .env file with your actual configuration values"
fi

# Check if database is accessible
echo "🗄️  Checking database connection..."
if python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
database_url = os.getenv('DATABASE_URL')
if database_url:
    print('✅ DATABASE_URL is set')
else:
    print('❌ DATABASE_URL not found in .env file')
    exit(1)
" 2>/dev/null; then
    echo "✅ Database configuration found"
else
    echo "❌ Please configure DATABASE_URL in .env file"
    exit 1
fi

# Run database migrations (if Alembic is configured)
if [ -f "alembic.ini" ]; then
    echo "🔄 Running database migrations..."
    alembic upgrade head
fi

# Initialize database with seed data
echo "🌱 Seeding database with initial data..."
python3 scripts/seed_data.py

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your actual configuration"
echo "2. Start the development server:"
echo "   source venv/bin/activate"
echo "   uvicorn backend.production.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "3. Visit http://localhost:8000/docs for API documentation"
echo "4. Visit http://localhost:8000/health for health check"
echo ""
echo "🔐 Default admin credentials:"
echo "   Email: admin@baintegrate.com"
echo "   Password: changeme123!"
echo "   (Change these in production!)"
echo ""
echo "Happy coding! 🎉"
