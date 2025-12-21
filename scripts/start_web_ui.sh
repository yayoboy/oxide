#!/bin/bash
#
# Start Oxide Web UI
#
# This script builds the frontend (if needed) and starts the web backend.

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔬 Oxide Web UI Startup${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Frontend directory
FRONTEND_DIR="$PROJECT_ROOT/src/oxide/web/frontend"
DIST_DIR="$FRONTEND_DIR/dist"

# Check if frontend is built
if [ ! -d "$DIST_DIR" ]; then
    echo -e "${YELLOW}Frontend not built. Building now...${NC}"
    cd "$FRONTEND_DIR"
    npm run build
    echo -e "${GREEN}✓ Frontend built successfully${NC}"
    echo ""
else
    echo -e "${GREEN}✓ Frontend already built${NC}"
    echo ""
fi

# Start the web backend
echo -e "${GREEN}Starting web backend on http://localhost:8000${NC}"
echo ""

cd "$PROJECT_ROOT"
python3 -m uvicorn oxide.web.backend.main:app --host 0.0.0.0 --port 8000 --reload
