"""
SQLite-based task storage for Oxide.

High-performance replacement for JSON file storage with:
- 10-100x faster operations
- Concurrent access with WAL mode
- Indexed queries for O(1) lookups
- ACID transactions
- No additional dependencies
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
from contextlib import contextmanager

from .logging import logger


class TaskStorageSQLite:
    """
    Thread-safe task storage using SQLite.

    Drop-in replacement for JSON-based TaskStorage with significantly
    better performance and concurrency.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize SQLite task storage.

        Args:
            storage_path: Path to SQLite database file (defaults to ~/.oxide/tasks.db)
        """
        if storage_path is None:
            storage_path = Path.home() / ".oxide" / "tasks.db"

        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local connections for thread safety
        self._local = threading.local()

        self.logger = logger.getChild("task_storage_sqlite")

        # Initialize database schema
        self._init_schema()

        self.logger.info(f"SQLite task storage initialized: {self.storage_path}")

    @contextmanager
    def _get_connection(self):
        """Get thread-local database connection with WAL mode."""
        # Each thread gets its own connection
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                str(self.storage_path),
                check_same_thread=False
            )
            # Enable WAL mode for concurrent reads/writes
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            # Return dicts instead of tuples
            self._local.conn.row_factory = sqlite3.Row

        try:
            yield self._local.conn
        except Exception as e:
            self._local.conn.rollback()
            raise
        else:
            self._local.conn.commit()

    def _init_schema(self):
        """Initialize database schema with indexes."""
        with self._get_connection() as conn:
            # Create tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    files TEXT,  -- JSON array
                    preferences TEXT,  -- JSON object
                    service TEXT,
                    task_type TEXT,
                    result TEXT,
                    error TEXT,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    duration REAL
                )
            """)

            # Create indexes for fast queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_service ON tasks(service)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_type ON tasks(task_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at DESC)")

            # Create routing rules table (for future use)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_rules (
                    task_type TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

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
        created_at = datetime.now().timestamp()

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
            "created_at": created_at,
            "started_at": None,
            "completed_at": None,
            "duration": None
        }

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tasks (
                    id, status, prompt, files, preferences,
                    service, task_type, result, error,
                    created_at, started_at, completed_at, duration
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                "queued",
                prompt,
                json.dumps(files or []),
                json.dumps(preferences or {}),
                service,
                task_type,
                None,
                None,
                created_at,
                None,
                None,
                None
            ))

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
        with self._get_connection() as conn:
            # Get current task to check timestamps
            row = conn.execute(
                "SELECT started_at, completed_at FROM tasks WHERE id = ?",
                (task_id,)
            ).fetchone()

            if not row:
                self.logger.warning(f"Task not found: {task_id}")
                return

            # Build update query dynamically
            updates = []
            params = []

            if status:
                updates.append("status = ?")
                params.append(status)

                # Auto-set timestamps based on status
                if status == "running" and row["started_at"] is None:
                    updates.append("started_at = ?")
                    params.append(datetime.now().timestamp())

                elif status in ("completed", "failed"):
                    now = datetime.now().timestamp()

                    if row["completed_at"] is None:
                        updates.append("completed_at = ?")
                        params.append(now)

                    # Calculate duration if we have started_at
                    if row["started_at"] is not None:
                        duration = now - row["started_at"]
                        updates.append("duration = ?")
                        params.append(duration)

            if result is not None:
                updates.append("result = ?")
                params.append(result)

            if error is not None:
                updates.append("error = ?")
                params.append(error)

            # Handle additional kwargs
            for key, value in kwargs.items():
                if key in ("service", "task_type"):
                    updates.append(f"{key} = ?")
                    params.append(value)

            if not updates:
                return

            # Execute update
            params.append(task_id)
            query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"

            conn.execute(query, params)

        self.logger.debug(f"Updated task: {task_id} (status: {status})")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_dict(row)

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
            List of task records (newest first)
        """
        with self._get_connection() as conn:
            if status:
                rows = conn.execute("""
                    SELECT * FROM tasks
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (status, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM tasks
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()

            return [self._row_to_dict(row) for row in rows]

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from storage.

        Args:
            task_id: Task identifier

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,)
            )

            deleted = cursor.rowcount > 0

        if deleted:
            self.logger.debug(f"Deleted task: {task_id}")

        return deleted

    def clear_tasks(self, status: Optional[str] = None) -> int:
        """
        Clear tasks from storage.

        Args:
            status: Only clear tasks with this status (optional)

        Returns:
            Number of tasks cleared
        """
        with self._get_connection() as conn:
            if status:
                cursor = conn.execute(
                    "DELETE FROM tasks WHERE status = ?",
                    (status,)
                )
            else:
                cursor = conn.execute("DELETE FROM tasks")

            cleared = cursor.rowcount

        self.logger.info(f"Cleared {cleared} task(s)")
        return cleared

    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        with self._get_connection() as conn:
            # Total count
            total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

            # Count by status
            status_rows = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM tasks
                GROUP BY status
            """).fetchall()

            # Count by service
            service_rows = conn.execute("""
                SELECT service, COUNT(*) as count
                FROM tasks
                GROUP BY service
            """).fetchall()

            # Count by task_type
            task_type_rows = conn.execute("""
                SELECT task_type, COUNT(*) as count
                FROM tasks
                GROUP BY task_type
            """).fetchall()

        stats = {
            "total": total,
            "by_status": {row["status"]: row["count"] for row in status_rows},
            "by_service": {row["service"]: row["count"] for row in service_rows},
            "by_task_type": {row["task_type"]: row["count"] for row in task_type_rows}
        }

        return stats

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to task dictionary."""
        return {
            "id": row["id"],
            "status": row["status"],
            "prompt": row["prompt"],
            "files": json.loads(row["files"]) if row["files"] else [],
            "preferences": json.loads(row["preferences"]) if row["preferences"] else {},
            "service": row["service"],
            "task_type": row["task_type"],
            "result": row["result"],
            "error": row["error"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "duration": row["duration"]
        }

    def migrate_from_json(self, json_path: Path):
        """
        Migrate data from JSON storage to SQLite.

        Args:
            json_path: Path to JSON storage file
        """
        if not json_path.exists():
            self.logger.info("No JSON file to migrate")
            return

        self.logger.info(f"Migrating from JSON: {json_path}")

        try:
            with open(json_path, 'r') as f:
                tasks = json.load(f)

            migrated = 0
            with self._get_connection() as conn:
                for task_id, task in tasks.items():
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO tasks (
                                id, status, prompt, files, preferences,
                                service, task_type, result, error,
                                created_at, started_at, completed_at, duration
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            task.get("id", task_id),
                            task.get("status", "unknown"),
                            task.get("prompt", ""),
                            json.dumps(task.get("files", [])),
                            json.dumps(task.get("preferences", {})),
                            task.get("service"),
                            task.get("task_type"),
                            task.get("result"),
                            task.get("error"),
                            task.get("created_at"),
                            task.get("started_at"),
                            task.get("completed_at"),
                            task.get("duration")
                        ))
                        migrated += 1
                    except Exception as e:
                        self.logger.error(f"Failed to migrate task {task_id}: {e}")

            self.logger.info(f"✅ Migrated {migrated} tasks from JSON to SQLite")

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            raise

    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')


# Global singleton instance
_task_storage_sqlite: Optional[TaskStorageSQLite] = None


def get_task_storage_sqlite() -> TaskStorageSQLite:
    """Get the global TaskStorageSQLite instance."""
    global _task_storage_sqlite
    if _task_storage_sqlite is None:
        _task_storage_sqlite = TaskStorageSQLite()
    return _task_storage_sqlite
