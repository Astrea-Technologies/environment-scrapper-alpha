import uuid
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .task_types import TaskType

class TaskManager:
    """Manages tasks in memory for the MVP."""

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, task_type: TaskType, params: dict) -> str:
        """Creates a new task entry and returns its ID."""
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        task_data = {
            "id": task_id,
            "type": task_type,
            "params": params,
            "status": "pending", # Statuses: pending, running, completed, failed
            "created_at": now,
            "updated_at": now,
            "result": None,
            "error": None,
        }
        async with self._lock:
            self.tasks[task_id] = task_data
        return task_id

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the full details of a task."""
        async with self._lock:
            return self.tasks.get(task_id)

    async def get_task_status(self, task_id: str) -> Optional[str]:
        """Retrieves the current status of a task."""
        task = await self.get_task(task_id)
        return task["status"] if task else None

    async def update_task_status(
        self, task_id: str, status: str, result: Any = None, error: str = None
    ) -> bool:
        """Updates the status and other relevant fields of a task."""
        async with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task["status"] = status
                task["updated_at"] = datetime.now(timezone.utc)
                if result is not None:
                    task["result"] = result
                if error is not None:
                    task["error"] = error
                return True
            return False

# Singleton instance to be used across the application
task_manager = TaskManager() 