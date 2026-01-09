#!/bin/bash
# Test script for Oxide cluster discovery and management

set -e

COMPOSE_FILE="docker-compose.test.yml"
BASE_URL_NODE1="http://localhost:8000"
BASE_URL_NODE2="http://localhost:8001"
BASE_URL_NODE3="http://localhost:8002"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Oxide Cluster Discovery Test Suite"
echo "=========================================="
echo ""

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS:${NC} $2"
    else
        echo -e "${RED}✗ FAIL:${NC} $2"
        exit 1
    fi
}

print_info() {
    echo -e "${YELLOW}ℹ INFO:${NC} $1"
}

# Step 1: Build and start cluster
print_info "Building Docker images..."
docker-compose -f $COMPOSE_FILE build

print_info "Starting cluster (3 nodes)..."
docker-compose -f $COMPOSE_FILE up -d

print_info "Waiting for nodes to start (30s)..."
sleep 30

# Step 2: Verify all nodes are healthy
print_info "Checking node health..."

for i in {1..3}; do
    port=$((7999 + i))
    response=$(curl -s http://localhost:$port/health || echo "ERROR")
    if echo "$response" | grep -q "healthy\|ok"; then
        print_result 0 "Node $i (port $port) is healthy"
    else
        print_result 1 "Node $i (port $port) is NOT healthy"
    fi
done

# Step 3: Wait for discovery to complete (3 broadcast cycles = 90s)
print_info "Waiting for discovery to complete (90s for 3 broadcast cycles)..."
sleep 90

# Step 4: Verify cluster discovery from each node
print_info "Testing cluster discovery..."

# Node 1 should see Node 2 and Node 3
response=$(curl -s $BASE_URL_NODE1/api/cluster/nodes)
node_count=$(echo "$response" | jq -r '.total_nodes // 0')
if [ "$node_count" -ge 2 ]; then
    print_result 0 "Node 1 discovered $node_count total nodes"
else
    print_result 1 "Node 1 should discover at least 2 nodes (found: $node_count)"
fi

# Node 2 should see Node 1 and Node 3
response=$(curl -s $BASE_URL_NODE2/api/cluster/nodes)
node_count=$(echo "$response" | jq -r '.total_nodes // 0')
if [ "$node_count" -ge 2 ]; then
    print_result 0 "Node 2 discovered $node_count total nodes"
else
    print_result 1 "Node 2 should discover at least 2 nodes (found: $node_count)"
fi

# Step 5: Verify health check endpoint
print_info "Testing health check endpoint..."

response=$(curl -s $BASE_URL_NODE1/api/cluster/health)
status=$(echo "$response" | jq -r '.status')
if [ "$status" = "healthy" ]; then
    print_result 0 "Health check endpoint returns healthy status"
else
    print_result 1 "Health check endpoint should return 'healthy' (got: $status)"
fi

# Step 6: Verify services matrix
print_info "Testing services matrix endpoint..."

response=$(curl -s $BASE_URL_NODE1/api/cluster/services-matrix)
total_nodes=$(echo "$response" | jq -r '.total_nodes // 0')
if [ "$total_nodes" -ge 1 ]; then
    print_result 0 "Services matrix shows $total_nodes nodes"

    # Display services found
    services=$(echo "$response" | jq -r '.services | keys[]' 2>/dev/null || echo "")
    if [ -n "$services" ]; then
        print_info "Services found in cluster:"
        echo "$services" | while read service; do
            echo "  - $service"
        done
    fi
else
    print_result 1 "Services matrix should show at least 1 node"
fi

# Step 7: Test node enable/disable
print_info "Testing node enable/disable functionality..."

# Get a remote node ID from node1
remote_node_id=$(curl -s $BASE_URL_NODE1/api/cluster/nodes | jq -r '.remote_nodes[0].node_id // ""')

if [ -n "$remote_node_id" ]; then
    print_info "Found remote node: $remote_node_id"

    # Disable the node
    response=$(curl -s -X POST $BASE_URL_NODE1/api/cluster/nodes/$remote_node_id/disable)
    if echo "$response" | jq -e '.enabled == false' > /dev/null 2>&1; then
        print_result 0 "Successfully disabled node $remote_node_id"
    else
        print_result 1 "Failed to disable node $remote_node_id"
    fi

    # Wait a bit
    sleep 2

    # Re-enable the node
    response=$(curl -s -X POST $BASE_URL_NODE1/api/cluster/nodes/$remote_node_id/enable)
    if echo "$response" | jq -e '.enabled == true' > /dev/null 2>&1; then
        print_result 0 "Successfully re-enabled node $remote_node_id"
    else
        print_result 1 "Failed to re-enable node $remote_node_id"
    fi
else
    print_info "Skipping enable/disable test (no remote nodes found)"
fi

# Step 8: Test persistence - restart node1 and verify it reloads discovered nodes
print_info "Testing persistence (restart node1)..."

docker-compose -f $COMPOSE_FILE restart oxide-node1

print_info "Waiting for node1 to restart (30s)..."
sleep 30

# Verify node1 still knows about other nodes
response=$(curl -s $BASE_URL_NODE1/api/cluster/nodes)
node_count=$(echo "$response" | jq -r '.total_nodes // 0')
if [ "$node_count" -ge 2 ]; then
    print_result 0 "Node 1 reloaded $node_count discovered nodes from database"
else
    print_result 1 "Node 1 should reload discovered nodes after restart (found: $node_count)"
fi

# Step 9: Test ping functionality
print_info "Testing node ping..."

if [ -n "$remote_node_id" ]; then
    response=$(curl -s -X POST $BASE_URL_NODE1/api/cluster/nodes/$remote_node_id/ping)
    reachable=$(echo "$response" | jq -r '.reachable')
    if [ "$reachable" = "true" ]; then
        latency=$(echo "$response" | jq -r '.latency_ms')
        print_result 0 "Successfully pinged remote node (latency: ${latency}ms)"
    else
        print_result 1 "Failed to ping remote node"
    fi
else
    print_info "Skipping ping test (no remote nodes found)"
fi

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}All tests passed!${NC}"
echo "=========================================="
echo ""
echo "Cluster is running with 3 nodes:"
echo "  - Node 1: $BASE_URL_NODE1"
echo "  - Node 2: $BASE_URL_NODE2"
echo "  - Node 3: $BASE_URL_NODE3"
echo ""
echo "Try these commands:"
echo "  curl $BASE_URL_NODE1/api/cluster/nodes | jq"
echo "  curl $BASE_URL_NODE1/api/cluster/health | jq"
echo "  curl $BASE_URL_NODE1/api/cluster/services-matrix | jq"
echo ""
echo "To stop the cluster:"
echo "  docker-compose -f $COMPOSE_FILE down -v"
echo ""
