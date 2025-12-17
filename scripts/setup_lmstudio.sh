#!/usr/bin/env bash
#
# LM Studio Setup Script
#
# This script helps configure LM Studio on your LAN
# for distributed LLM processing with Oxide.
#
# Usage:
#   ./scripts/setup_lmstudio.sh --ip 192.168.1.50 --port 1234
#

set -e

# Default values
REMOTE_IP=""
REMOTE_PORT="1234"
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
    --help)
      echo "LM Studio Setup Script"
      echo ""
      echo "Usage: $0 --ip IP_ADDRESS [--port PORT]"
      echo ""
      echo "Options:"
      echo "  --ip      Remote server IP address (required)"
      echo "  --port    LM Studio port (default: 1234)"
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

BASE_URL="http://${REMOTE_IP}:${REMOTE_PORT}/v1"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Oxide - LM Studio Setup${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "LM Studio server: ${GREEN}${BASE_URL}${NC}"
echo ""

# Step 1: Test connectivity
echo -e "${YELLOW}[1/4] Testing connectivity to LM Studio...${NC}"
if curl -s --connect-timeout 5 "${BASE_URL}/models" > /dev/null; then
  echo -e "${GREEN}✓ Successfully connected to LM Studio${NC}"
else
  echo -e "${RED}✗ Failed to connect to ${BASE_URL}${NC}"
  echo ""
  echo "Troubleshooting:"
  echo "1. Ensure LM Studio is running on ${REMOTE_IP}"
  echo ""
  echo "2. In LM Studio:"
  echo "   - Go to Settings → Server"
  echo "   - Enable 'Local Server'"
  echo "   - Set Port to ${REMOTE_PORT}"
  echo "   - Enable 'Network Access' (allow LAN connections)"
  echo "   - Load a model"
  echo ""
  echo "3. Check firewall settings allow port ${REMOTE_PORT}"
  echo ""
  echo "4. Verify the IP address: ${REMOTE_IP}"
  exit 1
fi

# Step 2: Check available models
echo ""
echo -e "${YELLOW}[2/4] Checking loaded models...${NC}"
MODELS_JSON=$(curl -s "${BASE_URL}/models")

if echo "$MODELS_JSON" | grep -q "\"data\""; then
  MODEL_COUNT=$(echo "$MODELS_JSON" | grep -o "\"id\"" | wc -l)

  if [ "$MODEL_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}! No models currently loaded in LM Studio${NC}"
    echo ""
    echo "Please load a model in LM Studio before continuing:"
    echo "  1. Open LM Studio"
    echo "  2. Go to 'My Models' or 'Search'"
    echo "  3. Load a model (e.g., Qwen, CodeLlama, Llama)"
    echo "  4. Wait for the model to load"
    echo ""
    read -p "Press Enter when a model is loaded, or Ctrl+C to cancel: "

    # Retry
    MODELS_JSON=$(curl -s "${BASE_URL}/models")
    MODEL_COUNT=$(echo "$MODELS_JSON" | grep -o "\"id\"" | wc -l)

    if [ "$MODEL_COUNT" -eq 0 ]; then
      echo -e "${RED}✗ Still no models loaded${NC}"
      exit 1
    fi
  fi

  echo -e "${GREEN}✓ Found ${MODEL_COUNT} model(s) loaded${NC}"
  echo ""
  echo "Loaded models:"
  echo "$MODELS_JSON" | grep -o '"id":"[^"]*"' | sed 's/"id":"//g' | sed 's/"//g' | sed 's/^/  - /'

  # Get the first model ID for testing
  DEFAULT_MODEL=$(echo "$MODELS_JSON" | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"//g' | sed 's/"//g')
  echo ""
  echo -e "Using model for testing: ${GREEN}${DEFAULT_MODEL}${NC}"
else
  echo -e "${RED}✗ Could not retrieve models list${NC}"
  exit 1
fi

# Step 3: Test model execution
echo ""
echo -e "${YELLOW}[3/4] Testing model execution...${NC}"
TEST_RESPONSE=$(curl -s -X POST "${BASE_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${DEFAULT_MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Say hello\"}],
    \"max_tokens\": 50,
    \"stream\": false
  }" \
  --max-time 30)

if echo "$TEST_RESPONSE" | grep -q "\"choices\""; then
  echo -e "${GREEN}✓ Model execution successful${NC}"
  RESPONSE_TEXT=$(echo "$TEST_RESPONSE" | grep -o '"content":"[^"]*"' | head -1 | sed 's/"content":"//g' | sed 's/"//g')
  echo -e "Response: ${RESPONSE_TEXT}"
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

# Update lmstudio configuration using Python
python3 << EOF
import yaml

with open("${CONFIG_FILE}", "r") as f:
    config = yaml.safe_load(f)

# Enable lmstudio and update settings
if "services" in config and "lmstudio" in config["services"]:
    config["services"]["lmstudio"]["enabled"] = True
    config["services"]["lmstudio"]["base_url"] = "${BASE_URL}"
    # LM Studio auto-detects model, so default_model can be null

    with open("${CONFIG_FILE}", "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print("✓ Configuration updated")
else:
    print("✗ lmstudio service not found in configuration")
    exit(1)
EOF

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ LM Studio service configured and enabled${NC}"
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
echo "   ${YELLOW}uv run python scripts/test_connection.py --service lmstudio${NC}"
echo ""
echo "2. Start Oxide and verify service status:"
echo "   ${YELLOW}uv run oxide-mcp${NC}"
echo ""
echo "3. View configuration:"
echo "   ${YELLOW}cat ${CONFIG_FILE}${NC}"
echo ""
echo "Note: LM Studio automatically uses the loaded model."
echo "To change models, load a different model in LM Studio."
echo ""
