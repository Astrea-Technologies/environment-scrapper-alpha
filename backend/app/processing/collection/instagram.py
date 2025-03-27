"""
Instagram Data Collector

This module provides a collector for Instagram data using APIFY's Instagram Scraper actor.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.core.config import settings
from app.processing.collection.base import BaseCollector
from app.services.repositories.social_media_account import SocialMediaAccountRepository

logger = logging.getLogger(__name__)


class InstagramCollector(BaseCollector):
    """
    Instagram data collector using APIFY's Instagram Scraper actor.
    
    This collector handles collecting posts, comments, and profile information
    from Instagram accounts via APIFY, and transforms the data into the format
    expected by the application's repositories.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the Instagram collector."""
        super().__init__(*args, **kwargs)
        self.platform_name = "instagram"
        self.actor_id = settings.APIFY_INSTAGRAM_ACTOR_ID
        self.account_repository = SocialMediaAccountRepository()
        
        # Instagram-specific default options
        self.default_run_options = {
            "maxPosts": settings.SCRAPING_MAX_POSTS,
            "resultsType": "posts",
            "addParentData": True,
            "includeComments": False,  # Will fetch separately
            "scrapePostsUntilDate": None,  # Will be set in collect_posts
        }
    
    async def _get_account_handle(self, account_id: Union[UUID, str]) -> str:
        """
        Get the Instagram handle for a given account ID.
        
        Args:
            account_id: UUID of the social media account
            
        Returns:
            Instagram handle
            
        Raises:
            ValueError: If the account is not found or has no handle
        """
        account = await self.account_repository.get(account_id)
        
        if not account:
            raise ValueError(f"Social media account not found: {account_id}")
        
        if not account.handle:
            raise ValueError(f"Account {account_id} has no Instagram handle")
        
        return account.handle
    
    async def collect_posts(
        self,
        account_id: Union[UUID, str],
        count: int = None,
        since_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Collect posts from an Instagram account.
        
        Args:
            account_id: UUID of the social media account to collect from
            count: Maximum number of posts to collect (defaults to settings.SCRAPING_MAX_POSTS)
            since_date: Only collect posts after this date (defaults to default date range)
            
        Returns:
            List of MongoDB IDs for the collected posts
        """
        handle = await self._get_account_handle(account_id)
        
        max_count = count or self.max_items
        start_date, _ = self.get_default_date_range() if not since_date else (since_date, datetime.utcnow())
        
        logger.info(f"Collecting posts for Instagram account {handle} (max: {max_count}, since: {start_date})")
        
        # Configure Instagram scraper input
        run_input = self.prepare_run_input(
            usernames=[handle],
            maxPosts=max_count,
            resultsType="posts",
            scrapePostsUntilDate=start_date.strftime("%Y-%m-%d")
        )
        
        # Run actor and get results
        results = await self.apify_client.start_and_wait_for_results(
            actor_id=self.actor_id,
            run_input=run_input,
            limit=max_count
        )
        
        # Filter for post objects only
        posts = []
        for item in results:
            # Instagram APIFY actor sometimes nests posts inside profile objects
            if "type" in item and item["type"] == "user":
                if "latestPosts" in item:
                    posts.extend(item["latestPosts"])
            else:
                # Assume it's a post object directly
                posts.append(item)
        
        logger.info(f"Collected {len(posts)} posts for Instagram account {handle}")
        
        # Save posts to MongoDB
        return await self.save_posts(posts, account_id)
    
    async def collect_comments(
        self,
        post_id: str,
        count: int = None
    ) -> List[Dict[str, Any]]:
        """
        Collect comments for an Instagram post.
        
        Args:
            post_id: MongoDB ID of the post to collect comments for
            count: Maximum number of comments to collect (defaults to settings.SCRAPING_MAX_COMMENTS)
            
        Returns:
            List of MongoDB IDs for the collected comments
        """
        post = await self.post_repository.get(post_id)
        
        if not post:
            raise ValueError(f"Post not found: {post_id}")
        
        ig_post_id = post.get("platform_id")
        if not ig_post_id:
            raise ValueError(f"Invalid post platform ID for {post_id}")
        
        # For Instagram, we need post URL
        post_url = None
        if "links" in post.get("content", {}) and post["content"]["links"]:
            for link in post["content"]["links"]:
                if "instagram.com/p/" in link:
                    post_url = link
                    break
        
        if not post_url:
            # Try to construct from shortcode if available
            shortcode = post.get("metadata", {}).get("shortcode")
            if shortcode:
                post_url = f"https://www.instagram.com/p/{shortcode}/"
            else:
                raise ValueError(f"Could not determine Instagram post URL for {post_id}")
        
        max_count = count or self.max_comments
        
        logger.info(f"Collecting comments for Instagram post {ig_post_id} (max: {max_count})")
        
        # Configure Instagram scraper for comments
        run_input = self.prepare_run_input(
            directUrls=[post_url],
            resultsType="comments",
            maxComments=max_count
        )
        
        # Run actor and get results
        results = await self.apify_client.start_and_wait_for_results(
            actor_id=self.actor_id,
            run_input=run_input
        )
        
        # Extract comments from results
        comments = []
        for item in results:
            if "type" in item and item["type"] == "post":
                if "comments" in item:
                    comments.extend(item["comments"])
            elif "id" in item and "ownerUsername" in item:
                # This is likely a comment object directly
                comments.append(item)
        
        logger.info(f"Collected {len(comments)} comments for Instagram post {ig_post_id}")
        
        # Save comments to MongoDB
        return await self.save_comments(comments, post_id)
    
    async def collect_profile(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Collect profile information for an Instagram account.
        
        Args:
            account_id: UUID of the social media account to collect profile for
            
        Returns:
            Updated account information
        """
        handle = await self._get_account_handle(account_id)
        
        logger.info(f"Collecting profile information for Instagram account {handle}")
        
        # Configure Instagram scraper for profile
        run_input = self.prepare_run_input(
            usernames=[handle],
            resultsType="details",
            maxPosts=0  # Don't need posts for profile info
        )
        
        # Run actor and get results
        results = await self.apify_client.start_and_wait_for_results(
            actor_id=self.actor_id,
            run_input=run_input,
            limit=1
        )
        
        # Find the profile info object
        profile_info = None
        for item in results:
            if "type" in item and item["type"] == "user":
                profile_info = item
                break
            
        if not profile_info:
            logger.warning(f"No profile information returned for Instagram account {handle}")
            return {}
        
        # Transform and update account
        account_data = self.transform_profile(profile_info)
        await self.account_repository.update(account_id, account_data)
        
        logger.info(f"Updated profile information for Instagram account {handle}")
        return account_data
    
    async def update_metrics(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Update engagement metrics for an Instagram account.
        
        This performs the same function as collect_profile but is named separately
        to match the interface requirements.
        
        Args:
            account_id: UUID of the social media account to update metrics for
            
        Returns:
            Updated account metrics
        """
        # For Instagram, updating metrics is the same as collecting profile
        return await self.collect_profile(account_id)
    
    def transform_post(
        self,
        raw_post: Dict[str, Any],
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Transform a raw Instagram post from APIFY into the format expected by the repository.
        
        Args:
            raw_post: Raw post data from APIFY
            account_id: UUID of the social media account
            
        Returns:
            Transformed post data
        """
        # Extract basic information
        post_id = raw_post.get("id", "")
        caption = raw_post.get("caption", "")
        shortcode = raw_post.get("shortCode", "")
        
        # Extract timestamps
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
                
        # Extract media URLs
        media_urls = []
        if "displayUrl" in raw_post:
            media_urls.append(raw_post["displayUrl"])
        
        if "videoUrl" in raw_post and raw_post["videoUrl"]:
            media_urls.append(raw_post["videoUrl"])
            
        if "images" in raw_post:
            for image in raw_post.get("images", []):
                if image and isinstance(image, str):
                    media_urls.append(image)
        
        # Extract post URL
        post_url = f"https://www.instagram.com/p/{shortcode}/" if shortcode else None
        links = [post_url] if post_url else []
        
        # Add any links from the caption
        links.extend(self.extract_links(caption))
        
        # Determine content type
        content_type = "post"
        if raw_post.get("isVideo", False) or "videoUrl" in raw_post:
            content_type = "video"
        elif "images" in raw_post and len(raw_post["images"]) > 1:
            content_type = "carousel"
        elif raw_post.get("__typename") == "GraphStoryVideo":
            content_type = "story"
        
        # Extract engagement metrics
        engagement = {
            "likes_count": raw_post.get("likesCount", 0),
            "comments_count": raw_post.get("commentsCount", 0),
            "shares_count": None,  # Instagram doesn't provide share counts
            "views_count": raw_post.get("videoViewCount", None) if content_type == "video" else None,
            "engagement_rate": None  # Calculate if needed
        }
        
        # Transform to application post format
        return {
            "platform_id": post_id,
            "platform": self.platform_name,
            "account_id": str(account_id),
            "content_type": content_type,
            "content": {
                "text": caption,
                "media": media_urls,
                "links": links,
                "hashtags": self.extract_hashtags(caption),
                "mentions": self.extract_mentions(caption)
            },
            "metadata": {
                "created_at": created_at,
                "language": "unknown",  # Instagram doesn't provide language info
                "location": raw_post.get("location", {}) if "location" in raw_post else None,
                "client": "Instagram",
                "is_repost": False,  # Instagram doesn't have traditional reposts
                "is_reply": False,
                "shortcode": shortcode
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
        Transform a raw Instagram comment from APIFY into the format expected by the repository.
        
        Args:
            raw_comment: Raw comment data from APIFY
            post_id: MongoDB ID of the parent post
            
        Returns:
            Transformed comment data
        """
        # Extract basic information
        comment_id = raw_comment.get("id", "")
        text = raw_comment.get("text", "")
        
        # Extract user info
        user_name = raw_comment.get("ownerUsername", "")
        user_id = raw_comment.get("ownerId", "")
        
        # Handle created_at (Instagram format can vary)
        created_at = datetime.utcnow()
        if "timestamp" in raw_comment:
            try:
                created_at = datetime.fromtimestamp(raw_comment["timestamp"] / 1000)
            except (ValueError, TypeError):
                pass
        
        # Extract engagement metrics
        engagement = {
            "likes_count": raw_comment.get("likesCount", 0),
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
                "media": [],  # Instagram comments don't typically have media
                "mentions": self.extract_mentions(text)
            },
            "metadata": {
                "created_at": created_at,
                "language": "unknown"  # Instagram doesn't provide language info
            },
            "engagement": engagement,
            "analysis": None  # Will be populated by analysis pipelines
        }
    
    def transform_profile(
        self,
        raw_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform a raw Instagram profile from APIFY into the format expected by the repository.
        
        Args:
            raw_profile: Raw profile data from APIFY
            
        Returns:
            Transformed profile data
        """
        # Extract handles and URLs
        username = raw_profile.get("username", "")
        profile_url = f"https://www.instagram.com/{username}/" if username else ""
        
        # Transform to application account format (for PostgreSQL update)
        return {
            "platform_id": raw_profile.get("id", ""),
            "handle": username,
            "name": raw_profile.get("fullName", ""),
            "url": profile_url,
            "verified": raw_profile.get("isVerified", False),
            "follower_count": raw_profile.get("followersCount", 0),
            "following_count": raw_profile.get("followsCount", 0)
        } 