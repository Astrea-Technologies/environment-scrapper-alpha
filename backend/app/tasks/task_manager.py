"""
MVP Task Management System

This module provides a simple task management system for the MVP version of the application.
IMPORTANT: This implementation intentionally does NOT use Celery, Redis, RabbitMQ or any 
related message broker infrastructure for the MVP.

Instead, it uses FastAPI's built-in background tasks feature for basic asynchronous processing.
Tasks are stored in memory and will be lost if the server restarts.

The design allows for easy migration to Celery in future versions.
"""

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, cast
from datetime import datetime
import asyncio
import traceback
from uuid import UUID

from fastapi import BackgroundTasks

from app.tasks.task_types import TaskPriority, TaskResult, TaskStatus

logger = logging.getLogger(__name__)

class Task:
    """Represents a single task in the task processing system."""
    
    def __init__(
        self,
        task_id: str,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
    ):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.result: Optional[TaskResult] = None
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None

    async def execute(self) -> TaskResult:
        """Execute the task and return the result."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        
        try:
            # Execute the task function
            result = await self.func(*self.args, **self.kwargs)
            self.status = TaskStatus.COMPLETED
            self.result = result
            
        except Exception as e:
            self.status = TaskStatus.FAILED
            error_message = f"Task {self.task_id} failed: {str(e)}"
            tb = traceback.format_exc()
            logger.error(f"{error_message}\n{tb}")
            
            self.error = error_message
            self.result = {
                "success": False,
                "error": error_message,
                "started_at": self.started_at,
                "completed_at": datetime.now(),
                "duration_seconds": (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
            }
            
        self.completed_at = datetime.now()
        return cast(TaskResult, self.result)


class TaskManager:
    """
    Task manager for the MVP version of the application.
    
    Handles both synchronous and background task execution,
    with basic task status tracking and error handling.
    
    Note: This is an in-memory implementation. Tasks will be lost if the server restarts.
          No persistent storage, distributed processing, or scheduled tasks are supported.
    """
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.logger = logger

    def create_task(
        self,
        func: Callable,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Create a new task to be executed.
        
        Args:
            func: Async function to be executed
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            priority: Task priority level
            task_id: Optional custom task ID (UUID will be generated if not provided)
            
        Returns:
            task_id: Unique identifier for the created task
        """
        args = args or []
        kwargs = kwargs or {}
        task_id = task_id or str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
        )
        
        self.tasks[task_id] = task
        self.logger.info(f"Created task {task_id} with priority {priority.name}")
        
        return task_id

    async def execute_task_sync(self, task_id: str) -> TaskResult:
        """
        Execute a task synchronously (blocking).
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            TaskResult: Result of the task execution
            
        Raises:
            ValueError: If the task ID is not found
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        self.logger.info(f"Executing task {task_id} synchronously")
        return await task.execute()

    def execute_task_async(self, task_id: str, background_tasks: BackgroundTasks) -> str:
        """
        Add a task to FastAPI's BackgroundTasks for asynchronous execution.
        
        Args:
            task_id: ID of the task to execute
            background_tasks: FastAPI BackgroundTasks instance
            
        Returns:
            task_id: The ID of the scheduled task
            
        Raises:
            ValueError: If the task ID is not found
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Add the task execution to FastAPI's background tasks
        background_tasks.add_task(self._execute_background_task, task_id)
        
        self.logger.info(f"Scheduled task {task_id} for background execution")
        return task_id

    async def _execute_background_task(self, task_id: str) -> None:
        """
        Internal method to execute a task in the background.
        
        Args:
            task_id: ID of the task to execute
        """
        task = self.tasks.get(task_id)
        if not task:
            self.logger.error(f"Background task {task_id} not found")
            return
        
        try:
            await task.execute()
        except Exception as e:
            self.logger.error(f"Unhandled error in background task {task_id}: {str(e)}")
            
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status of a task.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            Dict with task status information
            
        Raises:
            ValueError: If the task ID is not found
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "priority": task.priority.name,
            "error": task.error,
            "result": task.result["data"] if task.result and "data" in task.result else None
        }

    def get_all_tasks(
        self, 
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get a list of all tasks, optionally filtered by status.
        
        Args:
            status: Optional filter by task status
            limit: Maximum number of tasks to return
            offset: Offset for pagination
            
        Returns:
            List of task status dictionaries
        """
        tasks = list(self.tasks.values())
        
        # Filter by status if provided
        if status:
            tasks = [task for task in tasks if task.status == status]
            
        # Sort by created_at (newest first)
        tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)
        
        # Apply pagination
        tasks = tasks[offset:offset+limit]
        
        return [
            {
                "task_id": task.task_id,
                "status": task.status.value,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "priority": task.priority.name,
                "error": task.error,
            }
            for task in tasks
        ]

    def clear_completed_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clear completed or failed tasks older than the specified age.
        
        Args:
            max_age_hours: Maximum age in hours for tasks to be retained
            
        Returns:
            Number of tasks removed
        """
        current_time = datetime.now()
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                completed_at = task.completed_at or task.created_at
                age = (current_time - completed_at).total_seconds() / 3600
                
                if age > max_age_hours:
                    tasks_to_remove.append(task_id)
        
        # Remove the tasks
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            
        return len(tasks_to_remove)

    # Convenience methods for common task types
    
    def schedule_data_collection(
        self,
        platform: str,
        entity_ids: List[str],
        background_tasks: BackgroundTasks,
        **kwargs
    ) -> str:
        """
        Schedule a data collection task.
        
        Args:
            platform: Name of the social media platform
            entity_ids: List of entity IDs to collect data for
            background_tasks: FastAPI BackgroundTasks instance
            **kwargs: Additional parameters for collect_platform_data
            
        Returns:
            task_id: ID of the scheduled task
        """
        from app.tasks.task_types import collect_platform_data
        
        task_id = self.create_task(
            func=collect_platform_data,
            args=[platform, entity_ids],
            kwargs=kwargs,
            priority=TaskPriority.HIGH
        )
        
        return self.execute_task_async(task_id, background_tasks)
    
    def schedule_content_analysis(
        self,
        content_ids: List[str],
        analysis_types: List[str],
        background_tasks: BackgroundTasks,
        **kwargs
    ) -> str:
        """
        Schedule a content analysis task.
        
        Args:
            content_ids: List of content IDs to analyze
            analysis_types: Types of analysis to perform
            background_tasks: FastAPI BackgroundTasks instance
            **kwargs: Additional parameters for analyze_content
            
        Returns:
            task_id: ID of the scheduled task
        """
        from app.tasks.task_types import analyze_content
        
        task_id = self.create_task(
            func=analyze_content,
            args=[content_ids],
            kwargs={"analysis_types": analysis_types, **kwargs},
            priority=TaskPriority.MEDIUM
        )
        
        return self.execute_task_async(task_id, background_tasks)
    
    def schedule_relationship_analysis(
        self,
        entity_ids: List[str],
        background_tasks: BackgroundTasks,
        **kwargs
    ) -> str:
        """
        Schedule a relationship analysis task.
        
        Args:
            entity_ids: List of entity IDs to analyze relationships for
            background_tasks: FastAPI BackgroundTasks instance
            **kwargs: Additional parameters for analyze_relationships
            
        Returns:
            task_id: ID of the scheduled task
        """
        from app.tasks.task_types import analyze_relationships
        
        task_id = self.create_task(
            func=analyze_relationships,
            args=[entity_ids],
            kwargs=kwargs,
            priority=TaskPriority.LOW
        )
        
        return self.execute_task_async(task_id, background_tasks)
    
    def schedule_report_generation(
        self,
        report_type: str,
        background_tasks: BackgroundTasks,
        **kwargs
    ) -> str:
        """
        Schedule a report generation task.
        
        Args:
            report_type: Type of report to generate
            background_tasks: FastAPI BackgroundTasks instance
            **kwargs: Additional parameters for generate_report
            
        Returns:
            task_id: ID of the scheduled task
        """
        from app.tasks.task_types import generate_report
        
        task_id = self.create_task(
            func=generate_report,
            args=[report_type],
            kwargs=kwargs,
            priority=TaskPriority.LOW
        )
        
        return self.execute_task_async(task_id, background_tasks)

# Global TaskManager instance
_task_manager: Optional[TaskManager] = None

def get_task_manager() -> TaskManager:
    """
    Get the global TaskManager instance.
    Creates a new instance if one doesn't exist yet.
    
    Returns:
        TaskManager: Global task manager instance
    """
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager 