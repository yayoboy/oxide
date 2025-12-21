"""
Routing Rules API routes.

Endpoints for managing custom task-to-service routing assignments.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ....utils.routing_rules import get_routing_rules_manager
from ....utils.logging import logger


router = APIRouter()


class RoutingRule(BaseModel):
    """Routing rule model."""
    task_type: str
    service: str


@router.get("/rules")
async def list_routing_rules() -> Dict[str, Any]:
    """
    Get all custom routing rules.

    Returns:
        List of routing rules and statistics
    """
    try:
        rules_manager = get_routing_rules_manager()

        return {
            "rules": rules_manager.export_rules(),
            "stats": rules_manager.get_stats()
        }

    except Exception as e:
        logger.error(f"Error listing routing rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{task_type}")
async def get_routing_rule(task_type: str) -> Dict[str, Any]:
    """
    Get routing rule for a specific task type.

    Args:
        task_type: Type of task

    Returns:
        Routing rule if exists
    """
    rules_manager = get_routing_rules_manager()
    service = rules_manager.get_rule(task_type)

    if not service:
        raise HTTPException(
            status_code=404,
            detail=f"No routing rule found for task type '{task_type}'"
        )

    return {
        "task_type": task_type,
        "service": service
    }


@router.post("/rules")
async def create_routing_rule(rule: RoutingRule) -> Dict[str, Any]:
    """
    Create or update a routing rule.

    Args:
        rule: Routing rule with task_type and service

    Returns:
        Created/updated rule
    """
    try:
        rules_manager = get_routing_rules_manager()

        result = rules_manager.add_rule(rule.task_type, rule.service)

        return {
            "message": f"Routing rule {result['action']}",
            "rule": {
                "task_type": rule.task_type,
                "service": rule.service
            }
        }

    except Exception as e:
        logger.error(f"Error creating routing rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{task_type}")
async def update_routing_rule(task_type: str, rule: RoutingRule) -> Dict[str, Any]:
    """
    Update a routing rule.

    Args:
        task_type: Type of task to update
        rule: New rule configuration

    Returns:
        Updated rule
    """
    try:
        rules_manager = get_routing_rules_manager()

        # Ensure task_type matches
        if rule.task_type != task_type:
            raise HTTPException(
                status_code=400,
                detail="Task type in URL and body must match"
            )

        result = rules_manager.add_rule(rule.task_type, rule.service)

        return {
            "message": "Routing rule updated",
            "rule": {
                "task_type": rule.task_type,
                "service": rule.service
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating routing rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{task_type}")
async def delete_routing_rule(task_type: str) -> Dict[str, Any]:
    """
    Delete a routing rule.

    Args:
        task_type: Type of task

    Returns:
        Success message
    """
    rules_manager = get_routing_rules_manager()

    if not rules_manager.delete_rule(task_type):
        raise HTTPException(
            status_code=404,
            detail=f"No routing rule found for task type '{task_type}'"
        )

    return {
        "message": f"Routing rule for '{task_type}' deleted successfully"
    }


@router.post("/rules/clear")
async def clear_routing_rules() -> Dict[str, Any]:
    """
    Clear all routing rules.

    Returns:
        Number of rules cleared
    """
    try:
        rules_manager = get_routing_rules_manager()
        cleared = rules_manager.clear_all_rules()

        return {
            "message": f"Cleared {cleared} routing rule(s)",
            "cleared": cleared
        }

    except Exception as e:
        logger.error(f"Error clearing routing rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task-types")
async def get_available_task_types() -> Dict[str, Any]:
    """
    Get list of available task types that can be configured.

    Returns:
        List of task types with descriptions
    """
    # Standard task types from the classifier
    task_types = [
        {
            "name": "coding",
            "label": "Code Generation",
            "description": "Writing new code, implementing features",
            "recommended_services": ["qwen", "gemini"]
        },
        {
            "name": "code_review",
            "label": "Code Review",
            "description": "Reviewing code for bugs, improvements",
            "recommended_services": ["qwen", "gemini"]
        },
        {
            "name": "bug_search",
            "label": "Bug Search",
            "description": "Finding and analyzing bugs in code",
            "recommended_services": ["qwen", "gemini"]
        },
        {
            "name": "refactoring",
            "label": "Refactoring",
            "description": "Code refactoring and optimization",
            "recommended_services": ["qwen", "gemini"]
        },
        {
            "name": "documentation",
            "label": "Documentation",
            "description": "Writing documentation, comments",
            "recommended_services": ["gemini", "qwen"]
        },
        {
            "name": "codebase_analysis",
            "label": "Codebase Analysis",
            "description": "Analyzing large codebases, architecture",
            "recommended_services": ["gemini"]
        },
        {
            "name": "quick_query",
            "label": "Quick Query",
            "description": "Simple questions, quick responses",
            "recommended_services": ["ollama_local", "ollama_remote"]
        },
        {
            "name": "general",
            "label": "General",
            "description": "General purpose tasks",
            "recommended_services": ["ollama_local", "qwen"]
        }
    ]

    return {
        "task_types": task_types
    }
