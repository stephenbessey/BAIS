# Railway Database Connection Setup Guide

## The Problem

Your `railway.json` references `${{Postgres.DATABASE_URL}}`, but Railway needs the services to be **explicitly connected** in the UI for this to work.

## Solution: Connect Postgres to BAIS Service

### Option 1: Use Railway's Service Connection (Recommended)

1. **In Railway Dashboard:**
   - Go to your **BAIS** service (not Postgres)
   - Click on the **Variables** tab
   - Find the `DATABASE_URL` variable
   - **Delete it** if it's a static value (not a reference)

2. **Create a Reference:**
   - Click **"+ New Variable"**
   - Name: `DATABASE_URL`
   - Value: Click **"Add Reference"** button
   - Select your **Postgres** service from the dropdown
   - Select `DATABASE_URL` from the Postgres service variables
   - Click **"Add"**

   This creates a reference like: `${{Postgres.DATABASE_URL}}`

3. **Verify:**
   - The variable should show with a chain-link icon (🔗) indicating it's a reference
   - The value should be masked (showing `********`)

### Option 2: Manual Connection String

If the reference doesn't work:

1. **Get the Connection String:**
   - Go to your **Postgres** service
   - Click **Variables** tab
   - Copy the `DATABASE_URL` value

2. **Set it in BAIS Service:**
   - Go to your **BAIS** service
   - Click **Variables** tab
   - Click **"+ New Variable"**
   - Name: `DATABASE_URL`
   - Value: Paste the connection string you copied
   - Click **"Add"**

### Option 3: Use Railway's Connect Feature

1. **In Railway Dashboard:**
   - Go to your **BAIS** service
   - In the service settings, look for **"Connect to Service"** or **"Add Service"**
   - Select your **Postgres** service
   - Railway will automatically share the `DATABASE_URL` variable

## Verify It's Working

After setting up the connection:

1. **Check the Diagnostics Endpoint:**
   ```bash
   curl https://bais-production.up.railway.app/diagnostics
   ```
   
   Look for:
   ```json
   "DATABASE_URL": "set",
   "DATABASE_URL_value": "postgresql://***@postgres.railway.internal:5432/railway"
   ```

2. **Check the Logs:**
   After deployment, you should see:
   ```
   📊 DATABASE_URL found: postgresql://***@postgres.railway.internal:5432/railway
   ✅ Created BAIS tool handler with Railway database connection
   ✅ Database connection verified: X businesses in database
   ```

3. **Test the Search:**
   - Go to the chat interface
   - Search for "med spa in Las Vegas"
   - It should find your registered business

## Common Issues

### Issue: Variable shows but app doesn't see it
**Solution:** Make sure it's a **reference** (with chain-link icon), not a static value. Delete and recreate it as a reference.

### Issue: Service name mismatch
**Solution:** The service name in `railway.json` (`Postgres`) must match exactly what Railway shows. Check your Postgres service name in Railway.

### Issue: Variable not updating after changes
**Solution:** Railway may need a redeploy. Trigger a new deployment after changing variables.

## Current Status

Based on your Railway UI:
- ✅ DATABASE_URL variable exists
- ⚠️ Need to verify it's a **reference** (not static)
- ⚠️ Need to verify services are **connected**

The diagnostic endpoint at `/diagnostics` will show you exactly which variables are available and their values (masked for security).

