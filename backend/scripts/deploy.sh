#!/bin/bash

# BAIS Production Deployment Script
set -e

echo "🚀 Starting BAIS production deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure."
    exit 1
fi

# Load environment variables
source .env

# Build images
echo "📦 Building Docker images..."
docker-compose build --no-cache

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose run --rm bais-api python -m alembic upgrade head

# Start services
echo "🏃 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
docker-compose ps

# Run health checks
echo "✅ Running health checks..."
curl -f http://localhost:8000/health || { echo "❌ API health check failed"; exit 1; }
curl -f http://localhost:8003/oauth/.well-known/authorization_server || { echo "❌ OAuth health check failed"; exit 1; }

echo "🎉 BAIS deployment completed successfully!"
echo "📊 Access Grafana dashboard at: http://localhost:3001"
echo "📈 Access Prometheus at: http://localhost:9090"
echo "🔐 OAuth server at: http://localhost:8003"
echo "🌐 API server at: http://localhost:8000"
