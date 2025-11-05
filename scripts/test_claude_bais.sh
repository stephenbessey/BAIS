#!/bin/bash
# Test script for Claude + BAIS integration

echo "🧪 Testing Claude + BAIS Integration"
echo "=================================="
echo ""

# Get Railway URL from user if not set
if [ -z "$BAIS_WEBHOOK_URL" ]; then
    echo "Please enter your Railway URL (e.g., https://your-app.railway.app):"
    read RAILWAY_URL
    export BAIS_WEBHOOK_URL="${RAILWAY_URL}/api/v1/llm-webhooks/claude/tool-use"
    export BAIS_TOOLS_URL="${RAILWAY_URL}/api/v1/llm-webhooks/tools/definitions"
else
    echo "Using BAIS_WEBHOOK_URL: $BAIS_WEBHOOK_URL"
fi

# Test 1: Check if BAIS server is accessible
echo "1️⃣  Testing BAIS server connectivity..."
if curl -s -f "${BAIS_TOOLS_URL}" > /dev/null 2>&1; then
    echo "   ✅ BAIS server is accessible"
else
    echo "   ❌ Cannot reach BAIS server at ${BAIS_TOOLS_URL}"
    echo "   Make sure your Railway deployment is running!"
    exit 1
fi

# Test 2: Get tool definitions
echo ""
echo "2️⃣  Fetching BAIS tool definitions..."
TOOLS=$(curl -s "${BAIS_TOOLS_URL}")
if echo "$TOOLS" | grep -q "bais_search_businesses"; then
    echo "   ✅ Tool definitions loaded"
    echo "   Found tools:"
    echo "$TOOLS" | python3 -c "import sys, json; data=json.load(sys.stdin); [print(f'      - {t[\"name\"]}') for t in data.get('claude', [])]"
else
    echo "   ❌ Could not fetch tool definitions"
    exit 1
fi

# Test 3: Test direct BAIS search
echo ""
echo "3️⃣  Testing direct BAIS search..."
SEARCH_RESULT=$(curl -s -X POST "${BAIS_WEBHOOK_URL}" \
    -H "Content-Type: application/json" \
    -d '{"content": [{"name": "bais_search_businesses", "input": {"query": "New Life New Image", "location": "Las Vegas"}, "id": "test"}]}')

if echo "$SEARCH_RESULT" | grep -q "New Life New Image"; then
    echo "   ✅ BAIS search working - found your customer!"
else
    echo "   ⚠️  BAIS search completed but may not have found businesses"
    echo "   Result: $SEARCH_RESULT"
fi

# Test 4: Test Claude API with BAIS (if API key is set)
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "4️⃣  Testing Claude API with BAIS tools..."
    echo "   Query: 'find a med spa in Las Vegas'"
    echo ""
    python3 scripts/claude_with_bais.py "find a med spa in Las Vegas"
else
    echo ""
    echo "4️⃣  Skipping Claude API test (ANTHROPIC_API_KEY not set)"
    echo "   Set ANTHROPIC_API_KEY to test full integration"
fi

echo ""
echo "✅ Testing complete!"

