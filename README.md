# 🔬 Oxide - Intelligent LLM Orchestrator

**Intelligent routing and orchestration for distributed AI resources**

Oxide is a comprehensive platform for managing and orchestrating multiple Large Language Model (LLM) services. It intelligently routes tasks to the most appropriate LLM based on task characteristics, provides a web dashboard for monitoring and management, and integrates seamlessly with Claude Code via Model Context Protocol (MCP).

## ✨ Features

### 🎯 Intelligent Task Routing
- **Automatic Service Selection**: Analyzes task type, complexity, and file count to choose the optimal LLM
- **Custom Routing Rules**: Configure permanent task-to-service assignments via Web UI
- **Fallback Support**: Automatic failover to alternative services if primary is unavailable
- **Parallel Execution**: Distribute large codebase analysis across multiple LLMs
- **Manual Override**: Select specific services for individual tasks

### 🚀 Local LLM Management (NEW!)
- **Auto-Start Ollama**: Automatically starts Ollama if not running (macOS, Linux, Windows)
- **Auto-Detect Models**: Discovers available models without manual configuration
- **Smart Model Selection**: Chooses best model based on preferences and availability
- **Auto-Recovery**: Retries with service restart on temporary failures
- **Zero-Config LM Studio**: Works with LM Studio without model name configuration

### 🌐 Web Dashboard
- **Real-time Monitoring**: Live metrics for CPU, memory, task execution, and service health
- **Task Executor**: Execute tasks directly from the browser with service selection
- **Task Assignment Manager**: Configure which LLM handles specific task types
- **Task History**: Complete history of all executed tasks with results and metrics
- **WebSocket Support**: Real-time updates for task progress and system events
- **Service Management**: Monitor and test all configured LLM services

### 🔌 MCP Integration
- **Claude Code Integration**: Use Oxide directly within Claude Code
- **Three MCP Tools**:
  - `route_task` - Execute tasks with intelligent routing
  - `analyze_parallel` - Parallel codebase analysis
  - `list_services` - Check service health and availability
- **Persistent Task Storage**: All tasks saved to `~/.oxide/tasks.json`
- **Auto-start Web UI**: Optional automatic Web UI launch with MCP server

### 🛡️ Process Management
- **Automatic Cleanup**: All spawned processes (Web UI, Gemini, Qwen, etc.) cleaned up on exit
- **Signal Handlers**: Graceful shutdown on SIGTERM/SIGINT
- **Process Registry**: Tracks all child processes for guaranteed cleanup
- **No Orphaned Processes**: Ensures clean system state even on forced termination

### 📊 Supported LLM Services
- **Google Gemini** (CLI) - 2M+ token context window, ideal for large codebases
- **Qwen** (CLI) - Optimized for code generation and review
- **Ollama** (HTTP) - Local and remote instances
- **Extensible**: Easy to add new LLM adapters

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- uv package manager
- Node.js 18+ (for Web UI)
- Gemini CLI (optional)
- Qwen CLI (optional)
- Ollama (optional)

### Installation

```bash
# Clone the repository
cd /Users/yayoboy/Documents/GitHub/oxide

# Install dependencies
uv sync

# Build the Web UI
cd src/oxide/web/frontend
npm install
npm run build
cd ../../..

# Verify installation
uv run oxide-mcp --help
```

### Configuration

Edit `config/default.yaml`:

```yaml
services:
  gemini:
    enabled: true
    type: cli
    executable: gemini

  qwen:
    enabled: true
    type: cli
    executable: qwen

  ollama_local:
    enabled: true
    type: http
    base_url: http://localhost:11434
    model: qwen2.5-coder:7b
    default_model: qwen2.5-coder:7b

  ollama_remote:
    enabled: false
    type: http
    base_url: http://192.168.1.46:11434
    model: qwen2.5-coder:7b

routing_rules:
  prefer_local: true
  fallback_enabled: true

execution:
  timeout_seconds: 120
  max_retries: 2
  retry_on_failure: true
  max_parallel_workers: 3

logging:
  level: INFO
  console: true
  file: oxide.log
```

## 📖 Usage

### Option 1: MCP with Claude Code

1. **Configure Claude Code**

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

Setting `OXIDE_AUTO_START_WEB=true` automatically starts the Web UI at http://localhost:8000

2. **Use in Claude Code**

Claude will automatically use Oxide MCP tools:

```
You: "Analyze this codebase for architecture patterns"
Claude: Uses Oxide to route to Gemini (large context)

You: "Review this function for bugs"
Claude: Uses Oxide to route to Qwen (code specialist)

You: "What is 2+2?"
Claude: Uses Oxide to route to Ollama Local (quick query)
```

### Option 2: Web Dashboard

1. **Start the Web UI**

```bash
# Option A: Use the startup script
./scripts/start_web_ui.sh

# Option B: Manual start
python -m uvicorn oxide.web.backend.main:app --host 0.0.0.0 --port 8000

# Option C: Auto-start with MCP (set OXIDE_AUTO_START_WEB=true)
uv run oxide-mcp
```

2. **Access the Dashboard**

Open http://localhost:8000 in your browser

### Option 3: Python API

```python
from oxide.core.orchestrator import Orchestrator
from oxide.config.loader import load_config

# Initialize
config = load_config()
orchestrator = Orchestrator(config)

# Execute a task with intelligent routing
async for chunk in orchestrator.execute_task(
    prompt="Explain quantum computing",
    files=None,
    preferences=None  # Let Oxide choose
):
    print(chunk, end="")

# Execute with manual service selection
async for chunk in orchestrator.execute_task(
    prompt="Review this code",
    files=["src/main.py"],
    preferences={"preferred_service": "qwen"}
):
    print(chunk, end="")
```

## 🏗️ Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Oxide Orchestrator                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │  Classifier  │──▶│    Router    │──▶│   Adapters   │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│         │                   │                    │         │
│         │                   │                    │         │
│    Task Analysis      Route Decision       LLM Execution  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Process Manager - Lifecycle Management              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Task Storage - Persistent History                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Routing Rules - Custom Assignments                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
           │                  │                   │
           ▼                  ▼                   ▼
    ┌───────────┐      ┌───────────┐      ┌──────────┐
    │  MCP      │      │  Web UI   │      │ Python   │
    │  Server   │      │  Backend  │      │ API      │
    └───────────┘      └───────────┘      └──────────┘
```

### Key Components

#### 1. **Task Classifier** (`src/oxide/core/classifier.py`)
Analyzes tasks to determine:
- Task type (coding, review, codebase_analysis, etc.)
- Complexity score based on keywords and patterns
- File count and total size
- Whether parallel execution is beneficial

**Task Types:**
- `coding` - Code generation
- `code_review` - Code review
- `bug_search` - Bug analysis
- `refactoring` - Code refactoring
- `documentation` - Writing docs
- `codebase_analysis` - Large codebase analysis
- `quick_query` - Simple questions
- `general` - General purpose

#### 2. **Task Router** (`src/oxide/core/router.py`)
Routes tasks based on:
- Task classification results
- Custom routing rules (user-defined permanent assignments)
- Service health status and availability
- Fallback preferences and retry logic

#### 3. **Adapters** (`src/oxide/adapters/`)
Unified interface for different LLM types:

- **CLI Adapters** (`cli_adapter.py`):
  - Gemini (`gemini.py`) - Subprocess execution, 2M+ context
  - Qwen (`qwen.py`) - Code specialist
  - Automatic process tracking and cleanup

- **HTTP Adapters** (`ollama_http.py`):
  - Ollama Local/Remote - REST API communication
  - Streaming support
  - Health checks

All adapters implement:
- `execute()` - Task execution with streaming
- `health_check()` - Service availability check
- `get_service_info()` - Service metadata

#### 4. **Task Storage** (`src/oxide/utils/task_storage.py`)
Persistent task history management:

- **Storage**: `~/.oxide/tasks.json`
- **Thread-safe**: Concurrent read/write support
- **Tracked data**:
  - Task ID, status, timestamps
  - Prompt, files, preferences
  - Service used, task type
  - Result, error, duration
- **Features**:
  - List/filter tasks by status
  - Get statistics (by service, by type, by status)
  - Clear tasks (all or by status)

#### 5. **Process Manager** (`src/oxide/utils/process_manager.py`)
Lifecycle management for all spawned processes:

- **Tracks**: Web UI server, CLI processes (Gemini, Qwen)
- **Signal handlers**: SIGTERM, SIGINT, SIGHUP
- **Cleanup**: Automatic on exit (graceful → force kill)
- **Safety**: Prevents orphaned processes
- **atexit hook**: Final cleanup guarantee

#### 6. **Routing Rules Manager** (`src/oxide/utils/routing_rules.py`)
User-defined task-to-service assignments:

- **Storage**: `~/.oxide/routing_rules.json`
- **Format**: `{"task_type": "service_name"}`
- **Example**:
  ```json
  {
    "coding": "qwen",
    "code_review": "gemini",
    "bug_search": "qwen",
    "quick_query": "ollama_local"
  }
  ```
- **Priority**: Custom rules override intelligent routing

## 🎨 Web UI Features

### Dashboard Sections

#### 1. **System Metrics** (Real-time)
- **Services**: Total, enabled, healthy, unhealthy
- **Tasks**: Running, completed, failed, queued
- **System**: CPU %, Memory % and usage
- **WebSocket**: Active connections
- Auto-refresh every 2 seconds

#### 2. **Task Executor** 🚀
Execute tasks directly from the browser:

- **Prompt input**: Multi-line text area
- **Service selection**:
  - 🤖 **Auto** (Intelligent Routing) - Let Oxide choose
  - **Manual** - Select specific service (gemini, qwen, ollama, etc.)
- **Real-time streaming**: See results as they appear
- **Error handling**: Clear error messages
- **Integration**: Tasks appear immediately in history

#### 3. **LLM Services**
Service cards showing:
- **Status**: ✅ Healthy / ⚠️ Unavailable / ❌ Disabled
- **Type**: CLI or HTTP
- **Description**: Service capabilities
- **Details**: Base URL (HTTP), executable (CLI)
- **Context**: Max tokens (Gemini: 2M+)

#### 4. **Task Assignment Manager** ⚙️ ⭐ NEW
Configure permanent task-to-service assignments:

**Interface:**
- **Add Rule Form**:
  - Dropdown: Select task type (coding, review, etc.)
  - Dropdown: Select service (qwen, gemini, ollama)
  - Button: Add Rule
- **Active Rules Table**:
  - Task Type | Assigned Service | Description | Actions
  - Delete individual rules
  - Clear all rules

**Available Task Types:**
- **coding** → Code Generation → Recommended: qwen, gemini
- **code_review** → Code Review → Recommended: qwen, gemini
- **bug_search** → Bug Search → Recommended: qwen, gemini
- **refactoring** → Code Refactoring → Recommended: qwen, gemini
- **documentation** → Documentation → Recommended: gemini, qwen
- **codebase_analysis** → Large Codebase → Recommended: gemini
- **quick_query** → Simple Questions → Recommended: ollama_local
- **general** → General Purpose → Recommended: ollama_local, qwen

**Example Configuration:**
```
coding → qwen           (All code generation to qwen)
code_review → gemini    (All reviews to gemini)
bug_search → qwen       (Bug analysis to qwen)
quick_query → ollama    (Fast queries to local ollama)
```

When a task matches a rule, it's **always** routed to the assigned service, bypassing intelligent routing.

#### 5. **Task History** 📝
Complete history of all executed tasks:

- **From all sources**: MCP, Web UI, Python API
- **Auto-refresh**: Every 3 seconds
- **Display**:
  - Status badge (completed, running, failed, queued)
  - Timestamp, duration
  - Prompt preview (first 150 chars)
  - Service used, task type
  - File count
  - Error messages (if failed)
  - Result preview (first 200 chars)
- **Limit**: Latest 10 tasks by default

#### 6. **Live Updates** 🔔
WebSocket event stream:
- Real-time task progress
- Service status changes
- System events

## 📡 API Reference

### REST API

Base URL: `http://localhost:8000/api`

#### Tasks Endpoints

**Execute Task**
```http
POST /api/tasks/execute
Content-Type: application/json

{
  "prompt": "Your query here",
  "files": ["path/to/file.py"],
  "preferences": {
    "preferred_service": "qwen"
  }
}

Response: {"task_id": "...", "status": "queued", "message": "..."}
```

**List Tasks**
```http
GET /api/tasks/?limit=10&status=completed

Response: {
  "tasks": [...],
  "total": 42,
  "filtered": 10
}
```

**Get Task**
```http
GET /api/tasks/{task_id}

Response: {
  "id": "...",
  "status": "completed",
  "prompt": "...",
  "result": "...",
  "duration": 5.23,
  ...
}
```

**Delete Task**
```http
DELETE /api/tasks/{task_id}
```

**Clear Tasks**
```http
POST /api/tasks/clear?status=completed
```

#### Services Endpoints

**List Services**
```http
GET /api/services/

Response: {
  "services": {
    "gemini": {"enabled": true, "healthy": true, ...},
    ...
  },
  "total": 4,
  "enabled": 3
}
```

**Get Service**
```http
GET /api/services/{service_name}
```

**Health Check**
```http
POST /api/services/{service_name}/health
```

**Test Service**
```http
POST /api/services/{service_name}/test?test_prompt=Hello
```

#### Routing Rules Endpoints ⭐ NEW

**List All Rules**
```http
GET /api/routing/rules

Response: {
  "rules": [
    {"task_type": "coding", "service": "qwen"},
    ...
  ],
  "stats": {
    "total_rules": 3,
    "rules_by_service": {"qwen": 2, "gemini": 1},
    "task_types": ["coding", "code_review", "bug_search"]
  }
}
```

**Get Rule**
```http
GET /api/routing/rules/{task_type}
```

**Create/Update Rule**
```http
POST /api/routing/rules
Content-Type: application/json

{
  "task_type": "coding",
  "service": "qwen"
}

Response: {
  "message": "Routing rule updated",
  "rule": {"task_type": "coding", "service": "qwen"}
}
```

**Update Rule**
```http
PUT /api/routing/rules/{task_type}
Content-Type: application/json

{
  "task_type": "coding",
  "service": "gemini"
}
```

**Delete Rule**
```http
DELETE /api/routing/rules/{task_type}
```

**Clear All Rules**
```http
POST /api/routing/rules/clear
```

**Get Available Task Types**
```http
GET /api/routing/task-types

Response: {
  "task_types": [
    {
      "name": "coding",
      "label": "Code Generation",
      "description": "Writing new code, implementing features",
      "recommended_services": ["qwen", "gemini"]
    },
    ...
  ]
}
```

#### Monitoring Endpoints

**Get Metrics**
```http
GET /api/monitoring/metrics

Response: {
  "services": {"total": 4, "enabled": 3, "healthy": 2, ...},
  "tasks": {"total": 10, "running": 0, "completed": 8, ...},
  "system": {"cpu_percent": 25.3, "memory_percent": 45.7, ...},
  "websocket": {"connections": 1},
  "timestamp": 1234567890.123
}
```

**Get Stats**
```http
GET /api/monitoring/stats

Response: {
  "total_tasks": 42,
  "avg_duration": 5.67,
  "success_rate": 95.24,
  "tasks_by_status": {"completed": 40, "failed": 2}
}
```

**Health Check**
```http
GET /api/monitoring/health

Response: {
  "status": "healthy",
  "healthy": true,
  "issues": [],
  "cpu_percent": 25.3,
  "memory_percent": 45.7
}
```

### WebSocket API

Connect to `ws://localhost:8000/ws` for real-time updates.

**Message Types:**

1. **task_start**
```json
{
  "type": "task_start",
  "task_id": "...",
  "task_type": "coding",
  "service": "qwen"
}
```

2. **task_progress** (streaming)
```json
{
  "type": "task_progress",
  "task_id": "...",
  "chunk": "Here is the code..."
}
```

3. **task_complete**
```json
{
  "type": "task_complete",
  "task_id": "...",
  "success": true,
  "duration": 5.23
}
```

**Client Usage:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'task_progress') {
    console.log(data.chunk);
  }
};

// Keep-alive ping
setInterval(() => ws.send('ping'), 30000);
```

## 🔧 Development

### Project Structure

```
oxide/
├── config/
│   └── default.yaml                # Main configuration
├── src/oxide/
│   ├── core/
│   │   ├── classifier.py           # Task classification
│   │   ├── router.py               # Routing logic
│   │   └── orchestrator.py         # Main orchestrator
│   ├── adapters/
│   │   ├── base.py                 # Base adapter interface
│   │   ├── cli_adapter.py          # CLI adapter base
│   │   ├── gemini.py               # Gemini adapter
│   │   ├── qwen.py                 # Qwen adapter
│   │   └── ollama_http.py          # Ollama HTTP adapter
│   ├── execution/
│   │   └── parallel.py             # Parallel execution engine
│   ├── utils/
│   │   ├── task_storage.py         # Task persistence
│   │   ├── routing_rules.py        # Routing rules storage
│   │   ├── process_manager.py      # Process lifecycle
│   │   ├── logging.py              # Logging utilities
│   │   └── exceptions.py           # Custom exceptions
│   ├── mcp/
│   │   ├── server.py               # MCP server (FastMCP)
│   │   └── tools.py                # MCP tool definitions
│   └── web/
│       ├── backend/
│       │   ├── main.py             # FastAPI application
│       │   ├── websocket.py        # WebSocket manager
│       │   └── routes/
│       │       ├── tasks.py        # Task endpoints
│       │       ├── services.py     # Service endpoints
│       │       ├── routing.py      # Routing rules endpoints
│       │       └── monitoring.py   # Monitoring endpoints
│       └── frontend/               # React SPA
│           ├── src/
│           │   ├── components/
│           │   │   ├── TaskExecutor.jsx
│           │   │   ├── TaskAssignmentManager.jsx
│           │   │   ├── TaskHistory.jsx
│           │   │   ├── ServiceCard.jsx
│           │   │   └── MetricsDashboard.jsx
│           │   ├── hooks/
│           │   │   ├── useServices.js
│           │   │   ├── useMetrics.js
│           │   │   └── useWebSocket.js
│           │   ├── api/
│           │   │   └── client.js
│           │   └── App.jsx
│           ├── package.json
│           └── vite.config.js
├── tests/
│   ├── test_process_cleanup.py
│   └── test_task_history_integration.py
└── scripts/
    └── start_web_ui.sh
```

### Running Tests

```bash
# Process cleanup tests
python3 tests/test_process_cleanup.py

# Task history integration tests
python3 tests/test_task_history_integration.py

# All tests pass
# ✓ Sync process cleanup
# ✓ Async process cleanup
# ✓ Multiple process cleanup
# ✓ Signal handler cleanup
# ✓ Task storage integration
```

### Adding a New LLM Adapter

1. **Create adapter class**

```python
# src/oxide/adapters/my_llm.py
from .base import BaseAdapter
from typing import AsyncIterator, List, Optional

class MyLLMAdapter(BaseAdapter):
    def __init__(self, config: dict):
        super().__init__("my_llm", config)
        self.api_key = config.get("api_key")
        # Initialize your client...

    async def execute(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Execute task and stream results."""
        # Your implementation
        yield "Response chunk"

    async def health_check(self) -> bool:
        """Check if service is available."""
        # Your health check logic
        return True

    def get_service_info(self) -> dict:
        """Return service metadata."""
        info = super().get_service_info()
        info.update({
            "description": "My LLM Service",
            "max_tokens": 100000
        })
        return info
```

2. **Register in configuration**

```yaml
# config/default.yaml
services:
  my_llm:
    enabled: true
    type: http  # or 'cli'
    base_url: http://localhost:8080
    model: my-model
    api_key: ${MY_LLM_API_KEY}  # From environment
```

3. **Update orchestrator**

```python
# src/oxide/core/orchestrator.py
def _create_adapter(self, service_name, config):
    service_type = config.get("type")

    if service_type == "cli":
        if "my_llm" in service_name:
            from ..adapters.my_llm import MyLLMAdapter
            return MyLLMAdapter(config)
        # ... other CLI adapters

    elif service_type == "http":
        if "my_llm" in service_name:
            from ..adapters.my_llm import MyLLMAdapter
            return MyLLMAdapter(config)
        # ... other HTTP adapters
```

4. **Test your adapter**

```python
import asyncio
from oxide.core.orchestrator import Orchestrator
from oxide.config.loader import load_config

async def test():
    config = load_config()
    orchestrator = Orchestrator(config)

    async for chunk in orchestrator.execute_task(
        prompt="Test query",
        preferences={"preferred_service": "my_llm"}
    ):
        print(chunk, end="")

asyncio.run(test())
```

## 📊 Storage Files

Oxide creates the following files in `~/.oxide/`:

- **tasks.json** - Task execution history (all tasks from all sources)
- **routing_rules.json** - Custom routing rules (task type → service)
- **oxide.log** - Application logs (if file logging enabled)

**Example `tasks.json`:**
```json
{
  "task-uuid-1": {
    "id": "task-uuid-1",
    "status": "completed",
    "prompt": "What is quantum computing?",
    "files": [],
    "service": "ollama_local",
    "task_type": "quick_query",
    "result": "Quantum computing is...",
    "error": null,
    "created_at": 1234567890.123,
    "started_at": 1234567890.456,
    "completed_at": 1234567895.789,
    "duration": 5.333
  }
}
```

**Example `routing_rules.json`:**
```json
{
  "coding": "qwen",
  "code_review": "gemini",
  "bug_search": "qwen",
  "quick_query": "ollama_local"
}
```

## 🎯 Local LLM Management

### Auto-Start Ollama

Oxide can automatically start Ollama if it's not running:

```yaml
# config/default.yaml
services:
  ollama_local:
    type: http
    base_url: "http://localhost:11434"
    api_type: ollama
    enabled: true
    auto_start: true              # 🔥 Auto-start if not running
    auto_detect_model: true       # 🔥 Auto-detect best model
    max_retries: 2                # Retry on failures
    retry_delay: 2                # Seconds between retries
```

**What happens:**
1. First task execution checks if Ollama is running
2. If not, automatically starts Ollama via:
   - macOS: Opens Ollama.app or runs `ollama serve`
   - Linux: Uses systemd or runs `ollama serve`
   - Windows: Runs `ollama serve` as detached process
3. Waits up to 30s for Ollama to be ready
4. Proceeds with task execution

### Auto-Detect Models

No need to configure model names manually:

```yaml
lmstudio:
  type: http
  base_url: "http://192.168.1.33:1234/v1"
  api_type: openai_compatible
  enabled: true
  default_model: null           # 🔥 Will auto-detect
  auto_detect_model: true
  preferred_models:             # Priority order
    - "qwen"                    # Matches: qwen/qwen2.5-coder-14b
    - "coder"                   # Matches: mistralai/codestral-22b
    - "deepseek"                # Matches: deepseek/deepseek-r1
```

**Smart Selection Algorithm:**
1. Fetches available models from service
2. Tries exact match with preferred models
3. Tries partial match (e.g., "qwen" matches "qwen2.5-coder:7b")
4. Falls back to first available model

### Service Health Monitoring

```python
from oxide.utils.service_manager import get_service_manager

service_manager = get_service_manager()

# Comprehensive health check with auto-recovery
health = await service_manager.ensure_service_healthy(
    service_name="ollama_local",
    base_url="http://localhost:11434",
    api_type="ollama",
    auto_start=True,           # Try to start if down
    auto_detect_model=True     # Detect available models
)

print(f"Healthy: {health['healthy']}")
print(f"Models: {health['models']}")
print(f"Recommended: {health['recommended_model']}")
```

### Background Health Monitoring

```python
# Start monitoring (checks every 60s, auto-recovers on failure)
await service_manager.start_health_monitoring(
    service_name="ollama_local",
    base_url="http://localhost:11434",
    interval=60,
    auto_recovery=True
)
```

## 🎯 Usage Examples

### Example 1: Simple Query (Auto-Start Enabled)

```python
# Ollama will auto-start if not running!
async for chunk in orchestrator.execute_task("What is 2+2?"):
    print(chunk, end="")

# What happens:
# 1. Checks if Ollama is running → not running
# 2. Auto-starts Ollama (takes ~5s)
# 3. Auto-detects model: qwen2.5-coder:7b
# 4. Executes task
# 5. Returns: "4"
```

### Example 2: Code Review with Manual Selection

```python
async for chunk in orchestrator.execute_task(
    prompt="Review this code for bugs",
    files=["src/auth.py"],
    preferences={"preferred_service": "gemini"}
):
    print(chunk, end="")

# Forces routing to: gemini
# Gets large context window for thorough review
```

### Example 3: Large Codebase Analysis

```python
# Parallel analysis
from oxide.execution.parallel import ParallelExecutor

executor = ParallelExecutor(max_workers=3)

result = await executor.execute_parallel(
    prompt="Analyze architecture patterns",
    files=["src/**/*.py"],  # 50+ files
    services=["gemini", "qwen", "ollama_local"],
    strategy="split"
)

print(f"Completed in {result.total_duration_seconds}s")
print(result.aggregated_text)
```

### Example 4: Using Routing Rules

```python
# Set up rules via API
import requests

requests.post("http://localhost:8000/api/routing/rules", json={
    "task_type": "coding",
    "service": "qwen"
})

# Now all coding tasks go to qwen automatically
async for chunk in orchestrator.execute_task("Write a Python function to sort a list"):
    print(chunk, end="")

# Routes to: qwen (custom rule)
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/oxide.git
cd oxide

# Install dev dependencies
uv sync

# Install frontend dependencies
cd src/oxide/web/frontend
npm install
cd ../../..

# Run tests
python3 tests/test_process_cleanup.py
python3 tests/test_task_history_integration.py

# Start development servers
python -m uvicorn oxide.web.backend.main:app --reload &
cd src/oxide/web/frontend && npm run dev
```

## 📝 License

MIT License - Copyright (c) 2025 yayoboy

See LICENSE file for details.

## 👥 Authors

- **yayoboy** - *Initial work* - esoglobine@gmail.com

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- React dashboard using [Vite](https://vitejs.dev/) - Lightning-fast frontend tooling
- MCP integration via [Model Context Protocol](https://modelcontextprotocol.io/)
- Process management inspired by supervisor and systemd patterns
- WebSocket support via [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- Task classification inspired by semantic analysis techniques

## 📧 Support

For issues, questions, or suggestions:

- **GitHub Issues**: [https://github.com/yourusername/oxide/issues](https://github.com/yourusername/oxide/issues)
- **Email**: esoglobine@gmail.com

## 🗺️ Roadmap

### v0.2.0 (Planned)
- [ ] SQLite database for task storage
- [ ] Advanced metrics and analytics
- [ ] Cost tracking per service
- [ ] Rate limiting and quotas
- [ ] Multi-user support
- [ ] Docker deployment

### v0.3.0 (Future)
- [ ] Plugin system for custom adapters
- [ ] Workflow automation (task chains)
- [ ] A/B testing framework
- [ ] Performance benchmarking suite
- [ ] Auto-scaling for parallel execution

## 📊 Project Status

**Version**: 0.1.0
**Status**: ✅ Production Ready - MVP Complete!

### Completed Features
- [x] Project structure and dependencies
- [x] Configuration system
- [x] Task classifier
- [x] Task router with fallbacks
- [x] Adapter implementations (Gemini, Qwen, Ollama)
- [x] MCP server integration
- [x] Web UI dashboard (React + FastAPI)
- [x] Real-time monitoring and WebSocket
- [x] Task executor in Web UI
- [x] Task assignment manager (routing rules UI)
- [x] Persistent task storage
- [x] Process lifecycle management
- [x] Test suite (process cleanup, task storage)
- [x] Comprehensive documentation

### In Progress
- [ ] Production deployment guides
- [ ] Docker containerization
- [ ] Extended test coverage

---

**Built with ❤️ for intelligent LLM orchestration**

**Last Updated**: December 2025
