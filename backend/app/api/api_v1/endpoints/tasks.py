from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import UUID4

from app.api.deps import CurrentUser, TaskManagerDep
from app.tasks.task_types import TaskStatus

router = APIRouter()


@router.post("/data-collection")
async def create_data_collection_task(
    platform: str,
    entity_ids: List[str],
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
    current_user: CurrentUser,
) -> Dict[str, Any]:
    """
    Schedule a data collection task for social media platforms.
    """
    # Only allow superusers to schedule data collection tasks
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    task_id = task_manager.schedule_data_collection(
        platform=platform,
        entity_ids=entity_ids,
        background_tasks=background_tasks,
    )
    
    return {
        "success": True,
        "message": f"Data collection task scheduled for {platform}",
        "task_id": task_id
    }


@router.post("/content-analysis")
async def create_content_analysis_task(
    content_ids: List[str],
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
    current_user: CurrentUser,
    analysis_types: List[str] = Query(default=["sentiment", "topics", "entities"]),
) -> Dict[str, Any]:
    """
    Schedule a content analysis task for collected social media content.
    """
    # Only allow superusers to schedule analysis tasks
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    task_id = task_manager.schedule_content_analysis(
        content_ids=content_ids,
        analysis_types=analysis_types,
        background_tasks=background_tasks,
    )
    
    return {
        "success": True,
        "message": f"Content analysis task scheduled for {len(content_ids)} items",
        "task_id": task_id
    }


@router.post("/relationship-analysis")
async def create_relationship_analysis_task(
    entity_ids: List[str],
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
    current_user: CurrentUser,
    time_period: str = "last_30_days",
) -> Dict[str, Any]:
    """
    Schedule a relationship analysis task between political entities.
    """
    # Only allow superusers to schedule relationship analysis tasks
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    task_id = task_manager.schedule_relationship_analysis(
        entity_ids=entity_ids,
        background_tasks=background_tasks,
        time_period=time_period,
    )
    
    return {
        "success": True,
        "message": f"Relationship analysis task scheduled for {len(entity_ids)} entities",
        "task_id": task_id
    }


@router.post("/report-generation")
async def create_report_generation_task(
    report_type: str,
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
    current_user: CurrentUser,
    entity_ids: Optional[List[str]] = None,
    time_period: str = "last_30_days",
    format: str = "json",
) -> Dict[str, Any]:
    """
    Schedule a report generation task.
    """
    # Only allow superusers to schedule report generation tasks
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    task_id = task_manager.schedule_report_generation(
        report_type=report_type,
        background_tasks=background_tasks,
        entity_ids=entity_ids,
        time_period=time_period,
        format=format,
    )
    
    return {
        "success": True,
        "message": f"{report_type} report generation task scheduled",
        "task_id": task_id
    }


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    task_manager: TaskManagerDep,
    current_user: CurrentUser,
) -> Dict[str, Any]:
    """
    Get the status of a specific task.
    """
    try:
        task_status = task_manager.get_task_status(task_id)
        return {
            "success": True,
            "task": task_status
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/list")
async def list_tasks(
    task_manager: TaskManagerDep,
    current_user: CurrentUser,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List all tasks, optionally filtered by status.
    """
    # Convert string status to enum if provided
    task_status = None
    if status:
        try:
            task_status = TaskStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {', '.join([s.value for s in TaskStatus])}"
            )
    
    tasks = task_manager.get_all_tasks(
        status=task_status,
        limit=limit,
        offset=offset
    )
    
    return {
        "success": True,
        "tasks": tasks,
        "count": len(tasks),
        "total": len(task_manager.tasks)
    } 