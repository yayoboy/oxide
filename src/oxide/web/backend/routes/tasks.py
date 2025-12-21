"""
Tasks API routes.

Endpoints for executing and monitoring tasks.
"""
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from ....core.orchestrator import Orchestrator
from ....utils.logging import logger
from ....utils.exceptions import NoServiceAvailableError, ExecutionError
from ....utils.task_storage import get_task_storage


router = APIRouter()


class TaskRequest(BaseModel):
    """Request to execute a task."""
    prompt: str
    files: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None


class ParallelTaskRequest(BaseModel):
    """Request to execute parallel analysis."""
    directory: str
    prompt: str
    num_workers: Optional[int] = None


def get_orchestrator() -> Orchestrator:
    """Dependency to get orchestrator instance."""
    from ..main import get_orchestrator
    return get_orchestrator()


def get_ws_manager():
    """Dependency to get WebSocket manager."""
    from ..main import get_ws_manager
    return get_ws_manager()


@router.post("/execute")
async def execute_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Execute a task with intelligent routing.

    Args:
        request: Task request with prompt and optional files

    Returns:
        Task ID and initial status
    """
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Get task storage
        task_storage = get_task_storage()

        # Classify task to get type and service
        from ....core.classifier import TaskClassifier
        classifier = TaskClassifier()
        task_info = classifier.classify(request.prompt, request.files)
        service = task_info.recommended_services[0] if task_info.recommended_services else "unknown"

        # Store task info
        task_storage.add_task(
            task_id=task_id,
            prompt=request.prompt,
            files=request.files,
            preferences=request.preferences,
            service=service,
            task_type=task_info.task_type.value
        )

        # Execute task in background
        background_tasks.add_task(
            _execute_task_background,
            task_id,
            request.prompt,
            request.files,
            request.preferences,
            orchestrator
        )

        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Task queued for execution"
        }

    except Exception as e:
        logger.error(f"Error queuing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_task_background(
    task_id: str,
    prompt: str,
    files: Optional[List[str]],
    preferences: Optional[Dict[str, Any]],
    orchestrator: Orchestrator
):
    """
    Execute task in background and update status.

    Args:
        task_id: Task identifier
        prompt: Task prompt
        files: Optional file paths
        preferences: Optional routing preferences
        orchestrator: Orchestrator instance
    """
    from ..main import get_ws_manager

    ws_manager = get_ws_manager()
    task_storage = get_task_storage()

    try:
        # Update status to running
        task_storage.update_task(task_id, status="running")

        # Get task info for WebSocket broadcast
        task = task_storage.get_task(task_id)
        service = task.get("service", "unknown")
        task_type = task.get("task_type", "unknown")

        # Broadcast task start
        await ws_manager.broadcast_task_start(task_id, task_type, service)

        # Execute task
        chunks = []
        async for chunk in orchestrator.execute_task(prompt, files, preferences):
            chunks.append(chunk)
            # Stream to WebSocket clients
            await ws_manager.broadcast_task_progress(task_id, chunk)

        result = "".join(chunks)

        # Update task as completed
        task_storage.update_task(task_id, status="completed", result=result)

        # Get updated task for duration
        updated_task = task_storage.get_task(task_id)
        duration = updated_task.get("duration", 0)

        # Broadcast completion
        await ws_manager.broadcast_task_complete(task_id, True, duration)

    except NoServiceAvailableError as e:
        error_msg = f"No service available: {e}"
        logger.error(error_msg)

        task_storage.update_task(task_id, status="failed", error=error_msg)
        await ws_manager.broadcast_task_complete(task_id, False, error=error_msg)

    except ExecutionError as e:
        error_msg = f"Execution error: {e}"
        logger.error(error_msg)

        task_storage.update_task(task_id, status="failed", error=error_msg)
        await ws_manager.broadcast_task_complete(task_id, False, error=error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.error(error_msg)

        task_storage.update_task(task_id, status="failed", error=error_msg)
        await ws_manager.broadcast_task_complete(task_id, False, error=error_msg)


@router.get("/{task_id}")
async def get_task(task_id: str) -> Dict[str, Any]:
    """
    Get task status and result.

    Args:
        task_id: Task identifier

    Returns:
        Task information
    """
    task_storage = get_task_storage()
    task = task_storage.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    return task


@router.get("/")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    List recent tasks.

    Args:
        status: Filter by status (queued, running, completed, failed)
        limit: Maximum number of tasks to return

    Returns:
        List of tasks
    """
    task_storage = get_task_storage()
    tasks = task_storage.list_tasks(status=status, limit=limit)
    stats = task_storage.get_stats()

    return {
        "tasks": tasks,
        "total": stats["total"],
        "filtered": len(tasks)
    }


@router.delete("/{task_id}")
async def delete_task(task_id: str) -> Dict[str, Any]:
    """
    Delete a task from history.

    Args:
        task_id: Task identifier

    Returns:
        Success message
    """
    task_storage = get_task_storage()

    if not task_storage.delete_task(task_id):
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    return {
        "message": f"Task '{task_id}' deleted successfully"
    }


@router.post("/clear")
async def clear_tasks(status: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear task history.

    Args:
        status: Only clear tasks with this status (optional)

    Returns:
        Number of tasks cleared
    """
    task_storage = get_task_storage()
    cleared = task_storage.clear_tasks(status=status)

    return {
        "message": f"Cleared {cleared} task(s)",
        "cleared": cleared
    }
