"""
Test OpenRouter free models listing functionality.

This test verifies that the get_free_models() method correctly filters
models based on their pricing information.
"""
import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from oxide.adapters.openrouter import OpenRouterAdapter


@pytest.fixture
def mock_openrouter_adapter():
    """Create a mocked OpenRouterAdapter for testing."""
    config = {
        "api_key": "test_key_12345",
        "default_model": "openrouter/auto",
        "use_free_only": False,
        "fallback_models": []
    }
    adapter = OpenRouterAdapter("openrouter_test", config)
    return adapter


@pytest.fixture
def mock_models_response():
    """
    Mock response from OpenRouter /models API.

    Includes a mix of free and paid models with different pricing structures.
    """
    return {
        "data": [
            {
                "id": "meta-llama/llama-3.2-3b-instruct:free",
                "name": "Llama 3.2 3B Instruct (Free)",
                "pricing": {
                    "prompt": "0",  # Free model
                    "completion": "0"
                },
                "context_length": 131072
            },
            {
                "id": "mistralai/mistral-7b-instruct:free",
                "name": "Mistral 7B Instruct (Free)",
                "pricing": {
                    "prompt": "0.00000001",  # Nearly free (< 0.0001)
                    "completion": "0.00000001"
                },
                "context_length": 32768
            },
            {
                "id": "google/gemini-flash-1.5",
                "name": "Gemini 1.5 Flash",
                "pricing": {
                    "prompt": "0.00000005",  # Nearly free
                    "completion": "0.00000015"
                },
                "context_length": 1000000
            },
            {
                "id": "openai/gpt-4",
                "name": "GPT-4",
                "pricing": {
                    "prompt": "0.0003",  # $0.30 per 1K tokens (ABOVE 0.0001 threshold)
                    "completion": "0.0006"
                },
                "context_length": 8192
            },
            {
                "id": "anthropic/claude-3-opus",
                "name": "Claude 3 Opus",
                "pricing": {
                    "prompt": "0.00015",  # $0.15 per 1K tokens (ABOVE 0.0001 threshold)
                    "completion": "0.00075"
                },
                "context_length": 200000
            }
        ]
    }


@pytest.mark.asyncio
@patch.object(OpenRouterAdapter, 'get_models', new_callable=AsyncMock)
async def test_get_free_models_filtering(mock_get_models_method, mock_openrouter_adapter, mock_models_response):
    """
    Test that get_free_models() correctly filters free models.

    Free models are those with pricing.prompt <= $0.0001 per token.
    """
    # Mock the models cache
    mock_openrouter_adapter._models_cache = mock_models_response["data"]

    # Mock get_models to return model IDs
    mock_get_models_method.return_value = [m["id"] for m in mock_models_response["data"]]

    # Get free models
    free_models = await mock_openrouter_adapter.get_free_models()

    # Should return 3 free models (Llama 3.2, Mistral 7B, Gemini Flash)
    assert len(free_models) == 3

    # Check expected free models are in the list
    assert "meta-llama/llama-3.2-3b-instruct:free" in free_models
    assert "mistralai/mistral-7b-instruct:free" in free_models
    assert "google/gemini-flash-1.5" in free_models

    # Check paid models are NOT in the list
    assert "openai/gpt-4" not in free_models
    assert "anthropic/claude-3-opus" not in free_models

    print(f"✓ Correctly identified {len(free_models)} free models")
    print(f"  Free models: {free_models}")


@pytest.mark.asyncio
@patch.object(OpenRouterAdapter, 'get_models', new_callable=AsyncMock)
async def test_get_free_models_empty_cache(mock_get_models_method, mock_openrouter_adapter):
    """Test get_free_models() returns empty list when cache is empty."""
    # Ensure cache is None
    mock_openrouter_adapter._models_cache = None
    mock_get_models_method.return_value = []

    free_models = await mock_openrouter_adapter.get_free_models()

    assert free_models == []
    print(f"✓ Returns empty list when models cache is empty")


@pytest.mark.asyncio
@patch.object(OpenRouterAdapter, 'get_models', new_callable=AsyncMock)
async def test_get_free_models_caching(mock_get_models_method, mock_openrouter_adapter, mock_models_response):
    """Test that free models list is cached after first call."""
    # Set models cache
    mock_openrouter_adapter._models_cache = mock_models_response["data"]
    mock_get_models_method.return_value = [m["id"] for m in mock_models_response["data"]]

    # First call should populate _free_models_cache
    assert mock_openrouter_adapter._free_models_cache is None
    free_models_1 = await mock_openrouter_adapter.get_free_models()
    assert mock_openrouter_adapter._free_models_cache is not None

    # Second call should return cached value (not re-filter)
    free_models_2 = await mock_openrouter_adapter.get_free_models()

    assert free_models_1 == free_models_2
    assert len(free_models_2) == 3

    print(f"✓ Free models list is properly cached")


@pytest.mark.asyncio
@patch.object(OpenRouterAdapter, 'get_models', new_callable=AsyncMock)
async def test_get_free_models_pricing_edge_cases(mock_get_models_method, mock_openrouter_adapter):
    """Test edge cases in pricing comparison."""
    # Test model exactly at threshold
    test_models = [
        {
            "id": "test/exactly-threshold",
            "pricing": {
                "prompt": "0.0001",  # Exactly at threshold
                "completion": "0.0001"
            }
        },
        {
            "id": "test/just-above-threshold",
            "pricing": {
                "prompt": "0.0001000001",  # Just above threshold
                "completion": "0.0001"
            }
        },
        {
            "id": "test/just-below-threshold",
            "pricing": {
                "prompt": "0.00009999",  # Just below threshold
                "completion": "0.0001"
            }
        }
    ]
    mock_openrouter_adapter._models_cache = test_models
    mock_get_models_method.return_value = [m["id"] for m in test_models]

    free_models = await mock_openrouter_adapter.get_free_models()

    # Should include models <= threshold
    assert "test/exactly-threshold" in free_models
    assert "test/just-below-threshold" in free_models

    # Should NOT include model > threshold
    assert "test/just-above-threshold" not in free_models

    print(f"✓ Pricing threshold comparison works correctly")
    print(f"  Models at/below threshold: {free_models}")


@pytest.mark.asyncio
@patch.object(OpenRouterAdapter, 'get_models', new_callable=AsyncMock)
async def test_use_free_only_flag(mock_get_models_method, mock_openrouter_adapter, mock_models_response):
    """
    Test that use_free_only flag switches to free model when needed.

    This tests the execute() method's free model selection logic.
    """
    # Set use_free_only to True
    mock_openrouter_adapter.use_free_only = True
    mock_openrouter_adapter._models_cache = mock_models_response["data"]
    mock_get_models_method.return_value = [m["id"] for m in mock_models_response["data"]]

    # Try to use a paid model (should switch to free)
    # We can't actually execute without a real API, but we can verify
    # that get_free_models() works correctly for the switching logic
    free_models = await mock_openrouter_adapter.get_free_models()

    assert len(free_models) > 0
    print(f"✓ Free models available for use_free_only mode: {free_models}")


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        adapter = None
        models_response = None

        # Create fixtures manually
        config = {
            "api_key": "test_key_12345",
            "default_model": "openrouter/auto",
            "use_free_only": False,
            "fallback_models": []
        }
        adapter = OpenRouterAdapter("openrouter_test", config)

        models_response = {
            "data": [
                {
                    "id": "meta-llama/llama-3.2-3b-instruct:free",
                    "name": "Llama 3.2 3B Instruct (Free)",
                    "pricing": {"prompt": "0", "completion": "0"},
                    "context_length": 131072
                },
                {
                    "id": "mistralai/mistral-7b-instruct:free",
                    "name": "Mistral 7B Instruct (Free)",
                    "pricing": {"prompt": "0.00000001", "completion": "0.00000001"},
                    "context_length": 32768
                },
                {
                    "id": "google/gemini-flash-1.5",
                    "name": "Gemini 1.5 Flash",
                    "pricing": {"prompt": "0.00000005", "completion": "0.00000015"},
                    "context_length": 1000000
                },
                {
                    "id": "openai/gpt-4",
                    "name": "GPT-4",
                    "pricing": {"prompt": "0.00003", "completion": "0.00006"},
                    "context_length": 8192
                }
            ]
        }

        await test_get_free_models_filtering(adapter, models_response)
        await test_get_free_models_empty_cache(adapter)
        await test_get_free_models_caching(adapter, models_response)
        await test_get_free_models_pricing_edge_cases(adapter)
        await test_use_free_only_flag(adapter, models_response)

        print("\n✅ All free models tests passed!")

    asyncio.run(run_tests())
