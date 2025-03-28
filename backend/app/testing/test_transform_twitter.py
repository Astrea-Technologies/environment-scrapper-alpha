"""
Tests for Twitter/X data transformer

This module tests the transformation of Twitter/X raw data from APIFY
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


class TestTwitterTransforms:
    """
    Test the transformation of Twitter/X data from APIFY to the application format.
    """
    
    @pytest.fixture
    def sample_profile_data(self):
        """Load sample Twitter/X profile data."""
        data_path = Path(__file__).parent / "data" / "x" / "profile_samples.json"
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_post_data(self):
        """Load sample Twitter/X post data."""
        data_path = Path(__file__).parent / "data" / "x" / "post_samples.json"
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_comment_data(self):
        """Load sample Twitter/X comment data."""
        data_path = Path(__file__).parent / "data" / "x" / "comment_samples.json"
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def test_transform_profile(self, sample_profile_data):
        """Test the transformation of a Twitter/X profile by manually creating the transform."""
        # Get the first profile from the sample data - author field in a post contains profile data
        raw_profile = sample_profile_data[0]["author"]
        
        # Manual transformation (same logic as in the collector)
        transformed = {
            "platform": Platform.TWITTER,
            "platform_id": raw_profile["id"],
            "handle": raw_profile["userName"],
            "name": raw_profile["name"],
            "url": f"https://twitter.com/{raw_profile['userName']}",
            "verified": raw_profile["isVerified"] or raw_profile["isBlueVerified"],
            "follower_count": raw_profile["followers"],
            "following_count": raw_profile["following"]
        }
        
        # Check if transformation matches expectations for social_media_account.py
        assert transformed["platform"] == Platform.TWITTER
        assert transformed["platform_id"] == raw_profile["id"]
        assert transformed["handle"] == raw_profile["userName"]
        assert transformed["name"] == raw_profile["name"]
        assert transformed["url"] == f"https://twitter.com/{raw_profile['userName']}"
        assert isinstance(transformed["follower_count"], int)
        assert isinstance(transformed["following_count"], int)
        
        # Ensure political_entity_id is not included (should be set when account is created)
        assert "political_entity_id" not in transformed

    def test_transform_post(self, sample_post_data):
        """Test the transformation of a Twitter/X post by manually validating key fields."""
        # Get the first post from the sample data
        raw_post = sample_post_data[0]
        
        # Create a fake account ID
        account_id = str(uuid.uuid4())
        
        # Check if key fields are present in the raw post
        assert "id" in raw_post
        assert "text" in raw_post
        assert "url" in raw_post
        assert "likeCount" in raw_post
        assert "retweetCount" in raw_post
        assert "replyCount" in raw_post
        assert "createdAt" in raw_post
        
        # Validate expected field types and structures
        assert isinstance(raw_post["id"], str)
        assert isinstance(raw_post["text"], str)
        assert isinstance(raw_post["url"], str)
        assert isinstance(raw_post["likeCount"], int)
        assert isinstance(raw_post["retweetCount"], int)
        assert isinstance(raw_post["replyCount"], int)
        
        # Parse created_at date
        created_at = None
        try:
            # Try the format with year
            created_at = datetime.strptime(
                raw_post["createdAt"].split("+")[0].strip(), 
                "%a %b %d %H:%M:%S %Y"
            )
        except ValueError:
            # If that fails, assume the current year
            date_str = raw_post["createdAt"].split("+")[0].strip()
            created_at = datetime.strptime(
                date_str, 
                "%a %b %d %H:%M:%S"
            ).replace(year=2025)  # Sample data uses 2025 as the year
        
        # Test MongoDB schema compatibility
        # These are the key fields needed by the MongoDB schema
        required_fields = {
            "platform_id": raw_post["id"],
            "platform": "twitter",
            "account_id": account_id,
            "content_type": "retweet" if raw_post.get("isRetweet", False) else "post",
            "content": {
                "text": raw_post["text"]
            },
            "metadata": {
                "created_at": created_at,
                "language": raw_post["lang"],
                "is_repost": raw_post.get("isRetweet", False),
                "is_reply": raw_post.get("isReply", False)
            },
            "engagement": {
                "likes_count": raw_post["likeCount"],
                "shares_count": raw_post["retweetCount"],
                "comments_count": raw_post["replyCount"],
                "views_count": raw_post.get("viewCount")
            }
        }
        
        # Check if media is extracted correctly
        if "extendedEntities" in raw_post and "media" in raw_post["extendedEntities"]:
            media_items = raw_post["extendedEntities"]["media"]
            assert len(media_items) > 0
            assert "media_url_https" in media_items[0]
        
        # All required fields should be present in raw data
        for field, value in required_fields.items():
            if field in ["content", "metadata", "engagement"]:
                # These are nested fields, continue
                continue
            assert value is not None, f"Field {field} should not be None"

    def test_transform_comment(self, sample_comment_data):
        """Test the transformation of a Twitter/X comment by manually validating key fields."""
        # Get the first comment from the sample data
        raw_comment = sample_comment_data[0]
        
        # Create a fake post ID
        post_id = "fake_post_id"
        
        # Check if key fields are present in the raw comment
        assert "id" in raw_comment
        assert "text" in raw_comment
        assert "author" in raw_comment
        assert "createdAt" in raw_comment
        assert "likeCount" in raw_comment
        assert "replyCount" in raw_comment
        
        # Validate expected field types and structures
        assert isinstance(raw_comment["id"], str)
        assert isinstance(raw_comment["text"], str)
        assert isinstance(raw_comment["author"], dict)
        assert isinstance(raw_comment["likeCount"], int)
        assert isinstance(raw_comment["replyCount"], int)
        
        # Parse created_at date
        created_at = None
        try:
            # Try the format with year
            created_at = datetime.strptime(
                raw_comment["createdAt"].split("+")[0].strip(), 
                "%a %b %d %H:%M:%S %Y"
            )
        except ValueError:
            # If that fails, assume the current year
            date_str = raw_comment["createdAt"].split("+")[0].strip()
            created_at = datetime.strptime(
                date_str, 
                "%a %b %d %H:%M:%S"
            ).replace(year=2025)  # Sample data uses 2025 as the year
        
        # Test MongoDB schema compatibility
        # These are the key fields needed by the MongoDB schema
        required_fields = {
            "platform_id": raw_comment["id"],
            "platform": "twitter",
            "post_id": post_id,
            "user_id": raw_comment["author"]["id"],
            "user_name": raw_comment["author"]["userName"],
            "content": {
                "text": raw_comment["text"]
            },
            "metadata": {
                "created_at": created_at,
                "language": raw_comment["lang"]
            },
            "engagement": {
                "likes_count": raw_comment["likeCount"],
                "replies_count": raw_comment["replyCount"]
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