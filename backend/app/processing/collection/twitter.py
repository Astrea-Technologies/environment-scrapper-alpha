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
        created_at = datetime.strptime(
            raw_post.get("createdAt", "").split(".")[0], 
            "%Y-%m-%dT%H:%M:%S"
        ) if "createdAt" in raw_post else datetime.utcnow()
        
        # Extract media and links
        media_urls = []
        if "media" in raw_post:
            for media_item in raw_post.get("media", []):
                if "url" in media_item:
                    media_urls.append(media_item["url"])
        
        # Extract engagement metrics
        engagement = {
            "likes_count": raw_post.get("likeCount", 0),
            "shares_count": raw_post.get("retweetCount", 0),
            "comments_count": raw_post.get("replyCount", 0),
            "views_count": raw_post.get("viewCount", 0),
            "engagement_rate": None  # Calculate if needed
        }
        
        # Transform to application post format
        return {
            "platform_id": post_id,
            "platform": self.platform_name,
            "account_id": str(account_id),
            "content_type": "retweet" if raw_post.get("isRetweet", False) else "post",
            "content": {
                "text": text,
                "media": media_urls,
                "links": self.extract_links(text),
                "hashtags": self.extract_hashtags(text),
                "mentions": self.extract_mentions(text)
            },
            "metadata": {
                "created_at": created_at,
                "language": raw_post.get("lang", "unknown"),
                "location": None,  # Twitter API doesn't usually provide this
                "client": raw_post.get("source", "Twitter"),
                "is_repost": raw_post.get("isRetweet", False),
                "is_reply": raw_post.get("isReply", False)
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
        user = raw_comment.get("user", {})
        created_at = datetime.strptime(
            raw_comment.get("createdAt", "").split(".")[0], 
            "%Y-%m-%dT%H:%M:%S"
        ) if "createdAt" in raw_comment else datetime.utcnow()
        
        # Extract media
        media_urls = []
        if "media" in raw_comment:
            for media_item in raw_comment.get("media", []):
                if "url" in media_item:
                    media_urls.append(media_item["url"])
        
        # Extract engagement metrics
        engagement = {
            "likes_count": raw_comment.get("likeCount", 0),
            "replies_count": raw_comment.get("replyCount", 0)
        }
        
        # Transform to application comment format
        return {
            "platform_id": comment_id,
            "platform": self.platform_name,
            "post_id": post_id,
            "user_id": user.get("id", ""),
            "user_name": user.get("username", ""),
            "content": {
                "text": text,
                "media": media_urls,
                "mentions": self.extract_mentions(text)
            },
            "metadata": {
                "created_at": created_at,
                "language": raw_comment.get("lang", "unknown")
            },
            "engagement": engagement,
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