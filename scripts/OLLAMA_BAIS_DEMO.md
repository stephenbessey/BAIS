# 🤖 Ollama + BAIS Demo Guide

## Overview
This demo shows how BAIS works with Ollama to enable AI agents to discover and book services from businesses like "New Life New Image Med Spa".

## Prerequisites

1. **Ollama Running**: Your Ollama instance should be running at `http://golem:11434`
2. **Model Available**: The model `gpt-oss:120b` should be pulled and available
3. **BAIS Backend**: Deployed at `https://bais-production.up.railway.app`
4. **Customer Registered**: "New Life New Image Med Spa" should be registered in BAIS

## Quick Start

### 1. Test Ollama Connection
```bash
curl http://golem:11434/api/tags
```

Should return a list of available models including `gpt-oss:120b`.

### 2. Test BAIS Backend
```bash
curl https://bais-production.up.railway.app/api/v1/llm-webhooks/tools/definitions
```

Should return BAIS tool definitions.

### 3. Run Demo
```bash
cd /Users/stephenbessey/Documents/Development/BAIS

# Set environment variables (optional, defaults are set)
export OLLAMA_HOST="http://golem:11434"
export OLLAMA_MODEL="gpt-oss:120b"
export BAIS_WEBHOOK_URL="https://bais-production.up.railway.app/api/v1/llm-webhooks/claude/tool-use"
export BAIS_TOOLS_URL="https://bais-production.up.railway.app/api/v1/llm-webhooks/tools/definitions"

# Run demo queries
python3 scripts/ollama_with_bais.py "find a med spa in Las Vegas"
python3 scripts/ollama_with_bais.py "search for New Life New Image Med Spa"
python3 scripts/ollama_with_bais.py "what services does New Life New Image offer?"
```

## Demo Scenarios

### Scenario 1: Business Discovery
**Query**: "find a med spa in Las Vegas"

**Expected Flow**:
1. Ollama receives query with system prompt about BAIS tools
2. Ollama responds with tool call: `bais_search_businesses`
3. Script calls BAIS webhook
4. BAIS returns businesses (should include "New Life New Image Med Spa")
5. Ollama processes results and presents them to user

### Scenario 2: Service Discovery
**Query**: "what services does New Life New Image offer?"

**Expected Flow**:
1. Ollama calls `bais_search_businesses` to find the business
2. Gets business_id
3. Ollama calls `bais_get_business_services` with business_id
4. BAIS returns services (Botox, PRF, etc.)
5. Ollama presents services to user

### Scenario 3: Booking Flow
**Query**: "book a Botox appointment at New Life New Image for next Friday at 2pm"

**Expected Flow**:
1. Ollama searches for business
2. Gets services and finds "Neurotoxin / Botox"
3. Ollama calls `bais_execute_service` with:
   - business_id
   - service_id: "neurotoxin"
   - parameters: { appointment_date: "2024-XX-XX", appointment_time: "14:00", ... }
   - customer_info: { name, email, phone }
4. BAIS processes booking
5. Ollama confirms booking to user

## How It Works

### Tool Calling Strategy
Since Ollama models don't support native function calling like Claude, we use:

1. **Structured System Prompt**: Instructs the model to respond with JSON when it wants to use a tool
2. **JSON Parsing**: Script parses the model's response to extract tool calls
3. **Tool Execution**: Script calls BAIS webhooks with the tool parameters
4. **Result Injection**: Tool results are injected back into the conversation
5. **Iteration**: Process repeats until the model provides a final answer

### System Prompt
The system prompt guides the model to:
- Use tools when users ask about businesses
- Format tool calls as JSON: `{"tool_call": {"name": "...", "input": {...}}}`
- Process tool results naturally
- Provide helpful final answers

## Troubleshooting

### Issue: Ollama not responding
**Solution**: Check if Ollama is running
```bash
curl http://golem:11434/api/tags
```

### Issue: Model not found
**Solution**: Pull the model
```bash
ollama pull gpt-oss:120b
```

### Issue: Tool calls not being parsed
**Solution**: The model might not be following the JSON format. Try:
1. Adjusting the system prompt
2. Using a different model that's better at structured output
3. Adding more examples in the prompt

### Issue: BAIS webhook errors
**Solution**: Check BAIS backend is running
```bash
curl https://bais-production.up.railway.app/api/v1/llm-webhooks/health
```

### Issue: Business not found
**Solution**: Ensure customer is registered
```bash
export RAILWAY_URL="https://bais-production.up.railway.app"
python3 scripts/submit_customer.py customers/NewLifeNewImage_CORRECTED_BAIS_Submission.json
```

## Advanced Configuration

### Custom Model
```bash
export OLLAMA_MODEL="llama3.1:8b"
python3 scripts/ollama_with_bais.py "find a med spa in Las Vegas"
```

### Custom Ollama Host
```bash
export OLLAMA_HOST="http://localhost:11434"
python3 scripts/ollama_with_bais.py "find a med spa in Las Vegas"
```

### Local BAIS Backend
```bash
export BAIS_WEBHOOK_URL="http://localhost:8000/api/v1/llm-webhooks/claude/tool-use"
export BAIS_TOOLS_URL="http://localhost:8000/api/v1/llm-webhooks/tools/definitions"
python3 scripts/ollama_with_bais.py "find a med spa in Las Vegas"
```

## Expected Output

When running successfully, you should see:

```
🤖 Ollama with BAIS Tools Enabled
   Model: gpt-oss:120b
   Host: http://golem:11434
============================================================

🔧 Loading BAIS tools...
✅ Loaded 3 BAIS tools

💬 Asking Ollama: find a med spa in Las Vegas

🔧 Ollama wants to use tool: bais_search_businesses
   Input: {
     "query": "med spa",
     "location": "Las Vegas"
   }

📡 Calling BAIS: bais_search_businesses...
✅ BAIS returned result
   Result preview: [{"business_id": "...", "name": "New Life New Image Med Spa", ...}]...

============================================================
✅ Ollama's Response:
============================================================

I found a med spa in Las Vegas: New Life New Image Med Spa...
```

## Notes

- The demo uses structured prompts since Ollama doesn't support native function calling
- Tool call parsing uses regex and JSON parsing - may need adjustment for different models
- The script handles up to 5 tool-call iterations to prevent infinite loops
- All tool calls are logged for debugging

## Next Steps

1. Test with different queries
2. Adjust system prompt for better tool calling
3. Add more businesses to test universal discovery
4. Create a web UI for the demo
5. Integrate with other LLM providers (ChatGPT, Gemini)

