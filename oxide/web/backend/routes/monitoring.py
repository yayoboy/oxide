"""
Monitoring API routes.

Endpoints for system metrics and monitoring.
"""
import asyncio
import psutil
from typing import Dict, Any
from fastapi import APIRouter, Depends

from ....core.orchestrator import Orchestrator
from ....utils.logging import logger


router = APIRouter()


def get_orchestrator() -> Orchestrator:
    """Dependency to get orchestrator instance."""
    from ..main import get_orchestrator
    return get_orchestrator()


def get_ws_manager():
    """Dependency to get WebSocket manager."""
    from ..main import get_ws_manager
    return get_ws_manager()


@router.get("/metrics")
async def get_metrics(orchestrator: Orchestrator = Depends(get_orchestrator)) -> Dict[str, Any]:
    """
    Get system metrics.

    Returns:
        System metrics including CPU, memory, services, etc.
    """
    try:
        # Get service status
        service_status = await orchestrator.get_service_status()

        # Count services
        total_services = len(service_status)
        enabled_services = sum(1 for s in service_status.values() if s.get("enabled"))
        healthy_services = sum(1 for s in service_status.values() if s.get("healthy"))

        # Get task stats
        from .tasks import tasks_store

        total_tasks = len(tasks_store)
        running_tasks = sum(1 for t in tasks_store.values() if t["status"] == "running")
        completed_tasks = sum(1 for t in tasks_store.values() if t["status"] == "completed")
        failed_tasks = sum(1 for t in tasks_store.values() if t["status"] == "failed")

        # System resources
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_total_mb = memory.total / (1024 * 1024)

        # WebSocket connections
        ws_manager = get_ws_manager()
        ws_connections = ws_manager.get_connection_count()

        return {
            "services": {
                "total": total_services,
                "enabled": enabled_services,
                "healthy": healthy_services,
                "unhealthy": enabled_services - healthy_services
            },
            "tasks": {
                "total": total_tasks,
                "running": running_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks,
                "queued": total_tasks - running_tasks - completed_tasks - failed_tasks
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_used_mb": round(memory_used_mb, 2),
                "memory_total_mb": round(memory_total_mb, 2)
            },
            "websocket": {
                "connections": ws_connections
            },
            "timestamp": asyncio.get_event_loop().time()
        }

    except (AttributeError, KeyError, TypeError) as e:
        # Expected errors when services/tasks not properly initialized
        logger.warning(f"Metrics collection error (expected): {e}")
        return {
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }
    except OSError as e:
        # Expected system resource access errors
        logger.warning(f"System metrics error: {e}")
        return {
            "error": f"System metrics unavailable: {str(e)}",
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error getting metrics: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "timestamp": asyncio.get_event_loop().time()
        }


@router.get("/stats")
async def get_stats(orchestrator: Orchestrator = Depends(get_orchestrator)) -> Dict[str, Any]:
    """
    Get detailed statistics.

    Returns:
        Detailed statistics about task execution
    """
    try:
        from .tasks import tasks_store

        if not tasks_store:
            return {
                "total_tasks": 0,
                "avg_duration": 0,
                "success_rate": 0,
                "tasks_by_status": {}
            }

        # Calculate stats
        tasks = list(tasks_store.values())
        completed = [t for t in tasks if t["status"] == "completed"]

        # Average duration
        if completed:
            durations = [t.get("duration", 0) for t in completed]
            avg_duration = sum(durations) / len(durations)
        else:
            avg_duration = 0

        # Success rate
        total = len(tasks)
        succeeded = len(completed)
        failed = sum(1 for t in tasks if t["status"] == "failed")
        success_rate = (succeeded / total * 100) if total > 0 else 0

        # Tasks by status
        tasks_by_status = {}
        for task in tasks:
            status = task["status"]
            tasks_by_status[status] = tasks_by_status.get(status, 0) + 1

        return {
            "total_tasks": total,
            "avg_duration": round(avg_duration, 2),
            "success_rate": round(success_rate, 2),
            "tasks_by_status": tasks_by_status,
            "completed": succeeded,
            "failed": failed
        }

    except (AttributeError, KeyError, TypeError, ZeroDivisionError) as e:
        # Expected errors during stats calculation
        logger.warning(f"Stats calculation error (expected): {e}")
        return {"error": str(e)}
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error getting stats: {e}")
        return {"error": f"Unexpected error: {str(e)}"}


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Overall system health check.

    Returns:
        System health status
    """
    try:
        # Check if system is responsive
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        # Determine health status
        is_healthy = True
        issues = []

        if cpu_percent > 90:
            is_healthy = False
            issues.append("High CPU usage")

        if memory.percent > 90:
            is_healthy = False
            issues.append("High memory usage")

        status = "healthy" if is_healthy else "degraded"

        return {
            "status": status,
            "healthy": is_healthy,
            "issues": issues,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "timestamp": asyncio.get_event_loop().time()
        }

    except OSError as e:
        # Expected system resource access errors
        logger.warning(f"Health check system error: {e}")
        return {
            "status": "error",
            "healthy": False,
            "issues": [f"System metrics unavailable: {str(e)}"],
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected health check error: {e}")
        return {
            "status": "error",
            "healthy": False,
            "issues": [f"Unexpected error: {str(e)}"],
            "timestamp": asyncio.get_event_loop().time()
        }
