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


router = APIRouter()

# In-memory task storage (replace with database in production)
tasks_store: Dict[str, Dict[str, Any]] = {}


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

        # Store task info
        tasks_store[task_id] = {
            "id": task_id,
            "status": "queued",
            "prompt": request.prompt,
            "files": request.files or [],
            "result": None,
            "error": None,
            "created_at": asyncio.get_event_loop().time()
        }

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

    except (AttributeError, KeyError, TypeError, ValueError) as e:
        # Expected errors during task queueing
        logger.warning(f"Task queueing error (expected): {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error queuing task: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e


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
    start_time = asyncio.get_event_loop().time()

    try:
        # Update status to running
        tasks_store[task_id]["status"] = "running"
        tasks_store[task_id]["started_at"] = start_time

        # Classify task to get service info
        from ....core.classifier import TaskClassifier
        classifier = TaskClassifier()
        task_info = classifier.classify(prompt, files)

        # Broadcast task start
        await ws_manager.broadcast_task_start(
            task_id,
            task_info.task_type.value,
            task_info.recommended_services[0] if task_info.recommended_services else "unknown"
        )

        # Execute task
        chunks = []
        async for chunk in orchestrator.execute_task(prompt, files, preferences):
            chunks.append(chunk)
            # Stream to WebSocket clients
            await ws_manager.broadcast_task_progress(task_id, chunk)

        result = "".join(chunks)

        # Update task as completed
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        tasks_store[task_id].update({
            "status": "completed",
            "result": result,
            "completed_at": end_time,
            "duration": duration
        })

        # Broadcast completion
        await ws_manager.broadcast_task_complete(task_id, True, duration)

    except NoServiceAvailableError as e:
        error_msg = f"No service available: {e}"
        logger.error(error_msg)

        tasks_store[task_id].update({
            "status": "failed",
            "error": error_msg,
            "completed_at": asyncio.get_event_loop().time()
        })

        await ws_manager.broadcast_task_complete(task_id, False, error=error_msg)

    except ExecutionError as e:
        error_msg = f"Execution error: {e}"
        logger.error(error_msg)

        tasks_store[task_id].update({
            "status": "failed",
            "error": error_msg,
            "completed_at": asyncio.get_event_loop().time()
        })

        await ws_manager.broadcast_task_complete(task_id, False, error=error_msg)

    except (AttributeError, KeyError, TypeError) as e:
        # Expected errors during task execution (e.g., task_store access)
        error_msg = f"Task execution error: {e}"
        logger.warning(error_msg)

        tasks_store[task_id].update({
            "status": "failed",
            "error": error_msg,
            "completed_at": asyncio.get_event_loop().time()
        })

        await ws_manager.broadcast_task_complete(task_id, False, error=error_msg)

    except Exception as e:
        # Unexpected error - log with full traceback
        error_msg = f"Unexpected error: {e}"
        logger.exception(error_msg)

        tasks_store[task_id].update({
            "status": "failed",
            "error": error_msg,
            "completed_at": asyncio.get_event_loop().time()
        })

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
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    return tasks_store[task_id]


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
    tasks = list(tasks_store.values())

    # Filter by status if provided
    if status:
        tasks = [t for t in tasks if t["status"] == status]

    # Sort by creation time (newest first)
    tasks.sort(key=lambda t: t.get("created_at", 0), reverse=True)

    # Limit results
    tasks = tasks[:limit]

    return {
        "tasks": tasks,
        "total": len(tasks_store),
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
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    del tasks_store[task_id]

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
    global tasks_store

    if status:
        # Clear only tasks with specific status
        before_count = len(tasks_store)
        tasks_store = {
            tid: task for tid, task in tasks_store.items()
            if task["status"] != status
        }
        cleared = before_count - len(tasks_store)
    else:
        # Clear all tasks
        cleared = len(tasks_store)
        tasks_store = {}

    return {
        "message": f"Cleared {cleared} task(s)",
        "cleared": cleared
    }
