"""
Facebook Data Collector

This module provides a collector for Facebook data using APIFY's Facebook Scraper actor.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
from uuid import UUID

from app.core.config import settings
from app.processing.collection.base import BaseCollector
from app.services.repositories.social_media_account import SocialMediaAccountRepository

logger = logging.getLogger(__name__)


class FacebookCollector(BaseCollector):
    """
    Facebook data collector using APIFY's Facebook Scraper actor.
    
    This collector handles collecting posts, comments, and profile information
    from Facebook accounts via APIFY, and transforms the data into the format
    expected by the application's repositories.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the Facebook collector."""
        super().__init__(*args, **kwargs)
        self.platform_name = "facebook"
        self.actor_id = settings.APIFY_FACEBOOK_ACTOR_ID
        self.account_repository = SocialMediaAccountRepository()
        
        # Facebook-specific default options
        self.default_run_options = {
            "maxPosts": settings.SCRAPING_MAX_POSTS,
            "maxPostComments": 0,  # Don't collect comments during post collection
            "maxPostReactions": 1000,  # Collect reaction counts
            "commentsMode": "NONE",  # Don't collect comments during post collection
            "includeNestedComments": False,
            "reactionsMode": "SUMMARY",
            "addMessageTimestamps": True
        }
    
    async def _get_account_info(self, account_id: Union[UUID, str]) -> Dict[str, Any]:
        """
        Get Facebook account information for a given account ID.
        
        Args:
            account_id: UUID of the social media account
            
        Returns:
            Dictionary with account information
            
        Raises:
            ValueError: If the account is not found
        """
        account = await self.account_repository.get(account_id)
        
        if not account:
            raise ValueError(f"Social media account not found: {account_id}")
        
        profile_url = account.url
        handle = account.handle
        
        # We need at least one of these
        if not (profile_url or handle):
            raise ValueError(f"Account {account_id} has no Facebook URL or handle")
        
        return {
            "url": profile_url,
            "handle": handle
        }
    
    async def collect_posts(
        self,
        account_id: Union[UUID, str],
        count: int = None,
        since_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Collect posts from a Facebook account.
        
        Args:
            account_id: UUID of the social media account to collect from
            count: Maximum number of posts to collect (defaults to settings.SCRAPING_MAX_POSTS)
            since_date: Only collect posts after this date (defaults to default date range)
            
        Returns:
            List of MongoDB IDs for the collected posts
        """
        account_info = await self._get_account_info(account_id)
        
        max_count = count or self.max_items
        start_date, _ = self.get_default_date_range() if not since_date else (since_date, datetime.utcnow())
        
        # Determine the best way to identify the page
        profile_url = account_info.get("url")
        profile_name = account_info.get("handle")
        
        # First prefer the full URL, then the handle
        target = profile_url if profile_url else f"https://www.facebook.com/{profile_name}"
        
        logger.info(f"Collecting posts for Facebook account {target} (max: {max_count}, since: {start_date})")
        
        # Configure Facebook scraper input
        run_input = self.prepare_run_input(
            startUrls=[{"url": target}],
            maxPosts=max_count,
            startDate=start_date.strftime("%Y-%m-%d")
        )
        
        # Run actor and get results
        results = await self.apify_client.start_and_wait_for_results(
            actor_id=self.actor_id,
            run_input=run_input,
            limit=max_count
        )
        
        # Filter for posts only
        posts = [item for item in results if item.get("type") == "post"]
        
        logger.info(f"Collected {len(posts)} posts for Facebook account {target}")
        
        # Save posts to MongoDB
        return await self.save_posts(posts, account_id)
    
    async def collect_comments(
        self,
        post_id: str,
        count: int = None
    ) -> List[Dict[str, Any]]:
        """
        Collect comments for a Facebook post.
        
        Args:
            post_id: MongoDB ID of the post to collect comments for
            count: Maximum number of comments to collect (defaults to settings.SCRAPING_MAX_COMMENTS)
            
        Returns:
            List of MongoDB IDs for the collected comments
        """
        post = await self.post_repository.get(post_id)
        
        if not post:
            raise ValueError(f"Post not found: {post_id}")
        
        fb_post_id = post.get("platform_id")
        if not fb_post_id:
            raise ValueError(f"Invalid post platform ID for {post_id}")
        
        max_count = count or self.max_comments
        
        logger.info(f"Collecting comments for Facebook post {fb_post_id} (max: {max_count})")
        
        # For Facebook, we need the post URL
        post_url = f"https://www.facebook.com/permalink.php?id={fb_post_id}"
        if "links" in post.get("content", {}) and post["content"]["links"]:
            post_url = post["content"]["links"][0]  # Use the first link if available
        
        # Configure Facebook scraper for comments
        run_input = self.prepare_run_input(
            startUrls=[{"url": post_url}],
            maxPosts=1,  # Just get the original post
            maxPostComments=max_count,
            maxCommentReplies=10,
            commentsMode="DETAILED",
            includeNestedComments=True
        )
        
        # Run actor and get results
        results = await self.apify_client.start_and_wait_for_results(
            actor_id=self.actor_id,
            run_input=run_input
        )
        
        # Extract comments from results
        comments = []
        for item in results:
            if item.get("type") == "post" and "comments" in item:
                comments.extend(item.get("comments", []))
        
        logger.info(f"Collected {len(comments)} comments for Facebook post {fb_post_id}")
        
        # Save comments to MongoDB
        return await self.save_comments(comments, post_id)
    
    async def collect_profile(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Collect profile information for a Facebook account.
        
        Args:
            account_id: UUID of the social media account to collect profile for
            
        Returns:
            Updated account information
        """
        account_info = await self._get_account_info(account_id)
        
        # Determine the best way to identify the page
        profile_url = account_info.get("url")
        profile_name = account_info.get("handle")
        
        # First prefer the full URL, then the handle
        target = profile_url if profile_url else f"https://www.facebook.com/{profile_name}"
        
        logger.info(f"Collecting profile information for Facebook account {target}")
        
        # Configure Facebook scraper for profile
        run_input = self.prepare_run_input(
            startUrls=[{"url": target}],
            maxPosts=1,  # Just need basic page info
            includePageMetadata=True
        )
        
        # Run actor and get results
        results = await self.apify_client.start_and_wait_for_results(
            actor_id=self.actor_id,
            run_input=run_input,
            limit=2  # Might return page info separately
        )
        
        if not results:
            logger.warning(f"No profile information returned for Facebook account {target}")
            return {}
        
        # Find the page info object
        page_info = None
        for item in results:
            if item.get("type") == "page" or item.get("type") == "profile":
                page_info = item
                break
            
        if not page_info and len(results) > 0:
            # If no specific page object, try to extract from the first post
            page_info = results[0].get("page", {})
        
        if page_info:
            # Transform and update account
            account_data = self.transform_profile(page_info)
            await self.account_repository.update(account_id, account_data)
            
            logger.info(f"Updated profile information for Facebook account {target}")
            return account_data
        
        return {}
    
    async def update_metrics(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Update engagement metrics for a Facebook account.
        
        This performs the same function as collect_profile but is named separately
        to match the interface requirements.
        
        Args:
            account_id: UUID of the social media account to update metrics for
            
        Returns:
            Updated account metrics
        """
        # For Facebook, updating metrics is the same as collecting profile
        return await self.collect_profile(account_id)
    
    def transform_post(
        self,
        raw_post: Dict[str, Any],
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Transform a raw Facebook post from APIFY into the format expected by the repository.
        
        Args:
            raw_post: Raw post data from APIFY
            account_id: UUID of the social media account
            
        Returns:
            Transformed post data
        """
        # Extract basic information
        post_id = raw_post.get("postId", raw_post.get("id", ""))
        text = raw_post.get("text", "")
        
        # Handle created_at (Facebook format can vary)
        created_at = datetime.utcnow()
        if "timestamp" in raw_post:
            try:
                created_at = datetime.fromtimestamp(raw_post["timestamp"] / 1000)
            except (ValueError, TypeError):
                pass
        elif "createdAt" in raw_post:
            try:
                created_at = datetime.strptime(
                    raw_post.get("createdAt", "").split("+")[0], 
                    "%Y-%m-%dT%H:%M:%S"
                )
            except (ValueError, TypeError):
                pass
        
        # Extract media and links
        media_urls = []
        if "attachments" in raw_post:
            for attachment in raw_post.get("attachments", []):
                if "url" in attachment:
                    media_urls.append(attachment["url"])
        
        # Extract link to the post
        post_url = raw_post.get("postUrl", "")
        links = [post_url] if post_url else []
        
        # Add any links from the text
        links.extend(self.extract_links(text))
        
        # Extract engagement metrics
        reactions = raw_post.get("reactionsCount", {})
        engagement = {
            "likes_count": reactions.get("like", 0) + reactions.get("love", 0) + reactions.get("care", 0),
            "shares_count": raw_post.get("sharesCount", 0),
            "comments_count": raw_post.get("commentsCount", 0),
            "views_count": None,
            "engagement_rate": None  # Calculate if needed
        }
        
        # Determine the content type
        content_type = "post"
        if "sharingPostUrl" in raw_post or "sharingText" in raw_post:
            content_type = "share"
        elif raw_post.get("type") == "photo":
            content_type = "photo"
        elif raw_post.get("type") == "video":
            content_type = "video"
        elif raw_post.get("type") == "event":
            content_type = "event"
        
        # Transform to application post format
        return {
            "platform_id": post_id,
            "platform": self.platform_name,
            "account_id": str(account_id),
            "content_type": content_type,
            "content": {
                "text": text,
                "media": media_urls,
                "links": links,
                "hashtags": self.extract_hashtags(text),
                "mentions": self.extract_mentions(text)
            },
            "metadata": {
                "created_at": created_at,
                "language": raw_post.get("languageCode", "unknown"),
                "location": raw_post.get("location", None),
                "client": "Facebook",
                "is_repost": content_type == "share",
                "is_reply": False
            },
            "engagement": engagement,
            "analysis": None  # Will be populated by analysis pipelines
        }
    
    def transform_comment(
        self,
        raw_comment: Dict[str, Any],
        post_id: str
    ) -> Dict[str, Any]:
        """
        Transform a raw Facebook comment from APIFY into the format expected by the repository.
        
        Args:
            raw_comment: Raw comment data from APIFY
            post_id: MongoDB ID of the parent post
            
        Returns:
            Transformed comment data
        """
        # Extract basic information
        comment_id = raw_comment.get("commentId", raw_comment.get("id", ""))
        text = raw_comment.get("text", "")
        
        # Extract user info
        user_name = raw_comment.get("name", "")
        user_id = raw_comment.get("authorId", "")
        
        # Handle created_at (Facebook format can vary)
        created_at = datetime.utcnow()
        if "timestamp" in raw_comment:
            try:
                created_at = datetime.fromtimestamp(raw_comment["timestamp"] / 1000)
            except (ValueError, TypeError):
                pass
        
        # Extract media
        media_urls = []
        if "attachments" in raw_comment:
            for attachment in raw_comment.get("attachments", []):
                if "url" in attachment:
                    media_urls.append(attachment["url"])
        
        # Extract engagement metrics
        reactions = raw_comment.get("reactionsCount", {})
        if isinstance(reactions, dict):
            likes_count = sum(reactions.values())
        else:
            likes_count = reactions
            
        engagement = {
            "likes_count": likes_count,
            "replies_count": len(raw_comment.get("replies", []))
        }
        
        # Transform to application comment format
        return {
            "platform_id": comment_id,
            "platform": self.platform_name,
            "post_id": post_id,
            "user_id": user_id,
            "user_name": user_name,
            "content": {
                "text": text,
                "media": media_urls,
                "mentions": self.extract_mentions(text)
            },
            "metadata": {
                "created_at": created_at,
                "language": raw_comment.get("languageCode", "unknown")
            },
            "engagement": engagement,
            "analysis": None  # Will be populated by analysis pipelines
        }
    
    def transform_profile(
        self,
        raw_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform a raw Facebook profile from APIFY into the format expected by the repository.
        
        Args:
            raw_profile: Raw profile data from APIFY
            
        Returns:
            Transformed profile data
        """
        # Extract the page ID and handle
        page_id = raw_profile.get("pageId", raw_profile.get("id", ""))
        page_url = raw_profile.get("url", "")
        handle = ""
        
        # Try to extract handle from URL
        if page_url:
            try:
                path = urlparse(page_url).path
                if path and path != "/":
                    handle = path.strip("/").split("/")[0]
            except Exception:
                pass
        
        # Use name if handle extraction failed
        if not handle:
            handle = raw_profile.get("name", "").lower().replace(" ", "")
        
        # Transform to application account format (for PostgreSQL update)
        return {
            "platform_id": page_id,
            "handle": handle,
            "name": raw_profile.get("name", ""),
            "url": page_url,
            "verified": raw_profile.get("verified", False),
            "follower_count": raw_profile.get("followersCount", raw_profile.get("likes", 0)),
            "following_count": None  # Facebook often doesn't provide this
        } 