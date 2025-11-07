#!/bin/bash
# Quick test script for Ollama + BAIS integration

set -e

echo "🧪 Testing Ollama + BAIS Integration"
echo "===================================="
echo ""

# Check if Ollama is reachable
echo "1. Testing Ollama connection..."
if curl -s --max-time 5 "${OLLAMA_HOST:-http://golem:11434}/api/tags" > /dev/null; then
    echo "   ✅ Ollama is reachable at ${OLLAMA_HOST:-http://golem:11434}"
else
    echo "   ❌ Ollama is not reachable at ${OLLAMA_HOST:-http://golem:11434}"
    echo "   Please ensure Ollama is running and accessible"
    exit 1
fi

# Check if model is available
echo ""
echo "2. Checking if model is available..."
MODEL="${OLLAMA_MODEL:-gpt-oss:120b}"
MODELS=$(curl -s "${OLLAMA_HOST:-http://golem:11434}/api/tags" | python3 -c "import sys, json; models = json.load(sys.stdin).get('models', []); print('\\n'.join([m.get('name', '') for m in models]))" 2>/dev/null || echo "")

if echo "$MODELS" | grep -q "$MODEL"; then
    echo "   ✅ Model '$MODEL' is available"
else
    echo "   ⚠️  Model '$MODEL' not found in available models"
    echo "   Available models:"
    echo "$MODELS" | sed 's/^/      - /'
    echo ""
    echo "   You may need to pull the model:"
    echo "   ollama pull $MODEL"
fi

# Check if BAIS backend is reachable
echo ""
echo "3. Testing BAIS backend connection..."
BAIS_URL="${BAIS_TOOLS_URL:-https://bais-production.up.railway.app/api/v1/llm-webhooks/tools/definitions}"
if curl -s --max-time 10 "$BAIS_URL" > /dev/null; then
    echo "   ✅ BAIS backend is reachable at $BAIS_URL"
else
    echo "   ❌ BAIS backend is not reachable at $BAIS_URL"
    echo "   Please check your network connection or BAIS deployment status"
    exit 1
fi

# Test BAIS tools endpoint
echo ""
echo "4. Testing BAIS tools endpoint..."
TOOLS_RESPONSE=$(curl -s "$BAIS_URL")
if echo "$TOOLS_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); assert 'tools' in data or 'claude' in data" 2>/dev/null; then
    echo "   ✅ BAIS tools endpoint returns valid data"
    TOOL_COUNT=$(echo "$TOOLS_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); tools = data.get('tools', {}).get('claude', data.get('claude', [])); print(len(tools))" 2>/dev/null || echo "?")
    echo "   Found $TOOL_COUNT tool definitions"
else
    echo "   ⚠️  BAIS tools endpoint response format unexpected"
    echo "   Response preview: ${TOOLS_RESPONSE:0:200}..."
fi

# Check Python dependencies
echo ""
echo "5. Checking Python dependencies..."
MISSING_DEPS=()
for dep in requests; do
    if ! python3 -c "import $dep" 2>/dev/null; then
        MISSING_DEPS+=("$dep")
    fi
done

if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
    echo "   ✅ All required dependencies are installed"
else
    echo "   ⚠️  Missing dependencies: ${MISSING_DEPS[*]}"
    echo "   Install with: pip3 install ${MISSING_DEPS[*]}"
fi

echo ""
echo "===================================="
echo "✅ Pre-flight checks complete!"
echo ""
echo "You can now run the demo with:"
echo "  python3 scripts/ollama_with_bais.py 'find a med spa in Las Vegas'"
echo ""

