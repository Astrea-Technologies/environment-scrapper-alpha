"""
Instagram Data Collector

This module provides a collector for Instagram data using APIFY's Instagram Scraper actor.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.core.config import settings
from app.db.models.social_media_account import Platform
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
    
    def get_post_sync(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a post by ID using a synchronous approach.
        
        Args:
            post_id: The ID of the post to retrieve
            
        Returns:
            The post data if found, None otherwise
        """
        import pymongo
        from bson import ObjectId
        from app.core.config import settings
        
        # Connect to MongoDB directly (synchronous)
        client = pymongo.MongoClient(settings.MONGODB_URI)
        db = client.get_database(settings.MONGODB_DATABASE)
        collection = db.posts
        
        try:
            # Try to find the post
            post = collection.find_one({"_id": ObjectId(post_id)})
            return post
        except Exception as e:
            logger.error(f"Error getting post synchronously: {e}")
            return None
        finally:
            client.close()
    
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
        
        # Ensure we're not trying to update the account ID or political_entity_id
        if "id" in account_data:
            del account_data["id"]
        
        # Now update the account
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
            "engagement_rate": None,  # Calculate if needed
            "saves_count": raw_post.get("savesCount", None)  # Add saves count if available
        }
        
        # Handle dimensions
        dimensions = None
        if "dimensions" in raw_post:
            dimensions = raw_post["dimensions"]
        elif "imageWidth" in raw_post and "imageHeight" in raw_post:
            dimensions = {
                "width": raw_post["imageWidth"],
                "height": raw_post["imageHeight"]
            }
        
        # Handle location
        location = None
        if "location" in raw_post and raw_post["location"]:
            location = {
                "name": raw_post["location"].get("name"),
                "id": raw_post["location"].get("id"),
                "country": raw_post["location"].get("country"),
                "state": raw_post["location"].get("state"),
                "city": raw_post["location"].get("city")
            }
        
        # Handle owner
        owner = None
        if "ownerUsername" in raw_post or "ownerId" in raw_post:
            owner = {
                "username": raw_post.get("ownerUsername", ""),
                "id": raw_post.get("ownerId", ""),
                "verified": raw_post.get("ownerVerified", False)
            }
        
        # Handle tagged users
        tagged_users = []
        if "taggedUsers" in raw_post and isinstance(raw_post["taggedUsers"], list):
            for user in raw_post["taggedUsers"]:
                if isinstance(user, dict):
                    tagged_users.append({
                        "username": user.get("username", ""),
                        "id": user.get("id", ""),
                        "full_name": user.get("fullName"),
                        "is_verified": user.get("isVerified", False)
                    })
        
        # Handle child posts for carousel/sidecar
        child_posts = None
        if content_type == "carousel" and "sidecarChildren" in raw_post:
            child_posts = []
            for child in raw_post["sidecarChildren"]:
                child_type = "Video" if child.get("isVideo", False) else "Image"
                child_post = {
                    "id": child.get("id", ""),
                    "type": child_type,
                    "url": f"https://www.instagram.com/p/{child.get('shortCode', '')}/",
                    "display_url": child.get("displayUrl", "")
                }
                
                # Add dimensions if available
                if "dimensions" in child:
                    child_post["dimensions"] = child["dimensions"]
                elif "imageWidth" in child and "imageHeight" in child:
                    child_post["dimensions"] = {
                        "width": child["imageWidth"],
                        "height": child["imageHeight"]
                    }
                
                # Add alt_text if available
                if "accessibilityCaption" in child:
                    child_post["alt_text"] = child["accessibilityCaption"]
                
                child_posts.append(child_post)
        
        # Handle video data
        video_data = None
        if content_type == "video":
            video_data = {
                "duration": raw_post.get("videoDuration"),
                "video_url": raw_post.get("videoUrl"),
                "thumbnail_url": raw_post.get("displayUrl"),
                "is_muted": raw_post.get("isMuted", False)
            }
        
        # Transform to application post format
        return {
            "platform_id": post_id,
            "platform": self.platform_name,
            "account_id": str(account_id),
            "content_type": content_type,
            "short_code": shortcode,
            "url": post_url,
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
                "location": location,
                "client": "Instagram",
                "is_repost": False,  # Instagram doesn't have traditional reposts
                "is_reply": False,
                "dimensions": dimensions,
                "alt_text": raw_post.get("accessibilityCaption"),
                "product_type": raw_post.get("productType"),
                "owner": owner,
                "tagged_users": tagged_users
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
        Transform a raw Instagram comment from APIFY into the format expected by the repository.
        
        Args:
            raw_comment: Raw comment data from APIFY
            post_id: MongoDB ID of the parent post
            
        Returns:
            Transformed comment data
        """
        # Fetch parent post to get post_url
        post_url = None
        try:
            # Get post data synchronously
            post = self.get_post_sync(post_id)
            if post and "url" in post:
                post_url = post["url"]
            elif post and "short_code" in post:
                post_url = f"https://www.instagram.com/p/{post['short_code']}/"
            elif post and "metadata" in post and "shortcode" in post["metadata"]:
                post_url = f"https://www.instagram.com/p/{post['metadata']['shortcode']}/"
        except Exception as e:
            logger.warning(f"Could not fetch parent post for url: {str(e)}")
        
        # Extract basic information
        comment_id = raw_comment.get("id", "")
        text = raw_comment.get("text", "")
        
        # Extract user info
        user_name = raw_comment.get("ownerUsername", "")
        user_id = raw_comment.get("ownerId", "")
        user_full_name = raw_comment.get("ownerFullName", None)
        user_profile_pic = raw_comment.get("ownerProfilePicUrl", None)
        user_verified = raw_comment.get("ownerVerified", False)
        user_private = raw_comment.get("ownerIsPrivate", False)
        
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
        
        # Handle replies
        replies = []
        if "replies" in raw_comment and isinstance(raw_comment["replies"], list):
            for reply in raw_comment["replies"]:
                if isinstance(reply, dict):
                    reply_created_at = datetime.utcnow()
                    if "timestamp" in reply:
                        try:
                            reply_created_at = datetime.fromtimestamp(reply["timestamp"] / 1000)
                        except (ValueError, TypeError):
                            pass
                    
                    replies.append({
                        "platform_id": reply.get("id", ""),
                        "user_id": reply.get("ownerId", ""),
                        "user_name": reply.get("ownerUsername", ""),
                        "user_full_name": reply.get("ownerFullName"),
                        "user_profile_pic": reply.get("ownerProfilePicUrl"),
                        "user_verified": reply.get("ownerVerified", False),
                        "text": reply.get("text", ""),
                        "created_at": reply_created_at,
                        "likes_count": reply.get("likesCount", 0),
                        "replies_count": 0  # Instagram doesn't support nested replies
                    })
        
        # Handle user details
        user_details = None
        if any(key in raw_comment for key in ["fbid", "is_mentionable", "latest_reel_media", "profile_pic_id"]):
            user_details = {
                "fbid_v2": raw_comment.get("fbid"),
                "is_mentionable": raw_comment.get("is_mentionable"),
                "latest_reel_media": raw_comment.get("latest_reel_media"),
                "profile_pic_id": raw_comment.get("profile_pic_id")
            }
        
        # Check for parent comment
        is_reply = False
        parent_comment_id = None
        if "parentCommentId" in raw_comment:
            is_reply = True
            parent_comment_id = raw_comment["parentCommentId"]
        
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
                "media": [],  # Instagram comments don't typically have media
                "mentions": self.extract_mentions(text)
            },
            "metadata": {
                "created_at": created_at,
                "language": "unknown",  # Instagram doesn't provide language info
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
            "platform": Platform.INSTAGRAM,  # Use enum value
            "platform_id": raw_profile.get("id", ""),
            "handle": username,
            "name": raw_profile.get("fullName", ""),
            "url": profile_url,
            "verified": raw_profile.get("verified", False),
            "follower_count": raw_profile.get("followersCount", 0),
            "following_count": raw_profile.get("followsCount", 0)
            # Note: political_entity_id is not included here as this is used for updates only
            # The account should already exist with the political_entity_id set
        } 