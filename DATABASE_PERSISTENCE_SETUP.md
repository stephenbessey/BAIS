# Database Persistence Setup for BAIS

## Overview
BAIS now supports database persistence for businesses, ensuring they survive Railway restarts and are perfect for demos.

## How It Works

### 1. **Database Integration**
- Businesses are saved to database when `DATABASE_URL` is configured
- Falls back to in-memory storage if database is unavailable
- Both storage methods work simultaneously (database + memory)

### 2. **Database Models**
- `Business`: Stores business information (name, location, contact, etc.)
- `BusinessService`: Stores services for each business
- Uses compatible types (String for UUIDs, JSON for JSON fields) that work with both PostgreSQL and SQLite

### 3. **Registration Flow**
1. Business registration request received
2. If `DATABASE_URL` is set:
   - Save to database (persistent)
   - Also save to in-memory store (fast access)
3. If database unavailable:
   - Save to in-memory store only (works but not persistent)

### 4. **Search Flow**
1. Search queries database first
2. Falls back to in-memory store if database query fails
3. Returns combined results

## Railway Setup

### Option 1: Railway PostgreSQL (Recommended)
1. Add PostgreSQL service to Railway project
2. Railway automatically sets `DATABASE_URL` environment variable
3. Tables are created automatically on startup

### Option 2: External PostgreSQL
1. Get PostgreSQL connection string
2. Set `DATABASE_URL` environment variable in Railway
3. Format: `postgresql://user:password@host:port/database`

### Option 3: SQLite (Development Only)
- Not recommended for production/demos
- Use only if PostgreSQL is unavailable

## Verification

### Check Database Status
```bash
curl https://bais-production.up.railway.app/diagnostics
```

Look for:
```json
{
  "environment_check": {
    "required_env_vars": {
      "DATABASE_URL": "set"  // Should be "set"
    }
  }
}
```

### Test Persistence
1. Register a business:
   ```bash
   python3 scripts/submit_customer.py customers/NewLifeNewImage_CORRECTED_BAIS_Submission.json https://bais-production.up.railway.app
   ```

2. Restart Railway (or wait for auto-restart)

3. Search for business:
   ```bash
   python3 scripts/ollama_with_bais.py "find a med spa in Las Vegas"
   ```

4. Business should still appear (persisted in database)

## Current Status

✅ **Database models created** (Business, BusinessService)
✅ **Registration saves to database** (if DATABASE_URL configured)
✅ **Search queries database** (with fallback to memory)
✅ **Table initialization on startup** (automatic)
✅ **Compatible with PostgreSQL and SQLite**

## Next Steps

1. **Add PostgreSQL to Railway** (if not already added)
2. **Verify DATABASE_URL is set** in Railway environment variables
3. **Re-register business** after database is configured
4. **Test persistence** by restarting Railway

## Notes

- Database persistence is **automatic** when `DATABASE_URL` is configured
- In-memory storage still works as fallback
- Businesses are searchable immediately after registration
- No manual database setup required (tables created automatically)

