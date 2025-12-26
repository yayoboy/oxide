# Oxide Configuration Guide

Complete reference for configuring Oxide LLM Orchestrator.

## Table of Contents

1. [Configuration Files](#configuration-files)
2. [default.yaml Reference](#defaultyaml-reference)
3. [models.yaml Reference](#modelsyaml-reference)
4. [Service Configuration](#service-configuration)
5. [Routing Rules](#routing-rules)
6. [Advanced Configuration](#advanced-configuration)
7. [Configuration Validation](#configuration-validation)
8. [Hot Reload](#hot-reload)

---

## Configuration Files

Oxide uses two main YAML configuration files:

| File | Purpose | Location |
|------|---------|----------|
| **default.yaml** | Main configuration for services, routing, and system settings | `config/default.yaml` |
| **models.yaml** | Model capability profiles and optimization guidance | `config/models.yaml` |

### File Locations

```bash
oxide/
├── config/
│   ├── default.yaml    # Main configuration
│   └── models.yaml     # Model profiles
```

---

## default.yaml Reference

### Services Section

Configure LLM services (CLI tools and HTTP APIs).

#### CLI Service Configuration

```yaml
services:
  gemini:
    type: cli                    # Service type: 'cli' or 'http'
    executable: gemini           # Command to execute (must be in PATH)
    enabled: true                # Enable/disable service
    max_context_tokens: 2000000  # Maximum context window
    capabilities:                # Service capabilities (for routing)
      - codebase_analysis
      - architecture_design
      - multi_file_context
```

**Required fields for CLI services:**
- `type: cli`
- `executable` - Command name (e.g., `gemini`, `qwen`)
- `enabled` - Boolean flag

**Optional fields:**
- `max_context_tokens` - Maximum tokens for context window
- `capabilities` - List of task types this service excels at

#### HTTP Service Configuration (Ollama)

```yaml
services:
  ollama_local:
    type: http
    base_url: "http://localhost:11434"
    api_type: ollama             # 'ollama' or 'openai_compatible'
    enabled: true

    # Model configuration
    default_model: "qwen2.5-coder:7b"
    models:
      - "qwen2.5-coder:7b"
      - "qwen2.5-coder:14b"
      - "qwen3-coder:latest"

    # Auto-start and recovery
    auto_start: true             # Auto-start service if not running
    auto_detect_model: true      # Auto-detect model if default fails
    max_retries: 2               # Retry attempts on failure
    retry_delay: 2               # Seconds between retries

    capabilities:
      - quick_query
      - code_generation
      - documentation
```

**Required fields for HTTP services:**
- `type: http`
- `base_url` - Full URL including port
- `api_type` - Either `ollama` or `openai_compatible`
- `enabled` - Boolean flag

**Optional fields:**
- `default_model` - Model to use (null for auto-detection)
- `models` - List of available models
- `auto_start` - Auto-start service (only for local Ollama)
- `auto_detect_model` - Fallback to any available model
- `max_retries` - Retry attempts (default: 2)
- `retry_delay` - Delay between retries in seconds (default: 2)
- `preferred_models` - List of model names in priority order (for LM Studio)
- `capabilities` - List of task types

#### HTTP Service Configuration (LM Studio)

```yaml
services:
  lmstudio:
    type: http
    base_url: "http://192.168.1.33:1234/v1"  # LM Studio OpenAI-compatible endpoint
    api_type: openai_compatible
    enabled: true

    # Model detection (CRITICAL for LM Studio)
    default_model: null          # Always null - LM Studio requires auto-detection
    auto_start: false            # Cannot auto-start remote LM Studio
    auto_detect_model: true      # REQUIRED: Must be true
    max_retries: 2
    retry_delay: 2

    # Preferred models (in priority order)
    preferred_models:
      - "qwen"
      - "coder"
      - "codellama"
      - "deepseek"
```

**LM Studio Specific Notes:**
- **ALWAYS** set `auto_detect_model: true` - LM Studio doesn't persist model names
- Use `preferred_models` to prioritize which model to select
- The adapter will query `/v1/models` endpoint to find loaded model
- Best match from `preferred_models` will be selected

**How Preferred Models Work:**
1. **Exact Match**: If a preferred model name exactly matches an available model, it's selected immediately
2. **Partial Match**: If no exact match, searches for models containing the preferred name (case-insensitive)
   - Example: `"qwen"` matches `"qwen2.5-coder-7b"`
   - Example: `"coder"` matches `"qwen2.5-coder-7b"` or `"deepseek-coder-6.7b"`
3. **Priority Order**: Checks preferred models in the order specified
4. **Fallback**: If no preferred models match, selects the first available model

**Common Error Messages:**

*Connection Refused:*
```
Cannot connect to lmstudio at http://localhost:1234
Please check:
  1. Is LM Studio running?
  2. Is the server started in LM Studio (Local Server tab)?
  3. Is the base_url correct in your configuration?
  4. Is the port accessible? (Network/firewall issues)
```

*Model Not Found:*
```
Model 'qwen2.5-coder-7b' not found in lmstudio.
Please ensure the model is loaded in LM Studio.
Available models can be checked via the web UI.
```

*Server Error (500):*
```
lmstudio internal error. This may indicate the model crashed or ran out of memory.
Try restarting LM Studio or loading a smaller model.
```

**Troubleshooting:**
- Verify LM Studio is running and server is started (green indicator in Local Server tab)
- Check the base_url includes `/v1` prefix for OpenAI-compatible API
- Ensure at least one model is loaded in LM Studio
- For memory issues, try a smaller/quantized model (7B instead of 13B, Q4 instead of Q8)
- Check firewall settings if connecting to remote LM Studio instance

### Routing Rules Section

Define how tasks are routed to services based on task type.

```yaml
routing_rules:
  # Task type as key
  code_review:
    primary: qwen                # Primary service to use
    fallback:                    # Fallback services (in order)
      - ollama_local
      - ollama_remote
    timeout_seconds: 60          # Task timeout (optional)

  codebase_analysis:
    primary: gemini
    fallback:
      - qwen
      - ollama_local
    parallel_threshold_files: 20  # Use parallel execution if >20 files
    timeout_seconds: 180
```

**Fields:**
- `primary` (required) - Primary service name (must exist in `services`)
- `fallback` (optional) - List of fallback service names
- `timeout_seconds` (optional) - Override default timeout for this task type
- `parallel_threshold_files` (optional) - Enable parallel execution threshold

**Available task types:**
- `codebase_analysis` - Large codebase analysis
- `code_review` - Code quality review
- `code_generation` - Writing new code
- `quick_query` - Fast question answering
- `architecture_design` - System design
- `debugging` - Finding and fixing bugs
- `documentation` - Writing docs
- `refactoring` - Code refactoring

### Execution Settings

```yaml
execution:
  max_parallel_workers: 4       # Maximum parallel task workers
  timeout_seconds: 120          # Default timeout for all tasks
  streaming: true               # Enable streaming responses
  retry_on_failure: true        # Retry failed tasks
  max_retries: 5                # Maximum retry attempts
```

### Logging Configuration

```yaml
logging:
  level: INFO                   # Log level: DEBUG, INFO, WARNING, ERROR
  file: /tmp/oxide.log          # Log file path (null to disable)
  console: true                 # Enable console logging
```

### Memory Configuration

```yaml
memory:
  enabled: true                           # Enable context memory
  storage_path: ~/.oxide/memory.json      # Storage location
  max_conversations: 1000                 # Max conversations to store
  max_age_days: 30                        # Auto-prune older than this
  max_messages_per_conversation: 100      # Limit per conversation
  auto_prune_enabled: true                # Enable auto-pruning
  similarity_threshold: 0.5               # Minimum similarity for retrieval
```

**Memory features:**
- Persistent conversation history
- Context retrieval based on similarity
- Automatic pruning of old conversations
- Metadata storage for tracking

### Cluster Configuration

```yaml
cluster:
  enabled: false                # Enable multi-machine coordination
  broadcast_port: 8888          # UDP port for node discovery
  api_port: 8000                # HTTP API port
  discovery_interval: 30        # Seconds between discovery broadcasts
  load_balancing: true          # Enable load-based routing
```

**Cluster features:**
- Auto-discovery via UDP broadcast
- Load-based task distribution
- Remote task execution
- Health monitoring

---

## models.yaml Reference

Model capability profiles for optimization guidance.

```yaml
model_profiles:
  gemini:
    name: "Google Gemini"
    strengths:
      - "Large context window (2M+ tokens)"
      - "Multi-file analysis capability"
      - "Excellent architectural understanding"
    weaknesses:
      - "Higher latency compared to local models"
      - "Network dependency"
    optimal_for:
      - "Analyzing entire codebases (100+ files)"
      - "Understanding system architecture"
      - "Large-scale refactoring planning"
```

**Fields:**
- `name` - Human-readable model name
- `strengths` - List of model advantages
- `weaknesses` - List of model limitations
- `optimal_for` - Best use cases

**Purpose:**
- Documentation and guidance
- Not used by routing system (use `routing_rules` instead)
- Helps users understand when to use each model

---

## Service Configuration

### Service Types

#### 1. CLI Services

CLI services execute command-line tools like `gemini` or `qwen`.

**Configuration:**
```yaml
service_name:
  type: cli
  executable: command_name
  enabled: true
```

**Requirements:**
- Command must be in PATH
- Must support streaming output
- Should accept prompt as argument

**Examples:**
- Gemini CLI (`gemini -p "prompt"`)
- Qwen CLI (`qwen -p "prompt"`)

#### 2. HTTP Services (Ollama)

Ollama provides a local HTTP API for LLM inference.

**Configuration:**
```yaml
ollama_local:
  type: http
  base_url: "http://localhost:11434"
  api_type: ollama
  default_model: "qwen2.5-coder:7b"
  auto_start: true
  auto_detect_model: true
```

**Auto-start feature:**
- Detects if Ollama is running
- Attempts to start Ollama if not running
- Platform-specific start commands:
  - macOS: `open -a Ollama` or `ollama serve`
  - Linux: `systemctl start ollama` or `ollama serve`
  - Windows: Starts Ollama.exe

**Auto-detect model:**
- If `default_model` fails, tries other models in `models` list
- If no models specified, uses first available model
- Queries `/api/tags` to get available models

#### 3. HTTP Services (LM Studio)

LM Studio provides OpenAI-compatible API.

**Configuration:**
```yaml
lmstudio:
  type: http
  base_url: "http://192.168.1.33:1234/v1"
  api_type: openai_compatible
  default_model: null           # Always null
  auto_detect_model: true       # Always true
  preferred_models:
    - "qwen"
    - "coder"
```

**Important:**
- LM Studio doesn't persist model names
- Must use auto-detection every time
- Queries `/v1/models` endpoint
- Selects best match from `preferred_models`

---

## Routing Rules

### How Routing Works

1. **Task Classification** - Oxide classifies the task type
2. **Primary Service** - Tries primary service first
3. **Fallback Chain** - If primary fails, tries fallbacks in order
4. **Retry Logic** - Retries failed requests (configurable)

### Creating Routing Rules

```yaml
routing_rules:
  task_type:
    primary: service_name
    fallback:
      - fallback1
      - fallback2
    timeout_seconds: 60
```

**Best Practices:**
- Put fastest/cheapest service as primary for quick tasks
- Put most capable service as primary for complex tasks
- Order fallbacks by capability and availability
- Set appropriate timeouts for each task type

### Example Configurations

#### Cost-Optimized (Prefer Local)
```yaml
code_review:
  primary: ollama_local      # Free and fast
  fallback:
    - qwen                   # CLI fallback
    - gemini                 # Cloud fallback
```

#### Quality-Optimized (Prefer Cloud)
```yaml
code_review:
  primary: gemini            # Best quality
  fallback:
    - qwen                   # Good fallback
    - ollama_local           # Last resort
```

#### Speed-Optimized (Local Only)
```yaml
quick_query:
  primary: ollama_local      # Fastest
  fallback:
    - lmstudio               # Another local option
```

---

## Advanced Configuration

### Environment-Specific Configs

Create different configs for different environments:

```bash
config/
├── default.yaml          # Development config
├── production.yaml       # Production config
└── local.yaml            # Local-only config
```

Load specific config:
```python
from oxide.config.loader import load_config
from pathlib import Path

config = load_config(Path("config/production.yaml"))
```

### Service Priority by Capability

Match services to task capabilities:

```yaml
services:
  gemini:
    capabilities:
      - codebase_analysis
      - architecture_design

  qwen:
    capabilities:
      - code_review
      - code_generation
      - debugging

routing_rules:
  # Route to service with matching capability
  codebase_analysis:
    primary: gemini        # Has codebase_analysis capability

  code_review:
    primary: qwen          # Has code_review capability
```

### Timeout Configuration

Set timeouts at multiple levels:

```yaml
# Global default timeout
execution:
  timeout_seconds: 120

# Task-specific timeout
routing_rules:
  quick_query:
    timeout_seconds: 10      # Override for fast tasks

  codebase_analysis:
    timeout_seconds: 300     # Override for slow tasks
```

**Priority (highest to lowest):**
1. Task-specific timeout in routing rule
2. Global execution timeout
3. Hard-coded default (120s)

---

## Configuration Validation

### Automatic Validation

Oxide validates configuration on load using Pydantic schemas.

**Validation checks:**
- ✅ At least one service is enabled
- ✅ CLI services have `executable` defined
- ✅ HTTP services have `base_url` defined
- ✅ Routing rules reference existing services
- ✅ YAML syntax is correct
- ✅ Required fields are present

### Validation Errors

**Example error:**
```
ConfigError: Routing rule for 'code_review' references unknown primary service: nonexistent_service
```

**How to fix:**
1. Check spelling of service name
2. Ensure service is defined in `services` section
3. Check that service name matches exactly (case-sensitive)

### Manual Validation

Validate config without starting Oxide:

```python
from oxide.config.loader import load_config
from pathlib import Path

try:
    config = load_config(Path("config/default.yaml"))
    print("✅ Configuration is valid!")
except Exception as e:
    print(f"❌ Configuration error: {e}")
```

---

## Hot Reload

### Enabling Hot Reload

Hot reload allows configuration changes without restarting Oxide.

**Configuration:**
```yaml
# Add to default.yaml (future feature)
hot_reload:
  enabled: true
  watch_interval: 5        # Check for changes every 5 seconds
  auto_reload: true        # Automatically reload on change
```

### What Gets Reloaded

**Hot reloadable:**
- ✅ Service enable/disable
- ✅ Routing rules
- ✅ Timeouts
- ✅ Logging settings
- ✅ Memory settings

**Not hot reloadable (requires restart):**
- ❌ Service type changes (CLI ↔ HTTP)
- ❌ Service URLs/executables
- ❌ API types
- ❌ Cluster settings

### Manual Reload

Trigger reload via API:

```bash
# Reload configuration
curl -X POST http://localhost:8000/api/config/reload

# Response:
{
  "status": "reloaded",
  "changes": {
    "services_changed": ["ollama_local"],
    "routing_rules_changed": ["code_review"]
  }
}
```

### Web UI Reload

Access configuration panel in web UI:
1. Navigate to **Settings** → **Configuration**
2. Click **Reload Configuration**
3. Review changes before applying

---

## Common Configuration Patterns

### Pattern 1: Local Development

Fast, free, private local inference:

```yaml
services:
  ollama_local:
    enabled: true
    auto_start: true

  gemini:
    enabled: false       # Disable cloud for privacy

  qwen:
    enabled: false

routing_rules:
  code_review:
    primary: ollama_local
  code_generation:
    primary: ollama_local
```

### Pattern 2: Cloud-First

Best quality, don't care about cost:

```yaml
services:
  gemini:
    enabled: true
  qwen:
    enabled: true
  ollama_local:
    enabled: false       # Disable local

routing_rules:
  code_review:
    primary: gemini
    fallback: [qwen]
```

### Pattern 3: Hybrid (Recommended)

Balance speed, quality, and cost:

```yaml
services:
  gemini: { enabled: true }
  qwen: { enabled: true }
  ollama_local: { enabled: true, auto_start: true }

routing_rules:
  # Fast tasks → local
  quick_query:
    primary: ollama_local
    fallback: [qwen]

  # Quality tasks → cloud
  code_review:
    primary: qwen
    fallback: [ollama_local, gemini]

  # Large tasks → high-context
  codebase_analysis:
    primary: gemini
    fallback: [qwen, ollama_local]
```

### Pattern 4: Multi-Machine Cluster

Distributed processing across LAN:

```yaml
# Machine 1 (main)
cluster:
  enabled: true
  api_port: 8000

services:
  ollama_local: { enabled: true }
  gemini: { enabled: true }
```

```yaml
# Machine 2 (worker)
cluster:
  enabled: true
  api_port: 8001

services:
  ollama_remote: { enabled: true, base_url: "http://192.168.1.46:11434" }
```

---

## Troubleshooting

### Service Won't Start

**Problem:** Service shows as unhealthy

**Solutions:**
1. Check if executable is in PATH (for CLI services)
2. Check if URL is reachable (for HTTP services)
3. Check logs: `tail -f /tmp/oxide.log`
4. Test manually: `gemini -p "test"` or `curl http://localhost:11434/api/tags`

### Routing Not Working

**Problem:** Tasks always go to fallback

**Solutions:**
1. Check primary service is enabled
2. Check primary service is healthy
3. Review routing rules match task type
4. Check service capabilities

### Configuration Not Loading

**Problem:** Changes don't take effect

**Solutions:**
1. Restart Oxide (if hot reload not enabled)
2. Check YAML syntax: `yamllint config/default.yaml`
3. Check validation errors in logs
4. Use config API to view current config

---

## Configuration API

### View Current Configuration

```bash
# Get full configuration
GET /api/config

# Response:
{
  "services": { ... },
  "routing_rules": { ... },
  "execution": { ... }
}
```

### Update Configuration

```bash
# Update specific service
PATCH /api/config/services/ollama_local
{
  "enabled": false
}

# Update routing rule
PATCH /api/config/routing_rules/code_review
{
  "primary": "gemini"
}
```

### Validate Configuration

```bash
# Validate configuration changes
POST /api/config/validate
{
  "services": { ... }
}

# Response:
{
  "valid": true,
  "errors": []
}
```

---

## Best Practices

### 1. Start Simple

Begin with minimal config and add complexity as needed:

```yaml
services:
  ollama_local:
    type: http
    base_url: "http://localhost:11434"
    api_type: ollama
    enabled: true

routing_rules:
  code_review:
    primary: ollama_local
```

### 2. Use Auto-Detection

Let Oxide detect models automatically:

```yaml
ollama_local:
  default_model: null        # Let Oxide choose
  auto_detect_model: true
```

### 3. Set Appropriate Timeouts

Match timeouts to task complexity:
- Quick queries: 10-30s
- Code generation: 30-60s
- Code review: 60-120s
- Codebase analysis: 120-300s

### 4. Enable Retries

Always enable retries for production:

```yaml
execution:
  retry_on_failure: true
  max_retries: 3
```

### 5. Monitor and Adjust

Use metrics to optimize configuration:
- Track success rates per service
- Measure response times
- Monitor costs (if using cloud services)
- Adjust routing based on performance

---

## Summary

### Quick Reference

| Config File | Purpose |
|-------------|---------|
| `default.yaml` | Main configuration |
| `models.yaml` | Model capability profiles |

### Key Sections

| Section | Purpose |
|---------|---------|
| `services` | Define LLM services |
| `routing_rules` | Task routing logic |
| `execution` | Execution settings |
| `logging` | Logging configuration |
| `memory` | Context memory settings |
| `cluster` | Multi-machine setup |

### Important Concepts

- **Service Types**: CLI or HTTP
- **Auto-start**: Ollama can start automatically
- **Auto-detect**: Models can be detected automatically
- **Routing**: Primary service with fallback chain
- **Hot Reload**: Configuration changes without restart (future)
- **Validation**: Automatic validation on load

---

## Next Steps

1. **Review examples** in this guide
2. **Customize** `config/default.yaml` for your needs
3. **Test** services with health checks
4. **Monitor** performance and adjust routing
5. **Enable hot reload** for dynamic adjustments

For more help, see:
- [API Documentation](./api.md)
- [Service Health Monitoring](./monitoring.md)
- [Troubleshooting Guide](./troubleshooting.md)
