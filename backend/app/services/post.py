"""
Service for social media posts stored in MongoDB.

This module provides service functions that use the PostRepository to perform
operations on social media posts in the MongoDB database.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

import motor.motor_asyncio
from fastapi import Depends

from app.db.connections import get_mongodb
from app.services.repositories.post_repository import PostRepository


# Create a singleton instance of the repository
post_repository = PostRepository()


async def create_post(*, post_data: Dict[str, Any]) -> str:
    """
    Create a new social media post.
    
    Args:
        post_data: Dictionary with post data following the SocialMediaPost schema
        
    Returns:
        The ID of the created post
    """
    return await post_repository.create(post_data=post_data)


async def get_post(*, post_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a post by ID.
    
    Args:
        post_id: The ID of the post to retrieve
        
    Returns:
        The post data if found, None otherwise
    """
    return await post_repository.get(post_id=post_id)


async def get_post_by_platform_id(*, platform: str, platform_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a post by platform and platform-specific ID.
    
    Args:
        platform: The social media platform (e.g., twitter, facebook)
        platform_id: The platform-specific ID of the post
        
    Returns:
        The post data if found, None otherwise
    """
    return await post_repository.get_by_platform_id(platform=platform, platform_id=platform_id)


async def list_posts(
    *,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "metadata.created_at",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get a list of posts with pagination and sorting options.
    
    Args:
        skip: Number of posts to skip
        limit: Maximum number of posts to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of posts
    """
    return await post_repository.list(
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def get_posts_by_account(
    *,
    account_id: Union[UUID, str],
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "metadata.created_at",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get posts by account ID.
    
    Args:
        account_id: The UUID of the social media account
        skip: Number of posts to skip
        limit: Maximum number of posts to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of posts for the specified account
    """
    return await post_repository.find_by_account(
        account_id=account_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def get_posts_by_platform(
    *,
    platform: str,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "metadata.created_at",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get posts by platform.
    
    Args:
        platform: The social media platform (e.g., twitter, facebook)
        skip: Number of posts to skip
        limit: Maximum number of posts to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of posts for the specified platform
    """
    return await post_repository.find_by_platform(
        platform=platform,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def get_posts_by_date_range(
    *,
    start_date: datetime,
    end_date: datetime,
    account_id: Optional[Union[UUID, str]] = None,
    platform: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "metadata.created_at",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get posts within a date range with optional filtering.
    
    Args:
        start_date: Start date for the range
        end_date: End date for the range
        account_id: Optional account ID to filter by
        platform: Optional platform to filter by
        skip: Number of posts to skip
        limit: Maximum number of posts to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of posts within the date range
    """
    return await post_repository.find_by_date_range(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        platform=platform,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def search_posts_by_content(
    *,
    text: str,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "score",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Search posts by content text.
    
    Args:
        text: Text to search for in post content
        skip: Number of posts to skip
        limit: Maximum number of posts to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of posts matching the search text
    """
    return await post_repository.search_by_content(
        text=text,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def get_posts_by_engagement(
    *,
    metric: str,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    platform: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get posts by engagement metric value range.
    
    Args:
        metric: The engagement metric to filter by
        min_value: Minimum value for the metric
        max_value: Maximum value for the metric
        platform: Optional platform to filter by
        skip: Number of posts to skip
        limit: Maximum number of posts to return
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of posts with engagement metrics in the specified range
    """
    return await post_repository.find_by_engagement_metric(
        metric=metric,
        min_value=min_value,
        max_value=max_value,
        platform=platform,
        skip=skip,
        limit=limit,
        sort_direction=sort_direction
    )


async def update_post_engagement(
    *,
    post_id: str,
    metrics: Dict[str, Any]
) -> bool:
    """
    Update engagement metrics for a post.
    
    Args:
        post_id: The ID of the post to update
        metrics: Dictionary of engagement metrics to update
        
    Returns:
        True if the update was successful, False otherwise
    """
    return await post_repository.update_engagement_metrics(
        post_id=post_id,
        metrics=metrics
    )


async def update_post_analysis(
    *,
    post_id: str,
    analysis: Dict[str, Any]
) -> bool:
    """
    Update analysis results for a post.
    
    Args:
        post_id: The ID of the post to update
        analysis: Dictionary of analysis results to update
        
    Returns:
        True if the update was successful, False otherwise
    """
    return await post_repository.update_analysis_results(
        post_id=post_id,
        analysis=analysis
    )


async def update_post_vector_id(
    *,
    post_id: str,
    vector_id: str
) -> bool:
    """
    Update vector database reference ID for a post.
    
    Args:
        post_id: The ID of the post to update
        vector_id: The vector database reference ID
        
    Returns:
        True if the update was successful, False otherwise
    """
    return await post_repository.update_vector_id(
        post_id=post_id,
        vector_id=vector_id
    )


async def update_post(
    *,
    post_id: str,
    update_data: Dict[str, Any]
) -> bool:
    """
    Update a post with new data.
    
    Args:
        post_id: The ID of the post to update
        update_data: Dictionary with fields to update
        
    Returns:
        True if the update was successful, False otherwise
    """
    return await post_repository.update(
        post_id=post_id,
        update_data=update_data
    )


async def delete_post(*, post_id: str) -> bool:
    """
    Delete a post.
    
    Args:
        post_id: The ID of the post to delete
        
    Returns:
        True if the deletion was successful, False otherwise
    """
    return await post_repository.delete(post_id=post_id)


async def count_posts(*, query: Dict[str, Any] = None) -> int:
    """
    Count posts matching a query.
    
    Args:
        query: Query dictionary to filter posts
        
    Returns:
        Number of posts matching the query
    """
    return await post_repository.count(query=query) 