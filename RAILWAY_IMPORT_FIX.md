# 🔧 Railway Import Fix

## **Issue Found:**

The error is: `attempted relative import beyond top-level package`

This happens because `universal_webhooks.py` uses relative imports (`from ...core.universal_tools`), but when Railway runs from `backend/production`, the Python path doesn't include the necessary parent directories.

## **Fix Applied:**

I've updated `main_railway_final.py` to add the necessary directories to `sys.path`:
1. `backend/production` (current directory)
2. `backend` (parent directory)
3. This allows relative imports to work correctly

## **Next Steps:**

1. **Commit and push:**
   ```bash
   git add backend/production/main_railway_final.py
   git commit -m "Fix import path for universal_webhooks in Railway"
   git push
   ```

2. **Wait for Railway to redeploy** (2-3 minutes)

3. **Test the endpoints:**
   ```bash
   curl https://bais-production.up.railway.app/api/v1/llm-webhooks/tools/definitions
   ```

The import should now work correctly!

