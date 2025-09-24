#!/bin/bash

echo "=================================="
echo "BAIS Performance Test Suite"
echo "=================================="
echo ""

# Create reports directory
mkdir -p performance-tests/reports/final

echo "1. Running Baseline Tests..."
python performance-tests/baseline_test.py > performance-tests/reports/final/01-baseline.txt

echo "2. Running Load Tests..."
locust -f performance-tests/locust_load_test.py \
    --config performance-tests/configs/sustained.conf \
    --html performance-tests/reports/final/02-load-test.html \
    --csv performance-tests/reports/final/02-load-test

echo "3. Running Payment Workflow Benchmark..."
python performance-tests/payment_workflow_benchmark.py > performance-tests/reports/final/03-payment-benchmark.txt

echo "4. Running Cache Performance Tests..."
python performance-tests/test_caching_performance.py > performance-tests/reports/final/04-cache-performance.txt

echo "5. Running Database Performance Audit..."
python performance-tests/database_performance_audit.py > performance-tests/reports/final/05-database-audit.txt

echo "6. Running Memory Profile..."
python performance-tests/memory_profiler.py > performance-tests/reports/final/06-memory-profile.txt

echo "7. Generating Final Report..."
python performance-tests/generate_final_report.py

echo ""
echo "✅ All performance tests complete!"
echo "📊 Reports available in: performance-tests/reports/final/"
