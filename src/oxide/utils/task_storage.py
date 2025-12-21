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
        task_type: Optional[str] = None
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
            "result": None,
            "error": None,
            "created_at": datetime.now().timestamp(),
            "started_at": None,
            "completed_at": None,
            "duration": None
        }

        tasks[task_id] = task_record
        self._write_tasks(tasks)

        self.logger.debug(f"Added task: {task_id}")
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


def get_task_storage() -> TaskStorage:
    """Get the global TaskStorage instance."""
    global _task_storage
    if _task_storage is None:
        _task_storage = TaskStorage()
    return _task_storage
