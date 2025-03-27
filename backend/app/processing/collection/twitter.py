"""
Twitter Data Collector

This module provides a collector for Twitter data using APIFY's Twitter Scraper actor.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.core.config import settings
from app.processing.collection.base import BaseCollector
from app.services.repositories.social_media_account import SocialMediaAccountRepository

logger = logging.getLogger(__name__)


class TwitterCollector(BaseCollector):
    """
    Twitter data collector using APIFY's Twitter Scraper actor.
    
    This collector handles collecting posts, comments, and profile information
    from Twitter/X accounts via APIFY, and transforms the data into the format
    expected by the application's repositories.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the Twitter collector."""
        super().__init__(*args, **kwargs)
        self.platform_name = "twitter"
        self.actor_id = settings.APIFY_TWITTER_ACTOR_ID
        self.account_repository = SocialMediaAccountRepository()
        
        # Twitter-specific default options
        self.default_run_options = {
            "maxItems": settings.SCRAPING_MAX_POSTS,
            "includeReplies": False,
            "includeRetweets": True,
            "includeImages": True,
            "includeVideos": True
        }
    
    async def _get_account_handle(self, account_id: Union[UUID, str]) -> str:
        """
        Get the Twitter handle for a given account ID.
        
        Args:
            account_id: UUID of the social media account
            
        Returns:
            Twitter handle
            
        Raises:
            ValueError: If the account is not found or has no handle
        """
        account = await self.account_repository.get(account_id)
        
        if not account:
            raise ValueError(f"Social media account not found: {account_id}")
        
        if not account.handle:
            raise ValueError(f"Account {account_id} has no Twitter handle")
        
        return account.handle
    
    async def collect_posts(
        self,
        account_id: Union[UUID, str],
        count: int = None,
        since_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Collect tweets from a Twitter account.
        
        Args:
            account_id: UUID of the social media account to collect from
            count: Maximum number of tweets to collect (defaults to settings.SCRAPING_MAX_POSTS)
            since_date: Only collect tweets after this date (defaults to default date range)
            
        Returns:
            List of MongoDB IDs for the collected tweets
        """
        handle = await self._get_account_handle(account_id)
        
        max_count = count or self.max_items
        start_date, _ = self.get_default_date_range() if not since_date else (since_date, datetime.utcnow())
        
        logger.info(f"Collecting tweets for account {handle} (max: {max_count}, since: {start_date})")
        
        # Configure Twitter scraper input
        run_input = self.prepare_run_input(
            usernames=[handle],
            maxItems=max_count,
            dateFrom=start_date.strftime("%Y-%m-%d")
        )
        
        # Run actor and get results
        results = await self.apify_client.start_and_wait_for_results(
            actor_id=self.actor_id,
            run_input=run_input,
            limit=max_count
        )
        
        logger.info(f"Collected {len(results)} tweets for account {handle}")
        
        # Save posts to MongoDB
        return await self.save_posts(results, account_id)
    
    async def collect_comments(
        self,
        post_id: str,
        count: int = None
    ) -> List[Dict[str, Any]]:
        """
        Collect comments (replies) for a Twitter post.
        
        Args:
            post_id: MongoDB ID of the post to collect comments for
            count: Maximum number of comments to collect (defaults to settings.SCRAPING_MAX_COMMENTS)
            
        Returns:
            List of MongoDB IDs for the collected comments
        """
        post = await self.post_repository.get(post_id)
        
        if not post:
            raise ValueError(f"Post not found: {post_id}")
        
        tweet_id = post.get("platform_id")
        if not tweet_id:
            raise ValueError(f"Invalid post platform ID for {post_id}")
        
        max_count = count or self.max_comments
        
        logger.info(f"Collecting comments for tweet {tweet_id} (max: {max_count})")
        
        # Configure Twitter scraper for comments
        run_input = self.prepare_run_input(
            tweetUrls=[f"https://twitter.com/i/status/{tweet_id}"],
            maxReplies=max_count,
            maxItems=1,  # Just get the original tweet
            includeReplies=True  # Important - we want replies
        )
        
        # Run actor and get results
        results = await self.apify_client.start_and_wait_for_results(
            actor_id=self.actor_id,
            run_input=run_input
        )
        
        # Extract replies from results
        replies = []
        for tweet in results:
            if "repliedTo" in tweet:
                # Discard the main tweet and collect replies
                replies.extend(tweet.get("replies", []))
        
        logger.info(f"Collected {len(replies)} comments for tweet {tweet_id}")
        
        # Save comments to MongoDB
        return await self.save_comments(replies, post_id)
    
    async def collect_profile(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Collect profile information for a Twitter account.
        
        Args:
            account_id: UUID of the social media account to collect profile for
            
        Returns:
            Updated account information
        """
        handle = await self._get_account_handle(account_id)
        
        logger.info(f"Collecting profile information for Twitter account {handle}")
        
        # Configure Twitter scraper for profile
        run_input = self.prepare_run_input(
            usernames=[handle],
            maxItems=1,  # Just need one post to get profile info
            includeUserInfo=True
        )
        
        # Run actor and get results
        results = await self.apify_client.start_and_wait_for_results(
            actor_id=self.actor_id,
            run_input=run_input,
            limit=1
        )
        
        if not results:
            logger.warning(f"No profile information returned for Twitter account {handle}")
            return {}
        
        # Twitter profile info is embedded in the tweet data
        profile_info = results[0].get("user", {}) if results else {}
        
        if profile_info:
            # Transform and update account
            account_data = self.transform_profile(profile_info)
            await self.account_repository.update(account_id, account_data)
            
            logger.info(f"Updated profile information for Twitter account {handle}")
            return account_data
        
        return {}
    
    async def update_metrics(
        self,
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Update engagement metrics for a Twitter account.
        
        This performs the same function as collect_profile but is named separately
        to match the interface requirements.
        
        Args:
            account_id: UUID of the social media account to update metrics for
            
        Returns:
            Updated account metrics
        """
        # For Twitter, updating metrics is the same as collecting profile
        return await self.collect_profile(account_id)
    
    def transform_post(
        self,
        raw_post: Dict[str, Any],
        account_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Transform a raw tweet from APIFY into the format expected by the repository.
        
        Args:
            raw_post: Raw tweet data from APIFY
            account_id: UUID of the social media account
            
        Returns:
            Transformed post data
        """
        # Extract basic information
        post_id = raw_post.get("id", "")
        text = raw_post.get("text", "")
        post_url = raw_post.get("url", "")
        
        try:
            created_at = datetime.strptime(
                raw_post.get("createdAt", "").split(".")[0], 
                "%Y-%m-%dT%H:%M:%S"
            ) if "createdAt" in raw_post else datetime.utcnow()
        except (ValueError, TypeError):
            # Handle alternative date formats
            try:
                created_at = datetime.strptime(
                    raw_post.get("createdAt", "").split("+")[0].strip(), 
                    "%a %b %d %H:%M:%S %Y"
                )
            except (ValueError, TypeError):
                created_at = datetime.utcnow()
        
        # Extract media and links
        media_urls = []
        dimensions = None
        
        # Extract media from extended entities if available
        if "extendedEntities" in raw_post and "media" in raw_post["extendedEntities"]:
            for media_item in raw_post["extendedEntities"]["media"]:
                if "media_url_https" in media_item:
                    media_urls.append(media_item["media_url_https"])
                
                # Extract dimensions from the first media item
                if not dimensions and "sizes" in media_item and "large" in media_item["sizes"]:
                    dimensions = {
                        "width": media_item["sizes"]["large"].get("w", 0),
                        "height": media_item["sizes"]["large"].get("h", 0)
                    }
        
        # Extract regular media if extended entities not available
        elif "media" in raw_post:
            for media_item in raw_post.get("media", []):
                if "url" in media_item:
                    media_urls.append(media_item["url"])
        
        # Process hashtags and mentions from entities
        hashtags = []
        mentions = []
        
        if "entities" in raw_post:
            entities = raw_post["entities"]
            if "hashtags" in entities:
                hashtags = [tag.get("text", "") for tag in entities.get("hashtags", []) if "text" in tag]
            if "user_mentions" in entities:
                mentions = [mention.get("screen_name", "") for mention in entities.get("user_mentions", []) if "screen_name" in mention]
        else:
            # Fallback to extraction from text
            hashtags = self.extract_hashtags(text)
            mentions = self.extract_mentions(text)
        
        # Extract links
        links = [post_url] if post_url else []
        links.extend(self.extract_links(text))
        
        # Determine content type
        content_type = "post"
        if raw_post.get("isRetweet", False):
            content_type = "retweet"
        elif raw_post.get("isQuote", False):
            content_type = "quote"
        elif raw_post.get("isReply", False):
            content_type = "reply"
        
        # Check for media types
        has_video = False
        has_images = False
        child_posts = None
        video_data = None
        
        if "extendedEntities" in raw_post and "media" in raw_post["extendedEntities"]:
            media_items = raw_post["extendedEntities"]["media"]
            
            # Check for videos
            for item in media_items:
                if item.get("type") == "video" or item.get("type") == "animated_gif":
                    has_video = True
                    break
                elif item.get("type") == "photo":
                    has_images = True
            
            # For multiple images, create child posts
            if len(media_items) > 1:
                child_posts = []
                for i, item in enumerate(media_items):
                    child_post = {
                        "id": f"{post_id}_child_{i}",
                        "type": item.get("type", "Image"),
                        "url": post_url,
                        "display_url": item.get("media_url_https", "")
                    }
                    
                    # Add dimensions if available
                    if "sizes" in item and "large" in item["sizes"]:
                        child_post["dimensions"] = {
                            "width": item["sizes"]["large"].get("w", 0),
                            "height": item["sizes"]["large"].get("h", 0)
                        }
                    
                    child_posts.append(child_post)
            
            # For videos, extract video data
            if has_video:
                for item in media_items:
                    if item.get("type") == "video" or item.get("type") == "animated_gif":
                        video_url = None
                        thumbnail_url = item.get("media_url_https", "")
                        duration = None
                        
                        # Get video URL from variants
                        if "video_info" in item and "variants" in item["video_info"]:
                            variants = item["video_info"]["variants"]
                            best_bitrate = 0
                            for variant in variants:
                                if "content_type" in variant and variant["content_type"].startswith("video/"):
                                    if "bitrate" in variant and variant["bitrate"] > best_bitrate:
                                        best_bitrate = variant["bitrate"]
                                        video_url = variant.get("url", "")
                        
                        # Get duration
                        if "video_info" in item and "duration_millis" in item["video_info"]:
                            duration = item["video_info"]["duration_millis"] / 1000  # Convert to seconds
                        
                        video_data = {
                            "duration": duration,
                            "video_url": video_url,
                            "thumbnail_url": thumbnail_url,
                            "is_muted": item.get("type") == "animated_gif"  # GIFs are typically muted
                        }
                        break
        
        # Update content type based on media
        if content_type == "post":
            if has_video:
                content_type = "video"
            elif len(media_urls) > 1:
                content_type = "carousel"
            elif has_images:
                content_type = "image"
        
        # Extract engagement metrics
        engagement = {
            "likes_count": raw_post.get("likeCount", 0),
            "shares_count": raw_post.get("retweetCount", 0),
            "comments_count": raw_post.get("replyCount", 0),
            "views_count": raw_post.get("viewCount", 0),
            "engagement_rate": None,  # Calculate if needed
            "saves_count": raw_post.get("bookmarkCount", 0)  # Twitter now tracks bookmarks
        }
        
        # Extract alt text
        alt_text = None
        if "extendedEntities" in raw_post and "media" in raw_post["extendedEntities"]:
            for item in raw_post["extendedEntities"]["media"]:
                if "ext_alt_text" in item:
                    alt_text = item["ext_alt_text"]
                    break
        
        # Get tagged users if available
        tagged_users = []
        if "entities" in raw_post and "user_mentions" in raw_post["entities"]:
            for mention in raw_post["entities"]["user_mentions"]:
                tagged_user = {
                    "username": mention.get("screen_name", ""),
                    "id": mention.get("id_str", ""),
                    "full_name": mention.get("name", ""),
                    "is_verified": False  # Twitter API doesn't provide this in mentions
                }
                tagged_users.append(tagged_user)
        
        # Extract owner information
        owner = None
        if "author" in raw_post:
            author = raw_post["author"]
            owner = {
                "username": author.get("userName", ""),
                "id": author.get("id", ""),
                "verified": author.get("isVerified", False) or author.get("isBlueVerified", False)
            }
        
        # Transform to application post format
        return {
            "platform_id": post_id,
            "platform": self.platform_name,
            "account_id": str(account_id),
            "content_type": content_type,
            "short_code": post_id,  # Twitter uses the ID as the short code
            "url": post_url,
            "content": {
                "text": text,
                "media": media_urls,
                "links": links,
                "hashtags": hashtags,
                "mentions": mentions
            },
            "metadata": {
                "created_at": created_at,
                "language": raw_post.get("lang", "unknown"),
                "location": raw_post.get("place", None),
                "client": raw_post.get("source", "Twitter"),
                "is_repost": raw_post.get("isRetweet", False),
                "is_reply": raw_post.get("isReply", False),
                "dimensions": dimensions,
                "alt_text": alt_text,
                "tagged_users": tagged_users,
                "owner": owner
            },
            "engagement": engagement,
            "child_posts": child_posts,
            "video_data": video_data,
            "analysis": None  # Will be populated by analysis pipelines
        }
    
    def transform_comment(
        self,
        raw_comment: Dict[str, Any],
        post_id: str
    ) -> Dict[str, Any]:
        """
        Transform a raw Twitter reply from APIFY into the format expected by the repository.
        
        Args:
            raw_comment: Raw comment data from APIFY
            post_id: MongoDB ID of the parent post
            
        Returns:
            Transformed comment data
        """
        # Extract basic information
        comment_id = raw_comment.get("id", "")
        text = raw_comment.get("text", "")
        
        # Process author information
        author = raw_comment.get("author", {})
        user_id = author.get("id", "")
        user_name = author.get("userName", "")
        user_full_name = author.get("name", "")
        user_profile_pic = author.get("profilePicture", "")
        user_verified = author.get("isVerified", False) or author.get("isBlueVerified", False)
        user_private = False  # Twitter API doesn't consistently provide this
        
        # Parse created_at date
        try:
            created_at = datetime.strptime(
                raw_comment.get("createdAt", "").split(".")[0], 
                "%Y-%m-%dT%H:%M:%S"
            ) if "createdAt" in raw_comment else datetime.utcnow()
        except (ValueError, TypeError):
            # Handle alternative date formats
            try:
                created_at = datetime.strptime(
                    raw_comment.get("createdAt", "").split("+")[0].strip(), 
                    "%a %b %d %H:%M:%S %Y"
                )
            except (ValueError, TypeError):
                created_at = datetime.utcnow()
        
        # Extract media
        media_urls = []
        if "extendedEntities" in raw_comment and "media" in raw_comment["extendedEntities"]:
            for media_item in raw_comment["extendedEntities"]["media"]:
                if "media_url_https" in media_item:
                    media_urls.append(media_item["media_url_https"])
        elif "media" in raw_comment:
            for media_item in raw_comment.get("media", []):
                if "url" in media_item:
                    media_urls.append(media_item["url"])
        
        # Process mentions
        mentions = []
        if "entities" in raw_comment and "user_mentions" in raw_comment["entities"]:
            mentions = [mention.get("screen_name", "") for mention in raw_comment["entities"]["user_mentions"] if "screen_name" in mention]
        else:
            mentions = self.extract_mentions(text)
        
        # Extract engagement metrics
        engagement = {
            "likes_count": raw_comment.get("likeCount", 0),
            "replies_count": raw_comment.get("replyCount", 0)
        }
        
        # Get post URL
        post_url = raw_comment.get("url", "").split("?")[0] if raw_comment.get("url") else None
        
        # Determine if this is a reply to another comment
        is_reply = raw_comment.get("isReply", False)
        parent_comment_id = raw_comment.get("inReplyToId", None)
        
        # Extract replies if available
        replies = []
        
        # Build user_details
        user_details = {
            "is_mentionable": True,
            "profile_pic_id": None
        }
        
        # Transform to application comment format
        return {
            "platform_id": comment_id,
            "platform": self.platform_name,
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
                "media": media_urls,
                "mentions": mentions
            },
            "metadata": {
                "created_at": created_at,
                "language": raw_comment.get("lang", "unknown"),
                "is_reply": is_reply,
                "parent_comment_id": parent_comment_id
            },
            "engagement": engagement,
            "replies": replies,
            "user_details": user_details,
            "analysis": None  # Will be populated by analysis pipelines
        }
    
    def transform_profile(
        self,
        raw_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform a raw Twitter profile from APIFY into the format expected by the repository.
        
        Args:
            raw_profile: Raw profile data from APIFY
            
        Returns:
            Transformed profile data
        """
        # Transform to application account format (for PostgreSQL update)
        return {
            "platform_id": raw_profile.get("id", ""),
            "handle": raw_profile.get("username", ""),
            "name": raw_profile.get("displayName", ""),
            "url": f"https://twitter.com/{raw_profile.get('username', '')}",
            "verified": raw_profile.get("verified", False),
            "follower_count": raw_profile.get("followersCount", 0),
            "following_count": raw_profile.get("followingCount", 0)
        } 