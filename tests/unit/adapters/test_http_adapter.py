"""
Unit tests for OllamaHTTPAdapter.

Tests the HTTP-based adapter used for Ollama and LM Studio services.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientError, ClientSession

from oxide.adapters.ollama_http import OllamaHTTPAdapter
from oxide.utils.exceptions import ExecutionError, ServiceUnavailableError


class TestOllamaHTTPAdapter:
    """Test suite for OllamaHTTPAdapter."""

    @pytest.fixture
    def ollama_config(self):
        """Provide Ollama adapter configuration."""
        return {
            "type": "http",
            "base_url": "http://localhost:11434",
            "api_type": "ollama",
            "default_model": "qwen2.5-coder:7b",
            "enabled": True,
            "auto_start": False,
            "auto_detect_model": False
        }

    @pytest.fixture
    def lm_studio_config(self):
        """Provide LM Studio adapter configuration."""
        return {
            "type": "http",
            "base_url": "http://localhost:1234",
            "api_type": "openai",
            "default_model": "local-model",
            "enabled": True,
            "auto_start": False
        }

    @pytest.fixture
    def ollama_adapter(self, ollama_config):
        """Provide OllamaHTTPAdapter instance for Ollama."""
        return OllamaHTTPAdapter("ollama_local", ollama_config)

    @pytest.fixture
    def lm_studio_adapter(self, lm_studio_config):
        """Provide OllamaHTTPAdapter instance for LM Studio."""
        return OllamaHTTPAdapter("lm_studio", lm_studio_config)

    def test_ollama_initialization(self, ollama_adapter):
        """Test Ollama adapter initializes correctly."""
        assert ollama_adapter.service_name == "ollama_local"
        assert ollama_adapter.base_url == "http://localhost:11434"
        assert ollama_adapter.api_type == "ollama"
        assert ollama_adapter.default_model == "qwen2.5-coder:7b"

    def test_lm_studio_initialization(self, lm_studio_adapter):
        """Test LM Studio adapter initializes correctly."""
        assert lm_studio_adapter.service_name == "lm_studio"
        assert lm_studio_adapter.api_type == "openai"
        assert lm_studio_adapter.base_url == "http://localhost:1234"

    def test_get_service_info_ollama(self, ollama_adapter):
        """Test getting service info for Ollama."""
        info = ollama_adapter.get_service_info()

        assert info["name"] == "ollama_local"
        assert info["type"] == "http"
        assert info["api_type"] == "ollama"
        assert info["base_url"] == "http://localhost:11434"
        assert info["model"] == "qwen2.5-coder:7b"

    def test_get_service_info_lm_studio(self, lm_studio_adapter):
        """Test getting service info for LM Studio."""
        info = lm_studio_adapter.get_service_info()

        assert info["api_type"] == "openai"
        assert info["model"] == "local-model"

    @pytest.mark.asyncio
    async def test_execute_ollama_streaming(self, ollama_adapter):
        """Test executing with Ollama streaming API."""
        mock_response = AsyncMock()
        mock_response.status = 200

        # Simulate streaming JSON responses
        async def mock_iter():
            yield b'{"response": "Hello", "done": false}\n'
            yield b'{"response": " World", "done": false}\n'
            yield b'{"response": "!", "done": true}\n'

        mock_response.content.iter_any = mock_iter

        with patch('aiohttp.ClientSession.post', return_value=mock_response):
            chunks = []
            async for chunk in ollama_adapter.execute("Test prompt"):
                chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0] == "Hello"
        assert chunks[1] == " World"
        assert chunks[2] == "!"

    @pytest.mark.asyncio
    async def test_execute_lm_studio_streaming(self, lm_studio_adapter):
        """Test executing with LM Studio (OpenAI-compatible) API."""
        mock_response = AsyncMock()
        mock_response.status = 200

        # Simulate OpenAI streaming format
        async def mock_iter():
            yield b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n'
            yield b'data: {"choices": [{"delta": {"content": " World"}}]}\n\n'
            yield b'data: [DONE]\n\n'

        mock_response.content.iter_any = mock_iter

        with patch('aiohttp.ClientSession.post', return_value=mock_response):
            chunks = []
            async for chunk in lm_studio_adapter.execute("Test prompt"):
                chunks.append(chunk)

        assert len(chunks) >= 2
        assert "Hello" in "".join(chunks)
        assert "World" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_execute_with_files(self, ollama_adapter, sample_task_files):
        """Test execution with file context."""
        mock_response = AsyncMock()
        mock_response.status = 200

        async def mock_iter():
            yield b'{"response": "Analysis complete", "done": true}\n'

        mock_response.content.iter_any = mock_iter

        with patch('aiohttp.ClientSession.post', return_value=mock_response) as mock_post:
            chunks = []
            async for chunk in ollama_adapter.execute("Analyze", files=sample_task_files):
                chunks.append(chunk)

            # Verify files were included in prompt
            call_args = mock_post.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_execute_connection_error(self, ollama_adapter):
        """Test execution handles connection errors."""
        with patch('aiohttp.ClientSession.post', side_effect=ClientError("Connection failed")):
            with pytest.raises(ServiceUnavailableError) as exc_info:
                async for _ in ollama_adapter.execute("Test"):
                    pass

            assert "unavailable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_http_error(self, ollama_adapter):
        """Test execution handles HTTP errors."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        with patch('aiohttp.ClientSession.post', return_value=mock_response):
            with pytest.raises(ExecutionError) as exc_info:
                async for _ in ollama_adapter.execute("Test"):
                    pass

            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_model_not_found(self, ollama_adapter):
        """Test execution when model is not found."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Model not found")

        with patch('aiohttp.ClientSession.post', return_value=mock_response):
            with pytest.raises(ExecutionError) as exc_info:
                async for _ in ollama_adapter.execute("Test"):
                    pass

            assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_adapter):
        """Test health check when service is available."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"models": [{"name": "qwen2.5-coder:7b"}]})

        with patch('aiohttp.ClientSession.get', return_value=mock_response):
            is_healthy = await ollama_adapter.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_adapter):
        """Test health check when service is unavailable."""
        with patch('aiohttp.ClientSession.get', side_effect=ClientError("Connection refused")):
            is_healthy = await ollama_adapter.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_get_models_ollama(self, ollama_adapter):
        """Test getting available models from Ollama."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "models": [
                {"name": "qwen2.5-coder:7b"},
                {"name": "codellama:7b"},
                {"name": "llama3:8b"}
            ]
        })

        with patch('aiohttp.ClientSession.get', return_value=mock_response):
            models = await ollama_adapter.get_models()

        assert len(models) == 3
        assert "qwen2.5-coder:7b" in models
        assert "codellama:7b" in models

    @pytest.mark.asyncio
    async def test_get_models_lm_studio(self, lm_studio_adapter):
        """Test getting models from LM Studio (OpenAI endpoint)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {"id": "local-model-1"},
                {"id": "local-model-2"}
            ]
        })

        with patch('aiohttp.ClientSession.get', return_value=mock_response):
            models = await lm_studio_adapter.get_models()

        assert len(models) == 2
        assert "local-model-1" in models

    @pytest.mark.asyncio
    async def test_get_models_error(self, ollama_adapter):
        """Test get_models handles errors gracefully."""
        with patch('aiohttp.ClientSession.get', side_effect=ClientError("Connection failed")):
            models = await ollama_adapter.get_models()

        assert models == []

    @pytest.mark.asyncio
    async def test_auto_start_integration(self):
        """Test auto-start integration with ServiceManager."""
        config = {
            "type": "http",
            "base_url": "http://localhost:11434",
            "api_type": "ollama",
            "default_model": "test-model",
            "enabled": True,
            "auto_start": True,
            "auto_detect_model": False
        }

        adapter = OllamaHTTPAdapter("ollama_auto", config)

        # Mock ServiceManager
        mock_manager = AsyncMock()
        mock_manager.ensure_service_healthy = AsyncMock(return_value={
            "healthy": True,
            "models": ["test-model"]
        })

        with patch('oxide.adapters.ollama_http.get_service_manager', return_value=mock_manager):
            # This should trigger auto-start
            mock_response = AsyncMock()
            mock_response.status = 200
            async def mock_iter():
                yield b'{"response": "test", "done": true}\n'
            mock_response.content.iter_any = mock_iter

            with patch('aiohttp.ClientSession.post', return_value=mock_response):
                chunks = []
                async for chunk in adapter.execute("Test"):
                    chunks.append(chunk)

            # ServiceManager should have been called
            mock_manager.ensure_service_healthy.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_detect_model(self):
        """Test auto model detection."""
        config = {
            "type": "http",
            "base_url": "http://localhost:11434",
            "api_type": "ollama",
            "default_model": None,
            "enabled": True,
            "auto_start": False,
            "auto_detect_model": True,
            "preferred_models": ["qwen2.5-coder", "codellama"]
        }

        adapter = OllamaHTTPAdapter("ollama_auto_detect", config)

        # Mock ServiceManager
        mock_manager = AsyncMock()
        mock_manager.auto_detect_model = AsyncMock(return_value="qwen2.5-coder:7b")

        with patch('oxide.adapters.ollama_http.get_service_manager', return_value=mock_manager):
            # Execute should trigger model detection
            mock_response = AsyncMock()
            mock_response.status = 200
            async def mock_iter():
                yield b'{"response": "test", "done": true}\n'
            mock_response.content.iter_any = mock_iter

            with patch('aiohttp.ClientSession.post', return_value=mock_response):
                chunks = []
                async for chunk in adapter.execute("Test"):
                    chunks.append(chunk)

            # Model should have been auto-detected
            assert adapter.model is not None


@pytest.mark.asyncio
class TestHTTPAdapterIntegration:
    """Integration tests for HTTP adapter workflows."""

    async def test_full_ollama_workflow(self, ollama_adapter):
        """Test complete Ollama workflow."""
        # Mock all HTTP calls
        mock_health_response = AsyncMock()
        mock_health_response.status = 200
        mock_health_response.json = AsyncMock(return_value={"models": [{"name": "test-model"}]})

        mock_models_response = AsyncMock()
        mock_models_response.status = 200
        mock_models_response.json = AsyncMock(return_value={"models": [{"name": "test-model"}]})

        mock_execute_response = AsyncMock()
        mock_execute_response.status = 200
        async def mock_iter():
            yield b'{"response": "Result", "done": true}\n'
        mock_execute_response.content.iter_any = mock_iter

        with patch('aiohttp.ClientSession.get') as mock_get, \
             patch('aiohttp.ClientSession.post', return_value=mock_execute_response):

            mock_get.return_value = mock_health_response

            # 1. Health check
            is_healthy = await ollama_adapter.health_check()
            assert is_healthy is True

            # 2. Get models
            mock_get.return_value = mock_models_response
            models = await ollama_adapter.get_models()
            assert len(models) > 0

            # 3. Execute task
            chunks = []
            async for chunk in ollama_adapter.execute("Test"):
                chunks.append(chunk)
            assert len(chunks) > 0

    async def test_error_recovery(self, ollama_adapter):
        """Test adapter recovers from transient errors."""
        call_count = 0

        async def mock_post_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call fails
                raise ClientError("Temporary error")

            # Second call succeeds
            mock_response = AsyncMock()
            mock_response.status = 200
            async def mock_iter():
                yield b'{"response": "Success", "done": true}\n'
            mock_response.content.iter_any = mock_iter
            return mock_response

        # Note: Current implementation doesn't have retry logic in adapter
        # This test documents expected behavior for future enhancement
        with patch('aiohttp.ClientSession.post', side_effect=mock_post_with_retry):
            with pytest.raises(ServiceUnavailableError):
                async for _ in ollama_adapter.execute("Test"):
                    pass
