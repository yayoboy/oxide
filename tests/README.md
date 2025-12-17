# Oxide Test Suite

Comprehensive test suite for the Oxide LLM Orchestrator.

## Overview

This test suite provides extensive coverage of Oxide's core functionality including:
- Task classification and routing
- Adapter implementations
- Security validation
- Configuration management

## Test Coverage

### Unit Tests (`tests/unit/`)

#### `test_classifier.py`
Tests for the `TaskClassifier` component:
- Task type classification (codebase analysis, code review, debugging, etc.)
- Complexity scoring
- Parallel execution threshold detection
- Service recommendations
- Edge cases (empty files, large codebases)

**Key Tests:**
- `test_classify_large_codebase` - Validates parallel execution for large projects
- `test_keyword_matching_case_insensitive` - Ensures robust keyword detection
- `test_calculate_complexity_many_files` - Tests complexity calculation accuracy

#### `test_router.py`
Tests for the `TaskRouter` component:
- Primary service selection
- Fallback service handling
- Health check integration
- Timeout configuration
- Service availability detection

**Key Tests:**
- `test_fallback_when_primary_unhealthy` - Validates automatic failover
- `test_no_service_available_error` - Tests error handling when all services fail
- `test_route_parallel_execution` - Validates parallel routing mode

#### `test_adapters.py`
Tests for adapter implementations:
- CLIAdapter base functionality
- GeminiAdapter specialization
- QwenAdapter specialization
- Command building with files
- Health check implementations

**Key Tests:**
- `test_build_command_with_files` - Validates @file syntax
- `test_health_check_executable_not_found` - Tests graceful failure handling
- `test_execute_file_not_found` - Validates ServiceUnavailableError raising

#### `test_security.py` ⚠️ **Security-Critical**
Tests for security validation utilities:
- Prompt validation and sanitization
- Command injection detection
- File path validation
- Input sanitization

**Critical Security Tests:**
- `test_command_injection_semicolon` - Detects `;` command chaining
- `test_command_substitution_dollar` - Detects `$()` command substitution
- `test_command_substitution_backticks` - Detects backtick command substitution
- `test_device_redirect` - Prevents redirect to `/dev/*`
- `test_background_execution` - Detects `&` background execution

## Running Tests

### Run All Tests
```bash
uv run pytest tests/
```

### Run Specific Test File
```bash
uv run pytest tests/unit/test_classifier.py
```

### Run with Coverage
```bash
uv run pytest tests/ --cov=oxide --cov-report=html
```

### Run Verbose Mode
```bash
uv run pytest tests/ -v
```

### Run Only Fast Tests
```bash
uv run pytest tests/ -m "not slow"
```

### Run Security Tests Only
```bash
uv run pytest tests/ -m security
```

## Test Configuration

### `pytest.ini`
Configuration file with:
- Test discovery patterns
- Output formatting
- Asyncio mode settings
- Custom markers

### `conftest.py`
Shared fixtures including:
- `mock_config` - Mock Oxide configuration
- `temp_test_files` - Temporary test files
- `sample_prompts` - Sample task prompts for testing

## Writing Tests

### Test Structure
```python
class TestMyComponent:
    """Test suite for MyComponent."""

    @pytest.fixture
    def component(self):
        """Create component instance."""
        return MyComponent()

    def test_feature_name(self, component):
        """Test that feature does what it should."""
        result = component.do_something()
        assert result == expected_value
```

### Async Tests
```python
@pytest.mark.asyncio
async def test_async_feature(self):
    """Test async functionality."""
    result = await async_function()
    assert result is not None
```

### Using Markers
```python
@pytest.mark.slow
def test_slow_operation(self):
    """This test takes a long time."""
    pass

@pytest.mark.security
def test_security_validation(self):
    """Tests security features."""
    pass
```

## Test Statistics

- **Total Tests**: 73
- **Unit Tests**: 73
- **Integration Tests**: 0 (planned)
- **Test Pass Rate**: 100%

### Coverage by Component
- **Classifier**: 18 tests
- **Router**: 13 tests
- **Adapters**: 16 tests
- **Security**: 26 tests

## CI/CD Integration

Tests are automatically run on:
- Every commit to feature branches
- Pull request creation
- Pre-merge validation

### GitHub Actions (Planned)
```yaml
- name: Run tests
  run: uv run pytest tests/ -v --cov
```

## Security Testing

The security test suite (`test_security.py`) is **critical** and tests for:

1. **Command Injection Prevention**
   - Detects shell metacharacters
   - Validates command substitution attempts
   - Prevents pipe-based attacks

2. **Path Traversal Prevention**
   - Validates file paths
   - Prevents directory escape
   - Ensures file existence checks

3. **Input Sanitization**
   - Removes null bytes
   - Filters control characters
   - Validates input types

**⚠️ These tests must always pass before deployment.**

## Debugging Failed Tests

### View Full Output
```bash
uv run pytest tests/ -v --tb=long
```

### Run Single Test
```bash
uv run pytest tests/unit/test_classifier.py::TestTaskClassifier::test_classify_large_codebase
```

### Print Debug Info
```bash
uv run pytest tests/ -v -s  # -s shows print statements
```

### Use Debugger
```python
def test_something():
    import pdb; pdb.set_trace()
    # Test code here
```

## Future Improvements

- [ ] Add integration tests for end-to-end workflows
- [ ] Add performance benchmarking tests
- [ ] Add load testing for parallel execution
- [ ] Add mocking for external LLM services
- [ ] Increase coverage to 95%+
- [ ] Add mutation testing
- [ ] Add property-based testing with Hypothesis

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all existing tests pass
3. Add tests for edge cases
4. Update this README if needed
5. Maintain >90% code coverage

## Support

For test-related questions:
- Check test docstrings for detailed explanations
- Review `conftest.py` for available fixtures
- See pytest documentation: https://docs.pytest.org/
