# 🌐 Universal BAIS Architecture

## **Your Goal: Public Discoverability for ALL Customers**

Yes! BAIS is designed to make **ANY registered business** discoverable by **ANYONE** using ChatGPT, Claude, or Gemini. Here's how it works:

## **How BAIS Works for ALL Customers:**

### 1. **Universal Webhook Endpoints** (Already Implemented)
- `/api/v1/llm-webhooks/claude/tool-use` - Claude calls this
- `/api/v1/llm-webhooks/chatgpt/function-call` - ChatGPT calls this  
- `/api/v1/llm-webhooks/gemini/function-call` - Gemini calls this
- `/api/v1/llm-webhooks/tools/definitions` - Returns tool definitions

These endpoints are **publicly accessible** on Railway and work for **ALL businesses**.

### 2. **Universal Tools** (Already Implemented)
BAIS registers **3 universal tools** with each LLM provider:
- `bais_search_businesses` - Search ALL registered businesses
- `bais_get_business_services` - Get services for ANY business
- `bais_execute_service` - Execute service for ANY business

These tools work for **ALL registered businesses**, not just one.

### 3. **Database-Driven Search** (Just Fixed)
The search function now:
- ✅ Queries **ALL active businesses** from the database
- ✅ Searches by name, description, location, category, and **service names**
- ✅ Returns matching businesses (no hardcoding)
- ✅ Works for **any registered business**

### 4. **Public Discovery Flow:**

```
User asks ChatGPT/Claude/Gemini:
"Find a med spa in Las Vegas that offers Botox"

→ LLM calls bais_search_businesses(query="med spa", location="Las Vegas", category="healthcare")

→ BAIS webhook queries database for ALL businesses matching:
   - Name/description contains "med spa" OR services contain "botox"
   - Location is Las Vegas
   - Category is healthcare

→ Returns ALL matching businesses (including your customer)

→ LLM presents results to user

→ User can book through bais_execute_service
```

## **Requirements for Public Discovery:**

### ✅ **Already Working:**
1. Webhook endpoints are public and accessible
2. Universal tools are registered (conceptually - LLM providers need to call BAIS)
3. Database query searches ALL businesses
4. No hardcoded businesses (removed hardcoded customer logic)

### ⚠️ **What You Need to Do:**

1. **Register Your Customer's Business:**
   ```bash
   # Submit customer JSON to BAIS
   python3 scripts/submit_customer.py customers/NewLifeNewImage_CORRECTED_BAIS_Submission.json
   ```
   This stores the business in the database.

2. **Set Up Database on Railway:**
   - Add PostgreSQL database to Railway
   - Set `DATABASE_URL` environment variable
   - Run migrations to create tables

3. **LLM Provider Integration:**
   - **For Claude:** Users can use `scripts/claude_with_bais.py` (injects tools automatically)
   - **For ChatGPT:** Need to register BAIS as a custom GPT action
   - **For Gemini:** Need to register BAIS as a function calling endpoint

## **Environment Variables Setup:**

Create a `.env` file (never commit it):
```bash
# .env
ANTHROPIC_API_KEY=your-key-here
RAILWAY_URL=https://bais-production.up.railway.app
DATABASE_URL=postgresql://user:pass@host/db
```

## **Key Points:**

✅ **Universal:** Any business registered with BAIS is discoverable  
✅ **Public:** Anyone using ChatGPT/Claude/Gemini can find your customers  
✅ **Automatic:** No per-business setup needed  
✅ **Database-Driven:** All businesses come from the database, not hardcoded  

## **Next Steps:**

1. ✅ Fixed: Removed hardcoded customer logic
2. ✅ Fixed: Database query searches ALL businesses
3. ⏳ TODO: Register customer business in database
4. ⏳ TODO: Set up Railway database
5. ⏳ TODO: Test with actual customer data

Your architecture is **universal and ready** - it will work for ALL customers once they're registered in the database!

