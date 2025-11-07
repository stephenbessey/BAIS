# Connecting PostgreSQL to BAIS Service in Railway

## Problem
PostgreSQL service exists, but BAIS service shows `DATABASE_URL` as "not_set" because they're not connected.

## Solution: Add Variable Reference

Railway services need to be explicitly connected via **Variable References**.

## Steps to Connect Database

### Step 1: Go to BAIS Service Settings
1. In Railway dashboard, click on the **BAIS** service (not Postgres)
2. Click on the **"Variables"** tab

### Step 2: Add Variable Reference
1. Look for the section that says **"Add Variable Reference"** or **"Reference Variable from Another Service"**
2. Click **"+ New Variable"** or **"Add Reference"**
3. You'll see a dropdown to select a service - choose **"Postgres"**
4. Then select the variable **`DATABASE_URL`**
5. Railway will create a reference like: `${{Postgres.DATABASE_URL}}`

### Step 3: Verify Connection
After adding the reference:
1. The BAIS service should now show `DATABASE_URL` with a reference icon
2. The value will be something like `${{Postgres.DATABASE_URL}}`
3. Railway will automatically inject the actual connection string at runtime

### Step 4: Redeploy (if needed)
- Railway may automatically redeploy
- Or manually trigger a redeploy to apply changes

### Step 5: Verify It Works
```bash
curl https://bais-production.up.railway.app/diagnostics | python3 -m json.tool
```

Should now show:
```json
{
  "environment_check": {
    "required_env_vars": {
      "DATABASE_URL": "set"  // ✅ Should now be "set"
    }
  }
}
```

## Alternative: Manual Variable Setup

If Variable References don't work, you can manually copy the value:

### Step 1: Get DATABASE_URL from Postgres
1. Go to **Postgres** service → **Variables** tab
2. Find `DATABASE_URL`
3. Click to reveal/copy the value

### Step 2: Add to BAIS Service
1. Go to **BAIS** service → **Variables** tab
2. Click **"+ New Variable"**
3. Name: `DATABASE_URL`
4. Value: Paste the connection string from Postgres
5. Click **"Add"**

## Quick Visual Guide

```
Railway Dashboard
├── BAIS Service (bais-production.up.railway.app)
│   └── Variables Tab
│       └── [Add Variable Reference]
│           └── Service: Postgres
│           └── Variable: DATABASE_URL
│           └── Creates: ${{Postgres.DATABASE_URL}}
│
└── Postgres Service
    └── Variables Tab
        └── DATABASE_URL (source)
```

## What Happens After Connection

✅ BAIS service can access PostgreSQL database
✅ Tables are created automatically on startup
✅ Businesses are saved to database (persistent)
✅ Search queries database
✅ Perfect for demos - data persists!

## Troubleshooting

### Variable Reference Not Showing?
- Make sure both services are in the same Railway project
- Check that Postgres service is deployed and running
- Try refreshing the Railway dashboard

### Still Showing "not_set"?
1. Check Railway logs for BAIS service startup
2. Look for database connection messages
3. Verify the Variable Reference is saved correctly
4. Try manually adding the variable as a fallback

### Connection Errors?
- Check Railway logs for database connection errors
- Verify Postgres service is running
- Ensure the DATABASE_URL format is correct (should start with `postgresql://`)

