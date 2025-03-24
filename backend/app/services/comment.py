"""
Service for social media comments stored in MongoDB.

This module provides service functions that use the CommentRepository to perform
operations on social media comments in the MongoDB database.
"""

from typing import Dict, List, Optional, Any

import motor.motor_asyncio
from fastapi import Depends

from app.db.connections import get_mongodb
from app.services.repositories.comment_repository import CommentRepository


# Create a singleton instance of the repository
comment_repository = CommentRepository()


async def create_comment(*, comment_data: Dict[str, Any]) -> str:
    """
    Create a new social media comment.
    
    Args:
        comment_data: Dictionary with comment data following the SocialMediaComment schema
        
    Returns:
        The ID of the created comment
    """
    return await comment_repository.create(comment_data=comment_data)


async def get_comment(*, comment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a comment by ID.
    
    Args:
        comment_id: The ID of the comment to retrieve
        
    Returns:
        The comment data if found, None otherwise
    """
    return await comment_repository.get(comment_id=comment_id)


async def get_comment_by_platform_id(*, platform: str, platform_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a comment by platform and platform-specific ID.
    
    Args:
        platform: The social media platform (e.g., twitter, facebook)
        platform_id: The platform-specific ID of the comment
        
    Returns:
        The comment data if found, None otherwise
    """
    return await comment_repository.get_by_platform_id(platform=platform, platform_id=platform_id)


async def list_comments(
    *,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "metadata.created_at",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get a list of comments with pagination and sorting options.
    
    Args:
        skip: Number of comments to skip
        limit: Maximum number of comments to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of comments
    """
    return await comment_repository.list(
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def get_comments_by_post(
    *,
    post_id: str,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "metadata.created_at",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get comments for a specific post.
    
    Args:
        post_id: The ID of the post
        skip: Number of comments to skip
        limit: Maximum number of comments to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of comments for the specified post
    """
    return await comment_repository.find_by_post_id(
        post_id=post_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def get_comments_by_user(
    *,
    user_id: str,
    platform: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "metadata.created_at",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get comments by a specific user.
    
    Args:
        user_id: The platform-specific user ID
        platform: Optional platform to filter by
        skip: Number of comments to skip
        limit: Maximum number of comments to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of comments by the specified user
    """
    return await comment_repository.find_by_user_id(
        user_id=user_id,
        platform=platform,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def get_comments_by_sentiment(
    *,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    post_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "analysis.sentiment_score",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get comments by sentiment score range.
    
    Args:
        min_score: Minimum sentiment score (inclusive)
        max_score: Maximum sentiment score (inclusive)
        post_id: Optional post ID to filter by
        skip: Number of comments to skip
        limit: Maximum number of comments to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of comments with sentiment scores in the specified range
    """
    return await comment_repository.find_by_sentiment(
        min_score=min_score,
        max_score=max_score,
        post_id=post_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def get_toxic_comments(
    *,
    post_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "metadata.created_at",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Get toxic comments.
    
    Args:
        post_id: Optional post ID to filter by
        skip: Number of comments to skip
        limit: Maximum number of comments to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of toxic comments
    """
    return await comment_repository.find_by_toxicity(
        is_toxic=True,
        post_id=post_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def search_comments_by_content(
    *,
    text: str,
    post_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "score",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Search comments by content text.
    
    Args:
        text: Text to search for in comment content
        post_id: Optional post ID to filter by
        skip: Number of comments to skip
        limit: Maximum number of comments to return
        sort_by: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
        
    Returns:
        List of comments matching the search text
    """
    return await comment_repository.search_by_content(
        text=text,
        post_id=post_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


async def update_comment_engagement(
    *,
    comment_id: str,
    metrics: Dict[str, Any]
) -> bool:
    """
    Update engagement metrics for a comment.
    
    Args:
        comment_id: The ID of the comment to update
        metrics: Dictionary of engagement metrics to update
        
    Returns:
        True if the update was successful, False otherwise
    """
    return await comment_repository.update_engagement_metrics(
        comment_id=comment_id,
        metrics=metrics
    )


async def update_comment_analysis(
    *,
    comment_id: str,
    analysis: Dict[str, Any]
) -> bool:
    """
    Update analysis results for a comment.
    
    Args:
        comment_id: The ID of the comment to update
        analysis: Dictionary of analysis results to update
        
    Returns:
        True if the update was successful, False otherwise
    """
    return await comment_repository.update_analysis_results(
        comment_id=comment_id,
        analysis=analysis
    )


async def update_comment_vector_id(
    *,
    comment_id: str,
    vector_id: str
) -> bool:
    """
    Update vector database reference ID for a comment.
    
    Args:
        comment_id: The ID of the comment to update
        vector_id: The vector database reference ID
        
    Returns:
        True if the update was successful, False otherwise
    """
    return await comment_repository.update_vector_id(
        comment_id=comment_id,
        vector_id=vector_id
    )


async def update_comment(
    *,
    comment_id: str,
    update_data: Dict[str, Any]
) -> bool:
    """
    Update a comment with new data.
    
    Args:
        comment_id: The ID of the comment to update
        update_data: Dictionary with fields to update
        
    Returns:
        True if the update was successful, False otherwise
    """
    return await comment_repository.update(
        comment_id=comment_id,
        update_data=update_data
    )


async def delete_comment(*, comment_id: str) -> bool:
    """
    Delete a comment.
    
    Args:
        comment_id: The ID of the comment to delete
        
    Returns:
        True if the deletion was successful, False otherwise
    """
    return await comment_repository.delete(comment_id=comment_id)


async def count_comments(*, query: Dict[str, Any] = None) -> int:
    """
    Count comments matching a query.
    
    Args:
        query: Query dictionary to filter comments
        
    Returns:
        Number of comments matching the query
    """
    return await comment_repository.count(query=query) 