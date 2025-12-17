# Oxide Installation & Integration Guide

Complete guide to installing and integrating Oxide with Claude Code.

## Prerequisites

- **Python 3.11+** installed on your system
- **uv** package manager (recommended) or pip
- **Claude Code** installed
- Optional: Gemini CLI, Qwen CLI, Ollama

## Installation

### Step 1: Install Dependencies

```bash
cd /Users/yayoboy/Documents/GitHub/oxide

# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### Step 2: Verify Installation

Test that Oxide is installed correctly:

```bash
# Validate configuration
uv run python scripts/validate_config.py

# Test MCP server
uv run oxide-mcp --help
```

## Configuration

### Step 3: Configure Services

Edit `config/default.yaml` to enable/disable services and configure endpoints:

```yaml
services:
  # Local services
  gemini:
    type: cli
    executable: gemini  # Must be in PATH
    enabled: true

  qwen:
    type: cli
    executable: qwen    # Must be in PATH
    enabled: true

  ollama_local:
    type: http
    base_url: "http://localhost:11434"
    enabled: true
    default_model: "qwen2.5-coder:7b"

  # Network services (configure IPs)
  ollama_remote:
    type: http
    base_url: "http://192.168.1.100:11434"
    enabled: false  # Enable after setup

  lmstudio:
    type: http
    base_url: "http://192.168.1.50:1234/v1"
    enabled: false  # Enable after setup
```

### Step 4: Test Service Connections

Test connectivity to your LLM services:

```bash
# Test all services
uv run python scripts/test_connection.py

# Test specific service
uv run python scripts/test_connection.py --service gemini

# Detailed test with sample prompts
uv run python scripts/test_connection.py --all
```

## Integration with Claude Code

### Step 5: Add Oxide to Claude Settings

Add Oxide MCP server to Claude Code's settings:

**Location**: `~/.claude/settings.json` or `.claude/settings.local.json`

**Configuration**:

```json
{
  "mcpServers": {
    "oxide": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/yayoboy/Documents/GitHub/oxide",
        "run",
        "oxide-mcp"
      ],
      "env": {}
    }
  }
}
```

**Alternative (if not using uv)**:

```json
{
  "mcpServers": {
    "oxide": {
      "command": "python3",
      "args": [
        "-m",
        "oxide.mcp.server"
      ],
      "env": {
        "PYTHONPATH": "/Users/yayoboy/Documents/GitHub/oxide"
      }
    }
  }
}
```

### Step 6: Restart Claude Code

After adding the configuration:

1. **Restart Claude Code** completely
2. Oxide MCP server will start automatically

### Step 7: Verify Integration

In Claude Code, check that Oxide tools are available:

```
Ask Claude: "What Oxide tools are available?"
```

You should see three tools:
- `oxide.route_task` - Intelligent task routing
- `oxide.analyze_parallel` - Parallel codebase analysis
- `oxide.list_services` - Service status check

## Using Oxide with Claude

### Basic Usage

**Intelligent routing** (Claude selects best LLM automatically):

```
Use Oxide to review this code for bugs
```

**Analyze large codebase** in parallel:

```
Use Oxide to analyze the ./src directory for architectural patterns
```

**Check service status**:

```
Use Oxide to list available services
```

### Example Prompts

1. **Code Review**:
   ```
   Use oxide route_task to review these files for security issues:
   - src/auth.py
   - src/middleware.py
   ```

2. **Large Codebase Analysis**:
   ```
   Use oxide analyze_parallel to analyze ./backend directory.
   Find all API endpoints and their authentication mechanisms.
   ```

3. **Quick Query**:
   ```
   Use oxide route_task to explain what async/await does in Python
   ```

4. **Architecture Analysis**:
   ```
   Use oxide route_task with files from ./src to identify
   the main architectural patterns used in this codebase.
   ```

## Troubleshooting

### Issue: Oxide MCP server not starting

**Symptom**: Claude shows error "Failed to connect to oxide"

**Solutions**:
1. Check logs: `/tmp/oxide.log`
2. Test manually: `uv run oxide-mcp` (should show "Starting MCP server...")
3. Verify configuration: `uv run python scripts/validate_config.py`
4. Check Python version: `python3 --version` (must be 3.11+)

### Issue: Service unavailable errors

**Symptom**: "Service 'gemini' is unavailable"

**Solutions**:
1. Check if CLI tool is in PATH: `which gemini`
2. Test service directly: `uv run python scripts/test_connection.py --service gemini`
3. If network service (Ollama/LM Studio), verify:
   - Service is running on remote machine
   - Port is accessible: `curl http://192.168.1.100:11434/api/tags`
   - Firewall allows connections

### Issue: Configuration errors

**Symptom**: "Invalid configuration: ..."

**Solutions**:
1. Validate config: `uv run python scripts/validate_config.py`
2. Check YAML syntax (no tabs, proper indentation)
3. Ensure all required fields are present

### Issue: Import errors

**Symptom**: `ModuleNotFoundError: No module named 'oxide'`

**Solutions**:
1. Reinstall: `uv sync` or `pip install -e .`
2. Verify installation: `pip show oxide`
3. Check Python path in settings.json

## Network Services Setup

### Ollama Remote Setup

On the server machine (192.168.1.100):

```bash
# Start Ollama with network binding
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Pull models
ollama pull qwen2.5-coder:7b
```

Test from your machine:

```bash
curl http://192.168.1.100:11434/api/tags
```

### LM Studio Setup

On the laptop (192.168.1.50):

1. Open LM Studio
2. Go to **Settings** → **Server**
3. Enable **Local Server**
4. Set port to `1234`
5. Enable **Network Access** (allow LAN connections)
6. Load a model

Test from your machine:

```bash
curl http://192.168.1.50:1234/v1/models
```

## Advanced Configuration

### Custom Routing Rules

Edit routing rules in `config/default.yaml`:

```yaml
routing_rules:
  code_review:
    primary: qwen
    fallback: [ollama_local, ollama_remote]
    timeout_seconds: 60

  codebase_analysis:
    primary: gemini
    fallback: [qwen]
    parallel_threshold_files: 20  # Use parallel if >20 files
```

### Logging Configuration

Adjust logging in `config/default.yaml`:

```yaml
logging:
  level: DEBUG  # DEBUG, INFO, WARNING, ERROR
  file: /tmp/oxide.log
  console: true
```

View logs:

```bash
tail -f /tmp/oxide.log
```

### Performance Tuning

Adjust parallel execution in `config/default.yaml`:

```yaml
execution:
  max_parallel_workers: 5  # Increase for faster parallel execution
  timeout_seconds: 180     # Increase for large codebases
  retry_on_failure: true
  max_retries: 3
```

## Next Steps

- Read [README.md](README.md) for usage examples
- Check [config/default.yaml](config/default.yaml) for all configuration options
- Run tests: `uv run python scripts/test_connection.py --all`
- Enable network services and test with: `oxide list_services`

## Support

For issues or questions:
- Check logs: `/tmp/oxide.log`
- Run diagnostics: `uv run python scripts/test_connection.py`
- Validate config: `uv run python scripts/validate_config.py`

---

**Happy orchestrating! 🔬**
