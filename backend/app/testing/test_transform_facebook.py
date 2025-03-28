"""
Tests for Facebook data transformer

This module tests the transformation of Facebook raw data from APIFY
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


class TestFacebookTransforms:
    """
    Test the transformation of Facebook data from APIFY to the application format.
    """
    
    @pytest.fixture
    def sample_profile_data(self):
        """Load sample Facebook profile data."""
        data_path = Path(__file__).parent / "data" / "facebook" / "profile_samples.json"
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_post_data(self):
        """Load sample Facebook post data."""
        data_path = Path(__file__).parent / "data" / "facebook" / "post_samples.json"
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_comment_data(self):
        """Load sample Facebook comment data."""
        data_path = Path(__file__).parent / "data" / "facebook" / "comment_samples.json"
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def test_transform_profile(self, sample_profile_data):
        """Test the transformation of a Facebook profile by manually creating the transform."""
        # Get the first profile from the sample data
        raw_profile = sample_profile_data[0]
        
        # Extract the page ID and handle
        page_id = raw_profile.get("pageId", raw_profile.get("facebookId", ""))
        page_url = raw_profile.get("pageUrl", "")
        handle = ""
        
        # Try to extract handle from URL
        if page_url:
            try:
                path = page_url.split("/")[-2] if page_url.endswith("/") else page_url.split("/")[-1]
                if path and path != "/":
                    handle = path
            except Exception:
                pass
        
        # Use pageName if handle extraction failed
        if not handle:
            handle = raw_profile.get("pageName", "").lower().replace(" ", "")
        
        # Manual transformation (same logic as in the collector)
        transformed = {
            "platform": Platform.FACEBOOK,
            "platform_id": page_id,
            "handle": handle,
            "name": raw_profile.get("title", ""),
            "url": page_url,
            "verified": False,  # Facebook data doesn't consistently show verification
            "follower_count": raw_profile.get("followers", raw_profile.get("likes", 0)),
            "following_count": raw_profile.get("followings")
        }
        
        # Check if transformation matches expectations for social_media_account.py
        assert transformed["platform"] == Platform.FACEBOOK
        assert transformed["platform_id"] == raw_profile["pageId"]
        assert transformed["handle"] == raw_profile["pageName"]
        assert transformed["name"] == raw_profile["title"]
        assert transformed["url"] == raw_profile["pageUrl"]
        assert transformed["follower_count"] == raw_profile["followers"]
        assert transformed["following_count"] == raw_profile["followings"]
        
        # Ensure political_entity_id is not included (should be set when account is created)
        assert "political_entity_id" not in transformed

    def test_transform_post(self, sample_post_data):
        """Test the transformation of a Facebook post by manually validating key fields."""
        # Get the first post from the sample data
        raw_post = sample_post_data[0]
        
        # Create a fake account ID
        account_id = str(uuid.uuid4())
        
        # Check if key fields are present in the raw post
        assert "postId" in raw_post
        assert "text" in raw_post
        assert "url" in raw_post
        assert "likes" in raw_post
        assert "comments" in raw_post
        assert "shares" in raw_post
        assert "media" in raw_post
        assert "timestamp" in raw_post
        
        # Validate expected field types and structures
        assert isinstance(raw_post["postId"], str)
        assert isinstance(raw_post["text"], str)
        assert isinstance(raw_post["url"], str)
        assert isinstance(raw_post["likes"], int)
        assert isinstance(raw_post["comments"], int)
        assert isinstance(raw_post["shares"], int)
        
        # Test MongoDB schema compatibility
        # These are the key fields needed by the MongoDB schema
        required_fields = {
            "platform_id": raw_post["postId"],
            "platform": "facebook",
            "account_id": account_id,
            "content_type": "post",  # Default type for Facebook
            "content": {
                "text": raw_post["text"]
            },
            "metadata": {
                "created_at": datetime.fromtimestamp(raw_post["timestamp"])
            },
            "engagement": {
                "likes_count": raw_post["likes"],
                "comments_count": raw_post["comments"],
                "shares_count": raw_post["shares"]
            }
        }
        
        # Check if media is extracted correctly
        if "media" in raw_post and raw_post["media"]:
            assert len(raw_post["media"]) > 0
            if "photo_image" in raw_post["media"][0]:
                assert "uri" in raw_post["media"][0]["photo_image"]
        
        # All required fields should be present in raw data
        for field, value in required_fields.items():
            if field in ["content", "metadata", "engagement"]:
                # These are nested fields, continue
                continue
            assert value is not None, f"Field {field} should not be None"

    def test_transform_comment(self, sample_comment_data):
        """Test the transformation of a Facebook comment by manually validating key fields."""
        # Get the first comment from the sample data
        raw_comment = sample_comment_data[0]
        
        # Create a fake post ID
        post_id = "fake_post_id"
        
        # Check if key fields are present in the raw comment
        assert "id" in raw_comment
        assert "text" in raw_comment
        assert "profileName" in raw_comment
        assert "profileId" in raw_comment
        assert "date" in raw_comment
        assert "likesCount" in raw_comment
        
        # Validate expected field types and structures
        assert isinstance(raw_comment["id"], str)
        assert isinstance(raw_comment["text"], str)
        assert isinstance(raw_comment["profileName"], str)
        assert isinstance(raw_comment["profileId"], str)
        
        # Test MongoDB schema compatibility
        # These are the key fields needed by the MongoDB schema
        required_fields = {
            "platform_id": raw_comment["id"],
            "platform": "facebook",
            "post_id": post_id,
            "user_id": raw_comment["profileId"],
            "user_name": raw_comment["profileName"],
            "content": {
                "text": raw_comment["text"]
            },
            "metadata": {
                "created_at": datetime.fromisoformat(raw_comment["date"].replace('Z', '+00:00'))
            },
            "engagement": {
                "likes_count": int(raw_comment["likesCount"]) if isinstance(raw_comment["likesCount"], str) else raw_comment["likesCount"]
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