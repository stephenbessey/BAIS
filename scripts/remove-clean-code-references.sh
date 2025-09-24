#!/bin/bash

echo "🧹 Removing 'Clean Code' references from project files..."
echo "======================================================="

# List of files to update
files=(
    "./backend/production/core/payments/currency_manager.py"
    "./backend/production/core/mcp_sse_transport.py"
    "./backend/production/tests/test_cross_protocol_integration.py"
    "./backend/production/tests/conftest.py"
    "./backend/production/api/v1/mcp/subscription_router.py"
    "./backend/production/core/unified_error_handler.py"
    "./backend/production/api/v1/errors/unified_error_router.py"
    "./backend/production/api/v1/a2a/sse_router.py"
    "./backend/production/api/v1/mcp/prompts_router.py"
    "./backend/production/core/mcp_prompts.py"
    "./backend/production/api/v1/mcp/sse_router.py"
    "./backend/production/middleware/security_middleware.py"
    "./backend/production/core/mcp_graceful_shutdown.py"
    "./backend/production/core/mcp_audit_logger.py"
    "./backend/production/tests/test_mcp_protocol_compliance.py"
    "./backend/production/core/mcp_monitoring.py"
    "./backend/production/config/mcp_settings.py"
    "./backend/production/core/mcp_route_handlers.py"
    "./backend/production/core/mcp_input_validation.py"
    "./backend/production/core/mcp_authentication_service.py"
    "./backend/production/core/mcp_error_handler.py"
    "./backend/production/core/payments/business_validator.py"
    "./backend/production/core/payments/payment_event_publisher.py"
    "./backend/production/core/payments/cryptographic_mandate_validator.py"
    "./backend/production/core/a2a_agent_card_generator.py"
    "./backend/production/core/workflow_state_manager.py"
    "./backend/production/tests/integration/test_a2a_ap2_integration.py"
    "./backend/production/core/protocol_error_handler.py"
    "./backend/production/config/protocol_settings.py"
    "./backend/production/core/a2a_dependency_injection.py"
    "./backend/production/services/agent_service.py"
)

# Function to update a file
update_file() {
    local file=$1
    echo "Updating: $file"
    
    if [ -f "$file" ]; then
        # Replace various Clean Code references
        sed -i '' 's/Clean Code Implementation/Implementation/g' "$file"
        sed -i '' 's/following Clean Code principles/following best practices/g' "$file"
        sed -i '' 's/Clean Code principles/best practices/g' "$file"
        sed -i '' 's/ - Clean Code//g' "$file"
        sed -i '' 's/Clean Code Implementation/Implementation/g' "$file"
        sed -i '' 's/Comprehensive.*following Clean Code principles/Comprehensive implementation following best practices/g' "$file"
        
        echo "✅ Updated: $file"
    else
        echo "❌ File not found: $file"
    fi
}

# Update all files
for file in "${files[@]}"; do
    update_file "$file"
done

echo ""
echo "🎉 Clean Code references removal complete!"
echo "=========================================="
echo ""
echo "✅ All files updated to remove explicit 'Clean Code' references"
echo "✅ Maintained all clean code principles and practices"
echo "✅ Updated documentation to use 'best practices' terminology"
echo ""
echo "The codebase now follows clean code principles without explicit references."
