"""
Base Collector for Social Media Platforms

This module provides a base abstract class that defines the interface
and common functionality for all platform-specific social media collectors.
"""

import abc
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.core.config import settings
from app.processing.collection.apify_client import ApifyClient
from app.services.repositories.post_repository import PostRepository
from app.services.repositories.comment_repository import CommentRepository

logger = logging.getLogger(__name__)


class BaseCollector(abc.ABC):
    """
    Abstract base class for social media data collectors.
    
    This class defines the interface for platform-specific collectors 
    and provides common functionality for interacting with APIFY 
    and transforming collected data.
    """
    
    def __init__(
        self,
        apify_client: Optional[ApifyClient] = None,
        post_repository: Optional[PostRepository] = None,
        comment_repository: Optional[CommentRepository] = None
    ):
        """
        Initialize the collector with required dependencies.
        
        Args:
            apify_client: Optional APIFY client (will be created if not provided)
            post_repository: Optional post repository (will be created if not provided)
            comment_repository: Optional comment repository (will be created if not provided)
        """
        self.apify_client = apify_client or ApifyClient()
        self.post_repository = post_repository or PostRepository()
        self.comment_repository = comment_repository or CommentRepository()
        
        # Each platform must set these values
        self.platform_name: str = ""
        self.actor_id: str = ""
        self.default_run_options: Dict[str, Any] = {
            "maxItems": settings.SCRAPING_MAX_POSTS
        }
    
    @property
    def max_items(self) -> int:
        """Get the maximum number of items to collect."""
        return settings.SCRAPING_MAX_POSTS
    
    @property
    def max_comments(self) -> int:
        """Get the maximum number of comments to collect."""
        return settings.SCRAPING_MAX_COMMENTS
    
    def get_default_date_range(
        self,
        days_back: int = None
    ) -> tuple[datetime, datetime]:
        """
        Get default date range for data collection.
        
        Args:
            days_back: Number of days to look back (defaults to SCRAPING_DEFAULT_DAYS_BACK)
            
        Returns:
            Tuple of (start_date, end_date)
        """
        days = days_back or settings.SCRAPING_DEFAULT_DAYS_BACK
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date
    
    def prepare_run_input(self, **kwargs) -> Dict[str, Any]:
        """
        Prepare the run input for APIFY actor.
        
        Base implementation returns default run options,
        platforms should override to add platform-specific options.
        
        Args:
            **kwargs: Additional parameters to include in the run input
            
        Returns:
            Dictionary with run input for APIFY actor
        """
        run_input = self.default_run_options.copy()
        run_input.update(kwargs)
        return run_input
    
    @abc.abstractmethod
    async def collect_posts(
        self,
        account_id: Union[UUID, str],
        count: int = None,
        since_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Collect posts from a social media account.
        
        Args:
            account_id: UUID of the social media account to collect from
            count: Maximum number of posts to collect (defaults to SCRAPING_MAX_POSTS)
            since_date: Only collect posts after this date (defaults to default date range)
            
        Returns:
            List of collected and transformed posts
        """
        pass
    
    @abc.abstractmethod
    async def collect_comments(
        self,
        post_id: str,
        count: int = None
    ) -> List[Dict[str, Any]]:
        """
        Collect comments for a social media post.
        
        Args:
            post_id: MongoDB ID of the post to collect comments for
            count: Maximum number of comments to collect (defaults to SCRAPING_MAX_COMMENTS)
            
        Returns:
            List of collected and transformed comments
        """
        pass
    
    @abc.abstractmethod
    async def collect_profile(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Collect profile information for a social media account.
        
        Args:
            account_id: UUID of the social media account to collect profile for
            
        Returns:
            Dictionary with account profile information
        """
        pass
    
    @abc.abstractmethod
    async def update_metrics(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Update engagement metrics for a social media account.
        
        Args:
            account_id: UUID of the social media account to update metrics for
            
        Returns:
            Dictionary with updated metrics
        """
        pass
    
    @abc.abstractmethod
    def transform_post(self, raw_post: Dict[str, Any], account_id: Union[UUID, str]) -> Dict[str, Any]:
        """
        Transform a raw post from APIFY into the format expected by the repository.
        
        Args:
            raw_post: Raw post data from APIFY
            account_id: UUID of the social media account
            
        Returns:
            Transformed post data
        """
        pass
    
    @abc.abstractmethod
    def transform_comment(self, raw_comment: Dict[str, Any], post_id: str) -> Dict[str, Any]:
        """
        Transform a raw comment from APIFY into the format expected by the repository.
        
        Args:
            raw_comment: Raw comment data from APIFY
            post_id: MongoDB ID of the parent post
            
        Returns:
            Transformed comment data
        """
        pass
    
    @abc.abstractmethod
    def transform_profile(self, raw_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a raw profile from APIFY into the format expected by the repository.
        
        Args:
            raw_profile: Raw profile data from APIFY
            
        Returns:
            Transformed profile data
        """
        pass
    
    async def save_posts(
        self,
        posts: List[Dict[str, Any]],
        account_id: Union[UUID, str]
    ) -> List[str]:
        """
        Save collected posts to the repository.
        
        Args:
            posts: List of raw posts from APIFY
            account_id: UUID of the social media account
            
        Returns:
            List of MongoDB IDs for the saved posts
        """
        post_ids = []
        
        for raw_post in posts:
            try:
                # Check if post already exists
                existing_post = await self.post_repository.get_by_platform_id(
                    platform=self.platform_name,
                    platform_id=raw_post.get("id", "")
                )
                
                if existing_post:
                    # Update engagement metrics
                    post_data = self.transform_post(raw_post, account_id)
                    await self.post_repository.update_engagement_metrics(
                        post_id=str(existing_post["_id"]),
                        metrics=post_data["engagement"]
                    )
                    post_ids.append(str(existing_post["_id"]))
                else:
                    # Create new post
                    post_data = self.transform_post(raw_post, account_id)
                    post_id = await self.post_repository.create(post_data)
                    post_ids.append(post_id)
            
            except Exception as e:
                logger.error(f"Error saving post: {str(e)}", exc_info=True)
        
        return post_ids
    
    async def save_comments(
        self,
        comments: List[Dict[str, Any]],
        post_id: str
    ) -> List[str]:
        """
        Save collected comments to the repository.
        
        Args:
            comments: List of raw comments from APIFY
            post_id: MongoDB ID of the parent post
            
        Returns:
            List of MongoDB IDs for the saved comments
        """
        comment_ids = []
        
        for raw_comment in comments:
            try:
                # Check if comment already exists
                existing_comment = await self.comment_repository.get_by_platform_id(
                    platform=self.platform_name,
                    platform_id=raw_comment.get("id", "")
                )
                
                if existing_comment:
                    # Update engagement metrics
                    comment_data = self.transform_comment(raw_comment, post_id)
                    await self.comment_repository.update_engagement_metrics(
                        comment_id=str(existing_comment["_id"]),
                        metrics=comment_data["engagement"]
                    )
                    comment_ids.append(str(existing_comment["_id"]))
                else:
                    # Create new comment
                    comment_data = self.transform_comment(raw_comment, post_id)
                    comment_id = await self.comment_repository.create(comment_data)
                    comment_ids.append(comment_id)
            
            except Exception as e:
                logger.error(f"Error saving comment: {str(e)}", exc_info=True)
        
        return comment_ids
    
    def extract_hashtags(self, text: str) -> List[str]:
        """
        Extract hashtags from text.
        
        Args:
            text: Text to extract hashtags from
            
        Returns:
            List of hashtags without the # symbol
        """
        if not text:
            return []
        
        hashtags = []
        for word in text.split():
            if word.startswith('#'):
                # Remove the # and any trailing punctuation
                tag = word[1:].strip().rstrip('.,:;!?')
                if tag:
                    hashtags.append(tag)
        
        return hashtags
    
    def extract_mentions(self, text: str) -> List[str]:
        """
        Extract mentions from text.
        
        Args:
            text: Text to extract mentions from
            
        Returns:
            List of mentions without the @ symbol
        """
        if not text:
            return []
        
        mentions = []
        for word in text.split():
            if word.startswith('@'):
                # Remove the @ and any trailing punctuation
                mention = word[1:].strip().rstrip('.,:;!?')
                if mention:
                    mentions.append(mention)
        
        return mentions
    
    def extract_links(self, text: str) -> List[str]:
        """
        Extract links from text (simple implementation).
        
        Args:
            text: Text to extract links from
            
        Returns:
            List of extracted links
        """
        if not text:
            return []
        
        links = []
        for word in text.split():
            if word.startswith(('http://', 'https://')):
                # Remove any trailing punctuation
                link = word.strip().rstrip('.,:;!?')
                if link:
                    links.append(link)
        
        return links 