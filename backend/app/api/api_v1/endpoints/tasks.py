import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from app.tasks.task_manager import task_manager # Singleton instance
from app.tasks.task_types import TaskType

router = APIRouter()

# --- Dummy Task Implementations (Illustrative) ---

async def run_data_collection_task(task_id: str, params: Dict[str, Any]):
    """Example background task implementation with error handling."""
    await task_manager.update_task_status(task_id, status="running")
    try:
        # Simulate work
        print(f"Running task {task_id} (Data Collection) with params: {params}")
        await asyncio.sleep(5) # Simulate I/O bound operation
        account_id = params.get("account_id", "unknown")
        result = {"collected_items": 100, "account_processed": account_id}
        print(f"Task {task_id} completed.")
        await task_manager.update_task_status(task_id, status="completed", result=result)

        # --- Simple Workflow Example --- 
        # If this task succeeds, create a follow-up analysis task
        # Note: For MVP, this new task isn't automatically run by this background task.
        # It's just added to the queue. Another endpoint/mechanism would need to trigger it
        # or the background task itself could add *another* background task.
        follow_up_params = {"source_task_id": task_id, "items_to_analyze": result["collected_items"]}
        follow_up_task_id = await task_manager.create_task(TaskType.CONTENT_ANALYSIS, follow_up_params)
        print(f"Task {task_id} created follow-up task {follow_up_task_id}")
        # --------------------------------

    except Exception as e:
        error_msg = f"Task {task_id} failed: {str(e)}"
        print(error_msg)
        await task_manager.update_task_status(task_id, status="failed", error=error_msg)
    # finally: 
        # Add cleanup logic here if needed

async def run_content_analysis_task(task_id: str, params: Dict[str, Any]):
    """Example background task for content analysis."""
    await task_manager.update_task_status(task_id, status="running")
    try:
        print(f"Running task {task_id} (Content Analysis) with params: {params}")
        await asyncio.sleep(3)
        result = {"analysis_complete": True, "sentiment": "positive", "source": params.get("source_task_id")}
        print(f"Task {task_id} completed.")
        await task_manager.update_task_status(task_id, status="completed", result=result)
    except Exception as e:
        error_msg = f"Task {task_id} failed: {str(e)}"
        print(error_msg)
        await task_manager.update_task_status(task_id, status="failed", error=error_msg)

# Mapping task types to their execution functions
TASK_RUNNERS = {
    TaskType.DATA_COLLECTION: run_data_collection_task,
    TaskType.CONTENT_ANALYSIS: run_content_analysis_task,
    # Add other task types and their runners here
}

# --- API Models --- 

class TaskCreateRequest(BaseModel):
    task_type: TaskType
    params: Dict[str, Any]

class TaskCreateResponse(BaseModel):
    task_id: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    created_at: Any # Use Any for simplicity, ideally datetime
    updated_at: Any # Use Any for simplicity, ideally datetime
    result: Optional[Any] = None
    error: Optional[str] = None

# --- API Endpoints --- 

@router.post("/", response_model=TaskCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_task_endpoint(
    task_request: TaskCreateRequest,
    background_tasks: BackgroundTasks
):
    """Creates a new task and schedules it for background execution."""
    if task_request.task_type not in TASK_RUNNERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task type: {task_request.task_type}"
        )

    task_id = await task_manager.create_task(task_request.task_type, task_request.params)
    
    # Get the appropriate runner function for the task type
    task_runner = TASK_RUNNERS[task_request.task_type]
    
    # Add the task runner to FastAPI's background tasks
    background_tasks.add_task(task_runner, task_id=task_id, params=task_request.params)
    
    return {"task_id": task_id}

@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status_endpoint(task_id: str):
    """Retrieves the status and details of a specific task."""
    task_data = await task_manager.get_task(task_id)
    if not task_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Task with ID {task_id} not found"
        )
    # Convert datetime objects to string for JSON serialization if needed
    # For production, consider a more robust serialization approach
    # task_data["created_at"] = task_data["created_at"].isoformat()
    # task_data["updated_at"] = task_data["updated_at"].isoformat()
    return task_data 