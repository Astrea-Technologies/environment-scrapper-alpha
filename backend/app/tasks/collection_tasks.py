"""
Collection Tasks

This module provides task functions for social media data collection
using the platform-specific collectors from the APIFY API.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.processing.collection.factory import CollectorFactory
from app.tasks.task_types import TaskResult

logger = logging.getLogger(__name__)


async def scrape_account_posts(
    account_id: Union[UUID, str],
    platform: str,
    count: Optional[int] = None,
    since_date: Optional[datetime] = None,
    **kwargs
) -> TaskResult:
    """
    Task to scrape posts from a social media account.
    
    Args:
        account_id: UUID of the social media account to collect from
        platform: Social media platform (twitter, facebook, instagram)
        count: Maximum number of posts to collect
        since_date: Only collect posts after this date
        **kwargs: Additional platform-specific parameters
        
    Returns:
        TaskResult containing collected post IDs or error information
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting post collection task for {platform} account {account_id}")
    
    try:
        # Get the appropriate collector for the platform
        collector = CollectorFactory.get_collector(platform)
        
        # Collect posts
        post_ids = await collector.collect_posts(
            account_id=account_id,
            count=count,
            since_date=since_date
        )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Completed post collection task for {platform} account {account_id}, collected {len(post_ids)} posts in {duration:.2f} seconds")
        
        return {
            "success": True,
            "data": {
                "platform": platform,
                "account_id": str(account_id),
                "post_count": len(post_ids),
                "post_ids": post_ids
            },
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        }
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        error_message = f"Error collecting posts for {platform} account {account_id}: {str(e)}"
        
        logger.error(error_message, exc_info=True)
        
        return {
            "success": False,
            "error": error_message,
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        }


async def scrape_post_comments(
    post_id: str,
    platform: str,
    count: Optional[int] = None,
    **kwargs
) -> TaskResult:
    """
    Task to scrape comments for a social media post.
    
    Args:
        post_id: MongoDB ID of the post to collect comments for
        platform: Social media platform (twitter, facebook, instagram)
        count: Maximum number of comments to collect
        **kwargs: Additional platform-specific parameters
        
    Returns:
        TaskResult containing collected comment IDs or error information
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting comment collection task for {platform} post {post_id}")
    
    try:
        # Get the appropriate collector for the platform
        collector = CollectorFactory.get_collector(platform)
        
        # Collect comments
        comment_ids = await collector.collect_comments(
            post_id=post_id,
            count=count
        )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Completed comment collection task for {platform} post {post_id}, collected {len(comment_ids)} comments in {duration:.2f} seconds")
        
        return {
            "success": True,
            "data": {
                "platform": platform,
                "post_id": post_id,
                "comment_count": len(comment_ids),
                "comment_ids": comment_ids
            },
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        }
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        error_message = f"Error collecting comments for {platform} post {post_id}: {str(e)}"
        
        logger.error(error_message, exc_info=True)
        
        return {
            "success": False,
            "error": error_message,
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        }


async def update_account_profile(
    account_id: Union[UUID, str],
    platform: str,
    **kwargs
) -> TaskResult:
    """
    Task to update profile information for a social media account.
    
    Args:
        account_id: UUID of the social media account to update
        platform: Social media platform (twitter, facebook, instagram)
        **kwargs: Additional platform-specific parameters
        
    Returns:
        TaskResult containing updated profile data or error information
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting profile update task for {platform} account {account_id}")
    
    try:
        # Get the appropriate collector for the platform
        collector = CollectorFactory.get_collector(platform)
        
        # Update profile
        profile_data = await collector.collect_profile(account_id=account_id)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Completed profile update task for {platform} account {account_id} in {duration:.2f} seconds")
        
        return {
            "success": True,
            "data": {
                "platform": platform,
                "account_id": str(account_id),
                "profile_data": profile_data
            },
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        }
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        error_message = f"Error updating profile for {platform} account {account_id}: {str(e)}"
        
        logger.error(error_message, exc_info=True)
        
        return {
            "success": False,
            "error": error_message,
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        }


async def update_account_metrics(
    account_id: Union[UUID, str],
    platform: str,
    **kwargs
) -> TaskResult:
    """
    Task to update engagement metrics for a social media account.
    
    Args:
        account_id: UUID of the social media account to update
        platform: Social media platform (twitter, facebook, instagram)
        **kwargs: Additional platform-specific parameters
        
    Returns:
        TaskResult containing updated metrics data or error information
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting metrics update task for {platform} account {account_id}")
    
    try:
        # Get the appropriate collector for the platform
        collector = CollectorFactory.get_collector(platform)
        
        # Update metrics
        metrics_data = await collector.update_metrics(account_id=account_id)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Completed metrics update task for {platform} account {account_id} in {duration:.2f} seconds")
        
        return {
            "success": True,
            "data": {
                "platform": platform,
                "account_id": str(account_id),
                "metrics_data": metrics_data
            },
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        }
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        error_message = f"Error updating metrics for {platform} account {account_id}: {str(e)}"
        
        logger.error(error_message, exc_info=True)
        
        return {
            "success": False,
            "error": error_message,
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        }


async def batch_scrape_accounts(
    account_ids: List[Union[UUID, str]],
    platform: str,
    count_per_account: Optional[int] = None,
    since_date: Optional[datetime] = None,
    **kwargs
) -> TaskResult:
    """
    Task to batch scrape posts from multiple social media accounts.
    
    Args:
        account_ids: List of UUIDs of social media accounts to collect from
        platform: Social media platform (twitter, facebook, instagram)
        count_per_account: Maximum number of posts to collect per account
        since_date: Only collect posts after this date
        **kwargs: Additional platform-specific parameters
        
    Returns:
        TaskResult containing collected post IDs by account or error information
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting batch post collection task for {len(account_ids)} {platform} accounts")
    
    try:
        # Get the appropriate collector for the platform
        collector = CollectorFactory.get_collector(platform)
        
        results = {}
        for account_id in account_ids:
            try:
                # Collect posts for this account
                post_ids = await collector.collect_posts(
                    account_id=account_id,
                    count=count_per_account,
                    since_date=since_date
                )
                
                # Store results
                results[str(account_id)] = {
                    "success": True,
                    "post_count": len(post_ids),
                    "post_ids": post_ids
                }
                
            except Exception as e:
                # Record failure for this account but continue with others
                error_message = f"Error collecting posts for {platform} account {account_id}: {str(e)}"
                logger.error(error_message)
                
                results[str(account_id)] = {
                    "success": False,
                    "error": error_message
                }
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Count successes and failures
        success_count = sum(1 for r in results.values() if r.get("success", False))
        post_count = sum(r.get("post_count", 0) for r in results.values() if r.get("success", False))
        
        logger.info(
            f"Completed batch post collection task: {success_count}/{len(account_ids)} accounts succeeded, "
            f"collected {post_count} posts in {duration:.2f} seconds"
        )
        
        return {
            "success": True,
            "data": {
                "platform": platform,
                "account_count": len(account_ids),
                "success_count": success_count,
                "post_count": post_count,
                "results_by_account": results
            },
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        }
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        error_message = f"Error in batch collection task: {str(e)}"
        
        logger.error(error_message, exc_info=True)
        
        return {
            "success": False,
            "error": error_message,
            "started_at": start_time,
            "completed_at": end_time,
            "duration_seconds": duration
        } 