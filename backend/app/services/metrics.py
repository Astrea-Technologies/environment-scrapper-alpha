"""
Service for social media metrics stored in MongoDB.

This module provides service functions that use the MetricsRepository to perform
operations on social media metrics and aggregations in the MongoDB database.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import motor.motor_asyncio
from fastapi import Depends

from app.db.connections import get_mongodb
from app.services.repositories.metrics_repository import MetricsRepository


# Create a singleton instance of the repository
metrics_repository = MetricsRepository()


async def aggregate_engagement_by_platform(
    *,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    account_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Aggregate engagement metrics by social media platform.
    
    Args:
        start_date: Start date for the aggregation period
        end_date: End date for the aggregation period
        account_ids: Optional list of account IDs to filter by
        
    Returns:
        List of platform aggregations with engagement metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.aggregate_by_platform(
        start_date=start_date,
        end_date=end_date,
        account_ids=account_ids
    )


async def aggregate_engagement_by_account(
    *,
    platform: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Aggregate engagement metrics by social media account.
    
    Args:
        platform: Optional platform to filter by
        start_date: Start date for the aggregation period
        end_date: End date for the aggregation period
        top_n: Number of top accounts to return
        
    Returns:
        List of account aggregations with engagement metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.aggregate_by_account(
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        top_n=top_n
    )


async def aggregate_engagement_over_time(
    *,
    platform: Optional[str] = None,
    account_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    interval: str = "day"
) -> List[Dict[str, Any]]:
    """
    Aggregate engagement metrics over time with specified interval.
    
    Args:
        platform: Optional platform to filter by
        account_id: Optional account ID to filter by
        start_date: Start date for the aggregation period
        end_date: End date for the aggregation period
        interval: Time interval for aggregation (day, week, month)
        
    Returns:
        List of time-based aggregations with engagement metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.aggregate_over_time(
        platform=platform,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        interval=interval
    )


async def aggregate_sentiment_by_platform(
    *,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    account_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Aggregate sentiment metrics by social media platform.
    
    Args:
        start_date: Start date for the aggregation period
        end_date: End date for the aggregation period
        account_ids: Optional list of account IDs to filter by
        
    Returns:
        List of platform aggregations with sentiment metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.aggregate_sentiment_by_platform(
        start_date=start_date,
        end_date=end_date,
        account_ids=account_ids
    )


async def aggregate_sentiment_by_account(
    *,
    platform: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Aggregate sentiment metrics by social media account.
    
    Args:
        platform: Optional platform to filter by
        start_date: Start date for the aggregation period
        end_date: End date for the aggregation period
        top_n: Number of top accounts to return
        
    Returns:
        List of account aggregations with sentiment metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.aggregate_sentiment_by_account(
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        top_n=top_n
    )


async def aggregate_sentiment_over_time(
    *,
    platform: Optional[str] = None,
    account_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    interval: str = "day"
) -> List[Dict[str, Any]]:
    """
    Aggregate sentiment metrics over time with specified interval.
    
    Args:
        platform: Optional platform to filter by
        account_id: Optional account ID to filter by
        start_date: Start date for the aggregation period
        end_date: End date for the aggregation period
        interval: Time interval for aggregation (day, week, month)
        
    Returns:
        List of time-based aggregations with sentiment metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.aggregate_sentiment_over_time(
        platform=platform,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        interval=interval
    )


async def get_top_posts(
    *,
    platform: Optional[str] = None,
    account_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metric: str = "engagement",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get top posts by a specific metric.
    
    Args:
        platform: Optional platform to filter by
        account_id: Optional account ID to filter by
        start_date: Start date for the period
        end_date: End date for the period
        metric: Metric to rank posts by (engagement, likes, shares, comments)
        limit: Maximum number of posts to return
        
    Returns:
        List of top posts with relevant metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.get_top_posts(
        platform=platform,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        metric=metric,
        limit=limit
    )


async def get_account_growth(
    *,
    account_id: str,
    platform: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    interval: str = "day"
) -> List[Dict[str, Any]]:
    """
    Get follower/subscriber growth data for an account over time.
    
    Args:
        account_id: The account ID to analyze
        platform: Optional platform to filter by
        start_date: Start date for the period
        end_date: End date for the period
        interval: Time interval for aggregation (day, week, month)
        
    Returns:
        List of time-based follower growth data points
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.get_account_growth(
        account_id=account_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        interval=interval
    )


async def calculate_engagement_rate(
    *,
    account_id: str,
    platform: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Calculate engagement rate for an account.
    
    Args:
        account_id: The account ID to analyze
        platform: Optional platform to filter by
        start_date: Start date for the period
        end_date: End date for the period
        
    Returns:
        Dictionary with engagement rate metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.calculate_engagement_rate(
        account_id=account_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date
    )


async def compare_accounts(
    *,
    account_ids: List[str],
    platform: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Compare metrics between multiple accounts.
    
    Args:
        account_ids: List of account IDs to compare
        platform: Optional platform to filter by
        start_date: Start date for the period
        end_date: End date for the period
        metrics: Optional list of metrics to include in comparison
        
    Returns:
        Dictionary with comparison data for the specified accounts
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    if not metrics:
        metrics = ["followers", "posts", "engagement", "sentiment"]
    
    return await metrics_repository.compare_accounts(
        account_ids=account_ids,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        metrics=metrics
    )


async def get_topic_distribution(
    *,
    account_id: Optional[str] = None,
    platform: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get distribution of topics/themes in content.
    
    Args:
        account_id: Optional account ID to filter by
        platform: Optional platform to filter by
        start_date: Start date for the period
        end_date: End date for the period
        limit: Maximum number of topics to return
        
    Returns:
        List of topics with frequency and engagement metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.get_topic_distribution(
        account_id=account_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )


async def get_content_performance_by_type(
    *,
    account_id: Optional[str] = None,
    platform: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Get performance metrics grouped by content type.
    
    Args:
        account_id: Optional account ID to filter by
        platform: Optional platform to filter by
        start_date: Start date for the period
        end_date: End date for the period
        
    Returns:
        List of content types with performance metrics
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    return await metrics_repository.get_performance_by_content_type(
        account_id=account_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date
    ) 