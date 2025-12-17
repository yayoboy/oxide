# CLAUDE.md - AI Assistant Guide for Oxide

**Last Updated**: 2025-12-17
**Version**: 0.1.0
**Purpose**: Comprehensive guide for AI assistants working with the Oxide LLM Orchestrator codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Directory Structure](#directory-structure)
4. [Key Modules](#key-modules)
5. [Data Flow](#data-flow)
6. [Configuration System](#configuration-system)
7. [Adapter Pattern](#adapter-pattern)
8. [Development Workflow](#development-workflow)
9. [Skills and Plugins for Development](#skills-and-plugins-for-development)
10. [Code Conventions](#code-conventions)
11. [Testing Strategy](#testing-strategy)
12. [Common Tasks](#common-tasks)
13. [Debugging Guide](#debugging-guide)
14. [AI Assistant Guidelines](#ai-assistant-guidelines)

---

## Project Overview

### What is Oxide?

Oxide is an **intelligent LLM orchestration system** that routes tasks to the most appropriate language model based on task characteristics. It enables distributed AI resource utilization across local and network services.

### Core Capabilities

- **Automatic Task Routing**: Classifies tasks and routes to optimal LLM
- **Parallel Execution**: Distributes large codebase analysis across multiple LLMs
- **MCP Integration**: Native integration with Claude Code via Model Context Protocol
- **Multi-Service Support**: Gemini CLI, Qwen CLI, Ollama (local & remote), LM Studio
- **Web Dashboard**: Real-time monitoring and configuration UI

### Technology Stack

- **Language**: Python 3.11+
- **Package Manager**: uv
- **Framework**: FastAPI (web backend), React (web frontend)
- **Integration**: MCP (Model Context Protocol)
- **Configuration**: YAML + Pydantic validation
- **Async**: asyncio for concurrent operations

---

## Architecture

### System Design

```
┌─────────────────┐
│  Claude Code    │
│     (MCP)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Orchestrator   │  ◄── Core coordination engine
└────────┬────────┘
         │
    ┌────┴────┬────────────┬──────────┐
    ▼         ▼            ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Gemini  │ │  Qwen   │ │ Ollama  │ │LM Studio│
│   CLI   │ │   CLI   │ │  HTTP   │ │  HTTP   │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### Component Layers

1. **MCP Server Layer** (`oxide/mcp/`)
   - Exposes tools to Claude Code
   - Handles MCP protocol communication
   - Tool implementations: `route_task`, `analyze_parallel`, `list_services`

2. **Orchestration Layer** (`oxide/core/`)
   - **Classifier**: Analyzes tasks and determines task type
   - **Router**: Selects appropriate service based on routing rules
   - **Orchestrator**: Coordinates classification, routing, and execution

3. **Adapter Layer** (`oxide/adapters/`)
   - **BaseAdapter**: Abstract interface for all adapters
   - **CLI Adapters**: Gemini, Qwen (subprocess-based)
   - **HTTP Adapters**: Ollama, LM Studio (HTTP API-based)

4. **Execution Layer** (`oxide/execution/`)
   - **ParallelExecutor**: Distributes tasks across multiple services
   - Strategies: "split" (divide files) or "duplicate" (compare results)

5. **Configuration Layer** (`oxide/config/`)
   - YAML-based configuration
   - Pydantic models for validation
   - Service and routing rule definitions

6. **Web Layer** (`oxide/web/`)
   - **Backend**: FastAPI server with WebSocket support
   - **Frontend**: React dashboard for monitoring
   - Real-time service status and task history

---

## Directory Structure

```
oxide/
├── config/                    # Configuration files
│   ├── default.yaml          # Main configuration (services, routing rules)
│   └── models.yaml           # Model capability profiles
├── oxide/                     # Main package
│   ├── __init__.py
│   ├── launcher.py           # Unified launcher (MCP + Web)
│   ├── core/                 # Core orchestration logic
│   │   ├── classifier.py     # Task classification
│   │   ├── router.py         # Service routing
│   │   └── orchestrator.py   # Main orchestrator
│   ├── adapters/             # LLM service adapters
│   │   ├── base.py          # Abstract base adapter
│   │   ├── cli_adapter.py   # Base CLI adapter
│   │   ├── gemini.py        # Gemini CLI adapter
│   │   ├── qwen.py          # Qwen CLI adapter
│   │   └── ollama_http.py   # Ollama HTTP adapter
│   ├── execution/            # Parallel execution
│   │   └── parallel.py      # ParallelExecutor
│   ├── mcp/                  # MCP server
│   │   ├── server.py        # MCP server implementation
│   │   └── tools.py         # MCP tool implementations
│   ├── config/               # Configuration loading
│   │   └── loader.py        # Config loader + validation
│   ├── utils/                # Utilities
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── logging.py       # Logging setup
│   └── web/                  # Web UI
│       ├── backend/          # FastAPI backend
│       │   ├── main.py      # FastAPI app
│       │   ├── websocket.py # WebSocket handler
│       │   └── routes/      # API routes
│       └── frontend/         # React frontend
│           └── src/         # React components
├── src/oxide/                # Package source (for installation)
├── scripts/                  # Utility scripts
│   ├── start_all.sh         # Start all services
│   ├── test_network.py      # Test network services
│   ├── test_connection.py   # Test service connections
│   └── validate_config.py   # Validate configuration
├── pyproject.toml            # Project metadata + dependencies
├── uv.lock                   # Dependency lock file
├── README.md                 # User-facing documentation
├── QUICK_START.md           # Quick start guide
├── INSTALLATION.md          # Installation instructions
├── WEB_UI_GUIDE.md         # Web UI setup guide
├── AUTO_START_GUIDE.md     # Auto-start configuration
└── IMPLEMENTATION_SUMMARY.md # Implementation notes
```

---

## Key Modules

### 1. Classifier (`oxide/core/classifier.py`)

**Purpose**: Analyzes tasks and determines task type based on prompt and files.

**Key Classes**:
- `TaskType`: Enum of task types (CODEBASE_ANALYSIS, CODE_REVIEW, etc.)
- `TaskInfo`: Dataclass containing classification results
- `TaskClassifier`: Main classification logic

**Task Classification Logic**:
```python
# Thresholds
LARGE_CODEBASE_FILES = 20        # >20 files → CODEBASE_ANALYSIS
LARGE_CODEBASE_SIZE = 500_000    # >500KB → CODEBASE_ANALYSIS
QUICK_QUERY_MAX_FILES = 0        # No files + short prompt → QUICK_QUERY
QUICK_QUERY_MAX_PROMPT_LENGTH = 200

# Keyword-based detection
REVIEW_KEYWORDS = {"review", "analyze", "check", "audit", ...}
GENERATION_KEYWORDS = {"write", "create", "generate", ...}
DEBUG_KEYWORDS = {"debug", "fix", "bug", "error", ...}
```

**Key Methods**:
- `classify(prompt, files)`: Returns `TaskInfo` with task type, complexity, recommendations
- `_determine_task_type()`: Rule-based task type determination
- `_calculate_complexity()`: Complexity score (0.0-1.0) based on files/size/prompt
- `_recommend_services()`: Suggests services based on task type

### 2. Router (`oxide/core/router.py`)

**Purpose**: Selects appropriate LLM service based on task classification and routing rules.

**Key Classes**:
- `RouterDecision`: Dataclass containing routing decision
- `TaskRouter`: Main routing logic

**Routing Logic**:
1. Get routing rule for task type from config
2. Check if primary service is available (health check)
3. If unavailable, try fallback services in order
4. Determine execution mode (single vs. parallel)
5. Return RouterDecision with selected service

**Key Methods**:
- `route(task_info)`: Returns `RouterDecision` with service selection
- `_select_available_service()`: Finds first available service from primary + fallbacks
- `_is_service_available()`: Checks if service is enabled and healthy

### 3. Orchestrator (`oxide/core/orchestrator.py`)

**Purpose**: Main coordination engine that ties everything together.

**Key Responsibilities**:
1. Initialize all adapters from configuration
2. Classify incoming tasks (via Classifier)
3. Route tasks to services (via Router)
4. Execute tasks with retry/fallback logic
5. Health check and service status monitoring

**Key Methods**:
- `execute_task(prompt, files, preferences)`: Main execution entry point (async generator)
- `_execute_with_retry()`: Retry logic with fallback services
- `get_service_status()`: Health status of all services
- `test_service(service_name)`: Test a specific service

**Execution Flow**:
```python
async for chunk in orchestrator.execute_task(prompt, files):
    # 1. Classify task → TaskInfo
    # 2. Route task → RouterDecision
    # 3. Execute with retry/fallback
    # 4. Stream response chunks
    yield chunk
```

### 4. Adapters (`oxide/adapters/`)

**Purpose**: Provide uniform interface for different LLM services.

**Base Interface** (`base.py`):
```python
class BaseAdapter(ABC):
    @abstractmethod
    async def execute(prompt, files=None, **kwargs) -> AsyncIterator[str]:
        """Execute task and stream response chunks"""

    @abstractmethod
    async def health_check() -> bool:
        """Check if service is available"""

    def get_service_info() -> Dict[str, Any]:
        """Return service metadata"""
```

**Adapter Types**:

1. **CLI Adapters** (`gemini.py`, `qwen.py`)
   - Uses `asyncio.create_subprocess_exec()`
   - Streams stdout line-by-line
   - Health check: `executable --version`
   - File handling: Passes as CLI arguments

2. **HTTP Adapters** (`ollama_http.py`)
   - Uses `httpx.AsyncClient`
   - POST requests to API endpoints
   - Health check: GET `/api/tags` (Ollama) or `/v1/models` (OpenAI)
   - File handling: Reads and includes in prompt

### 5. MCP Server (`oxide/mcp/server.py`)

**Purpose**: Exposes Oxide functionality to Claude Code via MCP protocol.

**Available Tools**:

1. **`route_task`**
   - Routes task to best LLM automatically
   - Parameters: `prompt`, `files` (optional), `preferences` (optional)
   - Returns: Streamed response from selected service

2. **`analyze_parallel`**
   - Analyzes large codebase in parallel
   - Parameters: `directory`, `prompt`, `num_workers` (optional)
   - Returns: Aggregated results from multiple services

3. **`list_services`**
   - Lists all configured services with health status
   - Parameters: None
   - Returns: Service status information

**Auto-Start Web UI**:
- Checks `OXIDE_AUTO_START_WEB` environment variable
- If set to `true`, automatically starts web backend via subprocess

### 6. Parallel Executor (`oxide/execution/parallel.py`)

**Purpose**: Distributes tasks across multiple LLM services.

**Strategies**:

1. **Split Strategy** (default)
   - Divides files into chunks
   - Each service analyzes different subset
   - Faster for large codebases
   - Results aggregated sequentially

2. **Duplicate Strategy**
   - All services analyze same files
   - Useful for comparing model outputs
   - Results presented side-by-side

**Key Methods**:
- `execute_parallel()`: Main parallel execution entry point
- `_split_files()`: Divides files into N chunks
- `_aggregate_results()`: Combines results from multiple services

---

## Data Flow

### Task Execution Flow

```
1. Claude Code calls MCP tool
   ↓
2. MCP Server receives request
   ↓
3. OxideTools.route_task() called
   ↓
4. Orchestrator.execute_task()
   ├─→ Classifier.classify() → TaskInfo
   ├─→ Router.route(TaskInfo) → RouterDecision
   └─→ Orchestrator._execute_with_retry()
       ├─→ Try primary service
       │   └─→ Adapter.execute() → stream chunks
       ├─→ If fails, try fallback services
       └─→ If all fail, raise error
   ↓
5. Stream response chunks back to Claude Code
```

### Configuration Loading Flow

```
1. load_config() called
   ↓
2. Read config/default.yaml
   ↓
3. Parse YAML → dict
   ↓
4. Validate with Pydantic models
   ├─→ ServiceConfig validation
   ├─→ RoutingRuleConfig validation
   └─→ Cross-reference validation
   ↓
5. Return Config object
```

---

## Configuration System

### Main Configuration (`config/default.yaml`)

**Structure**:
```yaml
services:
  <service_name>:
    type: cli | http
    enabled: true | false
    # CLI-specific
    executable: <command>
    # HTTP-specific
    base_url: <url>
    api_type: ollama | openai_compatible
    default_model: <model_name>

routing_rules:
  <task_type>:
    primary: <service_name>
    fallback: [<service1>, <service2>, ...]
    timeout_seconds: <int>
    parallel_threshold_files: <int>

execution:
  max_parallel_workers: 3
  timeout_seconds: 120
  streaming: true
  retry_on_failure: true
  max_retries: 2

logging:
  level: INFO | DEBUG | WARNING | ERROR
  file: /path/to/logfile.log
  console: true | false
```

### Service Configuration

**CLI Service Example** (Gemini):
```yaml
gemini:
  type: cli
  executable: gemini
  enabled: true
  max_context_tokens: 2000000
  capabilities:
    - codebase_analysis
    - architecture_design
```

**HTTP Service Example** (Ollama):
```yaml
ollama_local:
  type: http
  base_url: "http://localhost:11434"
  api_type: ollama
  enabled: true
  default_model: "qwen2.5-coder:7b"
  models:
    - "qwen2.5-coder:7b"
    - "qwen2.5-coder:14b"
```

### Routing Rules

**Task Type → Service Mapping**:
- `codebase_analysis`: gemini (large context window)
- `code_review`: qwen (code-specialized)
- `code_generation`: qwen, ollama_local
- `quick_query`: ollama_local (fast, local)
- `debugging`: qwen, ollama_local
- `documentation`: ollama_local, qwen

**Fallback Chain**: Primary → Fallback1 → Fallback2 → ...

---

## Adapter Pattern

### Creating a New Adapter

**Step 1**: Create adapter class inheriting from `BaseAdapter`

```python
from typing import AsyncIterator, List, Optional
from ..adapters.base import BaseAdapter

class MyNewAdapter(BaseAdapter):
    def __init__(self, service_name: str, config: dict):
        super().__init__(service_name, config)
        # Initialize service-specific config

    async def execute(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        # Implement execution logic
        # Yield response chunks
        yield "response chunk"

    async def health_check(self) -> bool:
        # Implement health check
        return True
```

**Step 2**: Register adapter in `Orchestrator._create_adapter()`

```python
def _create_adapter(self, service_name: str, config: Dict) -> BaseAdapter:
    service_type = config.get("type")

    if service_type == "cli":
        if "mynew" in service_name.lower():
            return MyNewAdapter(service_name, config)
    # ... existing logic
```

**Step 3**: Add service to configuration

```yaml
services:
  mynew_service:
    type: cli
    executable: mynew
    enabled: true
```

### Adapter Implementation Guidelines

1. **Streaming**: Always yield chunks for responsive UX
2. **Error Handling**: Raise appropriate exceptions:
   - `ServiceUnavailableError`: Service not reachable
   - `ExecutionError`: Execution failed
   - `TimeoutError`: Operation timed out
3. **Health Checks**: Should be fast (<2 seconds)
4. **File Handling**: Support file context appropriately
5. **Logging**: Use `self.logger` for debugging

---

## Development Workflow

### Setup Development Environment

```bash
# Clone repository
git clone <repo-url>
cd oxide

# Install dependencies
uv sync

# Verify installation
uv run oxide-mcp --help
```

### Running Services

**Option 1: Unified Launcher**
```bash
uv run oxide-all  # Starts MCP + Web UI
```

**Option 2: Separate Services**
```bash
# Terminal 1: MCP Server
uv run oxide-mcp

# Terminal 2: Web Backend
uv run oxide-web

# Terminal 3: Web Frontend
cd oxide/web/frontend
npm install
npm run dev
```

**Option 3: Auto-Start Web UI**
```bash
# Set environment variable
export OXIDE_AUTO_START_WEB=true
uv run oxide-mcp
```

### Integration with Claude Code

Add to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "oxide": {
      "command": "uv",
      "args": ["--directory", "/path/to/oxide", "run", "oxide-mcp"],
      "env": {
        "OXIDE_AUTO_START_WEB": "true"
      }
    }
  }
}
```

### Making Changes

1. **Edit Code**: Make changes to relevant modules
2. **Test Locally**: Test with `uv run oxide-mcp`
3. **Validate Config**: Run `uv run python scripts/validate_config.py`
4. **Test Services**: Run `uv run python scripts/test_connection.py`
5. **Commit**: Follow conventional commit messages

---

## Skills and Plugins for Development

### Overview

This section describes the skills, plugins, and tools available to enhance development productivity when working on Oxide. These tools integrate with Claude Code and provide specialized capabilities for common development tasks.

### Claude Code Built-in Skills

**session-start-hook**
- **Purpose**: Set up repository environment for Claude Code web sessions
- **Use Case**: Create startup hooks to ensure tests and linters run during web sessions
- **How to Use**: `/skill session-start-hook` or let Claude invoke automatically when setting up the project
- **Relevant for Oxide**: Set up Python environment, activate venv, install dependencies

**Example Session Start Hook** (`.claude/hooks/session-start.sh`):
```bash
#!/bin/bash
# Ensure uv is available
command -v uv >/dev/null 2>&1 || { echo "uv not found"; exit 1; }

# Sync dependencies
uv sync

# Validate configuration
uv run python scripts/validate_config.py

echo "✅ Oxide development environment ready"
```

### MCP Servers for Development

MCP (Model Context Protocol) servers extend Claude Code with additional capabilities. Here are recommended MCP servers for Oxide development:

#### 1. **Oxide MCP Server** (Built-in)

**What it provides**:
- `route_task`: Intelligent task routing to best LLM
- `analyze_parallel`: Parallel codebase analysis
- `list_services`: Service health monitoring

**Configuration** (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "oxide": {
      "command": "uv",
      "args": ["--directory", "/path/to/oxide", "run", "oxide-mcp"],
      "env": {
        "OXIDE_AUTO_START_WEB": "true"
      }
    }
  }
}
```

**Usage in Development**:
```
# Test Oxide's own capabilities
Use oxide route_task to analyze the classifier.py module

# Check service health during development
Use oxide list_services
```

#### 2. **Filesystem MCP Server** (Recommended)

**What it provides**:
- Enhanced file operations
- Directory watching
- File search and indexing

**Why useful for Oxide**:
- Monitor config file changes
- Watch for service adapter updates
- Track log file changes

**Configuration**:
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/oxide"]
    }
  }
}
```

#### 3. **Git MCP Server** (Recommended)

**What it provides**:
- Git operations via MCP tools
- Commit history analysis
- Branch management

**Why useful for Oxide**:
- Track adapter implementation changes
- Review routing rule modifications
- Analyze configuration evolution

**Configuration**:
```json
{
  "mcpServers": {
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "/path/to/oxide"]
    }
  }
}
```

#### 4. **Python Environment MCP Server** (Recommended)

**What it provides**:
- Python package management
- Virtual environment handling
- Dependency resolution

**Why useful for Oxide**:
- Manage uv dependencies
- Check package versions
- Resolve dependency conflicts

#### 5. **PostgreSQL/SQLite MCP Server** (Optional)

**What it provides**:
- Database operations
- Query execution
- Schema management

**Why useful for Oxide** (future):
- Task history persistence
- Service metrics storage
- Usage analytics

### VS Code Extensions (if using VS Code)

While Oxide is primarily developed with Claude Code, these VS Code extensions are helpful:

1. **Python Extension** (`ms-python.python`)
   - Python language support
   - Debugging
   - Testing integration

2. **YAML Extension** (`redhat.vscode-yaml`)
   - YAML syntax validation
   - Schema validation for config files
   - Auto-completion

3. **Ruff** (`charliermarsh.ruff`)
   - Fast Python linter
   - Code formatting
   - Import sorting

4. **Pylance** (`ms-python.vscode-pylance`)
   - Type checking
   - Code intelligence
   - Import resolution

### Python Development Tools

#### Ruff (Recommended)

**Purpose**: Fast Python linter and formatter

**Installation**:
```bash
# Already included in dev dependencies
uv sync --dev
```

**Usage**:
```bash
# Lint code
uv run ruff check oxide/

# Format code
uv run ruff format oxide/

# Fix issues automatically
uv run ruff check --fix oxide/
```

**Configuration** (add to `pyproject.toml`):
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]
```

#### pytest (Testing Framework)

**Purpose**: Unit and integration testing

**Installation**:
```bash
# Already in dev dependencies
uv sync --dev
```

**Usage**:
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=oxide

# Run specific test
uv run pytest tests/test_classifier.py
```

#### mypy (Type Checking)

**Purpose**: Static type checking for Python

**Installation**:
```bash
# Add to dev dependencies
uv add --dev mypy
```

**Usage**:
```bash
# Type check entire codebase
uv run mypy oxide/

# Type check specific module
uv run mypy oxide/core/classifier.py
```

**Configuration** (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Claude Code Slash Commands

Create custom slash commands for common Oxide development tasks.

#### `.claude/commands/test-oxide.md`
```markdown
Run the following tests for Oxide:

1. Validate configuration: `uv run python scripts/validate_config.py`
2. Test service connections: `uv run python scripts/test_connection.py`
3. Run unit tests (when available): `uv run pytest`

Report any failures and suggest fixes.
```

**Usage**: `/test-oxide`

#### `.claude/commands/check-services.md`
```markdown
Check the health and status of all Oxide services:

1. Use the oxide list_services MCP tool
2. For any unhealthy services, diagnose the issue
3. Check logs at /tmp/oxide.log
4. Suggest configuration changes if needed

Provide a summary of service status.
```

**Usage**: `/check-services`

#### `.claude/commands/review-adapter.md`
```markdown
Review an adapter implementation for best practices:

1. Check if it properly inherits from BaseAdapter
2. Verify execute() streams chunks correctly
3. Check health_check() is implemented
4. Verify error handling (ServiceUnavailableError, etc.)
5. Check logging usage
6. Verify file handling
7. Check timeout handling

Provide detailed feedback and suggestions.
```

**Usage**: `/review-adapter`

### GitHub Actions Workflows (CI/CD)

Create workflows for automated testing and validation.

#### `.github/workflows/test.yml`
```yaml
name: Test Oxide

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Validate configuration
        run: uv run python scripts/validate_config.py

      - name: Run tests
        run: uv run pytest

      - name: Type check
        run: uv run mypy oxide/
```

### Pre-commit Hooks

Automate code quality checks before commits.

#### `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML, types-aiofiles]

  - repo: local
    hooks:
      - id: validate-config
        name: Validate Oxide Configuration
        entry: uv run python scripts/validate_config.py
        language: system
        pass_filenames: false
```

**Installation**:
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

### Docker Support (Optional)

For consistent development environments.

#### `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync

# Expose ports
EXPOSE 8000 3000

# Run MCP server by default
CMD ["uv", "run", "oxide-mcp"]
```

#### `docker-compose.yml`
```yaml
version: '3.8'

services:
  oxide-mcp:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config
      - ./oxide:/app/oxide
    environment:
      - OXIDE_AUTO_START_WEB=true

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
```

**Usage**:
```bash
# Build and run
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f
```

### Development Productivity Tips

#### 1. Use Claude Code's Task Agent

When working on complex features:
```
# In Claude Code:
"Plan the implementation of a new caching layer for Oxide adapters"
```

Claude Code's Task agent will:
- Explore the codebase
- Design the implementation
- Create a step-by-step plan
- Present for your approval

#### 2. Leverage Oxide's Own Tools

Use Oxide to analyze Oxide:
```
# Analyze Oxide's own code
Use oxide route_task to review the orchestrator.py module for potential improvements

# Parallel analysis
Use oxide analyze_parallel for ./oxide/adapters directory to compare adapter implementations
```

#### 3. Create Development Templates

**New Adapter Template** (`.claude/templates/new-adapter.py`):
```python
"""
<Service Name> adapter for Oxide.

<Brief description of the service>
"""
from typing import AsyncIterator, List, Optional
from ..adapters.base import BaseAdapter
from ..utils.exceptions import ServiceUnavailableError, ExecutionError

class <ServiceName>Adapter(BaseAdapter):
    """Adapter for <Service Name>."""

    def __init__(self, service_name: str, config: dict):
        super().__init__(service_name, config)
        # Initialize service-specific config
        self.<config_param> = config.get("<config_key>")

    async def execute(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Execute task on <Service Name>.

        Args:
            prompt: Task prompt
            files: Optional file paths
            **kwargs: Additional parameters

        Yields:
            Response chunks

        Raises:
            ServiceUnavailableError: If service is unreachable
            ExecutionError: If execution fails
        """
        try:
            # Implementation here
            yield "response chunk"

        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            raise ExecutionError(f"<Service Name> execution failed: {e}")

    async def health_check(self) -> bool:
        """
        Check if <Service Name> is available.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Implement health check
            return True
        except Exception as e:
            self.logger.debug(f"Health check failed: {e}")
            return False
```

#### 4. Use Environment Variables for Development

**`.env.development`**:
```bash
# Enable debug logging
OXIDE_LOG_LEVEL=DEBUG

# Auto-start web UI
OXIDE_AUTO_START_WEB=true

# Custom config path
OXIDE_CONFIG_PATH=./config/dev.yaml

# Development mode
OXIDE_DEV_MODE=true
```

**Load in development**:
```bash
# Source environment
source .env.development

# Run with development config
uv run oxide-mcp
```

### Recommended Workflow

**Daily Development Routine**:

1. **Start Development Session**
   ```bash
   # Pull latest changes
   git pull

   # Sync dependencies
   uv sync

   # Validate config
   uv run python scripts/validate_config.py

   # Start services
   uv run oxide-all
   ```

2. **Make Changes**
   - Use Claude Code for code generation/modification
   - Use `/test-oxide` command to validate
   - Use Oxide's own tools for code analysis
   - Run linter/formatter: `uv run ruff check --fix oxide/`

3. **Test Changes**
   ```bash
   # Unit tests
   uv run pytest

   # Integration tests
   uv run python scripts/test_connection.py

   # Manual testing via Claude Code
   # Use oxide route_task to test a simple query
   ```

4. **Commit Changes**
   ```bash
   # Pre-commit hooks run automatically
   git add .
   git commit -m "feat: add new feature"
   git push
   ```

### Integration Examples

**Example 1: Using Oxide with Git MCP Server**
```
# In Claude Code with both Oxide and Git MCP:

# Analyze recent changes
Use git to show the last 5 commits affecting oxide/adapters/

# Review changes with Oxide
Use oxide route_task to review the changes in oxide/adapters/gemini.py for potential issues
```

**Example 2: Using Oxide with Filesystem MCP**
```
# Watch for config changes and validate
Use filesystem to watch config/default.yaml for changes

# When changes detected, validate automatically
Use oxide list_services to check if services are still healthy
```

**Example 3: Development Workflow**
```
# 1. Create feature branch
Use git to create a new branch called "feature/new-adapter"

# 2. Generate adapter code
Generate a new adapter for OpenAI API following the template in .claude/templates/

# 3. Test adapter
Use oxide route_task to test the new adapter with a simple prompt

# 4. Commit changes
Use git to commit the changes with message "feat: add OpenAI adapter"
```

### Troubleshooting Skills and Plugins

**MCP Server Not Working**:
```bash
# Check MCP server status
cat ~/.claude/logs/mcp-*.log

# Test MCP server manually
uv run oxide-mcp

# Verify configuration
cat ~/.claude/settings.json
```

**Skill Not Available**:
```
# Check available skills
/help

# Verify skill file exists
ls .claude/skills/

# Check skill syntax
cat .claude/skills/session-start-hook.md
```

**Slash Command Not Found**:
```bash
# List available commands
ls .claude/commands/

# Check command syntax
cat .claude/commands/test-oxide.md
```

---

## Code Conventions

### Python Style

- **Python Version**: 3.11+
- **Style Guide**: PEP 8
- **Type Hints**: Use type hints for all function signatures
- **Docstrings**: Google-style docstrings for all public functions/classes
- **Async**: Use `async/await` for I/O operations

### Module Organization

```python
"""
Module docstring explaining purpose.

More detailed explanation if needed.
"""
# Standard library imports
import asyncio
from typing import List, Dict

# Third-party imports
import yaml
from pydantic import BaseModel

# Local imports
from ..utils.logging import logger
from ..utils.exceptions import BaseOxideError
```

### Naming Conventions

- **Classes**: PascalCase (`TaskClassifier`, `BaseAdapter`)
- **Functions/Methods**: snake_case (`execute_task`, `load_config`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private Methods**: Leading underscore (`_execute_with_retry`)
- **Exceptions**: End with "Error" (`ConfigError`, `AdapterError`)

### Error Handling

```python
# Use custom exceptions from utils.exceptions
from ..utils.exceptions import ServiceUnavailableError

# Raise with context
raise ServiceUnavailableError(
    service_name="gemini",
    reason="CLI executable not found"
)

# Log errors before raising
self.logger.error(f"Failed to connect: {e}")
raise AdapterError(f"Connection failed: {e}")
```

### Logging

```python
# Get logger for module
from ..utils.logging import logger

# Create child logger
self.logger = logger.getChild("classifier")

# Log at appropriate levels
self.logger.debug("Detailed debug info")
self.logger.info("Task classified as CODE_REVIEW")
self.logger.warning("Primary service unavailable, using fallback")
self.logger.error("All services failed")
```

### Configuration Validation

- Use Pydantic models for all configuration
- Add field validators for complex validation
- Provide clear error messages
- Use `Optional` for optional fields
- Provide sensible defaults

---

## Testing Strategy

### Current Test Coverage

**Existing Tests**:
- `scripts/test_network.py`: Test network services (Ollama remote, LM Studio)
- `scripts/test_connection.py`: Test service connections
- `scripts/validate_config.py`: Validate configuration files

**Missing Tests** (TODO):
- Unit tests for classifiers/router/orchestrator
- Integration tests for adapters
- MCP tool tests
- Parallel execution tests

### Testing Approach

**1. Unit Tests** (pytest)
```python
# tests/test_classifier.py
import pytest
from oxide.core.classifier import TaskClassifier, TaskType

def test_large_codebase_classification():
    classifier = TaskClassifier()
    task_info = classifier.classify(
        prompt="Analyze this code",
        files=[f"file{i}.py" for i in range(25)]
    )
    assert task_info.task_type == TaskType.CODEBASE_ANALYSIS
```

**2. Integration Tests**
```python
# tests/test_adapters.py
import pytest
from oxide.adapters.ollama_http import OllamaHTTPAdapter

@pytest.mark.asyncio
async def test_ollama_health_check():
    adapter = OllamaHTTPAdapter("test", {
        "base_url": "http://localhost:11434",
        "api_type": "ollama"
    })
    is_healthy = await adapter.health_check()
    assert is_healthy == True
```

**3. Manual Testing**
```bash
# Test MCP server
uv run oxide-mcp

# In Claude Code:
# Use oxide route_task to analyze this code
```

### Testing Guidelines

- Use `pytest` for all tests
- Use `pytest-asyncio` for async tests
- Mock external services where appropriate
- Test error conditions and edge cases
- Aim for >80% code coverage

---

## Common Tasks

### Adding a New Task Type

**1. Add to TaskType enum** (`oxide/core/classifier.py`):
```python
class TaskType(str, Enum):
    # ... existing types
    MY_NEW_TASK = "my_new_task"
```

**2. Add keyword detection** (`oxide/core/classifier.py`):
```python
MY_NEW_TASK_KEYWORDS = {"keyword1", "keyword2", "keyword3"}
```

**3. Add to classification logic**:
```python
def _determine_task_type(self, ...):
    # ... existing logic
    if prompt_words & self.MY_NEW_TASK_KEYWORDS:
        return TaskType.MY_NEW_TASK
```

**4. Add service recommendations**:
```python
def _recommend_services(self, task_type, ...):
    recommendations = {
        # ... existing mappings
        TaskType.MY_NEW_TASK: ["service1", "service2"],
    }
```

**5. Add routing rule** (`config/default.yaml`):
```yaml
routing_rules:
  my_new_task:
    primary: service1
    fallback:
      - service2
    timeout_seconds: 60
```

### Adding a New LLM Service

**1. Create adapter class** (see [Adapter Pattern](#adapter-pattern))

**2. Add to configuration**:
```yaml
services:
  my_service:
    type: cli  # or http
    executable: myservice  # for CLI
    enabled: true
```

**3. Test adapter**:
```bash
uv run python scripts/test_connection.py
```

**4. Update routing rules** to use new service

### Modifying Routing Rules

Edit `config/default.yaml`:
```yaml
routing_rules:
  code_review:
    primary: my_new_service  # Changed
    fallback:
      - qwen
      - ollama_local
```

Validate:
```bash
uv run python scripts/validate_config.py
```

Restart MCP server to apply changes.

### Debugging Service Issues

**1. Check service health**:
```python
# In Claude Code:
# Use oxide list_services
```

**2. Check logs**:
```bash
tail -f /tmp/oxide.log
```

**3. Test service directly**:
```bash
# CLI service
gemini --version

# HTTP service
curl http://localhost:11434/api/tags
```

**4. Enable debug logging** (`config/default.yaml`):
```yaml
logging:
  level: DEBUG
```

---

## Debugging Guide

### Common Issues

**1. "Service unavailable" errors**

**Cause**: Service not running or misconfigured

**Fix**:
- Check if CLI executable is in PATH: `which gemini`
- Check if HTTP service is running: `curl <base_url>`
- Verify configuration in `config/default.yaml`
- Check health with `list_services` tool

**2. "No service available" errors**

**Cause**: All configured services are disabled or unhealthy

**Fix**:
- Enable at least one service in config
- Check service health
- Review fallback chains in routing rules

**3. Timeout errors**

**Cause**: Task taking too long

**Fix**:
- Increase timeout in routing rules
- Increase global timeout in execution config
- Use faster service for task type
- Enable parallel execution for large tasks

**4. Import errors**

**Cause**: Package not installed correctly

**Fix**:
```bash
uv sync
uv run oxide-mcp
```

**5. Configuration errors**

**Cause**: Invalid YAML or validation failure

**Fix**:
```bash
# Validate config
uv run python scripts/validate_config.py

# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config/default.yaml'))"
```

### Debugging Workflow

**Step 1**: Check logs
```bash
tail -f /tmp/oxide.log
```

**Step 2**: Enable debug logging
```yaml
logging:
  level: DEBUG
```

**Step 3**: Test services individually
```bash
uv run python scripts/test_connection.py
```

**Step 4**: Test with simple prompt
```python
# In Claude Code:
# Use oxide route_task with prompt "Hello"
```

**Step 5**: Check MCP server output
```bash
# MCP server logs to stderr
uv run oxide-mcp 2>&1 | tee mcp.log
```

---

## AI Assistant Guidelines

### Understanding the Codebase

**Before Making Changes**:
1. Read this CLAUDE.md file completely
2. Understand the architecture and data flow
3. Identify which modules need modification
4. Check existing patterns and conventions
5. Review related code in the module

**Key Areas to Understand**:
- Classification logic (keywords, thresholds)
- Routing rules (primary, fallback chains)
- Adapter interface (execute, health_check)
- Configuration structure (YAML → Pydantic)
- Error handling (custom exceptions)

### Making Code Changes

**DO**:
- ✅ Follow existing code patterns
- ✅ Add type hints to all functions
- ✅ Write docstrings for public APIs
- ✅ Use custom exceptions from `utils.exceptions`
- ✅ Log at appropriate levels
- ✅ Handle errors gracefully with fallbacks
- ✅ Test changes with `uv run oxide-mcp`
- ✅ Validate config with `scripts/validate_config.py`
- ✅ Update relevant documentation

**DON'T**:
- ❌ Break existing APIs without migration plan
- ❌ Add dependencies without updating pyproject.toml
- ❌ Skip error handling
- ❌ Remove logging statements
- ❌ Hardcode values (use config instead)
- ❌ Ignore async/await conventions
- ❌ Commit without testing

### Common Modification Patterns

**1. Adding a Feature**:
```
1. Understand current implementation
2. Design feature (data flow, interfaces)
3. Update relevant modules
4. Add configuration if needed
5. Test manually
6. Update documentation
```

**2. Fixing a Bug**:
```
1. Reproduce the bug
2. Check logs for error messages
3. Identify root cause
4. Fix in appropriate module
5. Test fix
6. Add logging if needed for future debugging
```

**3. Refactoring**:
```
1. Understand current code flow
2. Ensure tests exist (or add them)
3. Refactor incrementally
4. Test after each change
5. Maintain backward compatibility
```

### Working with Configuration

**When to use configuration**:
- Service endpoints, models, capabilities
- Routing rules and priorities
- Timeouts, retries, thresholds
- Feature flags

**How to add config**:
1. Add field to appropriate Pydantic model in `config/loader.py`
2. Add validation if needed
3. Update `config/default.yaml` with new field
4. Access via `self.config.<section>.<field>`
5. Document in docstring

### Testing Checklist

Before considering a change complete:
- [ ] Code follows existing patterns
- [ ] Type hints added
- [ ] Docstrings written
- [ ] Error handling implemented
- [ ] Logging added
- [ ] Configuration validated
- [ ] Manual testing done
- [ ] Documentation updated

### Communication with User

**When to ask for clarification**:
- Multiple valid implementation approaches
- Breaking changes required
- New dependencies needed
- Security considerations
- Performance trade-offs
- API design decisions

**What to include in responses**:
- Clear explanation of changes
- File paths and line numbers
- Reasoning behind decisions
- Potential impacts or side effects
- Testing performed
- Next steps or recommendations

### Example Workflows

**Scenario 1: User wants to add a new LLM service**

**Response approach**:
1. Ask for service details (CLI vs HTTP, endpoint/executable, etc.)
2. Explain adapter pattern and which to use
3. Create adapter class
4. Add to configuration
5. Register in orchestrator
6. Test with simple prompt
7. Update documentation

**Scenario 2: User wants to change routing logic**

**Response approach**:
1. Understand current routing rules
2. Clarify desired routing behavior
3. Determine if config change or code change needed
4. Update routing rules in config OR classifier logic
5. Validate configuration
6. Test with representative prompts
7. Explain how to verify changes

**Scenario 3: User reports service failures**

**Response approach**:
1. Check logs for errors
2. Test service health
3. Verify configuration
4. Check network connectivity (for HTTP services)
5. Check executable availability (for CLI services)
6. Suggest fixes based on diagnosis
7. Add more logging if needed for future debugging

---

## Project Philosophy

### Design Principles

1. **Simplicity**: Keep implementations simple and understandable
2. **Extensibility**: Easy to add new services and task types
3. **Reliability**: Graceful fallbacks and error handling
4. **Performance**: Parallel execution for large tasks
5. **Observability**: Comprehensive logging and monitoring

### Architecture Decisions

**Why MCP?**
- Native integration with Claude Code
- Standard protocol for AI tool integration
- Streaming support for responsive UX

**Why Async/Await?**
- Non-blocking I/O for multiple services
- Better performance for parallel execution
- Native streaming support

**Why YAML Configuration?**
- Human-readable and editable
- Easy to version control
- Supports comments for documentation

**Why Adapter Pattern?**
- Uniform interface for different services
- Easy to add new services
- Swappable implementations

---

## Future Considerations

### Planned Improvements

1. **Test Suite**: Comprehensive unit and integration tests
2. **Advanced Routing**: ML-based routing instead of rule-based
3. **Caching**: Cache responses for repeated queries
4. **Metrics**: Track usage, performance, success rates
5. **Security**: API key management, rate limiting
6. **Documentation Generation**: Auto-generate API docs

### Extension Points

- **New Adapters**: Support more LLM services
- **New Strategies**: Additional parallel execution strategies
- **Custom Classifiers**: ML-based task classification
- **Plugin System**: User-defined custom tools
- **Cost Tracking**: Track token usage and costs

---

## Quick Reference

### File Locations

| Purpose | File Path |
|---------|-----------|
| Main configuration | `config/default.yaml` |
| Model profiles | `config/models.yaml` |
| Task classification | `oxide/core/classifier.py` |
| Service routing | `oxide/core/router.py` |
| Main orchestrator | `oxide/core/orchestrator.py` |
| MCP server | `oxide/mcp/server.py` |
| MCP tools | `oxide/mcp/tools.py` |
| Base adapter | `oxide/adapters/base.py` |
| Configuration loader | `oxide/config/loader.py` |
| Custom exceptions | `oxide/utils/exceptions.py` |
| Logging setup | `oxide/utils/logging.py` |

### Command Reference

```bash
# Run MCP server
uv run oxide-mcp

# Run web UI
uv run oxide-web

# Run both
uv run oxide-all

# Validate configuration
uv run python scripts/validate_config.py

# Test network services
uv run python scripts/test_network.py

# Test service connections
uv run python scripts/test_connection.py

# Start all services (script)
./scripts/start_all.sh
```

### Key Constants

```python
# Classification thresholds
LARGE_CODEBASE_FILES = 20
LARGE_CODEBASE_SIZE = 500_000  # bytes
QUICK_QUERY_MAX_FILES = 0
QUICK_QUERY_MAX_PROMPT_LENGTH = 200

# Execution defaults
DEFAULT_TIMEOUT = 120  # seconds
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_PARALLEL_WORKERS = 3
```

### Environment Variables

```bash
# Auto-start web UI with MCP server
OXIDE_AUTO_START_WEB=true

# Custom config path (if needed)
OXIDE_CONFIG_PATH=/path/to/config.yaml
```

---

## Conclusion

This guide provides comprehensive information for AI assistants working with the Oxide codebase. When in doubt:

1. **Read the code**: The code is well-documented with docstrings
2. **Check the logs**: Logs provide detailed debugging information
3. **Test incrementally**: Test each change before proceeding
4. **Ask for clarification**: When multiple approaches exist, ask the user
5. **Follow patterns**: Maintain consistency with existing code

**Remember**: The goal is to create a reliable, maintainable, and extensible LLM orchestration system. Every change should align with this goal.

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: AI assistants working on Oxide
**Next Review**: When major architectural changes occur
