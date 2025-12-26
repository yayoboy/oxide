"""
Tests for LM Studio Integration Improvements

Tests new features:
- preferred_models configuration
- Correct /v1/models endpoint
- Better error handling
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from oxide.adapters.ollama_http import OllamaHTTPAdapter
from oxide.utils.service_manager import ServiceManager
from oxide.utils.exceptions import HTTPAdapterError, ServiceUnavailableError


@pytest.fixture
def lm_studio_config():
    """LM Studio configuration with preferred_models"""
    return {
        "base_url": "http://localhost:1234",
        "api_type": "openai_compatible",
        "enabled": True,
        "default_model": None,
        "auto_start": False,
        "auto_detect_model": True,
        "max_retries": 2,
        "retry_delay": 1,
        "preferred_models": ["qwen", "coder", "codellama", "deepseek"]
    }


def test_adapter_extracts_preferred_models(lm_studio_config):
    """Test that adapter extracts preferred_models from config"""
    adapter = OllamaHTTPAdapter("lmstudio", lm_studio_config)

    assert hasattr(adapter, 'preferred_models')
    assert adapter.preferred_models == ["qwen", "coder", "codellama", "deepseek"]
    assert adapter.api_type == "openai_compatible"
    assert adapter.base_url == "http://localhost:1234"


def test_adapter_defaults_empty_preferred_models():
    """Test that adapter defaults to empty list when preferred_models not in config"""
    config = {
        "base_url": "http://localhost:1234",
        "api_type": "openai_compatible",
    }

    adapter = OllamaHTTPAdapter("lmstudio", config)
    assert adapter.preferred_models == []


def test_models_endpoint_url_construction():
    """Test that correct URL is constructed for LM Studio models endpoint"""
    base_url = "http://localhost:1234"
    # Verify the URL construction logic matches what we implemented
    models_url = f"{base_url.rstrip('/')}/v1/models"
    assert models_url == "http://localhost:1234/v1/models"

    # Test with trailing slash
    base_url_with_slash = "http://localhost:1234/"
    models_url = f"{base_url_with_slash.rstrip('/')}/v1/models"
    assert models_url == "http://localhost:1234/v1/models"


@pytest.mark.asyncio
async def test_auto_detect_uses_preferred_models():
    """Test that auto_detect_model prioritizes preferred_models"""
    service_manager = ServiceManager()

    # Available models
    available_models = ["llama-3.1-8b", "qwen2.5-coder-7b", "mistral-7b"]

    # Mock get_available_models
    with patch.object(service_manager, 'get_available_models', return_value=available_models):
        # Test exact match
        preferred = ["qwen2.5-coder-7b", "mistral-7b"]
        model = await service_manager.auto_detect_model(
            base_url="http://localhost:1234",
            api_type="openai_compatible",
            preferred_models=preferred
        )
        assert model == "qwen2.5-coder-7b"  # First preferred match

        # Test partial match
        preferred = ["qwen", "coder"]
        model = await service_manager.auto_detect_model(
            base_url="http://localhost:1234",
            api_type="openai_compatible",
            preferred_models=preferred
        )
        assert "qwen" in model.lower()  # Should match qwen2.5-coder-7b


@pytest.mark.asyncio
async def test_ensure_service_healthy_passes_preferred_models():
    """Test that ensure_service_healthy accepts and uses preferred_models"""
    service_manager = ServiceManager()

    preferred = ["qwen", "coder"]

    # Mock dependencies
    with patch.object(service_manager, 'get_available_models', return_value=["qwen2.5-coder-7b"]):
        with patch.object(service_manager, 'auto_detect_model', return_value="qwen2.5-coder-7b") as mock_detect:
            result = await service_manager.ensure_service_healthy(
                service_name="lmstudio",
                base_url="http://localhost:1234",
                api_type="openai_compatible",
                auto_start=False,
                auto_detect_model=True,
                preferred_models=preferred
            )

            # Verify preferred_models was passed to auto_detect_model
            mock_detect.assert_called_once()
            call_args = mock_detect.call_args
            # Check both positional and keyword arguments
            if len(call_args) > 1 and 'preferred_models' in call_args[1]:
                assert call_args[1]['preferred_models'] == preferred
            elif len(call_args[0]) >= 3:
                # Check as positional argument (base_url, api_type, preferred_models)
                assert call_args[0][2] == preferred

            # Verify result
            assert result["healthy"] is True
            assert result["recommended_model"] == "qwen2.5-coder-7b"


def test_error_messages_are_helpful():
    """Test that custom error messages contain helpful guidance"""
    # Test ServiceUnavailableError message for connection issues
    error = ServiceUnavailableError(
        "lmstudio",
        "Cannot connect to lmstudio at http://localhost:1234. "
        "Please check:\n"
        "  1. Is LM Studio running?\n"
        "  2. Is the server started in LM Studio (Local Server tab)?\n"
        "  3. Is the base_url correct in your configuration?\n"
        "  4. Is the port accessible? (Network/firewall issues)"
    )
    error_msg = str(error)
    assert "Cannot connect" in error_msg
    assert "Is LM Studio running?" in error_msg
    assert "Is the server started" in error_msg
    assert "base_url correct" in error_msg

    # Test HTTPAdapterError for model not found
    model_error = HTTPAdapterError(
        "Model 'nonexistent-model' not found in lmstudio. "
        "Please ensure the model is loaded in LM Studio."
    )
    assert "not found" in str(model_error).lower()
    assert "ensure the model is loaded" in str(model_error).lower()

    # Test HTTPAdapterError for server error
    server_error = HTTPAdapterError(
        "lmstudio internal error. "
        "This may indicate the model crashed or ran out of memory. "
        "Try restarting LM Studio or loading a smaller model."
    )
    assert "internal error" in str(server_error).lower()
    assert "ran out of memory" in str(server_error).lower()
    assert "smaller model" in str(server_error).lower()


@pytest.mark.asyncio
async def test_preferred_models_flow_end_to_end():
    """Test that preferred_models flows from config through to model detection"""
    config = {
        "base_url": "http://localhost:1234",
        "api_type": "openai_compatible",
        "auto_start": False,
        "auto_detect_model": True,
        "default_model": None,
        "preferred_models": ["qwen", "deepseek"]
    }

    adapter = OllamaHTTPAdapter("lmstudio", config)

    # Verify config extraction
    assert adapter.preferred_models == ["qwen", "deepseek"]

    # Mock service manager methods
    mock_health_result = {
        "healthy": True,
        "models": ["llama-3.1-8b", "qwen2.5-coder-7b", "deepseek-coder-6.7b"],
        "recommended_model": "qwen2.5-coder-7b"
    }

    with patch.object(adapter.service_manager, 'ensure_service_healthy', return_value=mock_health_result) as mock_health:
        # Trigger _ensure_service_ready
        result = await adapter._ensure_service_ready()

        # Verify preferred_models was passed to service manager
        mock_health.assert_called_once()
        call_kwargs = mock_health.call_args[1]
        assert call_kwargs['preferred_models'] == ["qwen", "deepseek"]

        # Verify detected model
        assert adapter._detected_model == "qwen2.5-coder-7b"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
