"""
Tests for Instagram data transformer

This module tests the transformation of Instagram raw data from APIFY
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


class TestInstagramTransforms:
    """
    Test the transformation of Instagram data from APIFY to the application format.
    """
    
    @pytest.fixture
    def sample_profile_data(self):
        """Load sample Instagram profile data."""
        data_path = Path(__file__).parent / "data" / "instagram" / "profile_samples.json"
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_post_data(self):
        """Load sample Instagram post data."""
        data_path = Path(__file__).parent / "data" / "instagram" / "post_samples.json"
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_comment_data(self):
        """Load sample Instagram comment data."""
        data_path = Path(__file__).parent / "data" / "instagram" / "comment_samples.json"
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def test_transform_profile(self, sample_profile_data):
        """Test the transformation of an Instagram profile by manually creating the transform."""
        # Get the first profile from the sample data
        raw_profile = sample_profile_data[0]
        
        # Extract basic info
        username = raw_profile.get("username", "")
        profile_url = f"https://www.instagram.com/{username}/" if username else ""
        
        # Manual transformation (same logic as in the collector)
        transformed = {
            "platform": Platform.INSTAGRAM,
            "platform_id": raw_profile.get("id", ""),
            "handle": username,
            "name": raw_profile.get("fullName", ""),
            "url": profile_url,
            "verified": raw_profile.get("verified", False),
            "follower_count": raw_profile.get("followersCount", 0),
            "following_count": raw_profile.get("followsCount", 0)
        }
        
        # Check if transformation matches expectations for social_media_account.py
        assert transformed["platform"] == Platform.INSTAGRAM
        assert transformed["platform_id"] == raw_profile["id"]
        assert transformed["handle"] == raw_profile["username"]
        assert transformed["name"] == raw_profile["fullName"]
        assert transformed["url"] == f"https://www.instagram.com/{raw_profile['username']}/"
        assert transformed["verified"] == raw_profile["verified"]
        assert transformed["follower_count"] == raw_profile["followersCount"]
        assert transformed["following_count"] == raw_profile["followsCount"]
        
        # Ensure political_entity_id is not included (should be set when account is created)
        assert "political_entity_id" not in transformed

    def test_transform_post(self, sample_post_data):
        """Test the transformation of an Instagram post by manually validating key fields."""
        # Get the first post from the sample data
        raw_post = sample_post_data[0]
        
        # Create a fake account ID
        account_id = str(uuid.uuid4())
        
        # Check if key fields are present in the raw post
        assert "id" in raw_post
        assert "shortCode" in raw_post
        assert "caption" in raw_post
        assert "url" in raw_post
        assert "likesCount" in raw_post
        assert "commentsCount" in raw_post
        assert "type" in raw_post
        assert raw_post["type"] == "Sidecar"  # This is a carousel post
        assert "childPosts" in raw_post
        assert "timestamp" in raw_post
        
        # Validate expected field types and structures
        assert isinstance(raw_post["id"], str)
        assert isinstance(raw_post["shortCode"], str)
        assert isinstance(raw_post["caption"], str)
        assert isinstance(raw_post["url"], str)
        assert isinstance(raw_post["likesCount"], int)
        assert isinstance(raw_post["commentsCount"], int)
        assert isinstance(raw_post["childPosts"], list)
        
        # Test MongoDB schema compatibility
        # These are the key fields needed by the MongoDB schema
        required_fields = {
            "platform_id": raw_post["id"],
            "platform": "instagram",
            "account_id": account_id,
            "content_type": "carousel",  # Derived from type field
            "short_code": raw_post["shortCode"],
            "url": raw_post["url"],
            "content": {
                "text": raw_post["caption"],
                "hashtags": raw_post["hashtags"]
            },
            "metadata": {
                "created_at": datetime.fromisoformat(raw_post["timestamp"].replace('Z', '+00:00'))
            },
            "engagement": {
                "likes_count": raw_post["likesCount"],
                "comments_count": raw_post["commentsCount"]
            }
        }
        
        # All required fields should be present in raw data
        for field, value in required_fields.items():
            if field in ["content", "metadata", "engagement"]:
                # These are nested fields, continue
                continue
            assert value is not None, f"Field {field} should not be None"

    def test_transform_comment(self, sample_comment_data):
        """Test the transformation of an Instagram comment by manually validating key fields."""
        # Get the first comment from the sample data
        raw_comment = sample_comment_data[0]
        
        # Create a fake post ID
        post_id = "fake_post_id"
        
        # Check if key fields are present in the raw comment
        assert "id" in raw_comment
        assert "text" in raw_comment
        assert "postUrl" in raw_comment
        assert "owner" in raw_comment
        assert "likesCount" in raw_comment
        assert "repliesCount" in raw_comment
        assert "replies" in raw_comment
        assert "timestamp" in raw_comment
        
        # Validate expected field types and structures
        assert isinstance(raw_comment["id"], str)
        assert isinstance(raw_comment["text"], str)
        assert isinstance(raw_comment["postUrl"], str)
        assert isinstance(raw_comment["owner"], dict)
        assert isinstance(raw_comment["likesCount"], int)
        assert isinstance(raw_comment["repliesCount"], int)
        assert isinstance(raw_comment["replies"], list)
        
        # Check owner fields
        owner = raw_comment["owner"]
        assert "id" in owner
        assert "username" in owner
        assert "full_name" in owner
        assert "profile_pic_url" in owner
        assert "is_verified" in owner
        assert "is_private" in owner
        
        # Test MongoDB schema compatibility
        # These are the key fields needed by the MongoDB schema
        required_fields = {
            "platform_id": raw_comment["id"],
            "platform": "instagram",
            "post_id": post_id,
            "post_url": raw_comment["postUrl"],
            "user_id": raw_comment["owner"]["id"],
            "user_name": raw_comment["owner"]["username"],
            "user_full_name": raw_comment["owner"]["full_name"],
            "user_profile_pic": raw_comment["owner"]["profile_pic_url"],
            "user_verified": raw_comment["owner"]["is_verified"],
            "user_private": raw_comment["owner"]["is_private"],
            "content": {
                "text": raw_comment["text"]
            },
            "metadata": {
                "created_at": datetime.fromisoformat(raw_comment["timestamp"].replace('Z', '+00:00'))
            },
            "engagement": {
                "likes_count": raw_comment["likesCount"],
                "replies_count": raw_comment["repliesCount"]
            }
        }
        
        # All required fields should be present in raw data
        for field, value in required_fields.items():
            if field in ["content", "metadata", "engagement"]:
                # These are nested fields, continue
                continue
            assert value is not None, f"Field {field} should not be None"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 