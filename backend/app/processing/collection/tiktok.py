"""
TikTok Data Collector

This module provides a collector for TikTok data using APIFY's TikTok Scraper actor.
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.core.config import settings
from app.processing.collection.base import BaseCollector
from app.services.repositories.social_media_account import SocialMediaAccountRepository
from app.processing.collection.apify_client import ApifyClient

# Constants for APIFY actors
TIKTOK_SCRAPER_ACTOR_ID = "rH3CGsQVKPj35ePsK"  # TikTok Scraper
TIKTOK_POST_SCRAPER_ACTOR_ID = "ZxHXJ2dyhbpx8TQyx"  # TikTok Video Scraper
TIKTOK_COMMENT_SCRAPER_ACTOR_ID = "sJqYjqDcTKvF9TYrK"  # TikTok Comment Scraper

logger = logging.getLogger(__name__)


# Standalone transformation functions for testing purposes
def transform_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform raw TikTok profile data into the format expected by the repository.

    Args:
        profile: The raw TikTok profile data.

    Returns:
        The transformed profile.
    """
    # Extract basic information
    profile_id = profile.get("id", "")
    handle = profile.get("uniqueId", "")
    name = profile.get("nickname", "")
    bio = profile.get("signature", "")
    verified = profile.get("verified", False)
    private = profile.get("privateAccount", False)
    
    # Construct the profile URL
    url = f"https://www.tiktok.com/@{handle}"
    
    # Extract follower and following counts
    follower_count = profile.get("followerCount", 0)
    following_count = profile.get("followingCount", 0)
    
    # Extract post count and total likes
    post_count = profile.get("videoCount", 0)
    total_likes = profile.get("heartCount", 0)
    
    # Extract profile picture URLs
    profile_pic_url = profile.get("avatarMedium", "")
    
    # Construct the transformed profile
    transformed_profile = {
        "platform_id": profile_id,
        "handle": handle,
        "name": name,
        "bio": bio,
        "url": url,
        "verified": verified,
        "private": private,
        "follower_count": follower_count,
        "following_count": following_count,
        "post_count": post_count,
        "total_likes": total_likes,
        "profile_pic_url": profile_pic_url
    }
    
    return transformed_profile

def transform_post(post: Dict[str, Any], account_id: str) -> Dict[str, Any]:
    """
    Transform raw TikTok post data into the format expected by the repository.

    Args:
        post: The raw TikTok post data.
        account_id: The account ID this post belongs to.

    Returns:
        The transformed post.
    """
    # Extract basic information
    post_id = post.get("id", "")
    text = post.get("desc", "")
    post_url = post.get("webVideoUrl", "")
    
    # Extract creation date and format it properly
    created_at = None
    if "createTime" in post:
        try:
            # TikTok provides timestamps in seconds since epoch
            created_at = datetime.fromtimestamp(post.get("createTime", 0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid creation time for TikTok post {post_id}")
            created_at = datetime.now()
    
    # Extract media URLs
    media_urls = []
    if "videoUrl" in post and post["videoUrl"]:
        media_urls.append(post["videoUrl"])
    
    # Extract hashtags
    hashtags = []
    if "hashtags" in post and isinstance(post["hashtags"], list):
        hashtags = [tag["name"] for tag in post["hashtags"] if "name" in tag]
    else:
        # Try to extract hashtags from text
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text)
    
    # Extract mentions
    mentions = []
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, text)
    
    # Determine content type (TikTok posts are always videos)
    content_type = "video"
    
    # Extract engagement metrics
    likes_count = post.get("diggCount", 0)
    comments_count = post.get("commentCount", 0)
    shares_count = post.get("shareCount", 0)
    views_count = post.get("playCount", 0)
    saves_count = post.get("collectCount", 0)
    
    # Extract video metadata if available
    dimensions = {"width": 0, "height": 0}
    video_duration = 0
    
    if "videoMeta" in post:
        video_meta = post["videoMeta"]
        dimensions["width"] = video_meta.get("width", 0)
        dimensions["height"] = video_meta.get("height", 0)
        video_duration = video_meta.get("duration", 0)
    
    # Extract author information
    owner_info = {}
    if "authorMeta" in post:
        author = post["authorMeta"]
        owner_info = {
            "id": author.get("id", ""),
            "username": author.get("name", ""),
            "full_name": author.get("nickname", ""),
            "verified": author.get("verified", False)
        }
    
    # Extract thumbnail URL
    thumbnail_url = ""
    if "covers" in post and post["covers"] and isinstance(post["covers"], list):
        thumbnail_url = post["covers"][0]
    
    # Construct the transformed post
    transformed_post = {
        "platform_id": post_id,
        "platform": "tiktok",
        "account_id": account_id,
        "content_type": content_type,
        "short_code": post_id,
        "url": post_url,
        "content": {
            "text": text,
            "media": media_urls,
            "hashtags": hashtags,
            "mentions": mentions
        },
        "metadata": {
            "created_at": created_at,
            "dimensions": dimensions,
            "alt_text": "",  # TikTok does not provide alt text
            "tagged_users": [],  # TikTok does not provide tagged users in the API
            "owner": owner_info
        },
        "engagement": {
            "likes_count": likes_count,
            "comments_count": comments_count,
            "shares_count": shares_count,
            "views_count": views_count,
            "saves_count": saves_count
        },
        "video_data": {
            "duration": video_duration,
            "video_url": post.get("videoUrl", ""),
            "thumbnail_url": thumbnail_url
        }
    }
    
    return transformed_post

def transform_comment(comment: Dict[str, Any], post_id: str) -> Dict[str, Any]:
    """
    Transform raw TikTok comment data into the format expected by the repository.

    Args:
        comment: The raw TikTok comment data.
        post_id: The post ID this comment belongs to.

    Returns:
        The transformed comment.
    """
    # Extract basic information
    comment_id = comment.get("id", "")
    text = comment.get("text", "")
    
    # Extract user information
    user_info = comment.get("user", {})
    user_id = user_info.get("id", "")
    user_name = user_info.get("uniqueId", "")
    user_full_name = user_info.get("nickname", "")
    user_profile_pic = user_info.get("avatarThumb", "")
    user_verified = user_info.get("verified", False)
    user_private = user_info.get("privateAccount", False)
    
    # Extract creation date and format it properly
    created_at = None
    if "createTime" in comment:
        try:
            # TikTok provides timestamps in seconds since epoch
            created_at = datetime.fromtimestamp(comment.get("createTime", 0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid creation time for TikTok comment {comment_id}")
            created_at = datetime.now()
    
    # Extract mentions
    mentions = []
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, text)
    
    # Determine if this is a reply
    is_reply = comment.get("isReply", False)
    
    # Extract engagement metrics
    likes_count = comment.get("diggCount", 0)
    replies_count = comment.get("replyCount", 0)
    
    # Process replies if available
    replies = []
    if "replies" in comment and isinstance(comment["replies"], list):
        for reply in comment["replies"]:
            reply_created_at = None
            try:
                reply_created_at = datetime.fromtimestamp(reply.get("createTime", 0))
            except (ValueError, TypeError):
                reply_created_at = datetime.now()
            
            replies.append({
                "platform_id": reply.get("id", ""),
                "text": reply.get("text", ""),
                "created_at": reply_created_at,
                "user_id": reply.get("userId", ""),
                "user_name": reply.get("uniqueId", ""),
                "user_full_name": reply.get("nickname", ""),
                "user_profile_pic": reply.get("avatarThumb", ""),
                "user_verified": reply.get("verified", False),
                "likes_count": reply.get("diggCount", 0)
            })
    
    # Construct the post URL from the post_id
    post_url = f"https://www.tiktok.com/video/{post_id}"
    
    # Construct the transformed comment
    transformed_comment = {
        "platform_id": comment_id,
        "platform": "tiktok",
        "post_id": post_id,
        "post_url": post_url,
        "user_id": user_id,
        "user_name": user_name,
        "user_full_name": user_full_name,
        "user_profile_pic": user_profile_pic,
        "user_verified": user_verified,
        "user_private": user_private,
        "content": {
            "text": text,
            "mentions": mentions
        },
        "metadata": {
            "created_at": created_at,
            "is_reply": is_reply
        },
        "engagement": {
            "likes_count": likes_count,
            "replies_count": replies_count
        },
        "replies": replies,
        "user_details": {
            "id": user_id,
            "username": user_name,
            "full_name": user_full_name,
            "profile_pic_url": user_profile_pic,
            "verified": user_verified,
            "private": user_private
        }
    }
    
    return transformed_comment


class TikTokCollector(BaseCollector):
    """
    TikTok data collector using APIFY's TikTok Scraper actor.
    
    This collector handles collecting posts, comments, and profile information
    from TikTok accounts via APIFY, and transforms the data into the format
    expected by the application's repositories.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the TikTok collector.

        Args:
            **kwargs: Additional arguments for the base collector.
        """
        super().__init__(**kwargs)
        self.platform_name = "tiktok"
        self.actor_id = TIKTOK_SCRAPER_ACTOR_ID
        self.post_actor_id = TIKTOK_POST_SCRAPER_ACTOR_ID
        self.comment_actor_id = TIKTOK_COMMENT_SCRAPER_ACTOR_ID
        self.api_key = settings.APIFY_API_KEY
        self.account_repository = SocialMediaAccountRepository()
        
        # TikTok-specific default options
        self.default_run_options = {
            "maxPosts": settings.SCRAPING_MAX_POSTS,
            "commentsPerPost": 0,  # Don't collect comments during post collection
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False
        }
    
    def _get_account_handle(self, account_id: Union[UUID, str]) -> str:
        """
        Get the TikTok handle for a given account ID.
        
        Args:
            account_id: UUID of the social media account
            
        Returns:
            TikTok handle
            
        Raises:
            ValueError: If the account is not found or has no handle
        """
        account = self.account_repository.get(account_id)
        
        if not account:
            raise ValueError(f"Social media account not found: {account_id}")
        
        if not account.handle:
            raise ValueError(f"Account {account_id} has no TikTok handle")
        
        return account.handle
    
    def collect_posts(
        self,
        account_id: Union[UUID, str],
        count: int = None,
        since_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Collect videos from a TikTok account.
        
        Args:
            account_id: UUID of the social media account to collect from
            count: Maximum number of videos to collect (defaults to settings.SCRAPING_MAX_POSTS)
            since_date: Only collect videos after this date (defaults to default date range)
            
        Returns:
            List of MongoDB IDs for the collected posts
        """
        handle = self._get_account_handle(account_id)
        
        max_count = count or self.max_items
        start_date, _ = self.get_default_date_range() if not since_date else (since_date, datetime.utcnow())
        
        logger.info(f"Collecting videos for TikTok account {handle} (max: {max_count}, since: {start_date})")
        
        # Create input for the APIFY task
        input_data = {
            "username": handle,
            "maxPosts": max_count,
            "downloadVideos": False,  # We only need the video URLs, not the files
            "proxyConfiguration": {"useApifyProxy": True},
        }
        
        # Add since date if provided
        if since_date:
            input_data["dateFrom"] = since_date.strftime("%Y-%m-%d")
        
        # Run the APIFY task
        run_result = self._run_actor(self.post_actor_id, input_data)
        
        # Process the results
        if not run_result or "items" not in run_result:
            logger.warning(f"No posts found for TikTok account: {handle}")
            return []
        
        logger.info(f"Collected {len(run_result['items'])} videos for TikTok account {handle}")
        
        # Save posts to MongoDB
        return self.save_posts(run_result['items'], account_id)
    
    def collect_comments(
        self,
        post_id: str,
        count: int = None
    ) -> List[Dict[str, Any]]:
        """
        Collect comments for a TikTok post.
        
        Args:
            post_id: MongoDB ID of the post to collect comments for
            count: Maximum number of comments to collect (defaults to settings.SCRAPING_MAX_COMMENTS)
            
        Returns:
            List of MongoDB IDs for the collected comments
        """
        post = self.post_repository.get(post_id)
        
        if not post:
            raise ValueError(f"Post not found: {post_id}")
        
        tiktok_post_id = post.get("platform_id")
        if not tiktok_post_id:
            raise ValueError(f"Invalid post platform ID for {post_id}")
        
        max_count = count or self.max_comments
        
        logger.info(f"Collecting comments for TikTok post {tiktok_post_id} (max: {max_count})")
        
        # Get the post URL
        post_url = post.get("url")
        if not post_url:
            raise ValueError(f"No URL found for post {post_id}")
        
        # Create input for the APIFY task
        input_data = {
            "videoUrl": post_url,
            "maxComments": max_count,
            "maxReplies": 10,  # Limit replies to avoid huge data volumes
            "proxyConfiguration": {"useApifyProxy": True},
        }
        
        # Run the APIFY task
        run_result = self._run_actor(self.comment_actor_id, input_data)
        
        # Process the results
        if not run_result or "items" not in run_result:
            logger.warning(f"No comments found for TikTok post: {post_url}")
            return []
        
        # Extract comments from results
        comments = []
        for comment_data in run_result["items"]:
            if "comments" in comment_data:
                comments.extend(comment_data["comments"])
        
        logger.info(f"Collected {len(comments)} comments for TikTok post {tiktok_post_id}")
        
        # Save comments to MongoDB
        return self.save_comments(comments, post_id)
    
    def collect_profile(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Collect profile information for a TikTok account.
        
        Args:
            account_id: UUID of the social media account to collect profile for
            
        Returns:
            Updated account information
        """
        handle = self._get_account_handle(account_id)
        
        logger.info(f"Collecting profile information for TikTok account {handle}")
        
        # Create input for the APIFY task
        input_data = {
            "username": handle,
            "proxyConfiguration": {"useApifyProxy": True},
        }
        
        # Run the APIFY task
        run_result = self._run_actor(self.actor_id, input_data)
        
        # Process the results
        if not run_result or "userInfo" not in run_result:
            logger.warning(f"No profile found for TikTok account: {handle}")
            return {}
        
        # TikTok profile info might be in the userInfo field
        profile_info = run_result.get("userInfo", {})
        
        if profile_info:
            # Transform and update account
            account_data = self.transform_profile(profile_info)
            self.account_repository.update(account_id, account_data)
            
            logger.info(f"Updated profile information for TikTok account {handle}")
            return account_data
        
        return {}
    
    def update_metrics(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Update engagement metrics for a TikTok account.
        
        This performs the same function as collect_profile but is named separately
        to match the interface requirements.
        
        Args:
            account_id: UUID of the social media account to update metrics for
            
        Returns:
            Updated account metrics
        """
        # For TikTok, updating metrics is the same as collecting profile
        return self.collect_profile(account_id)
    
    def transform_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Use the standalone transform_profile function."""
        return transform_profile(profile)
    
    def transform_post(self, post: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        """Use the standalone transform_post function."""
        return transform_post(post, account_id)
    
    def transform_comment(self, comment: Dict[str, Any], post_id: str) -> Dict[str, Any]:
        """Use the standalone transform_comment function."""
        return transform_comment(comment, post_id) 