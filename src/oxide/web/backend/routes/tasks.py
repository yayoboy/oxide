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
from ....utils.path_validator import validate_paths, SecurityError


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
        # Validate file paths for security
        validated_files = request.files
        if request.files:
            try:
                validated_paths = validate_paths(request.files, require_exists=False)
                validated_files = [str(p) for p in validated_paths]
            except SecurityError as e:
                logger.error(f"Security validation failed: {e}")
                raise HTTPException(
                    status_code=403,
                    detail=f"Security validation failed: {str(e)}"
                )

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Get task storage
        task_storage = get_task_storage()

        # Classify task to get type and service
        from ....core.classifier import TaskClassifier
        classifier = TaskClassifier()
        task_info = classifier.classify(request.prompt, validated_files)
        service = task_info.recommended_services[0] if task_info.recommended_services else "unknown"

        # Store task info
        task_storage.add_task(
            task_id=task_id,
            prompt=request.prompt,
            files=validated_files,
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
    import json
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
        execution_mode = task.get("execution_mode", "single")

        # Broadcast task start
        await ws_manager.broadcast_task_start(task_id, task_type, service)

        # Execute task
        chunks = []
        is_broadcast_mode = execution_mode == "broadcast_all"

        async for chunk in orchestrator.execute_task(prompt, files, preferences):
            chunks.append(chunk)

            # Handle broadcast_all mode differently
            if is_broadcast_mode:
                # Parse JSON chunk and broadcast with service identifier
                try:
                    chunk_obj = json.loads(chunk)
                    await ws_manager.broadcast_task_broadcast_chunk(
                        task_id=task_id,
                        service=chunk_obj.get("service", "unknown"),
                        chunk=chunk_obj.get("chunk", ""),
                        done=chunk_obj.get("done", False),
                        timestamp=chunk_obj.get("timestamp", 0),
                        error=chunk_obj.get("error"),
                        total_chunks=chunk_obj.get("total_chunks")
                    )
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse broadcast chunk in task {task_id}")
            else:
                # Standard single/parallel mode - stream as before
                await ws_manager.broadcast_task_progress(task_id, chunk)

        result = "".join(chunks)

        # Update task as completed
        # For broadcast mode, results are already stored per-service in orchestrator
        # For single/parallel mode, store the combined result
        if not is_broadcast_mode:
            task_storage.update_task(task_id, status="completed", result=result)
        else:
            task_storage.update_task(task_id, status="completed")

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


@router.post("/broadcast")
async def execute_broadcast_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Execute a task in broadcast_all mode - sends to ALL available LLMs simultaneously.

    This allows real-time comparison of responses from different LLM services.

    Args:
        request: Task request with prompt and optional files

    Returns:
        Task ID and initial status
    """
    try:
        # Validate file paths for security
        validated_files = request.files
        if request.files:
            try:
                validated_paths = validate_paths(request.files, require_exists=False)
                validated_files = [str(p) for p in validated_paths]
            except SecurityError as e:
                logger.error(f"Security validation failed: {e}")
                raise HTTPException(
                    status_code=403,
                    detail=f"Security validation failed: {str(e)}"
                )

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Get task storage
        task_storage = get_task_storage()

        # Add broadcast_all preference
        preferences = request.preferences or {}
        preferences["broadcast_all"] = True  # Signal to use broadcast mode

        # Classify task to get type
        from ....core.classifier import TaskClassifier
        classifier = TaskClassifier()
        task_info = classifier.classify(request.prompt, validated_files)

        # Store task info with broadcast execution mode
        task_storage.add_task(
            task_id=task_id,
            prompt=request.prompt,
            files=validated_files,
            preferences=preferences,
            service="broadcast_all",  # Indicate multiple services
            task_type=task_info.task_type.value,
            execution_mode="broadcast_all"
        )

        # Execute task in background
        background_tasks.add_task(
            _execute_broadcast_task_background,
            task_id,
            request.prompt,
            request.files,
            preferences,
            orchestrator
        )

        return {
            "task_id": task_id,
            "status": "queued",
            "execution_mode": "broadcast_all",
            "message": "Task queued for broadcast execution on all available LLMs"
        }

    except Exception as e:
        logger.error(f"Error queuing broadcast task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_broadcast_task_background(
    task_id: str,
    prompt: str,
    files: Optional[List[str]],
    preferences: Optional[Dict[str, Any]],
    orchestrator: Orchestrator
):
    """
    Execute task in broadcast_all mode in background.

    Args:
        task_id: Task identifier
        prompt: Task prompt
        files: Optional file paths
        preferences: Routing preferences (should include broadcast_all=True)
        orchestrator: Orchestrator instance
    """
    import json
    from ..main import get_ws_manager
    from ....core.classifier import TaskClassifier

    ws_manager = get_ws_manager()
    task_storage = get_task_storage()

    try:
        # Update status to running
        task_storage.update_task(task_id, status="running")

        # Get task info
        task = task_storage.get_task(task_id)
        task_type = task.get("task_type", "unknown")

        # Broadcast task start
        await ws_manager.broadcast_task_start(task_id, task_type, "broadcast_all")

        # Classify task to get routing decision
        classifier = TaskClassifier()
        task_info = classifier.classify(prompt, files)

        # Get broadcast routing decision
        from ....core.router import TaskRouter
        from ....config.loader import load_config
        config = load_config()
        router = TaskRouter(config, service_health_checker=orchestrator._check_service_health)
        decision = await router.route_broadcast_all(task_info)

        # Log broadcast info
        logger.info(
            f"Broadcasting task {task_id} to {len(decision.broadcast_services)} services: "
            f"{', '.join(decision.broadcast_services)}"
        )

        # Execute with broadcast_all routing
        chunks = []
        service_responses = {}

        async for chunk in orchestrator.execute_task(prompt, files, preferences):
            chunks.append(chunk)

            # Parse JSON chunk and broadcast with service identifier
            try:
                chunk_obj = json.loads(chunk)
                service_name = chunk_obj.get("service")

                await ws_manager.broadcast_task_broadcast_chunk(
                    task_id=task_id,
                    service=chunk_obj.get("service", "unknown"),
                    chunk=chunk_obj.get("chunk", ""),
                    done=chunk_obj.get("done", False),
                    timestamp=chunk_obj.get("timestamp", 0),
                    error=chunk_obj.get("error"),
                    total_chunks=chunk_obj.get("total_chunks")
                )
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse broadcast chunk in task {task_id}")

        # Update task as completed
        task_storage.update_task(task_id, status="completed")

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
