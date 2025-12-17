#!/usr/bin/env bash
#
# Ollama Remote Setup Script
#
# This script helps configure a remote Ollama instance on your LAN
# for distributed LLM processing with Oxide.
#
# Usage:
#   ./scripts/setup_ollama_remote.sh --ip 192.168.1.100 --port 11434
#

set -e

# Default values
REMOTE_IP=""
REMOTE_PORT="11434"
MODEL="qwen2.5-coder:7b"
CONFIG_FILE="config/default.yaml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --ip)
      REMOTE_IP="$2"
      shift 2
      ;;
    --port)
      REMOTE_PORT="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --help)
      echo "Ollama Remote Setup Script"
      echo ""
      echo "Usage: $0 --ip IP_ADDRESS [--port PORT] [--model MODEL]"
      echo ""
      echo "Options:"
      echo "  --ip      Remote server IP address (required)"
      echo "  --port    Ollama port (default: 11434)"
      echo "  --model   Model to use (default: qwen2.5-coder:7b)"
      echo "  --help    Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Validate required arguments
if [ -z "$REMOTE_IP" ]; then
  echo -e "${RED}Error: Remote IP address is required${NC}"
  echo "Usage: $0 --ip IP_ADDRESS [--port PORT]"
  exit 1
fi

REMOTE_URL="http://${REMOTE_IP}:${REMOTE_PORT}"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Oxide - Ollama Remote Setup${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "Remote server: ${GREEN}${REMOTE_URL}${NC}"
echo -e "Model: ${GREEN}${MODEL}${NC}"
echo ""

# Step 1: Test connectivity
echo -e "${YELLOW}[1/4] Testing connectivity to remote server...${NC}"
if curl -s --connect-timeout 5 "${REMOTE_URL}/api/tags" > /dev/null; then
  echo -e "${GREEN}✓ Successfully connected to ${REMOTE_URL}${NC}"
else
  echo -e "${RED}✗ Failed to connect to ${REMOTE_URL}${NC}"
  echo ""
  echo "Troubleshooting:"
  echo "1. Ensure Ollama is running on the remote server:"
  echo "   ${YELLOW}OLLAMA_HOST=0.0.0.0:${REMOTE_PORT} ollama serve${NC}"
  echo ""
  echo "2. Check firewall settings allow port ${REMOTE_PORT}"
  echo ""
  echo "3. Verify the IP address: ${REMOTE_IP}"
  exit 1
fi

# Step 2: Check available models
echo ""
echo -e "${YELLOW}[2/4] Checking available models on remote server...${NC}"
MODELS_JSON=$(curl -s "${REMOTE_URL}/api/tags")

if echo "$MODELS_JSON" | grep -q "\"models\""; then
  MODEL_COUNT=$(echo "$MODELS_JSON" | grep -o "\"name\"" | wc -l)
  echo -e "${GREEN}✓ Found ${MODEL_COUNT} model(s) on remote server${NC}"

  # Check if desired model exists
  if echo "$MODELS_JSON" | grep -q "\"${MODEL}\""; then
    echo -e "${GREEN}✓ Model '${MODEL}' is available${NC}"
  else
    echo -e "${YELLOW}! Model '${MODEL}' not found on remote server${NC}"
    echo ""
    echo "Available models:"
    echo "$MODELS_JSON" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | sed 's/^/  - /'
    echo ""
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Setup cancelled"
      exit 1
    fi
  fi
else
  echo -e "${RED}✗ Could not retrieve models list${NC}"
  exit 1
fi

# Step 3: Test model execution
echo ""
echo -e "${YELLOW}[3/4] Testing model execution...${NC}"
TEST_RESPONSE=$(curl -s -X POST "${REMOTE_URL}/api/generate" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"${MODEL}\", \"prompt\": \"Say hello\", \"stream\": false}" \
  --max-time 30)

if echo "$TEST_RESPONSE" | grep -q "\"response\""; then
  echo -e "${GREEN}✓ Model execution successful${NC}"
else
  echo -e "${RED}✗ Model execution failed${NC}"
  echo "Response: $TEST_RESPONSE"
  exit 1
fi

# Step 4: Update Oxide configuration
echo ""
echo -e "${YELLOW}[4/4] Updating Oxide configuration...${NC}"

if [ ! -f "$CONFIG_FILE" ]; then
  echo -e "${RED}✗ Configuration file not found: ${CONFIG_FILE}${NC}"
  exit 1
fi

# Backup config
cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"
echo -e "Created backup: ${CONFIG_FILE}.backup"

# Update ollama_remote configuration using Python
python3 << EOF
import yaml

with open("${CONFIG_FILE}", "r") as f:
    config = yaml.safe_load(f)

# Enable ollama_remote and update settings
if "services" in config and "ollama_remote" in config["services"]:
    config["services"]["ollama_remote"]["enabled"] = True
    config["services"]["ollama_remote"]["base_url"] = "${REMOTE_URL}"
    config["services"]["ollama_remote"]["default_model"] = "${MODEL}"

    with open("${CONFIG_FILE}", "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print("✓ Configuration updated")
else:
    print("✗ ollama_remote service not found in configuration")
    exit(1)
EOF

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Ollama remote service configured and enabled${NC}"
else
  echo -e "${RED}✗ Failed to update configuration${NC}"
  # Restore backup
  mv "${CONFIG_FILE}.backup" "$CONFIG_FILE"
  exit 1
fi

# Success
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Next steps:"
echo "1. Test the connection:"
echo "   ${YELLOW}uv run python scripts/test_connection.py --service ollama_remote${NC}"
echo ""
echo "2. Start Oxide and verify service status:"
echo "   ${YELLOW}uv run oxide-mcp${NC}"
echo ""
echo "3. View configuration:"
echo "   ${YELLOW}cat ${CONFIG_FILE}${NC}"
echo ""
