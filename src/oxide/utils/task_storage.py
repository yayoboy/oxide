"""
Shared task storage for Oxide.

Provides persistent storage for task history that can be accessed by both
the MCP server and Web backend.
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading

from .logging import logger


class TaskStorage:
    """
    Thread-safe and async-safe task storage using JSON file.

    Stores task execution history that persists across MCP and Web server restarts.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize task storage.

        Args:
            storage_path: Path to JSON storage file (defaults to ~/.oxide/tasks.json)
        """
        if storage_path is None:
            storage_path = Path.home() / ".oxide" / "tasks.json"

        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread lock for file operations
        self._lock = threading.Lock()

        self.logger = logger.getChild("task_storage")

        # Ensure file exists
        if not self.storage_path.exists():
            self._write_tasks({})

        self.logger.info(f"Task storage initialized: {self.storage_path}")

    def _read_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Read tasks from JSON file."""
        try:
            with self._lock:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(f"Failed to read tasks: {e}, returning empty dict")
            return {}

    def _write_tasks(self, tasks: Dict[str, Dict[str, Any]]):
        """Write tasks to JSON file."""
        try:
            with self._lock:
                with open(self.storage_path, 'w') as f:
                    json.dump(tasks, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to write tasks: {e}")

    def add_task(
        self,
        task_id: str,
        prompt: str,
        files: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
        service: Optional[str] = None,
        task_type: Optional[str] = None,
        execution_mode: str = "single"
    ) -> Dict[str, Any]:
        """
        Add a new task to storage.

        Args:
            task_id: Unique task identifier
            prompt: Task prompt
            files: Optional list of file paths
            preferences: Optional routing preferences
            service: Service that will execute the task
            task_type: Type of task
            execution_mode: Execution mode (single, parallel, broadcast_all)

        Returns:
            Created task record
        """
        tasks = self._read_tasks()

        task_record = {
            "id": task_id,
            "status": "queued",
            "prompt": prompt,
            "files": files or [],
            "preferences": preferences or {},
            "service": service,
            "task_type": task_type,
            "execution_mode": execution_mode,
            "result": None,
            "error": None,
            "broadcast_results": [],  # For broadcast_all mode: list of {service, result, error, chunks, completed_at}
            "created_at": datetime.now().timestamp(),
            "started_at": None,
            "completed_at": None,
            "duration": None
        }

        tasks[task_id] = task_record
        self._write_tasks(tasks)

        self.logger.debug(f"Added task: {task_id} (mode: {execution_mode})")
        return task_record

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        result: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs
    ):
        """
        Update task fields.

        Args:
            task_id: Task identifier
            status: New status (queued, running, completed, failed)
            result: Task result
            error: Error message if failed
            **kwargs: Additional fields to update
        """
        tasks = self._read_tasks()

        if task_id not in tasks:
            self.logger.warning(f"Task not found: {task_id}")
            return

        # Update fields
        if status:
            tasks[task_id]["status"] = status

            # Auto-set timestamps based on status
            if status == "running" and not tasks[task_id].get("started_at"):
                tasks[task_id]["started_at"] = datetime.now().timestamp()
            elif status in ("completed", "failed"):
                if not tasks[task_id].get("completed_at"):
                    tasks[task_id]["completed_at"] = datetime.now().timestamp()

                # Calculate duration if not set
                if tasks[task_id].get("started_at") and not tasks[task_id].get("duration"):
                    duration = tasks[task_id]["completed_at"] - tasks[task_id]["started_at"]
                    tasks[task_id]["duration"] = duration

        if result is not None:
            tasks[task_id]["result"] = result

        if error is not None:
            tasks[task_id]["error"] = error

        # Update additional fields
        for key, value in kwargs.items():
            tasks[task_id][key] = value

        self._write_tasks(tasks)
        self.logger.debug(f"Updated task: {task_id} (status: {status})")

    def add_broadcast_result(
        self,
        task_id: str,
        service: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
        chunks: int = 0
    ):
        """
        Add a result from a specific service in broadcast_all mode.

        Args:
            task_id: Task identifier
            service: Service name that produced this result
            result: Result text from the service
            error: Error message if the service failed
            chunks: Number of chunks received from this service
        """
        tasks = self._read_tasks()

        if task_id not in tasks:
            self.logger.warning(f"Task not found: {task_id}")
            return

        # Initialize broadcast_results if it doesn't exist (backward compatibility)
        if "broadcast_results" not in tasks[task_id]:
            tasks[task_id]["broadcast_results"] = []

        # Check if this service already has a result
        existing_idx = None
        for idx, br in enumerate(tasks[task_id]["broadcast_results"]):
            if br.get("service") == service:
                existing_idx = idx
                break

        broadcast_result = {
            "service": service,
            "result": result,
            "error": error,
            "chunks": chunks,
            "completed_at": datetime.now().timestamp()
        }

        if existing_idx is not None:
            # Update existing result
            tasks[task_id]["broadcast_results"][existing_idx] = broadcast_result
        else:
            # Add new result
            tasks[task_id]["broadcast_results"].append(broadcast_result)

        self._write_tasks(tasks)
        self.logger.debug(f"Added broadcast result for task {task_id} from {service} ({chunks} chunks)")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID."""
        tasks = self._read_tasks()
        return tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List tasks with optional filtering.

        Args:
            status: Filter by status
            limit: Maximum number of tasks to return

        Returns:
            List of task records
        """
        tasks = list(self._read_tasks().values())

        # Filter by status
        if status:
            tasks = [t for t in tasks if t.get("status") == status]

        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.get("created_at", 0), reverse=True)

        # Limit results
        return tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from storage.

        Args:
            task_id: Task identifier

        Returns:
            True if deleted, False if not found
        """
        tasks = self._read_tasks()

        if task_id not in tasks:
            return False

        del tasks[task_id]
        self._write_tasks(tasks)

        self.logger.debug(f"Deleted task: {task_id}")
        return True

    def clear_tasks(self, status: Optional[str] = None) -> int:
        """
        Clear tasks from storage.

        Args:
            status: Only clear tasks with this status (optional)

        Returns:
            Number of tasks cleared
        """
        tasks = self._read_tasks()

        if status:
            # Clear only tasks with specific status
            before_count = len(tasks)
            tasks = {
                tid: task for tid, task in tasks.items()
                if task.get("status") != status
            }
            cleared = before_count - len(tasks)
        else:
            # Clear all tasks
            cleared = len(tasks)
            tasks = {}

        self._write_tasks(tasks)
        self.logger.info(f"Cleared {cleared} task(s)")
        return cleared

    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        tasks = list(self._read_tasks().values())

        stats = {
            "total": len(tasks),
            "by_status": {},
            "by_service": {},
            "by_task_type": {}
        }

        for task in tasks:
            # Count by status
            status = task.get("status", "unknown")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Count by service
            service = task.get("service", "unknown")
            stats["by_service"][service] = stats["by_service"].get(service, 0) + 1

            # Count by task type
            task_type = task.get("task_type", "unknown")
            stats["by_task_type"][task_type] = stats["by_task_type"].get(task_type, 0) + 1

        return stats


# Global singleton instance
_task_storage: Optional[TaskStorage] = None


def get_task_storage():
    """
    Get the global TaskStorage instance.

    Returns either TaskStorage (JSON) or TaskStorageSQLite based on configuration.
    The storage backend is determined by config.storage.backend setting.
    """
    global _task_storage

    if _task_storage is None:
        # Import here to avoid circular dependency
        try:
            from ..config.loader import load_config
            config = load_config()
            backend = config.storage.backend
        except Exception as e:
            logger.warning(f"Failed to load config, defaulting to JSON storage: {e}")
            backend = "json"

        if backend == "sqlite":
            from .task_storage_sqlite import TaskStorageSQLite
            _task_storage = TaskStorageSQLite()
            logger.info("Using SQLite storage backend")
        else:
            _task_storage = TaskStorage()
            logger.info("Using JSON storage backend")

    return _task_storage
