# Railway Deployment Troubleshooting Guide

## Multiple Deployment Configurations Created

I've created several deployment configurations to help resolve the issue:

### 1. Updated railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "cd backend/production && uvicorn main_simple:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30
  }
}
```

### 2. Alternative: Procfile
```
web: cd backend/production && uvicorn main_simple:app --host 0.0.0.0 --port $PORT
```

### 3. Nixpacks Configuration (nixpacks.toml)
```toml
[phases.setup]
nixPkgs = ["python311", "pip"]

[phases.install]
cmds = [
    "pip install -r backend/production/requirements_minimal.txt"
]

[start]
cmd = "cd backend/production && uvicorn main_simple:app --host 0.0.0.0 --port $PORT"
```

## Common Railway Deployment Issues & Solutions

### Issue 1: Build Failures
**Symptoms**: Build process fails during dependency installation
**Solutions**:
- Try the minimal requirements file: `requirements_minimal.txt`
- Check if all dependencies are compatible with Python 3.11
- Use the nixpacks.toml configuration for more control

### Issue 2: Import Errors
**Symptoms**: "ModuleNotFoundError" or "attempted relative import"
**Solutions**:
- Using `main_simple.py` which has no relative imports
- Changed working directory to `backend/production` before starting

### Issue 3: Port Binding Issues
**Symptoms**: "Address already in use" or port binding errors
**Solutions**:
- Using `$PORT` environment variable (Railway requirement)
- Binding to `0.0.0.0` instead of `127.0.0.1`

### Issue 4: Health Check Failures
**Symptoms**: Railway reports unhealthy status
**Solutions**:
- Health endpoint configured at `/health`
- 30-second timeout for health checks

## Step-by-Step Deployment Process

### Option 1: Use railway.json (Recommended)
1. Commit all changes to your repository
2. Deploy to Railway - it should use the railway.json configuration
3. Check Railway logs for any specific error messages

### Option 2: Use Procfile
1. If railway.json doesn't work, Railway will fall back to Procfile
2. The Procfile provides the same startup command

### Option 3: Use nixpacks.toml
1. This gives Railway explicit build instructions
2. Uses minimal dependencies to avoid conflicts

## Debugging Steps

### 1. Check Railway Logs
Look for these specific error patterns:
- `ModuleNotFoundError`: Import issues
- `Address already in use`: Port binding issues
- `No such file or directory`: Path issues
- `Permission denied`: File permission issues

### 2. Test Locally
```bash
# Test the exact command Railway will use
cd backend/production
uvicorn main_simple:app --host 0.0.0.0 --port 8000
```

### 3. Verify File Structure
Ensure these files exist:
- `backend/production/main_simple.py`
- `backend/production/requirements_minimal.txt`
- `railway.json` (in root)
- `Procfile` (in root)
- `nixpacks.toml` (in root)

## Environment Variables

Railway may need these environment variables:
- `PORT`: Automatically set by Railway
- `PYTHONPATH`: May need to be set to include the project root

## If All Else Fails

### Minimal Working Example
If the current setup still fails, try this ultra-minimal approach:

1. Create a single `app.py` file in the root:
```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health():
    return {"status": "ok"}
```

2. Update railway.json:
```json
{
  "deploy": {
    "startCommand": "uvicorn app:app --host 0.0.0.0 --port $PORT"
  }
}
```

## Next Steps

1. **Try the current configuration** - It should work with the fixes I've made
2. **Check Railway logs** - Look for specific error messages
3. **Share the error** - If it still fails, share the exact error message from Railway logs
4. **Fall back to minimal** - If needed, we can create an even simpler version

The current setup should resolve the most common Railway deployment issues. Let me know what specific error you're seeing and I can provide more targeted help.
