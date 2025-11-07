# Fix Summary: Business Not Appearing in Search

## Problem
Customer's business "New Life New Image Med Spa" was not appearing in search results after registration.

## Root Causes Identified

1. **Response Format Error**: `UniversalToolResponse` expected a dict but `search_businesses` returns a list
   - **Fixed**: Changed `result` type to `Union[Dict, List, Any]`

2. **Storage Isolation**: `BUSINESS_STORE` in `routes_simple.py` wasn't accessible from `universal_tools.py`
   - **Fixed**: Created `shared_storage.py` module for cross-module access

3. **Routes Not Included**: `main_simple.py` wasn't including `routes_simple` or webhooks
   - **Fixed**: Updated `main_simple.py` to include routes and webhooks

4. **Search Matching**: Search logic wasn't flexible enough for "med spa" queries
   - **Fixed**: Improved word matching and location normalization

## Changes Made

### 1. Fixed Response Format (`universal_webhooks.py`)
```python
class UniversalToolResponse(BaseModel):
    result: Optional[Union[Dict[str, Any], List[Dict[str, Any]], Any]] = None
```

### 2. Created Shared Storage (`shared_storage.py`)
- Centralized `BUSINESS_STORE` that both `routes_simple` and `universal_tools` can access
- Ensures businesses registered via API are discoverable by search

### 3. Updated Routes (`routes_simple.py`)
- Now imports and uses `shared_storage.BUSINESS_STORE`
- Uses `register_business()` function for consistency

### 4. Updated Search Logic (`universal_tools.py`)
- Multiple import paths for `shared_storage`
- Improved word matching (e.g., "med spa" matches "Med Spa")
- Better location normalization (e.g., "Las Vegas" matching)

### 5. Updated Main App (`main_simple.py`)
- Includes `routes_simple` router
- Includes `universal_webhooks` router
- Added debug endpoint `/api/v1/debug/businesses`

## Next Steps

1. **Wait for Railway Deployment** (2-3 minutes after push)
2. **Re-register Business** (in-memory storage clears on restart):
   ```bash
   python3 scripts/submit_customer.py customers/NewLifeNewImage_CORRECTED_BAIS_Submission.json https://bais-production.up.railway.app
   ```
3. **Test Search**:
   ```bash
   python3 scripts/ollama_with_bais.py "find a med spa in Las Vegas"
   ```
4. **Verify**:
   ```bash
   python3 scripts/test_business_search.py
   ```

## Important Notes

- **In-Memory Storage**: Businesses are stored in-memory and will be lost on Railway restart
- **Re-registration Required**: Business must be re-registered after each deployment
- **Future Improvement**: Use database (PostgreSQL) for persistent storage when `DATABASE_URL` is configured

## Testing

After Railway redeploys:
1. Check debug endpoint: `curl https://bais-production.up.railway.app/api/v1/debug/businesses`
2. Re-register business
3. Test search via webhook
4. Test with Ollama demo script

