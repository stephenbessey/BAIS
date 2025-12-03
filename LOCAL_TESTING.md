# Local Testing Guide

## Understanding the Setup

BAIS has two separate environments:

1. **Railway (Production)**: Has a PostgreSQL database where businesses are persisted
2. **Local Development**: Uses in-memory storage (unless DATABASE_URL is set)

## The Issue

When you register a business on Railway:
- ✅ Business is saved to Railway's PostgreSQL database
- ✅ Business persists across Railway deployments
- ❌ Business is NOT available in your local server's in-memory storage

## Solutions

### Option 1: Test on Railway (Recommended)

Test directly on Railway where the business is registered:
- Chat Interface: `https://bais-production.up.railway.app/chat`
- The business will be found because it's in Railway's database

### Option 2: Register Locally for Testing

If you want to test locally, register the business on your local server:

```bash
# Make sure your local server is running first
./start_bais.sh

# In another terminal, register the business locally
python3 scripts/submit_customer.py customers/NewLifeNewImage_CORRECTED_BAIS_Submission.json http://localhost:8000
```

This will populate the local in-memory store.

### Option 3: Use Railway Database Locally (Advanced)

If you want to connect your local server to Railway's database:

1. Get Railway's DATABASE_URL from Railway dashboard
2. Set it as an environment variable:
   ```bash
   export DATABASE_URL="postgresql://user:pass@host:port/dbname"
   ```
3. Start your local server - it will use Railway's database

⚠️ **Warning**: This is not recommended for production data. Use a separate database for local development.

## Current Status

- ✅ Business registered on Railway: `new-life-new-image-med-spa`
- ✅ Railway database: Has the business
- ❌ Local in-memory store: Empty (unless you register locally)

## Quick Test

To verify the business is on Railway:

```bash
curl https://bais-production.up.railway.app/api/v1/businesses/debug/list
```

This will show all businesses in Railway's database.

