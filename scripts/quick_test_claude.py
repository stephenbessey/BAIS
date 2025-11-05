#!/usr/bin/env python3
"""
Quick test script for Claude + BAIS integration
"""

import os
import sys

# Your Railway URL (update this)
RAILWAY_URL = os.getenv("RAILWAY_URL", "")

if not RAILWAY_URL:
    print("Please enter your Railway URL:")
    print("Example: https://your-app.railway.app")
    RAILWAY_URL = input("Railway URL: ").strip()
    if not RAILWAY_URL.startswith("http"):
        RAILWAY_URL = f"https://{RAILWAY_URL}"

# Set environment variables
os.environ["BAIS_WEBHOOK_URL"] = f"{RAILWAY_URL}/api/v1/llm-webhooks/claude/tool-use"
os.environ["BAIS_TOOLS_URL"] = f"{RAILWAY_URL}/api/v1/llm-webhooks/tools/definitions"

# Get API key from environment or prompt user
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("\n⚠️  ANTHROPIC_API_KEY not found in environment.")
    print("Please set it as an environment variable:")
    print("  export ANTHROPIC_API_KEY='your-key-here'")
    print("\nOr enter it now (will not be saved):")
    ANTHROPIC_API_KEY = input("Anthropic API Key: ").strip()
    if not ANTHROPIC_API_KEY:
        print("❌ API key required. Exiting.")
        sys.exit(1)

os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

# Import and run the main script
from claude_with_bais import ask_claude_with_bais

print("\n" + "="*60)
print("🧪 Testing Claude + BAIS Integration")
print("="*60)
print(f"\n📍 Railway URL: {RAILWAY_URL}")
print(f"🔑 API Key: Set")
print()

# Test query
query = "find a med spa in Las Vegas that offers Botox treatments"
print(f"💬 Query: {query}")
print()

result = ask_claude_with_bais(query)

print("\n" + "="*60)
print("✅ RESULT:")
print("="*60)
print(result)
print()

