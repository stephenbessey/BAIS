# BAIS API Server

A FastAPI-based server for business agent integration services.

## Quick Start

### Local Development
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

### API Endpoints
- `GET /` - Server status
- `GET /health` - Health check
- `GET /api/status` - API status
- `GET /docs` - Interactive API documentation

## Deployment

This application is configured for Railway deployment with:
- Python 3.11
- FastAPI framework
- Automatic health checks

## Environment Variables

- `PORT` - Server port (automatically set by Railway)

## License

Proprietary software. All rights reserved.