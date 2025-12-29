---
sidebar_position: 3
---

# MCP Integration

Oxide integrates with Claude Code via the Model Context Protocol (MCP), providing seamless LLM orchestration directly within your development workflow.

## What is MCP?

Model Context Protocol (MCP) is Anthropic's standard for connecting AI assistants like Claude Code to external tools and services. Oxide implements an MCP server that exposes three powerful tools for intelligent LLM routing.

## Installation

### 1. Install Oxide

```bash
git clone https://github.com/yayoboy/oxide.git
cd oxide
uv sync --all-extras
```

### 2. Configure Claude Code

Add Oxide to your Claude Code MCP servers configuration:

**macOS/Linux**: `~/.claude/config.json`
**Windows**: `%APPDATA%\Claude\config.json`

```json
{
  "mcpServers": {
    "oxide": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/your-username/path/to/oxide",
        "run",
        "oxide-mcp"
      ],
      "env": {
        "OPENROUTER_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### 3. Restart Claude Code

```bash
# Restart Claude Code to load the new MCP server
claude --restart
```

## MCP Tools

Oxide exposes three MCP tools:

### 1. `route_task` - Intelligent Task Routing

Execute tasks with automatic LLM service selection.

**Parameters:**
```typescript
{
  prompt: string;           // The task prompt
  files?: string[];         // Optional file paths for context
  preferences?: {           // Optional routing preferences
    service?: string;       // Prefer specific service
    task_type?: string;     // Override task type classification
    max_tokens?: number;    // Maximum tokens for response
    temperature?: number;   // Sampling temperature (0-1)
  }
}
```

**Example Usage in Claude Code:**

```
User: Use Oxide to analyze this codebase and find potential bugs.

Claude: I'll use the route_task tool to analyze the codebase for bugs.
```

Claude Code will automatically:
1. Call `route_task` with your prompt
2. Oxide classifies the task type (code_review)
3. Routes to the best service (e.g., Qwen for code analysis)
4. Returns the analysis results

**Direct Tool Call Example:**
```json
{
  "tool": "route_task",
  "params": {
    "prompt": "Review this code for security vulnerabilities",
    "files": [
      "/path/to/auth.py",
      "/path/to/database.py"
    ],
    "preferences": {
      "service": "qwen",
      "task_type": "code_review"
    }
  }
}
```

### 2. `analyze_parallel` - Parallel Codebase Analysis

Distribute large codebase analysis across multiple LLMs for faster processing.

**Parameters:**
```typescript
{
  directory: string;        // Directory to analyze
  prompt: string;           // Analysis prompt
  num_workers?: number;     // Number of parallel workers (default: 3)
}
```

**How It Works:**
1. Splits files in directory into chunks
2. Distributes chunks across multiple LLM services
3. Processes in parallel for maximum speed
4. Aggregates results into single response

**Example Usage:**

```
User: Analyze the entire src/ directory for code quality issues using Oxide.

Claude: I'll use analyze_parallel to distribute this analysis across multiple LLMs.
```

**Direct Tool Call Example:**
```json
{
  "tool": "analyze_parallel",
  "params": {
    "directory": "/path/to/src",
    "prompt": "Analyze code quality and suggest improvements",
    "num_workers": 4
  }
}
```

**Performance Benefits:**
- **Single LLM**: 2-5 minutes for large codebase
- **Parallel (3 workers)**: 30-60 seconds
- **Speedup**: Up to 5x faster

### 3. `list_services` - Service Health Check

Check availability and status of all configured LLM services.

**Parameters:**
```typescript
{}  // No parameters required
```

**Returns:**
```json
{
  "services": {
    "gemini": {
      "type": "cli",
      "healthy": true,
      "available": true,
      "info": {
        "executable": "gemini",
        "context_window": 2000000
      }
    },
    "qwen": {
      "type": "cli",
      "healthy": true,
      "available": true
    },
    "ollama_local": {
      "type": "http",
      "healthy": true,
      "available": true,
      "info": {
        "base_url": "http://localhost:11434",
        "model": "llama2"
      }
    },
    "openrouter": {
      "type": "http",
      "healthy": true,
      "available": true,
      "info": {
        "api_url": "https://openrouter.ai/api/v1"
      }
    }
  },
  "routing_rules": [
    {
      "task_type": "code_generation",
      "service": "openrouter",
      "model": "anthropic/claude-3.5-sonnet"
    }
  ]
}
```

**Example Usage:**

```
User: Check which LLM services are available in Oxide.

Claude: I'll check the service status using list_services.
```

## Task Routing Logic

### Automatic Service Selection

Oxide automatically selects the best service based on:

1. **Task Type Classification**:
   - Code generation → Code-optimized models (Qwen, Claude)
   - Question answering → General models (Gemini, GPT)
   - Large codebases → High context models (Gemini 2M tokens)
   - Quick queries → Fast local models (Ollama)

2. **Service Health**:
   - Only routes to healthy, available services
   - Automatic failover if primary service fails

3. **Custom Routing Rules**:
   - User-defined rules take precedence
   - Configure in `config/default.yaml` or Web UI

4. **Performance Metrics**:
   - Tracks response time and success rate
   - Prefers faster, more reliable services

### Example Routing Scenarios

**Scenario 1: Large Codebase Analysis**
```
Prompt: "Analyze this 500-file codebase for security issues"
Files: 500 Python files

→ Classified as: code_review, large_context
→ Routed to: Gemini CLI (2M token context)
→ Reasoning: Needs high context window
```

**Scenario 2: Quick Code Generation**
```
Prompt: "Write a function to validate email addresses"
Files: None

→ Classified as: code_generation, simple
→ Routed to: Ollama (local, fast)
→ Reasoning: Simple task, local is faster
```

**Scenario 3: Custom Rule Match**
```
Prompt: "Generate API documentation"
Files: 10 TypeScript files

→ Custom rule: task_type=code_generation → openrouter/claude-3.5-sonnet
→ Routed to: OpenRouter (Claude 3.5 Sonnet)
→ Reasoning: User-defined rule takes precedence
```

## Configuration

### Oxide Configuration

Configure services in `config/default.yaml`:

```yaml
services:
  gemini:
    enabled: true
    type: cli
    executable: gemini
    priority: high
    capabilities:
      - code_review
      - large_context
      - question_answer

  qwen:
    enabled: true
    type: cli
    executable: qwen
    priority: high
    capabilities:
      - code_generation
      - code_review

  ollama_local:
    enabled: true
    type: http
    base_url: http://localhost:11434
    model: llama2
    priority: medium
    capabilities:
      - question_answer
      - chat

  openrouter:
    enabled: true
    type: http
    api_key: ${OPENROUTER_API_KEY}
    priority: high
    capabilities:
      - code_generation
      - question_answer
      - creative_writing

routing:
  rules:
    - task_type: code_generation
      service: openrouter
      model: anthropic/claude-3.5-sonnet
      priority: 1

    - task_type: large_context
      service: gemini
      priority: 1
```

### MCP Server Configuration

Additional MCP-specific settings:

```yaml
mcp:
  enabled: true
  auto_start_web_ui: true  # Launch Web UI when MCP server starts
  task_storage_path: ~/.oxide/tasks.json
  max_parallel_tasks: 3
```

## Task Storage

All tasks executed via MCP are stored in `~/.oxide/tasks.json`:

```json
{
  "tasks": [
    {
      "id": "abc123",
      "prompt": "Review code for bugs",
      "task_type": "code_review",
      "service": "qwen",
      "status": "completed",
      "result": "Found 3 potential issues...",
      "execution_time": 4.2,
      "tokens_used": 1200,
      "cost": 0.002,
      "timestamp": "2024-12-27T12:00:00Z"
    }
  ]
}
```

Access task history via:
- **Web UI**: http://localhost:8000 → Task History tab
- **API**: `GET /api/tasks/history/`

## Advanced Usage

### Custom Routing via Preferences

Override automatic routing:

```json
{
  "tool": "route_task",
  "params": {
    "prompt": "Explain quantum computing",
    "preferences": {
      "service": "gemini",  // Force specific service
      "temperature": 0.3,    // More focused responses
      "max_tokens": 2000     // Limit response length
    }
  }
}
```

### Batch Processing

Process multiple tasks in sequence:

```python
# In your MCP client
tasks = [
  {"prompt": "Review auth.py", "files": ["auth.py"]},
  {"prompt": "Review database.py", "files": ["database.py"]},
  {"prompt": "Review api.py", "files": ["api.py"]},
]

for task in tasks:
  result = await mcp_client.call_tool("route_task", task)
  print(f"Task completed: {result}")
```

### Context-Aware Analysis

Oxide maintains context across related tasks:

```
1. First task: "Analyze this codebase architecture"
   → Context stored

2. Second task: "Based on the architecture, suggest improvements"
   → Uses context from first task
   → More relevant suggestions
```

## Monitoring

### Real-time Monitoring via Web UI

When MCP server starts, access the Web UI at:
```
http://localhost:8000
```

Features:
- **Live Metrics**: CPU, memory, task execution
- **Service Health**: Status of all LLM services
- **Task History**: All MCP-executed tasks
- **Configuration**: Edit routing rules

### API Monitoring

Query task history via API:

```bash
curl http://localhost:8000/api/tasks/history/?limit=10
```

```json
{
  "total": 50,
  "tasks": [
    {
      "id": "abc123",
      "prompt": "...",
      "status": "completed",
      "execution_time": 4.2
    }
  ]
}
```

## Troubleshooting

### MCP Server Not Starting

```bash
# Check if Oxide is installed
uv run oxide-mcp --version

# Check configuration
cat ~/.claude/config.json

# View logs
tail -f ~/.claude/logs/mcp.log
```

### Service Not Available

```bash
# Check service health
uv run python -c "
from oxide.core.orchestrator import Orchestrator
from oxide.config import load_config

config = load_config('config/default.yaml')
orchestrator = Orchestrator(config)

import asyncio
services = asyncio.run(orchestrator.list_services())
print(services)
"
```

### Task Routing to Wrong Service

1. Check routing rules in `config/default.yaml`
2. Verify service capabilities match task type
3. Use `preferences.service` to force specific service

### Authentication Issues

```bash
# Verify API keys in environment
echo $OPENROUTER_API_KEY
echo $OPENAI_API_KEY

# Or set in Claude Code MCP config
{
  "env": {
    "OPENROUTER_API_KEY": "your-key"
  }
}
```

## Examples

### Example 1: Code Review with Qwen

```
User in Claude Code:
"Use Oxide to review auth.py for security vulnerabilities"

Claude Code:
→ Calls: route_task("Review auth.py for security vulnerabilities", files=["auth.py"])
→ Oxide routes to: Qwen (code_review capability)
→ Returns: Detailed security analysis
```

### Example 2: Large Codebase with Gemini

```
User:
"Analyze the entire src/ directory architecture"

Claude Code:
→ Calls: analyze_parallel(directory="src/", prompt="Analyze architecture")
→ Oxide: Splits 200 files across 3 LLMs
→ Returns: Aggregated architecture analysis in 45 seconds
```

### Example 3: Service Discovery

```
User:
"What LLM services are available?"

Claude Code:
→ Calls: list_services()
→ Returns: Status of Gemini, Qwen, Ollama, OpenRouter
```

## Next Steps

- **[Configuration Guide](../guides/configuration)** - Configure services and routing
- **[API Reference](./overview)** - Complete API documentation
- **[Examples](../examples/mcp-integration)** - More MCP examples
