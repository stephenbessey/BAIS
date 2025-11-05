#!/bin/bash
# Test script for Claude booking flow

BASE_URL="http://localhost:8000"
BUSINESS_ID="new-life-new-image-med-spa-077db44b"

echo "🧪 Testing Claude Booking Flow"
echo "=============================="
echo ""

echo "1️⃣  Searching for business..."
curl -s -X POST "$BASE_URL/api/v1/search/businesses" \
  -H "Content-Type: application/json" \
  -d '{"query": "New Life New Image Med Spa", "location": "Las Vegas"}' | python3 -m json.tool
echo ""
echo ""

echo "2️⃣  Getting available services..."
curl -s "$BASE_URL/api/v1/businesses/$BUSINESS_ID/services" | python3 -m json.tool | head -30
echo ""
echo ""

echo "3️⃣  Checking availability for Botox..."
curl -s "$BASE_URL/api/v1/businesses/$BUSINESS_ID/services/neurotoxin/availability?date=2025-11-07&time=14:00" | python3 -m json.tool
echo ""
echo ""

echo "4️⃣  Creating test booking..."
BOOKING_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/bookings" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "'$BUSINESS_ID'",
    "service_id": "neurotoxin",
    "appointment_date": "2025-11-07",
    "appointment_time": "14:00",
    "patient_name": "Test Patient",
    "phone_number": "+1-555-123-4567",
    "email": "test@example.com",
    "parameters": {
      "neurotoxin_type": "botox",
      "treatment_areas": ["forehead", "crow'\''s feet"],
      "units_needed": 50,
      "previous_neurotoxin": false
    }
  }')

echo "$BOOKING_RESPONSE" | python3 -m json.tool
echo ""
echo ""

BOOKING_ID=$(echo "$BOOKING_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('booking_id', ''))")

if [ -n "$BOOKING_ID" ]; then
  echo "5️⃣  Retrieving booking details..."
  curl -s "$BASE_URL/api/v1/bookings/$BOOKING_ID" | python3 -m json.tool
  echo ""
  echo ""
  echo "✅ Booking flow test complete!"
else
  echo "❌ Failed to create booking"
fi

