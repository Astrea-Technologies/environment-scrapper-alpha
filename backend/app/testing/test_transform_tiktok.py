"""
Tests for TikTok data transformer

This module tests the transformation of TikTok raw data from APIFY
to the format expected by the application's repositories.
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.models.social_media_account import Platform


class TestTikTokTransforms:
    """
    Test the transformation of TikTok data from APIFY to the application format.
    
    Note: Since we don't have actual TikTok sample data files yet, these tests
    create mock data that mimics the expected structure from APIFY's TikTok scraper.
    """
    
    @pytest.fixture
    def mock_profile_data(self):
        """Create mock TikTok profile data."""
        return {
            "id": "12345678",
            "uniqueId": "tiktok_user",
            "nickname": "TikTok User Name",
            "signature": "Bio text here",
            "verified": True,
            "privateAccount": False,
            "followerCount": 100000,
            "followingCount": 1000,
            "heartCount": 500000,
            "videoCount": 200,
            "avatarLarger": "https://p16-sign-va.tiktokcdn.com/profile_pic_large.jpg",
            "avatarMedium": "https://p16-sign-va.tiktokcdn.com/profile_pic_medium.jpg",
            "avatarThumb": "https://p16-sign-va.tiktokcdn.com/profile_pic_thumb.jpg"
        }
    
    @pytest.fixture
    def mock_post_data(self):
        """Create mock TikTok post data."""
        return {
            "id": "7123456789012345678",
            "desc": "This is a TikTok video #tiktok #test @mention",
            "createTime": 1640995200,  # 2022-01-01T00:00:00
            "webVideoUrl": "https://www.tiktok.com/@tiktok_user/video/7123456789012345678",
            "videoUrl": "https://v16-webapp.tiktok.com/video.mp4",
            "covers": [
                "https://p16-sign-va.tiktokcdn.com/thumbnail.jpg"
            ],
            "diggCount": 50000,
            "shareCount": 5000,
            "commentCount": 2000,
            "playCount": 100000,
            "collectCount": 3000,
            "hashtags": [
                {"id": "123", "name": "tiktok"},
                {"id": "456", "name": "test"}
            ],
            "videoMeta": {
                "width": 1080,
                "height": 1920,
                "duration": 15.5
            },
            "authorMeta": {
                "id": "12345678",
                "name": "tiktok_user",
                "nickname": "TikTok User Name",
                "verified": True
            }
        }
    
    @pytest.fixture
    def mock_comment_data(self):
        """Create mock TikTok comment data."""
        return {
            "id": "7123456789012345679",
            "text": "This is a comment @reply",
            "createTime": 1641081600,  # 2022-01-02T00:00:00
            "user": {
                "id": "87654321",
                "uniqueId": "commenter",
                "nickname": "Commenter Name",
                "avatarThumb": "https://p16-sign-va.tiktokcdn.com/commenter_avatar.jpg",
                "verified": False,
                "privateAccount": False
            },
            "diggCount": 1000,
            "replyCount": 5,
            "isReply": False,
            "replies": [
                {
                    "id": "7123456789012345680",
                    "text": "This is a reply",
                    "createTime": 1641168000,  # 2022-01-03T00:00:00
                    "userId": "12345678",
                    "uniqueId": "tiktok_user",
                    "nickname": "TikTok User Name",
                    "avatarThumb": "https://p16-sign-va.tiktokcdn.com/profile_pic_thumb.jpg",
                    "verified": True,
                    "diggCount": 500,
                    "replyCount": 0
                }
            ]
        }
    
    def test_transform_profile(self, mock_profile_data):
        """Test the transformation of a TikTok profile."""
        # Import and patch the transform_profile function directly
        from app.processing.collection.tiktok import transform_profile
        
        # Transform the profile data
        transformed = transform_profile(mock_profile_data)
        
        # Check if transformation matches expectations for social_media_account.py
        assert transformed["platform_id"] == mock_profile_data["id"]
        assert transformed["handle"] == mock_profile_data["uniqueId"]
        assert transformed["name"] == mock_profile_data["nickname"]
        assert transformed["url"] == f"https://www.tiktok.com/@{mock_profile_data['uniqueId']}"
        assert transformed["verified"] == mock_profile_data["verified"]
        assert transformed["follower_count"] == mock_profile_data["followerCount"]
        assert transformed["following_count"] == mock_profile_data["followingCount"]
        
        # Ensure the platform isn't included (should be set when using with SocialMediaAccountRepository)
        assert "platform" not in transformed
        
        # Ensure political_entity_id is not included (should be set when account is created)
        assert "political_entity_id" not in transformed

    def test_transform_post(self, mock_post_data):
        """Test the transformation of a TikTok post."""
        # Import and patch the transform_post function directly
        from app.processing.collection.tiktok import transform_post
        
        # Create a fake account ID
        account_id = str(uuid.uuid4())
        
        # Transform the post data
        transformed = transform_post(mock_post_data, account_id)
        
        # Check if transformation matches expectations for MongoDB schema
        assert transformed["platform_id"] == mock_post_data["id"]
        assert transformed["platform"] == "tiktok"
        assert transformed["account_id"] == account_id
        assert transformed["content_type"] == "video"
        assert transformed["short_code"] == mock_post_data["id"]
        assert transformed["url"] == mock_post_data["webVideoUrl"]
        
        # Check content
        assert transformed["content"]["text"] == mock_post_data["desc"]
        assert mock_post_data["videoUrl"] in transformed["content"]["media"]
        assert len(transformed["content"]["hashtags"]) == 2
        assert "tiktok" in transformed["content"]["hashtags"]
        assert "test" in transformed["content"]["hashtags"]
        
        # Check metadata
        assert isinstance(transformed["metadata"]["created_at"], datetime)
        assert transformed["metadata"]["dimensions"]["width"] == mock_post_data["videoMeta"]["width"]
        assert transformed["metadata"]["dimensions"]["height"] == mock_post_data["videoMeta"]["height"]
        assert transformed["metadata"]["owner"]["username"] == mock_post_data["authorMeta"]["name"]
        
        # Check engagement
        assert transformed["engagement"]["likes_count"] == mock_post_data["diggCount"]
        assert transformed["engagement"]["shares_count"] == mock_post_data["shareCount"]
        assert transformed["engagement"]["comments_count"] == mock_post_data["commentCount"]
        assert transformed["engagement"]["views_count"] == mock_post_data["playCount"]
        assert transformed["engagement"]["saves_count"] == mock_post_data["collectCount"]
        
        # Check video data
        assert transformed["video_data"]["duration"] == mock_post_data["videoMeta"]["duration"]
        assert transformed["video_data"]["video_url"] == mock_post_data["videoUrl"]
        assert transformed["video_data"]["thumbnail_url"] == mock_post_data["covers"][0]

    def test_transform_comment(self, mock_comment_data):
        """Test the transformation of a TikTok comment."""
        # Import and patch the transform_comment function directly
        from app.processing.collection.tiktok import transform_comment
        
        # Create a fake post ID
        post_id = str(uuid.uuid4())
        
        # Transform the comment data
        transformed = transform_comment(mock_comment_data, post_id)
        
        # Check if transformation matches expectations for MongoDB schema
        assert transformed["platform_id"] == mock_comment_data["id"]
        assert transformed["platform"] == "tiktok"
        assert transformed["post_id"] == post_id
        assert transformed["user_id"] == mock_comment_data["user"]["id"]
        assert transformed["user_name"] == mock_comment_data["user"]["uniqueId"]
        assert transformed["user_full_name"] == mock_comment_data["user"]["nickname"]
        assert transformed["user_profile_pic"] == mock_comment_data["user"]["avatarThumb"]
        assert transformed["user_verified"] == mock_comment_data["user"]["verified"]
        
        # Check content
        assert transformed["content"]["text"] == mock_comment_data["text"]
        
        # Check metadata
        assert isinstance(transformed["metadata"]["created_at"], datetime)
        assert transformed["metadata"]["is_reply"] == mock_comment_data["isReply"]
        
        # Check engagement
        assert transformed["engagement"]["likes_count"] == mock_comment_data["diggCount"]
        assert transformed["engagement"]["replies_count"] == mock_comment_data["replyCount"]
        
        # Check replies
        assert len(transformed["replies"]) == len(mock_comment_data["replies"])
        assert transformed["replies"][0]["platform_id"] == mock_comment_data["replies"][0]["id"]
        assert transformed["replies"][0]["text"] == mock_comment_data["replies"][0]["text"]


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 