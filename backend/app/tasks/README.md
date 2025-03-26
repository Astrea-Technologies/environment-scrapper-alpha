# Task Processing System (MVP Version)

This module provides a simplified task processing system for the Political Social Media Analysis Platform. It serves as a replacement for a full Celery/Redis implementation in the MVP version, with a focus on simplicity and easy integration with FastAPI.

## Key Components

### 1. Task Manager

The `TaskManager` class (`task_manager.py`) is the central component of the system, responsible for:

- Creating and tracking tasks
- Executing tasks synchronously or asynchronously using FastAPI's `BackgroundTasks`
- Maintaining task status (pending, running, completed, failed)
- Providing error handling and logging
- Offering convenience methods for common task types

### 2. Task Types

The `task_types.py` module defines:

- Common enums like `TaskPriority` and `TaskStatus`
- Type definitions for task results
- Base function signatures for different types of operations:
  - `collect_platform_data()`: For platform-specific data collection
  - `analyze_content()`: For content analysis (sentiment, topics, etc.)
  - `analyze_relationships()`: For entity relationship analysis
  - `generate_report()`: For report generation

### 3. API Integration

The task processing system integrates with FastAPI through:

- Dependency injection (`TaskManagerDep` in `app/api/deps.py`)
- API endpoints in `app/api/api_v1/endpoints/tasks.py` 

## Usage

### Creating and Running Tasks

```python
from fastapi import Depends, BackgroundTasks
from app.api.deps import TaskManagerDep

@app.post("/example")
async def example_endpoint(
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
):
    # Create and schedule a task
    task_id = task_manager.create_task(
        func=some_async_function,
        args=[arg1, arg2],
        kwargs={"key": "value"}
    )
    
    # Execute asynchronously
    task_manager.execute_task_async(task_id, background_tasks)
    
    # Or execute synchronously
    result = await task_manager.execute_task_sync(task_id)
    
    return {"task_id": task_id}
```

### Using Convenience Methods

```python
# Data collection
task_id = task_manager.schedule_data_collection(
    platform="twitter",
    entity_ids=["id1", "id2"],
    background_tasks=background_tasks
)

# Content analysis
task_id = task_manager.schedule_content_analysis(
    content_ids=["content1", "content2"],
    analysis_types=["sentiment", "topics"],
    background_tasks=background_tasks
)
```

### Checking Task Status

```python
# Get status of a specific task
status = task_manager.get_task_status(task_id)

# Get all tasks
tasks = task_manager.get_all_tasks()
```

## Future Migration to Celery

This implementation is designed for easy future migration to a full Celery/Redis infrastructure:

1. The task function signatures are compatible with Celery task definitions
2. The status tracking aligns with Celery's task states
3. The interface is abstracted to make replacement straightforward

When migrating to Celery:
- Update the implementation of `TaskManager` to use Celery under the hood
- Maintain the same interface for backward compatibility
- Add additional Celery-specific features as needed 