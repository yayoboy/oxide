"""
API key management endpoints for Oxide Web Backend.

Provides secure storage and validation of API keys for external services.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Optional
import os
from pathlib import Path

from ....utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


class APIKeyUpdate(BaseModel):
    """Request model for API key update"""
    service: str = Field(..., description="Service name (e.g., 'openrouter')")
    api_key: str = Field(..., min_length=10, description="API key value")


class APIKeyTest(BaseModel):
    """Request model for API key validation"""
    service: str = Field(..., description="Service name")
    api_key: Optional[str] = Field(None, description="API key to test (optional if already configured)")


class APIKeyStatus(BaseModel):
    """Response model for API key status"""
    service: str
    configured: bool
    valid: Optional[bool] = None
    key_preview: Optional[str] = None  # First/last 4 chars only


@router.get("/status/{service}/", response_model=APIKeyStatus)
async def get_api_key_status(service: str):
    """
    Get API key configuration status for a service.

    Returns whether an API key is configured and optionally validates it.
    """
    # Check environment variable
    env_var_name = f"{service.upper()}_API_KEY"
    api_key = os.getenv(env_var_name)

    if not api_key:
        return APIKeyStatus(
            service=service,
            configured=False,
            valid=None,
            key_preview=None
        )

    # Create preview (first 4 + last 4 chars)
    key_preview = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) >= 8 else "****"

    return APIKeyStatus(
        service=service,
        configured=True,
        valid=None,  # Don't validate on status check
        key_preview=key_preview
    )


@router.post("/test/")
async def test_api_key(request: APIKeyTest):
    """
    Test API key validity by making a test request to the service.

    Returns success/failure status with error details if applicable.
    """
    service = request.service.lower()
    api_key = request.api_key

    # If no key provided, try to get from environment
    if not api_key:
        env_var_name = f"{service.upper()}_API_KEY"
        api_key = os.getenv(env_var_name)

        if not api_key:
            raise HTTPException(
                status_code=400,
                detail=f"No API key provided and {env_var_name} not set"
            )

    # Test the API key based on service
    if service == "openrouter":
        return await _test_openrouter_key(api_key)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"API key testing not supported for service: {service}"
        )


async def _test_openrouter_key(api_key: str) -> Dict:
    """Test OpenRouter API key by calling the models endpoint."""
    import aiohttp

    try:
        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    model_count = len(data.get("data", []))

                    return {
                        "success": True,
                        "valid": True,
                        "message": f"API key is valid. {model_count} models available.",
                        "details": {
                            "model_count": model_count,
                            "service": "openrouter"
                        }
                    }
                elif response.status == 401:
                    return {
                        "success": False,
                        "valid": False,
                        "message": "Invalid API key. Authentication failed.",
                        "details": {
                            "error_code": 401,
                            "service": "openrouter"
                        }
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "valid": None,
                        "message": f"API request failed with status {response.status}",
                        "details": {
                            "error_code": response.status,
                            "error_message": error_text[:200],
                            "service": "openrouter"
                        }
                    }

    except aiohttp.ClientConnectorError as e:
        return {
            "success": False,
            "valid": None,
            "message": "Cannot connect to OpenRouter API. Check your internet connection.",
            "details": {
                "error": str(e),
                "service": "openrouter"
            }
        }
    except Exception as e:
        logger.error(f"Error testing OpenRouter API key: {e}")
        return {
            "success": False,
            "valid": None,
            "message": f"Unexpected error: {str(e)}",
            "details": {
                "error": str(e),
                "service": "openrouter"
            }
        }


@router.post("/update/")
async def update_api_key(request: APIKeyUpdate):
    """
    Update API key for a service.

    NOTE: For security, API keys should be set via environment variables.
    This endpoint provides guidance on how to set them properly.
    """
    service = request.service.lower()
    env_var_name = f"{service.upper()}_API_KEY"

    # We don't actually store the API key - that would be insecure
    # Instead, provide instructions for setting it via environment variable
    return {
        "success": False,
        "message": "API keys cannot be set via web UI for security reasons.",
        "instructions": {
            "method": "environment_variable",
            "variable_name": env_var_name,
            "steps": [
                f"1. Stop the Oxide server",
                f"2. Set environment variable: export {env_var_name}='your_api_key_here'",
                f"3. Restart the Oxide server",
                f"4. Alternatively, add to your shell profile (.bashrc, .zshrc, etc.)"
            ],
            "docker_instructions": [
                f"If using Docker, add to docker-compose.yml:",
                f"  environment:",
                f"    - {env_var_name}=your_api_key_here"
            ]
        }
    }
