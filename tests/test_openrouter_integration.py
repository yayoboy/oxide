"""
Test OpenRouter integration in orchestrator.
"""
import pytest
import asyncio
from oxide.core.orchestrator import Orchestrator
from oxide.config.loader import load_config


@pytest.mark.asyncio
async def test_openrouter_adapter_initialization():
    """Test that OpenRouter adapter initializes correctly."""
    orchestrator = Orchestrator()

    # Verify OpenRouter is in adapters
    assert "openrouter" in orchestrator.adapters

    adapter = orchestrator.adapters["openrouter"]

    # Check adapter type
    assert adapter.__class__.__name__ == "OpenRouterAdapter"

    # Check configuration
    assert adapter.service_name == "openrouter"
    assert adapter.base_url == "https://openrouter.ai/api/v1"
    assert adapter.default_model == "openrouter/auto"
    assert adapter.use_free_only == False

    # Check fallback models were loaded
    assert len(adapter.fallback_models) > 0
    assert "google/gemini-flash-1.5" in adapter.fallback_models

    print(f"✓ OpenRouter adapter initialized successfully")
    print(f"  - Base URL: {adapter.base_url}")
    print(f"  - Default model: {adapter.default_model}")
    print(f"  - Fallback models: {adapter.fallback_models}")
    print(f"  - Has API key: {bool(adapter.api_key)}")


@pytest.mark.asyncio
async def test_openrouter_health_check_without_key():
    """Test health check fails gracefully without API key."""
    orchestrator = Orchestrator()
    adapter = orchestrator.adapters["openrouter"]

    # Health check should return False without API key
    is_healthy = await adapter.health_check()
    assert is_healthy == False

    print(f"✓ Health check correctly returns False without API key")


@pytest.mark.asyncio
async def test_openrouter_service_info():
    """Test service info includes all expected fields."""
    orchestrator = Orchestrator()
    adapter = orchestrator.adapters["openrouter"]

    info = adapter.get_service_info()

    # Check all expected fields
    assert "name" in info
    assert "base_url" in info
    assert "default_model" in info
    assert "use_free_only" in info
    assert "has_api_key" in info
    assert "fallback_models" in info

    assert info["base_url"] == "https://openrouter.ai/api/v1"
    assert info["default_model"] == "openrouter/auto"
    assert info["has_api_key"] == False  # No key in test env

    print(f"✓ Service info contains all expected fields")
    print(f"  Info: {info}")


@pytest.mark.asyncio
async def test_openrouter_execute_without_key():
    """Test execute fails with clear error message without API key."""
    orchestrator = Orchestrator()
    adapter = orchestrator.adapters["openrouter"]

    # Should raise HTTPAdapterError with clear message
    from oxide.utils.exceptions import HTTPAdapterError

    with pytest.raises(HTTPAdapterError) as exc_info:
        chunks = []
        async for chunk in adapter.execute(
            prompt="Test query",
            files=None,
            model=None,
            timeout=5
        ):
            chunks.append(chunk)

    error_msg = str(exc_info.value)
    assert "No API key configured" in error_msg or "API key" in error_msg

    print(f"✓ Execute fails with clear error: {error_msg}")


@pytest.mark.asyncio
async def test_openrouter_routing_rules():
    """Test OpenRouter is included in routing rules."""
    config = load_config()

    # Check general_purpose routing (routing_rules is a dict)
    assert "general_purpose" in config.routing_rules
    general_purpose = config.routing_rules["general_purpose"]
    assert general_purpose.primary == "openrouter"

    # Check quick_query fallback
    quick_query = config.routing_rules["quick_query"]
    assert "openrouter" in quick_query.fallback

    print(f"✓ OpenRouter correctly configured in routing rules")
    print(f"  - Primary for: general_purpose")
    print(f"  - Fallback for: quick_query")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_openrouter_adapter_initialization())
    asyncio.run(test_openrouter_health_check_without_key())
    asyncio.run(test_openrouter_service_info())
    asyncio.run(test_openrouter_execute_without_key())
    asyncio.run(test_openrouter_routing_rules())

    print("\n✅ All OpenRouter integration tests passed!")
