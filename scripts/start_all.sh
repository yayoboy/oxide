#!/usr/bin/env bash
#
# Start All Oxide Services
#
# Launches both MCP server and Web UI backend
# Use Ctrl+C to stop all services
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# PID file to track processes
PID_FILE="/tmp/oxide_pids.txt"

# Cleanup function
cleanup() {
    echo ""
    echo -e "${BLUE}Stopping all services...${NC}"

    if [ -f "$PID_FILE" ]; then
        while read pid; do
            if ps -p $pid > /dev/null 2>&1; then
                echo "Stopping process $pid..."
                kill $pid 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi

    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🚀 Starting Oxide Services${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Clear old PID file
rm -f "$PID_FILE"

# Start MCP server
echo -e "${GREEN}[1/2] Starting MCP Server...${NC}"
uv run oxide-mcp > /tmp/oxide-mcp.log 2>&1 &
MCP_PID=$!
echo $MCP_PID >> "$PID_FILE"
echo -e "   ✅ MCP Server started (PID: $MCP_PID)"
echo -e "   Log: /tmp/oxide-mcp.log"

# Wait a moment
sleep 2

# Start Web UI
echo ""
echo -e "${GREEN}[2/2] Starting Web UI Backend...${NC}"
uv run oxide-web > /tmp/oxide-web.log 2>&1 &
WEB_PID=$!
echo $WEB_PID >> "$PID_FILE"
echo -e "   ✅ Web UI Backend started (PID: $WEB_PID)"
echo -e "   Log: /tmp/oxide-web.log"

# Wait for Web UI to be ready
echo ""
echo -e "${BLUE}Waiting for Web UI to be ready...${NC}"
sleep 3

# Check if services are running
if ps -p $MCP_PID > /dev/null && ps -p $WEB_PID > /dev/null; then
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}✅ All Services Running!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo -e "📊 Services:"
    echo -e "   • MCP Server (PID: $MCP_PID)"
    echo -e "   • Web UI Backend (PID: $WEB_PID)"
    echo ""
    echo -e "🌐 URLs:"
    echo -e "   • API: http://localhost:8000"
    echo -e "   • Docs: http://localhost:8000/docs"
    echo ""
    echo -e "📝 Logs:"
    echo -e "   • MCP: /tmp/oxide-mcp.log"
    echo -e "   • Web: /tmp/oxide-web.log"
    echo ""
    echo -e "⚠️  Press ${RED}Ctrl+C${NC} to stop all services"
    echo ""

    # Wait for user interrupt
    wait
else
    echo -e "${RED}❌ Failed to start services${NC}"
    cleanup
fi
