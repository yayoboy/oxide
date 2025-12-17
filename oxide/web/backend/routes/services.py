"""
Services API routes.

Endpoints for managing and monitoring LLM services.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ....core.orchestrator import Orchestrator
from ....utils.logging import logger


router = APIRouter()


class ServiceUpdateRequest(BaseModel):
    """Request to update service configuration."""
    enabled: bool


def get_orchestrator() -> Orchestrator:
    """Dependency to get orchestrator instance."""
    from ..main import get_orchestrator
    return get_orchestrator()


@router.get("/")
async def list_services(orchestrator: Orchestrator = Depends(get_orchestrator)) -> Dict[str, Any]:
    """
    Get list of all configured services with their status.

    Returns:
        Dictionary with service information
    """
    try:
        status = await orchestrator.get_service_status()

        return {
            "services": status,
            "total": len(status),
            "enabled": sum(1 for s in status.values() if s.get("enabled")),
            "healthy": sum(1 for s in status.values() if s.get("healthy"))
        }

    except (AttributeError, KeyError, TypeError) as e:
        # Expected errors when orchestrator not properly initialized
        logger.warning(f"Service listing error (expected): {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error listing services: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e


@router.get("/{service_name}")
async def get_service(
    service_name: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific service.

    Args:
        service_name: Name of the service

    Returns:
        Service information
    """
    try:
        # Check if service exists
        if service_name not in orchestrator.adapters:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

        # Get adapter info
        adapter = orchestrator.adapters[service_name]
        info = adapter.get_service_info()

        # Get health status
        is_healthy = await orchestrator._check_service_health(service_name)

        return {
            "name": service_name,
            "healthy": is_healthy,
            "info": info
        }

    except HTTPException:
        raise
    except (AttributeError, KeyError) as e:
        # Expected errors accessing adapter or its methods
        logger.warning(f"Service access error for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error getting service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e


@router.post("/{service_name}/health")
async def check_service_health(
    service_name: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Perform health check on a specific service.

    Args:
        service_name: Name of the service

    Returns:
        Health check result
    """
    try:
        if service_name not in orchestrator.adapters:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

        is_healthy = await orchestrator._check_service_health(service_name)

        return {
            "service": service_name,
            "healthy": is_healthy
        }

    except HTTPException:
        raise
    except (AttributeError, KeyError) as e:
        # Expected errors accessing health check
        logger.warning(f"Health check access error for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error checking health for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e


@router.post("/{service_name}/test")
async def test_service(
    service_name: str,
    test_prompt: str = "Hello",
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Test a service with a simple prompt.

    Args:
        service_name: Name of the service
        test_prompt: Test prompt to send

    Returns:
        Test results
    """
    try:
        if service_name not in orchestrator.adapters:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

        result = await orchestrator.test_service(service_name, test_prompt)

        return {
            "service": service_name,
            "test_prompt": test_prompt,
            **result
        }

    except HTTPException:
        raise
    except (AttributeError, KeyError, TypeError) as e:
        # Expected errors during service test
        logger.warning(f"Service test error for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error testing service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e


@router.get("/{service_name}/models")
async def get_service_models(
    service_name: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, List[str]]:
    """
    Get list of available models for a service.

    Args:
        service_name: Name of the service

    Returns:
        List of available models
    """
    try:
        if service_name not in orchestrator.adapters:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

        adapter = orchestrator.adapters[service_name]
        models = await adapter.get_models()

        return {
            "service": service_name,
            "models": models
        }

    except HTTPException:
        raise
    except (AttributeError, KeyError) as e:
        # Expected errors accessing adapter models
        logger.warning(f"Model access error for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error getting models for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e


@router.get("/routing/rules")
async def get_routing_rules(
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Get routing rules configuration.

    Returns:
        Routing rules summary
    """
    try:
        rules = orchestrator.get_routing_rules()

        return {
            "rules": rules,
            "total": len(rules)
        }

    except (AttributeError, KeyError, TypeError) as e:
        # Expected errors accessing routing rules
        logger.warning(f"Routing rules access error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error getting routing rules: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e
