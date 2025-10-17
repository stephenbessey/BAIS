# Railway Deployment Troubleshooting Guide

## 🔧 Enhanced Diagnostic Features

Your BAIS deployment now includes comprehensive diagnostic capabilities to help identify and resolve issues quickly.

## 📊 Diagnostic Endpoints

### 1. Basic Health Check
```
GET /health
```
**Purpose**: Railway's health check endpoint
**Expected Response**: `{"status": "healthy", ...}`

### 2. Detailed Health Check
```
GET /health/detailed
```
**Purpose**: Comprehensive health information
**Response Includes**:
- System information
- Environment variables status
- Import errors (if any)
- Recommendations for fixes

### 3. Full Diagnostics
```
GET /diagnostics
```
**Purpose**: Complete system diagnostics
**Response Includes**:
- Python version and environment
- Working directory
- Environment variables (masked)
- Import errors with full traceback
- Available modules
- Timestamp

## 🚀 Pre-Deployment Checks

### Run Local Diagnostic Script
```bash
python3 diagnostic_check.py
```

**This script checks**:
- ✅ Python version compatibility
- ✅ All required dependencies
- ✅ File structure completeness
- ✅ Import functionality
- ✅ Environment variables
- ✅ Railway configuration

## 🔍 Troubleshooting Common Issues

### Issue 1: Health Check Failing

**Symptoms**: Railway shows "service unavailable"
**Diagnosis**: Check `/health/detailed` endpoint
**Common Causes**:
- Import errors in main_full.py
- Missing dependencies
- Database connection issues

**Solutions**:
1. Check Railway logs for detailed error messages
2. Verify all dependencies in requirements.txt
3. Ensure environment variables are set
4. Check `/diagnostics` endpoint for import errors

### Issue 2: Import Errors

**Symptoms**: App fails to start with ImportError
**Diagnosis**: Check `/diagnostics` endpoint
**Common Causes**:
- Missing modules in backend/production
- Relative import issues
- Dependency conflicts

**Solutions**:
1. Run `python3 diagnostic_check.py` locally first
2. Check that all files exist in backend/production/
3. Verify import paths are correct
4. Test imports manually: `python -c "from backend.production.main_full import app"`

### Issue 3: Database Connection Issues

**Symptoms**: App starts but database operations fail
**Diagnosis**: Check environment variables in `/diagnostics`
**Common Causes**:
- DATABASE_URL not set in Railway
- PostgreSQL service not added to Railway project
- Connection string format incorrect

**Solutions**:
1. Add PostgreSQL service in Railway dashboard
2. Set DATABASE_URL environment variable
3. Verify connection string format
4. Check Railway service status

### Issue 4: Environment Variables Missing

**Symptoms**: Features not working as expected
**Diagnosis**: Check `/diagnostics` environment_check section
**Required Variables**:
- `PORT` (set automatically by Railway)
- `DATABASE_URL` (from PostgreSQL service)
- `REDIS_URL` (from Redis service, optional)

**Optional Variables**:
- `BAIS_ENVIRONMENT=production`
- `OAUTH_CLIENT_ID`
- `OAUTH_CLIENT_SECRET`
- `AP2_API_KEY`
- `AP2_SECRET_KEY`
- `ENCRYPTION_KEY`

## 📋 Railway Configuration

### Current railway.json
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "cd backend/production && uvicorn main_full:app --host 0.0.0.0 --port $PORT --log-level info",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 60,
    "healthcheckInterval": 10,
    "healthcheckRetries": 6
  }
}
```

**Enhanced Features**:
- Increased health check timeout (60s)
- More health check retries (6)
- Detailed logging enabled
- Comprehensive error handling

## 🔧 Deployment Steps

### 1. Pre-Deployment
```bash
# Run diagnostic checks
python3 diagnostic_check.py

# Verify all checks pass before deploying
```

### 2. Railway Setup
1. **Add Services**:
   - PostgreSQL database
   - Redis (optional)
   
2. **Set Environment Variables**:
   - Go to Variables tab in Railway
   - Add required environment variables
   
3. **Deploy**:
   ```bash
   railway up
   ```

### 3. Post-Deployment Verification
1. **Check Health**:
   ```
   GET https://your-app.railway.app/health
   ```

2. **Run Diagnostics**:
   ```
   GET https://your-app.railway.app/diagnostics
   ```

3. **Test API Endpoints**:
   ```
   GET https://your-app.railway.app/docs
   ```

## 🚨 Emergency Recovery

### If Deployment Fails Completely

1. **Fallback to Phase 1**:
   ```bash
   # Update railway.json startCommand to:
   "cd backend/production && uvicorn main_railway:app --host 0.0.0.0 --port $PORT"
   railway up
   ```

2. **Check Railway Logs**:
   - Go to Railway dashboard
   - Click on your service
   - View deployment logs for detailed error information

3. **Local Testing**:
   ```bash
   # Test locally first
   cd backend/production
   uvicorn main_full:app --host 0.0.0.0 --port 8000
   ```

## 📞 Support Information

### Key Files for Troubleshooting
- `backend/production/main_full.py` - Main application with diagnostics
- `railway.json` - Railway configuration
- `requirements.txt` - Dependencies
- `diagnostic_check.py` - Local diagnostic script

### Log Locations
- Railway deployment logs (Railway dashboard)
- Application logs (accessible via `/diagnostics`)
- Health check logs (Railway health monitoring)

### Quick Commands
```bash
# Local diagnostic check
python3 diagnostic_check.py

# Test local startup
cd backend/production && uvicorn main_full:app --host 0.0.0.0 --port 8000

# Railway deployment
railway up

# Check Railway logs
railway logs
```

This enhanced setup provides comprehensive diagnostic capabilities to quickly identify and resolve any deployment issues!
