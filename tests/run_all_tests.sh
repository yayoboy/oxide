#!/bin/bash

# Run all performance optimization tests
# Usage: ./tests/run_all_tests.sh

set -e  # Exit on error

echo "============================================================"
echo "🧪 Oxide Performance Optimizations - Full Test Suite"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo -e "${YELLOW}Running: $test_name${NC}"

    if eval "$test_command"; then
        echo -e "${GREEN}✅ $test_name PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ $test_name FAILED${NC}"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Navigate to project root
cd "$(dirname "$0")/.."

echo "📁 Working directory: $(pwd)"
echo ""

# Test 1: Python Syntax
echo "============================================================"
echo "Test Suite 1: Python Syntax Validation"
echo "============================================================"
run_test "metrics_cache.py syntax" "python3 -m py_compile src/oxide/utils/metrics_cache.py"
run_test "main.py syntax" "python3 -m py_compile src/oxide/web/backend/main.py"
run_test "monitoring.py syntax" "python3 -m py_compile src/oxide/web/backend/routes/monitoring.py"
run_test "websocket.py syntax" "python3 -m py_compile src/oxide/web/backend/websocket.py"

# Test 2: JavaScript Syntax
echo "============================================================"
echo "Test Suite 2: JavaScript Syntax Validation"
echo "============================================================"
run_test "useWebSocketStore.js syntax" "node --check src/oxide/web/frontend/src/stores/useWebSocketStore.js"
run_test "useServicesStore.js syntax" "node --check src/oxide/web/frontend/src/stores/useServicesStore.js"
run_test "useMetricsStore.js syntax" "node --check src/oxide/web/frontend/src/stores/useMetricsStore.js"
run_test "useTasksStore.js syntax" "node --check src/oxide/web/frontend/src/stores/useTasksStore.js"
run_test "useUIStore.js syntax" "node --check src/oxide/web/frontend/src/stores/useUIStore.js"
run_test "stores/index.js syntax" "node --check src/oxide/web/frontend/src/stores/index.js"

# Test 3: MetricsCache Functionality
echo "============================================================"
echo "Test Suite 3: MetricsCache Functionality"
echo "============================================================"
run_test "MetricsCache Tests" "uv run python tests/test_metrics_cache.py"

# Test 4: WebSocket Manager
echo "============================================================"
echo "Test Suite 4: WebSocket Manager"
echo "============================================================"
run_test "WebSocket Manager Tests" "uv run python tests/test_websocket_manager.py"

# Test 5: Backend Integration
echo "============================================================"
echo "Test Suite 5: Backend Integration"
echo "============================================================"
run_test "Backend Integration Tests" "uv run python tests/test_backend_integration.py"

# Summary
echo "============================================================"
echo "📊 Test Results Summary"
echo "============================================================"
echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"
else
    echo -e "${GREEN}❌ Tests Failed: $TESTS_FAILED${NC}"
fi
echo "📝 Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

# Final verdict
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo "✅ Performance optimizations are working correctly"
    echo "✅ Backend is ready for deployment"
    echo "✅ Frontend stores are syntactically correct"
    echo ""
    echo "Next steps:"
    echo "  1. Start the development server: ./scripts/start_web_ui.sh"
    echo "  2. Migrate components using STORE_MIGRATION.md"
    echo "  3. Add React.memo to frequently rendered components"
    echo ""
    exit 0
else
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}============================================================${NC}"
    echo ""
    echo "Please review the failed tests above and fix the issues."
    echo ""
    exit 1
fi
