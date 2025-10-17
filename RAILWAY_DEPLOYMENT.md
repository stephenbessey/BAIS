# Railway Deployment Guide for BAIS

This guide will help you deploy your BAIS (Business-Agent Integration Standard) application to Railway.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Railway CLI** (optional but recommended):
   ```bash
   npm install -g @railway/cli
   ```

## Deployment Options

Your project has multiple deployment configurations. Choose one:

### Option 1: Complete BAIS Backend (Recommended for Railway)

This uses the full production backend with all customer integration features:

**Files used:**
- `backend/production/main.py` (full BAIS application)
- `requirements.txt` (complete dependencies)
- `railway.json` (Railway configuration)
- `.dockerignore` (excludes Node.js files)

### Option 2: Production Backend

This uses the more complex backend structure:

**Files used:**
- `backend/production/main_simple.py`
- `backend/production/requirements_minimal.txt`
- `Procfile`

## Step-by-Step Deployment

### Method 1: Railway Dashboard (Recommended)

1. **Connect Repository**
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your BAIS repository

2. **Configure Service**
   - Railway will auto-detect your Python application
   - It should use your `railway.json` configuration
   - If not, add these environment variables:
     - `PORT`: Railway will set this automatically
     - `PYTHON_VERSION`: `3.11.0`

3. **Deploy**
   - Railway will automatically build and deploy
   - Monitor the deployment logs
   - Your app will be available at the generated Railway URL

### Method 2: Railway CLI

1. **Login to Railway**
   ```bash
   railway login
   ```

2. **Initialize Project**
   ```bash
   railway init
   ```

3. **Deploy**
   ```bash
   railway up
   ```

## Configuration Files Explained

### `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30
  }
}
```

### `nixpacks.toml`
```toml
[providers]
python = "3.11"

[phases.setup]
nixPkgs = ["python311", "pip"]

[phases.install]
cmds = [
    "pip install -r requirements.txt"
]

[start]
cmd = "uvicorn app:app --host 0.0.0.0 --port $PORT"
```

## Health Check Endpoints

## Your Complete BAIS Backend Endpoints:

### Core Endpoints:
- `GET /` - Welcome message
- `GET /health` - Health check for Railway monitoring
- `GET /docs` - FastAPI interactive documentation

### Business Management API:
- `POST /api/v1/businesses` - Register new business
- `GET /api/v1/businesses/{business_id}` - Get business status

### Agent Interaction:
- `POST /api/v1/agents/interact` - Agent interaction endpoint

### A2A Protocol (Agent-to-Agent):
- A2A Discovery endpoints for agent discovery
- A2A Tasks for task management
- A2A SSE for real-time communication

### MCP Protocol (Model Context Protocol):
- MCP SSE transport endpoints
- MCP Prompts management
- MCP Subscriptions management

### Payment Processing (AP2):
- `POST /api/v1/payments/mandates` - Create payment mandates
- `POST /api/v1/payments/transactions` - Process transactions
- Webhook endpoints for payment notifications

### Monitoring & Health:
- Circuit breaker monitoring endpoints
- Performance metrics endpoints
- Monitoring dashboard endpoints

## Troubleshooting

### Common Issues

1. **Port Binding Error**
   - Ensure your app uses `$PORT` environment variable
   - Railway sets this automatically

2. **Python Version Issues**
   - Check `runtime.txt` specifies Python 3.11.0
   - Or use `nixpacks.toml` configuration

3. **Dependency Issues**
   - Verify `requirements.txt` has all needed packages
   - Check build logs for missing dependencies

4. **Import Errors**
   - Ensure all imports are absolute (not relative)
   - Check file structure matches import paths

### Checking Deployment Status

1. **Railway Dashboard**
   - View real-time logs
   - Check deployment status
   - Monitor resource usage

2. **CLI Commands**
   ```bash
   railway status
   railway logs
   railway open
   ```

## Environment Variables

Railway automatically provides:
- `PORT` - Port your app should listen on
- `RAILWAY_ENVIRONMENT` - Environment name
- `RAILWAY_PROJECT_ID` - Your project ID

## Custom Domain (Optional)

1. In Railway dashboard, go to Settings
2. Add a custom domain
3. Update DNS records as instructed

## Monitoring

Your app includes basic health checks. For production monitoring:
- Use Railway's built-in metrics
- Add application monitoring (e.g., Sentry)
- Set up alerts for health check failures

## Next Steps

After successful deployment:
1. Test all endpoints
2. Set up monitoring
3. Configure custom domain (if needed)
4. Set up CI/CD for automatic deployments

## Support

- Railway Documentation: [docs.railway.app](https://docs.railway.app)
- Railway Discord: [discord.gg/railway](https://discord.gg/railway)
- Your app logs: Available in Railway dashboard
