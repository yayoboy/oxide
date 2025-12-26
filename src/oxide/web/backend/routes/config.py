"""
Configuration Management API Endpoints

Provides REST API for viewing, validating, and reloading configuration.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from ....config.loader import load_config, Config, ConfigError, save_config
from ....config.hot_reload import get_hot_reload_manager
from ....utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])


# Request/Response models
class ConfigResponse(BaseModel):
    """Full configuration response"""
    services: Dict[str, Any]
    routing_rules: Dict[str, Any]
    execution: Dict[str, Any]
    logging: Dict[str, Any]
    memory: Optional[Dict[str, Any]] = None
    cluster: Optional[Dict[str, Any]] = None


class ValidationResponse(BaseModel):
    """Configuration validation response"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class ReloadResponse(BaseModel):
    """Configuration reload response"""
    status: str
    reload_count: int
    changes: Dict[str, Any]
    timestamp: float


class ServicePatchRequest(BaseModel):
    """Request to patch service configuration"""
    enabled: Optional[bool] = None
    auto_start: Optional[bool] = None
    auto_detect_model: Optional[bool] = None
    default_model: Optional[str] = None


class RoutingRulePatchRequest(BaseModel):
    """Request to patch routing rule"""
    primary: Optional[str] = None
    fallback: Optional[List[str]] = None
    timeout_seconds: Optional[int] = None


# API Endpoints

@router.get("/", response_model=ConfigResponse)
async def get_configuration():
    """
    Get current configuration.

    Returns complete configuration including all sections.
    """
    try:
        # Get hot reload manager if available
        manager = get_hot_reload_manager()

        if manager and manager.current_config:
            config = manager.current_config
        else:
            # Fallback to loading from file
            config = load_config()

        # Convert to dict
        config_dict = config.model_dump(mode="json", exclude_none=True)

        return ConfigResponse(**config_dict)

    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services")
async def get_services_config():
    """
    Get services configuration.

    Returns only the services section.
    """
    try:
        manager = get_hot_reload_manager()
        config = manager.current_config if manager else load_config()

        return {
            "services": config.model_dump(mode="json")["services"]
        }

    except Exception as e:
        logger.error(f"Failed to get services config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/{service_name}")
async def get_service_config(service_name: str):
    """
    Get configuration for a specific service.

    Args:
        service_name: Name of service

    Returns:
        Service configuration
    """
    try:
        manager = get_hot_reload_manager()
        config = manager.current_config if manager else load_config()

        if service_name not in config.services:
            raise HTTPException(
                status_code=404,
                detail=f"Service '{service_name}' not found"
            )

        service_config = config.services[service_name]

        return {
            "service_name": service_name,
            "config": service_config.model_dump(mode="json")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get service config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing-rules")
async def get_routing_rules():
    """
    Get routing rules configuration.

    Returns only the routing_rules section.
    """
    try:
        manager = get_hot_reload_manager()
        config = manager.current_config if manager else load_config()

        return {
            "routing_rules": config.model_dump(mode="json")["routing_rules"]
        }

    except Exception as e:
        logger.error(f"Failed to get routing rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing-rules/{task_type}")
async def get_routing_rule(task_type: str):
    """
    Get routing rule for a specific task type.

    Args:
        task_type: Task type name

    Returns:
        Routing rule configuration
    """
    try:
        manager = get_hot_reload_manager()
        config = manager.current_config if manager else load_config()

        if task_type not in config.routing_rules:
            raise HTTPException(
                status_code=404,
                detail=f"Routing rule for '{task_type}' not found"
            )

        rule = config.routing_rules[task_type]

        return {
            "task_type": task_type,
            "rule": rule.model_dump(mode="json")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get routing rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=ValidationResponse)
async def validate_configuration(config_data: Dict[str, Any]):
    """
    Validate configuration without applying it.

    Args:
        config_data: Configuration to validate

    Returns:
        Validation result with errors/warnings
    """
    errors = []
    warnings = []

    try:
        # Try to parse configuration
        config = Config(**config_data)

        # Additional validation checks
        enabled_services = config.get_enabled_services()

        if len(enabled_services) == 0:
            warnings.append("No services are enabled")

        # Check routing rules
        for task_type, rule in config.routing_rules.items():
            # Check if primary service is enabled
            primary_config = config.services.get(rule.primary)
            if primary_config and not primary_config.enabled:
                warnings.append(
                    f"Routing rule '{task_type}' uses disabled primary service: {rule.primary}"
                )

            # Check fallbacks
            for fallback in rule.fallback:
                fallback_config = config.services.get(fallback)
                if fallback_config and not fallback_config.enabled:
                    warnings.append(
                        f"Routing rule '{task_type}' uses disabled fallback service: {fallback}"
                    )

        return ValidationResponse(
            valid=True,
            errors=[],
            warnings=warnings
        )

    except Exception as e:
        errors.append(str(e))

        return ValidationResponse(
            valid=False,
            errors=errors,
            warnings=warnings
        )


@router.post("/reload", response_model=ReloadResponse)
async def reload_configuration():
    """
    Reload configuration from file.

    Triggers configuration reload and returns changes detected.
    """
    try:
        manager = get_hot_reload_manager()

        if not manager:
            raise HTTPException(
                status_code=503,
                detail="Hot reload not enabled. Restart server to apply changes."
            )

        # Get stats before reload
        old_reload_count = manager.reload_count

        # Reload configuration
        new_config = manager.reload()

        # Get changes from last reload event
        changes = {}
        if manager.reload_count > old_reload_count:
            # Successfully reloaded
            changes = manager._detect_changes(
                manager.current_config,
                new_config
            ) if manager.current_config else {}

        return ReloadResponse(
            status="reloaded",
            reload_count=manager.reload_count,
            changes=changes,
            timestamp=manager.last_reload_time or 0
        )

    except ConfigError as e:
        logger.error(f"Configuration reload failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid configuration: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reload/stats")
async def get_reload_stats():
    """
    Get hot reload statistics.

    Returns information about reload status and history.
    """
    try:
        manager = get_hot_reload_manager()

        if not manager:
            return {
                "enabled": False,
                "message": "Hot reload not enabled"
            }

        stats = manager.get_stats()

        return {
            "enabled": True,
            **stats
        }

    except Exception as e:
        logger.error(f"Failed to get reload stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/services/{service_name}")
async def patch_service_config(
    service_name: str,
    patch: ServicePatchRequest
):
    """
    Partially update service configuration.

    Args:
        service_name: Name of service to update
        patch: Fields to update

    Returns:
        Updated service configuration
    """
    try:
        manager = get_hot_reload_manager()

        if not manager:
            raise HTTPException(
                status_code=503,
                detail="Hot reload not enabled. Edit config file and restart."
            )

        config = manager.current_config

        if service_name not in config.services:
            raise HTTPException(
                status_code=404,
                detail=f"Service '{service_name}' not found"
            )

        # Update service config
        service_config = config.services[service_name]

        if patch.enabled is not None:
            service_config.enabled = patch.enabled

        if patch.auto_start is not None:
            # Only for HTTP services
            if service_config.type.value == "http":
                # Add auto_start field (not in Pydantic model by default)
                # This would require extending ServiceConfig model
                pass

        if patch.auto_detect_model is not None:
            # Only for HTTP services
            pass

        if patch.default_model is not None:
            service_config.default_model = patch.default_model

        # Save configuration back to file
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent.parent.parent.parent / "config" / "default.yaml"
        save_config(config, config_path)

        # Reload
        manager.reload()

        logger.info(f"Service '{service_name}' configuration updated")

        return {
            "status": "updated",
            "service_name": service_name,
            "config": service_config.model_dump(mode="json")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to patch service config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/routing-rules/{task_type}")
async def patch_routing_rule(
    task_type: str,
    patch: RoutingRulePatchRequest
):
    """
    Partially update routing rule.

    Args:
        task_type: Task type to update
        patch: Fields to update

    Returns:
        Updated routing rule
    """
    try:
        manager = get_hot_reload_manager()

        if not manager:
            raise HTTPException(
                status_code=503,
                detail="Hot reload not enabled. Edit config file and restart."
            )

        config = manager.current_config

        if task_type not in config.routing_rules:
            raise HTTPException(
                status_code=404,
                detail=f"Routing rule for '{task_type}' not found"
            )

        # Update routing rule
        rule = config.routing_rules[task_type]

        if patch.primary is not None:
            # Validate service exists
            if patch.primary not in config.services:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown service: {patch.primary}"
                )
            rule.primary = patch.primary

        if patch.fallback is not None:
            # Validate all fallback services exist
            for service in patch.fallback:
                if service not in config.services:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown service: {service}"
                    )
            rule.fallback = patch.fallback

        if patch.timeout_seconds is not None:
            rule.timeout_seconds = patch.timeout_seconds

        # Save configuration back to file
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent.parent.parent.parent / "config" / "default.yaml"
        save_config(config, config_path)

        # Reload
        manager.reload()

        logger.info(f"Routing rule for '{task_type}' updated")

        return {
            "status": "updated",
            "task_type": task_type,
            "rule": rule.model_dump(mode="json")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to patch routing rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
