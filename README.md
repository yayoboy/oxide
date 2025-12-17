# Oxide - Intelligent LLM Orchestrator

Oxide is an intelligent orchestration system that allows Claude Code to automatically route tasks to the most appropriate LLM based on task characteristics, enabling distributed AI resource utilization across local and network services.

## Features

- **Automatic Task Routing**: Intelligently classifies tasks and routes them to the optimal LLM
- **Parallel Execution**: Distributes large codebase analysis across multiple LLMs simultaneously
- **MCP Integration**: Native integration with Claude Code via Model Context Protocol
- **Multi-Service Support**: Works with Gemini CLI, Qwen CLI, Ollama (local & remote), and LM Studio
- **Web Dashboard**: Real-time monitoring and configuration UI (coming soon)

## Architecture

```
Claude Code (MCP) � Oxide Orchestrator � [Gemini | Qwen | Ollama | LM Studio]
```

### Supported Services

**Local Services:**
- **Gemini CLI**: Large context window (2M tokens) - ideal for codebase analysis
- **Qwen CLI**: Code-specialized - best for code review and generation
- **Ollama**: Local inference - fast, low-latency queries

**Network Services (LAN):**
- **LM Studio**: OpenAI-compatible API on laptop
- **Ollama Remote**: Distributed processing on server

## Installation

```bash
# Clone the repository
cd /Users/yayoboy/Documents/GitHub/oxide

# Install dependencies
uv sync

# Verify installation
uv run oxide-mcp --help
```

## Configuration

Configure services in `config/default.yaml`:

```yaml
services:
  gemini:
    type: cli
    executable: gemini
    enabled: true

  qwen:
    type: cli
    executable: qwen
    enabled: true

  ollama_local:
    type: http
    base_url: "http://localhost:11434"
    enabled: true
    default_model: "qwen2.5-coder:7b"
```

## Integration with Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "oxide": {
      "command": "uv",
      "args": ["--directory", "/Users/yayoboy/Documents/GitHub/oxide", "run", "oxide-mcp"],
      "env": {
        "OXIDE_AUTO_START_WEB": "true"
      }
    }
  }
}
```

**Note:** Setting `OXIDE_AUTO_START_WEB=true` automatically starts the Web UI when the MCP server launches!

## Quick Start

### Launch All Services

Multiple ways to start Oxide:

```bash
# Option 1: Unified launcher (MCP + Web UI)
uv run oxide-all

# Option 2: Auto-start Web UI with MCP (set OXIDE_AUTO_START_WEB=true in settings.json)
uv run oxide-mcp

# Option 3: Shell script
./scripts/start_all.sh

# Option 4: Separate services
uv run oxide-mcp    # MCP server only
uv run oxide-web    # Web UI only
```

See [AUTO_START_GUIDE.md](AUTO_START_GUIDE.md) for detailed auto-start configuration.

## Usage

Once integrated with Claude, use the MCP tools:

```
# Intelligent task routing
Use oxide route_task to analyze this code for bugs

# Parallel codebase analysis
Use oxide analyze_parallel to analyze the ./src directory

# Check service status
Use oxide list_services to show available LLMs
```

## Task Classification

Oxide automatically classifies tasks:

- **CODEBASE_ANALYSIS** (>20 files or >500KB) � Gemini
- **CODE_REVIEW** ("review" keyword) � Qwen
- **CODE_GENERATION** ("generate"/"write" keywords) � Qwen/Ollama
- **QUICK_QUERY** (simple, no files) � Ollama Local

## Web Dashboard

Oxide includes a **real-time web dashboard** for monitoring and control:

```bash
# Start backend server
uv run oxide-web

# Start frontend (in another terminal)
cd oxide/web/frontend && npm install && npm run dev
```

Access at **http://localhost:3000**

**Features:**
- Real-time service status monitoring
- Task execution history
- System metrics (CPU, memory)
- WebSocket live updates
- Service health checks

See [WEB_UI_GUIDE.md](WEB_UI_GUIDE.md) for complete setup guide.

## Network Services Setup

Configure remote LLM services on your LAN:

```bash
# Setup Ollama on another machine
./scripts/setup_ollama_remote.sh --ip 192.168.1.100

# Setup LM Studio on laptop
./scripts/setup_lmstudio.sh --ip 192.168.1.50

# Test network services
uv run python scripts/test_network.py --all

# Scan network for services
uv run python scripts/test_network.py --scan 192.168.1.0/24
```

## Development Status

✅ **Production Ready - MVP Complete!**

- [x] Project structure and dependencies
- [x] Configuration system ✅
- [x] Adapter implementations ✅ (Gemini, Qwen, Ollama, LM Studio)
- [x] Task classification and routing ✅
- [x] MCP server ✅
- [x] Web UI dashboard ✅
- [x] Network services support ✅
- [x] Real-time monitoring ✅
- [ ] Test suite
- [ ] Production documentation

## Requirements

- Python 3.11+
- uv package manager
- Gemini CLI (optional)
- Qwen CLI (optional)
- Ollama (optional)

## License

MIT

## Author

yayoboy <esoglobine@gmail.com>
