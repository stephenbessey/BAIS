#!/bin/bash
# Script to register the default business on Railway

RAILWAY_URL="${RAILWAY_URL:-https://bais-production.up.railway.app}"
CUSTOMER_FILE="customers/NewLifeNewImage_CORRECTED_BAIS_Submission.json"

echo "🚀 Registering business on Railway..."
echo "   URL: $RAILWAY_URL"
echo "   File: $CUSTOMER_FILE"
echo ""

python3 scripts/submit_customer.py "$CUSTOMER_FILE" "$RAILWAY_URL"

echo ""
echo "✅ Registration complete!"
echo ""
echo "To verify, check:"
echo "   curl $RAILWAY_URL/api/v1/businesses/new-life-new-image-med-spa"
echo ""

