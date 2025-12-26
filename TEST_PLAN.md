# Oxide LLM Orchestrator - Test Implementation Plan

## Executive Summary

This document outlines a comprehensive testing strategy to achieve 80%+ code coverage for the Oxide LLM Orchestrator. The plan covers unit tests, integration tests, and end-to-end tests with detailed fixtures and mocking strategies.

**Current Coverage:** ~10% (only 2 test files)
**Target Coverage:** 80%+
**Timeline:** Phased approach with immediate priority on core components

---

## 1. Codebase Analysis

### 1.1 Core Components (Priority: CRITICAL)

#### **src/oxide/core/classifier.py** (260 lines)
- **Complexity:** Medium
- **Coverage:** 0%
- **Testing Priority:** HIGH
- **Key Functions:**
  - `classify()` - Main classification logic
  - `_determine_task_type()` - Task type detection
  - `_calculate_complexity()` - Complexity scoring
  - `_recommend_services()` - Service recommendation
  - `_should_use_parallel()` - Parallel execution decision
  - `_calculate_total_size()` - File size calculation

#### **src/oxide/core/router.py** (206 lines)
- **Complexity:** Medium-High
- **Coverage:** 0%
- **Testing Priority:** HIGH
- **Key Functions:**
  - `route()` - Main routing decision
  - `_route_from_recommendations()` - Fallback routing
  - `_select_available_service()` - Service selection with fallback
  - `_is_service_available()` - Service availability check

#### **src/oxide/core/orchestrator.py** (444 lines)
- **Complexity:** High
- **Coverage:** 0%
- **Testing Priority:** CRITICAL
- **Key Functions:**
  - `execute_task()` - Main task execution with streaming
  - `_execute_with_retry()` - Retry and fallback logic
  - `_check_service_health()` - Health checking
  - `get_service_status()` - Service status aggregation
  - `test_service()` - Service testing

### 1.2 Adapters (Priority: HIGH)

#### **src/oxide/adapters/base.py** (96 lines)
- Abstract interface definition
- **Testing Strategy:** Test via concrete implementations

#### **src/oxide/adapters/cli_adapter.py** (217 lines)
- **Coverage:** 0%
- **Testing Priority:** HIGH
- **Key Functions:**
  - `execute()` - CLI execution with streaming
  - `_build_command()` - Command construction
  - `_stream_output()` - Output streaming
  - `health_check()` - CLI tool availability

#### **src/oxide/adapters/gemini.py** (31 lines)
- **Coverage:** 0%
- **Testing Priority:** MEDIUM
- **Strategy:** Inherits from CLIAdapter, test overrides

#### **src/oxide/adapters/qwen.py** (Similar to gemini.py)
- **Coverage:** 0%
- **Testing Priority:** MEDIUM

#### **src/oxide/adapters/ollama_http.py** (455 lines)
- **Coverage:** 0%
- **Testing Priority:** HIGH
- **Key Functions:**
  - `_ensure_service_ready()` - Auto-start and model detection
  - `execute()` - HTTP execution with retries
  - `_execute_ollama()` - Ollama API protocol
  - `_execute_openai_compatible()` - OpenAI API protocol
  - `health_check()` - HTTP health check
  - `get_models()` - Model listing

### 1.3 Utilities (Priority: MEDIUM-HIGH)

#### **src/oxide/utils/task_storage.py** (286 lines)
- **Coverage:** ~30% (partial integration test exists)
- **Testing Priority:** MEDIUM
- **Key Functions:**
  - `add_task()` - Task creation
  - `update_task()` - Task updates with status tracking
  - `get_task()` - Task retrieval
  - `list_tasks()` - Task listing with filters
  - `delete_task()` - Task deletion
  - `clear_tasks()` - Bulk deletion
  - `get_stats()` - Statistics aggregation

#### **src/oxide/utils/service_manager.py** (408 lines)
- **Coverage:** 0%
- **Testing Priority:** HIGH
- **Key Functions:**
  - `ensure_ollama_running()` - Auto-start Ollama
  - `_start_ollama()` - Platform-specific startup
  - `get_available_models()` - Model discovery
  - `auto_detect_model()` - Smart model selection
  - `ensure_service_healthy()` - Comprehensive health check

#### **src/oxide/utils/process_manager.py**
- **Coverage:** ~60% (test exists)
- **Testing Priority:** LOW (already tested)

#### **src/oxide/utils/routing_rules.py**
- **Coverage:** Unknown
- **Testing Priority:** MEDIUM

### 1.4 API Endpoints (Priority: HIGH)

#### **src/oxide/web/backend/routes/tasks.py** (266 lines)
- **Coverage:** 0%
- **Testing Priority:** HIGH
- **Endpoints:**
  - `POST /execute` - Task execution
  - `GET /{task_id}` - Task status retrieval
  - `GET /` - Task listing
  - `DELETE /{task_id}` - Task deletion
  - `POST /clear` - Clear tasks

#### **src/oxide/web/backend/routes/services.py** (211 lines)
- **Coverage:** 0%
- **Testing Priority:** HIGH
- **Endpoints:**
  - `GET /` - List all services
  - `GET /{service_name}` - Service details
  - `POST /{service_name}/health` - Health check
  - `POST /{service_name}/test` - Service test
  - `GET /{service_name}/models` - Model listing
  - `GET /routing/rules` - Routing rules

#### **src/oxide/web/backend/routes/config.py**
- **Coverage:** 0%
- **Testing Priority:** MEDIUM

#### **src/oxide/web/backend/routes/monitoring.py**
- **Coverage:** 0%
- **Testing Priority:** MEDIUM

### 1.5 Other Components

#### **src/oxide/memory/context_memory.py**
- **Testing Priority:** MEDIUM
- **Coverage:** Some existing tests

#### **src/oxide/analytics/cost_tracker.py**
- **Testing Priority:** MEDIUM
- **Coverage:** Some existing tests

#### **src/oxide/cluster/coordinator.py**
- **Testing Priority:** LOW
- **Coverage:** Some existing tests

#### **src/oxide/config/loader.py**
- **Testing Priority:** MEDIUM
- **Coverage:** Unknown

---

## 2. Test Structure

```
tests/
├── __init__.py
├── conftest.py                      # Shared fixtures and configuration
├── pytest.ini                       # Pytest configuration
│
├── unit/                            # Unit tests (isolated components)
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── test_classifier.py       # TaskClassifier tests
│   │   ├── test_router.py           # TaskRouter tests
│   │   └── test_orchestrator.py     # Orchestrator tests
│   │
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── test_base_adapter.py     # Base adapter tests
│   │   ├── test_cli_adapter.py      # CLI adapter tests
│   │   ├── test_gemini_adapter.py   # Gemini-specific tests
│   │   ├── test_qwen_adapter.py     # Qwen-specific tests
│   │   └── test_ollama_http.py      # Ollama HTTP adapter tests
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── test_task_storage.py     # TaskStorage unit tests
│   │   ├── test_service_manager.py  # ServiceManager tests
│   │   ├── test_routing_rules.py    # Routing rules tests
│   │   └── test_exceptions.py       # Exception classes tests
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── test_loader.py           # Config loading tests
│   │   └── test_hot_reload.py       # Hot reload tests
│   │
│   └── analytics/
│       ├── __init__.py
│       └── test_cost_tracker.py     # Cost tracking tests
│
├── integration/                     # Integration tests (component interactions)
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── test_tasks_api.py        # Tasks endpoints
│   │   ├── test_services_api.py     # Services endpoints
│   │   ├── test_config_api.py       # Config endpoints
│   │   └── test_monitoring_api.py   # Monitoring endpoints
│   │
│   ├── test_end_to_end_flow.py      # Complete task flow
│   └── test_service_integration.py  # Service manager + adapters
│
└── fixtures/                        # Test fixtures and mock data
    ├── __init__.py
    ├── sample_configs.py
    ├── sample_files.py
    └── mock_responses.py
```

---

## 3. Testing Dependencies

### 3.1 Required Packages

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",           # Coverage reporting
    "pytest-mock>=3.14.0",          # Mocking utilities
    "pytest-timeout>=2.3.0",        # Timeout handling
    "httpx>=0.27.0",                # Async HTTP client for API tests
    "respx>=0.21.0",                # HTTP mocking for aiohttp
    "fakefs>=5.0.0",                # Filesystem mocking
    "freezegun>=1.5.0",             # Time mocking
]
```

### 3.2 Pytest Configuration

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests (isolated components)
    integration: Integration tests (component interactions)
    slow: Slow tests requiring external services
    requires_network: Tests requiring network access

addopts =
    -v
    --strict-markers
    --tb=short
    --cov=src/oxide
    --cov-report=html
    --cov-report=term-missing
    --cov-branch
    --cov-fail-under=80
```

---

## 4. Mocking & Fixture Strategies

### 4.1 Common Fixtures (conftest.py)

```python
# Mock Configuration
@pytest.fixture
def mock_config():
    """Provide a complete mock Config object"""

# Mock Orchestrator
@pytest.fixture
def mock_orchestrator():
    """Provide a mock Orchestrator with basic dependencies"""

# Mock Adapters
@pytest.fixture
def mock_cli_adapter():
    """Mock CLI adapter for testing"""

@pytest.fixture
def mock_http_adapter():
    """Mock HTTP adapter for testing"""

# Mock Services
@pytest.fixture
def mock_subprocess():
    """Mock subprocess for CLI adapter tests"""

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for HTTP adapter tests"""

# Test Files and Data
@pytest.fixture
def temp_test_files(tmp_path):
    """Create temporary test files"""

@pytest.fixture
def sample_task_prompts():
    """Provide sample task prompts for classification"""

# FastAPI Test Client
@pytest.fixture
def api_client():
    """Provide FastAPI TestClient"""

# Task Storage
@pytest.fixture
def temp_task_storage(tmp_path):
    """Isolated task storage for testing"""
```

### 4.2 Mocking Strategies by Component

#### **Classifier Tests**
- **No External Dependencies:** Straightforward unit tests
- **Mock:** File system operations (`Path.stat()`)
- **Focus:** Logic correctness, edge cases

#### **Router Tests**
- **Mock:** Service health checker (async callable)
- **Mock:** Config object
- **Focus:** Routing logic, fallback behavior

#### **Orchestrator Tests**
- **Mock:** All adapters
- **Mock:** Classifier, Router
- **Mock:** Memory, CostTracker
- **Focus:** Task execution flow, retry logic, error handling

#### **CLI Adapter Tests**
- **Mock:** `asyncio.create_subprocess_exec`
- **Mock:** Process stdout/stderr streams
- **Focus:** Command construction, streaming, error handling

#### **HTTP Adapter Tests**
- **Mock:** `aiohttp.ClientSession`
- **Mock:** HTTP responses (using `respx` or `aioresponses`)
- **Focus:** API protocol compliance, retry logic, error messages

#### **Service Manager Tests**
- **Mock:** `subprocess.Popen`, `shutil.which`
- **Mock:** HTTP health check calls
- **Mock:** Platform detection (`platform.system()`)
- **Focus:** Auto-start logic, model detection, platform-specific behavior

#### **API Endpoint Tests**
- **Use:** FastAPI TestClient
- **Mock:** Orchestrator dependency
- **Mock:** WebSocket manager
- **Focus:** Request/response validation, error handling, background tasks

---

## 5. Test Case Examples

### 5.1 Classifier Tests (`test_classifier.py`)

```python
class TestTaskClassifier:
    """Test suite for TaskClassifier"""

    def test_classify_quick_query(self):
        """Test classification of quick queries"""
        classifier = TaskClassifier()
        task_info = classifier.classify("What is 2 + 2?")
        assert task_info.task_type == TaskType.QUICK_QUERY
        assert task_info.file_count == 0
        assert task_info.complexity_score < 0.3

    def test_classify_code_review(self):
        """Test code review detection"""
        classifier = TaskClassifier()
        task_info = classifier.classify(
            "Review this code for bugs",
            files=["src/main.py"]
        )
        assert task_info.task_type == TaskType.CODE_REVIEW
        assert "review" in [s for s in task_info.recommended_services]

    def test_classify_large_codebase(self, temp_large_files):
        """Test large codebase detection"""
        classifier = TaskClassifier()
        task_info = classifier.classify(
            "Analyze this codebase",
            files=temp_large_files  # 25+ files
        )
        assert task_info.task_type == TaskType.CODEBASE_ANALYSIS
        assert task_info.use_parallel is True
        assert "gemini" in task_info.recommended_services

    def test_complexity_calculation(self):
        """Test complexity score calculation"""
        classifier = TaskClassifier()
        # Small task
        task1 = classifier.classify("Hello", files=[])
        assert task1.complexity_score < 0.2

        # Large task
        task2 = classifier.classify(
            "Analyze entire codebase" * 100,
            files=["file" + str(i) for i in range(100)]
        )
        assert task2.complexity_score > 0.8
```

### 5.2 Router Tests (`test_router.py`)

```python
class TestTaskRouter:
    """Test suite for TaskRouter"""

    async def test_route_basic(self, mock_config):
        """Test basic routing decision"""
        router = TaskRouter(mock_config)
        task_info = TaskInfo(
            task_type=TaskType.CODE_REVIEW,
            file_count=1,
            total_size_bytes=1000,
            complexity_score=0.3,
            recommended_services=["qwen"]
        )

        decision = await router.route(task_info)
        assert decision.primary_service == "qwen"
        assert decision.execution_mode == "single"

    async def test_route_with_fallback(self, mock_config):
        """Test routing with service fallback"""
        # Mock health checker that fails primary service
        async def health_checker(service_name):
            return service_name != "primary_service"

        router = TaskRouter(mock_config, health_checker)
        # Test fallback logic

    async def test_route_no_service_available(self, mock_config):
        """Test routing when no service is available"""
        router = TaskRouter(mock_config)
        # All services disabled/unhealthy
        with pytest.raises(NoServiceAvailableError):
            await router.route(task_info)
```

### 5.3 Orchestrator Tests (`test_orchestrator.py`)

```python
class TestOrchestrator:
    """Test suite for Orchestrator"""

    async def test_execute_task_success(self, mock_config, mock_adapter):
        """Test successful task execution"""
        orchestrator = Orchestrator(mock_config)
        orchestrator.adapters = {"test_service": mock_adapter}

        # Mock adapter to yield test response
        async def mock_execute(*args, **kwargs):
            yield "Hello"
            yield " "
            yield "World"

        mock_adapter.execute = mock_execute

        result = []
        async for chunk in orchestrator.execute_task("Test prompt"):
            result.append(chunk)

        assert "".join(result) == "Hello World"

    async def test_execute_task_with_retry(self, mock_config):
        """Test task execution with retry on failure"""
        orchestrator = Orchestrator(mock_config)

        # Mock adapter that fails twice then succeeds
        attempt_count = 0
        async def mock_execute(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ServiceUnavailableError("test", "Failed")
            yield "Success"

        # Test retry logic

    async def test_execute_task_memory_integration(self, mock_config):
        """Test memory storage during task execution"""
        orchestrator = Orchestrator(mock_config)
        # Verify memory is populated with user/assistant messages
```

### 5.4 CLI Adapter Tests (`test_cli_adapter.py`)

```python
class TestCLIAdapter:
    """Test suite for CLIAdapter"""

    async def test_execute_success(self, mock_subprocess):
        """Test successful CLI execution"""
        config = {"executable": "test-cli", "type": "cli"}
        adapter = CLIAdapter("test", config)

        # Mock subprocess that yields output
        mock_process = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[b"Line 1\n", b"Line 2\n", b""]
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = []
        async for chunk in adapter.execute("Test prompt"):
            result.append(chunk)

        assert len(result) == 2

    async def test_build_command_with_files(self):
        """Test command building with file references"""
        config = {"executable": "gemini", "type": "cli"}
        adapter = CLIAdapter("gemini", config)

        cmd = await adapter._build_command(
            "Analyze this",
            files=["/path/to/file1.py", "/path/to/file2.py"]
        )

        assert cmd[0] == "gemini"
        assert cmd[1] == "-p"
        assert "@/path/to/file1.py" in cmd[2]
        assert "@/path/to/file2.py" in cmd[2]

    async def test_timeout_handling(self, mock_subprocess):
        """Test timeout during execution"""
        adapter = CLIAdapter("test", {"executable": "test-cli"})

        # Mock process that hangs
        with pytest.raises(TimeoutError):
            async for _ in adapter.execute("prompt", timeout=1):
                await asyncio.sleep(10)
```

### 5.5 HTTP Adapter Tests (`test_ollama_http.py`)

```python
class TestOllamaHTTPAdapter:
    """Test suite for OllamaHTTPAdapter"""

    async def test_execute_ollama_api(self, respx_mock):
        """Test Ollama API execution"""
        config = {
            "base_url": "http://localhost:11434",
            "api_type": "ollama",
            "default_model": "qwen2.5-coder"
        }
        adapter = OllamaHTTPAdapter("ollama_local", config)

        # Mock health check
        respx_mock.get("http://localhost:11434/api/tags").mock(
            return_value=Response(200, json={"models": [{"name": "qwen2.5-coder"}]})
        )

        # Mock generate endpoint
        respx_mock.post("http://localhost:11434/api/generate").mock(
            return_value=Response(
                200,
                stream=[
                    b'{"response":"Hello","done":false}\n',
                    b'{"response":" World","done":true}\n'
                ]
            )
        )

        result = []
        async for chunk in adapter.execute("Test"):
            result.append(chunk)

        assert "".join(result) == "Hello World"

    async def test_auto_start_ollama(self, mock_service_manager):
        """Test Ollama auto-start functionality"""
        adapter = OllamaHTTPAdapter("ollama", {
            "base_url": "http://localhost:11434",
            "api_type": "ollama",
            "auto_start": True
        })

        # Verify auto-start is triggered when service is down
```

### 5.6 API Endpoint Tests (`test_tasks_api.py`)

```python
class TestTasksAPI:
    """Test suite for Tasks API endpoints"""

    async def test_execute_task_endpoint(self, api_client, mock_orchestrator):
        """Test POST /tasks/execute"""
        response = api_client.post("/api/tasks/execute", json={
            "prompt": "Test prompt",
            "files": [],
            "preferences": {}
        })

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    async def test_get_task_status(self, api_client, task_storage):
        """Test GET /tasks/{task_id}"""
        # Create a test task
        task_id = "test-123"
        task_storage.add_task(task_id, "Test prompt")

        response = api_client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["id"] == task_id

    async def test_list_tasks(self, api_client, task_storage):
        """Test GET /tasks/"""
        # Add multiple tasks
        for i in range(5):
            task_storage.add_task(f"task-{i}", f"Prompt {i}")

        response = api_client.get("/api/tasks/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 5
        assert data["total"] == 5
```

---

## 6. Coverage Goals by Component

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| core/classifier.py | 0% | 95% | CRITICAL |
| core/router.py | 0% | 95% | CRITICAL |
| core/orchestrator.py | 0% | 85% | CRITICAL |
| adapters/cli_adapter.py | 0% | 90% | HIGH |
| adapters/ollama_http.py | 0% | 90% | HIGH |
| adapters/gemini.py | 0% | 85% | MEDIUM |
| adapters/qwen.py | 0% | 85% | MEDIUM |
| utils/task_storage.py | 30% | 95% | MEDIUM |
| utils/service_manager.py | 0% | 85% | HIGH |
| web/backend/routes/tasks.py | 0% | 90% | HIGH |
| web/backend/routes/services.py | 0% | 90% | HIGH |
| **Overall Project** | **~10%** | **80%+** | - |

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1)
1. Set up test infrastructure (conftest.py, fixtures)
2. Add test dependencies to pyproject.toml
3. Configure pytest.ini
4. Create initial mock utilities

### Phase 2: Core Components (Week 1-2)
1. Implement classifier tests (95% coverage)
2. Implement router tests (95% coverage)
3. Implement orchestrator tests (85% coverage)

### Phase 3: Adapters (Week 2)
1. Implement CLI adapter tests (90% coverage)
2. Implement HTTP adapter tests (90% coverage)
3. Implement specific adapter tests (Gemini, Qwen)

### Phase 4: Utilities & API (Week 2-3)
1. Complete task_storage tests (95% coverage)
2. Implement service_manager tests (85% coverage)
3. Implement API endpoint tests (90% coverage)

### Phase 5: Integration & Polish (Week 3)
1. Write integration tests
2. Achieve 80%+ overall coverage
3. Document test patterns
4. Set up CI/CD integration

---

## 8. Test Execution Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/oxide --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run specific test file
pytest tests/unit/core/test_classifier.py

# Run with verbose output
pytest -v

# Run failed tests only
pytest --lf

# Run tests in parallel
pytest -n auto
```

---

## 9. Success Criteria

- [ ] Overall code coverage >= 80%
- [ ] All core components >= 85% coverage
- [ ] All adapters >= 85% coverage
- [ ] All API endpoints >= 90% coverage
- [ ] Zero failing tests
- [ ] All edge cases documented and tested
- [ ] Comprehensive mocking strategy implemented
- [ ] CI/CD integration configured
- [ ] Test documentation complete

---

## 10. Risk Mitigation

### Risk: External Service Dependencies
**Mitigation:** Comprehensive mocking of all external HTTP calls and CLI processes

### Risk: Async Code Complexity
**Mitigation:** Use pytest-asyncio with proper fixtures and event loop management

### Risk: File System Operations
**Mitigation:** Use tmp_path fixtures and fakefs for filesystem mocking

### Risk: Platform-Specific Code
**Mitigation:** Mock platform.system() and test all platform branches

### Risk: Process Management
**Mitigation:** Mock subprocess module completely, never spawn real processes in tests

---

## Appendix A: Quick Reference

### Test Naming Conventions
- Unit tests: `test_<function_name>_<scenario>`
- Integration tests: `test_<feature>_integration`
- Classes: `TestClassName`

### Fixture Scopes
- `function`: Default, new instance per test
- `class`: Shared within test class
- `module`: Shared within test module
- `session`: Shared across entire test session

### Common Assertions
```python
assert result == expected
assert result is None
assert "substring" in text
assert len(items) == 5
with pytest.raises(ExceptionType):
    dangerous_function()
```

### Async Test Pattern
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```
