"""
MongoDB schema definitions using Pydantic models.

This module defines Pydantic models for MongoDB collections used for
storing social media content and engagement data in the Political
Social Media Analysis Platform.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class PostContent(BaseModel):
    """Content sub-schema for social media posts."""
    text: str
    media: List[HttpUrl] = []
    links: List[HttpUrl] = []
    hashtags: List[str] = []
    mentions: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "text": "Excited to announce our new policy on #ClimateChange with @EPA",
                "media": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
                "links": ["https://example.com/policy"],
                "hashtags": ["ClimateChange", "GreenFuture"],
                "mentions": ["EPA", "WhiteHouse"]
            }
        }


class PostMetadata(BaseModel):
    """Metadata sub-schema for social media posts."""
    created_at: datetime
    language: str
    location: Optional[Dict[str, Any]] = None
    client: Optional[str] = None
    is_repost: bool = False
    is_reply: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "created_at": "2023-06-15T14:32:19Z",
                "language": "en",
                "location": {"country": "USA", "state": "DC"},
                "client": "Twitter Web App",
                "is_repost": False,
                "is_reply": False
            }
        }


class PostEngagement(BaseModel):
    """Engagement metrics sub-schema for social media posts."""
    likes_count: int = 0
    shares_count: int = 0
    comments_count: int = 0
    views_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    
    class Config:
        schema_extra = {
            "example": {
                "likes_count": 1245,
                "shares_count": 327,
                "comments_count": 89,
                "views_count": 15720,
                "engagement_rate": 3.8
            }
        }


class PostAnalysis(BaseModel):
    """Content analysis sub-schema for social media posts."""
    sentiment_score: Optional[float] = None
    topics: List[str] = []
    entities_mentioned: List[str] = []
    key_phrases: List[str] = []
    emotional_tone: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "sentiment_score": 0.64,
                "topics": ["climate", "environment", "policy"],
                "entities_mentioned": ["EPA", "Climate Change Initiative"],
                "key_phrases": ["new policy", "climate action", "sustainable future"],
                "emotional_tone": "positive"
            }
        }


class SocialMediaPost(BaseModel):
    """
    Schema for social media posts stored in MongoDB.
    
    This model represents a post from various social media platforms
    including its content, metadata, engagement metrics, and analysis.
    """
    platform_id: str = Field(..., description="Original ID from the social media platform")
    platform: str = Field(..., description="Social media platform name (e.g., twitter, facebook)")
    account_id: UUID = Field(..., description="Reference to PostgreSQL SocialMediaAccount UUID")
    content_type: str = Field(..., description="Type of post (e.g., post, story, video)")
    
    content: PostContent
    metadata: PostMetadata
    engagement: PostEngagement
    analysis: Optional[PostAnalysis] = None
    vector_id: Optional[str] = Field(None, description="Reference to vector database entry")
    
    class Config:
        schema_extra = {
            "example": {
                "platform_id": "1458794356725891073",
                "platform": "twitter",
                "account_id": "123e4567-e89b-12d3-a456-426614174000",
                "content_type": "post",
                "content": {
                    "text": "Excited to announce our new policy on #ClimateChange with @EPA",
                    "media": ["https://example.com/image1.jpg"],
                    "links": ["https://example.com/policy"],
                    "hashtags": ["ClimateChange", "GreenFuture"],
                    "mentions": ["EPA", "WhiteHouse"]
                },
                "metadata": {
                    "created_at": "2023-06-15T14:32:19Z",
                    "language": "en",
                    "location": {"country": "USA", "state": "DC"},
                    "client": "Twitter Web App",
                    "is_repost": False,
                    "is_reply": False
                },
                "engagement": {
                    "likes_count": 1245,
                    "shares_count": 327,
                    "comments_count": 89,
                    "views_count": 15720,
                    "engagement_rate": 3.8
                },
                "analysis": {
                    "sentiment_score": 0.64,
                    "topics": ["climate", "environment", "policy"],
                    "entities_mentioned": ["EPA", "Climate Change Initiative"],
                    "key_phrases": ["new policy", "climate action", "sustainable future"],
                    "emotional_tone": "positive"
                },
                "vector_id": "vec_123456789"
            }
        }


class CommentContent(BaseModel):
    """Content sub-schema for social media comments."""
    text: str
    media: Optional[List[HttpUrl]] = None
    mentions: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "text": "Great initiative! @GreenOrg should partner on this",
                "media": ["https://example.com/comment-img.jpg"],
                "mentions": ["GreenOrg"]
            }
        }


class CommentMetadata(BaseModel):
    """Metadata sub-schema for social media comments."""
    created_at: datetime
    language: str
    location: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "created_at": "2023-06-15T15:45:22Z",
                "language": "en",
                "location": {"country": "USA", "state": "CA"}
            }
        }


class CommentEngagement(BaseModel):
    """Engagement metrics sub-schema for social media comments."""
    likes_count: int = 0
    replies_count: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "likes_count": 45,
                "replies_count": 3
            }
        }


class CommentAnalysis(BaseModel):
    """Content analysis sub-schema for social media comments."""
    sentiment_score: Optional[float] = None
    emotional_tone: Optional[str] = None
    toxicity_flag: Optional[bool] = None
    entities_mentioned: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "sentiment_score": 0.78,
                "emotional_tone": "positive",
                "toxicity_flag": False,
                "entities_mentioned": ["GreenOrg"]
            }
        }


class SocialMediaComment(BaseModel):
    """
    Schema for social media comments stored in MongoDB.
    
    This model represents a comment on a social media post including
    its content, metadata, engagement metrics, and analysis.
    """
    platform_id: str = Field(..., description="Original ID from the social media platform")
    platform: str = Field(..., description="Social media platform name (e.g., twitter, facebook)")
    post_id: str = Field(..., description="Reference to MongoDB post ID")
    user_id: str = Field(..., description="User ID from the platform")
    user_name: str = Field(..., description="User name from the platform")
    
    content: CommentContent
    metadata: CommentMetadata
    engagement: CommentEngagement
    analysis: Optional[CommentAnalysis] = None
    vector_id: Optional[str] = Field(None, description="Reference to vector database entry")
    
    class Config:
        schema_extra = {
            "example": {
                "platform_id": "1458812639457283072",
                "platform": "twitter",
                "post_id": "1458794356725891073",
                "user_id": "987654321",
                "user_name": "EcoAdvocate",
                "content": {
                    "text": "Great initiative! @GreenOrg should partner on this",
                    "media": ["https://example.com/comment-img.jpg"],
                    "mentions": ["GreenOrg"]
                },
                "metadata": {
                    "created_at": "2023-06-15T15:45:22Z",
                    "language": "en",
                    "location": {"country": "USA", "state": "CA"}
                },
                "engagement": {
                    "likes_count": 45,
                    "replies_count": 3
                },
                "analysis": {
                    "sentiment_score": 0.78,
                    "emotional_tone": "positive",
                    "toxicity_flag": False,
                    "entities_mentioned": ["GreenOrg"]
                },
                "vector_id": "vec_987654321"
            }
        }


class TopicAnalysis(BaseModel):
    """
    Schema for topic analysis data stored in MongoDB.
    
    This model represents a topic that can be analyzed across social media content,
    including its definition, related keywords, and categorization.
    """
    topic_id: str = Field(..., description="Unique identifier for the topic")
    name: str = Field(..., description="Descriptive name of the topic")
    keywords: List[str] = Field(..., description="List of related keywords or phrases")
    description: Optional[str] = Field(None, description="Optional explanation of the topic")
    category: str = Field(..., description="Broader category the topic belongs to (e.g., Economy, Healthcare)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the topic was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the topic was last updated")
    
    class Config:
        schema_extra = {
            "example": {
                "topic_id": "climate_change_2023",
                "name": "Climate Change Policy",
                "keywords": ["global warming", "carbon emissions", "climate crisis", "net zero", "paris agreement"],
                "description": "Political discourse related to climate change policy measures and initiatives",
                "category": "Environment",
                "created_at": "2023-06-01T12:00:00Z",
                "updated_at": "2023-06-15T14:30:00Z"
            }
        }


class TopicOccurrence(BaseModel):
    """
    Schema for tracking where topics occur in social media content.
    
    This model represents an instance where a specific topic was detected
    in a post or comment, including detection confidence and sentiment context.
    """
    topic_id: str = Field(..., description="Reference to TopicAnalysis topic_id")
    content_id: str = Field(..., description="Reference to post or comment where topic was detected")
    content_type: str = Field(..., description="Type of content (post or comment)")
    confidence_score: float = Field(..., description="Confidence score for topic detection (0.0-1.0)")
    sentiment_context: Optional[float] = Field(None, description="Sentiment score specifically for this topic in this content")
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="When the topic was identified in this content")
    relevant_text_segment: Optional[str] = Field(None, description="The text segment where the topic was identified")
    
    class Config:
        schema_extra = {
            "example": {
                "topic_id": "climate_change_2023",
                "content_id": "60d5ec7a8f3a7c9a1b3e4f5a",
                "content_type": "post",
                "confidence_score": 0.87,
                "sentiment_context": 0.32,
                "detected_at": "2023-06-15T15:22:13Z",
                "relevant_text_segment": "Our new policy aims to address the climate crisis through significant carbon reduction measures."
            }
        }


class EntityTopicBreakdown(BaseModel):
    """Sub-model for entity breakdown in topic trends."""
    entity_id: UUID = Field(..., description="Reference to PoliticalEntity UUID")
    entity_name: str = Field(..., description="Name of the political entity")
    mention_count: int = Field(..., description="Number of times the entity mentioned this topic")
    sentiment_average: Optional[float] = Field(None, description="Average sentiment for this entity on this topic")
    
    class Config:
        schema_extra = {
            "example": {
                "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "entity_name": "Senator Smith",
                "mention_count": 15,
                "sentiment_average": 0.45
            }
        }


class PlatformTopicBreakdown(BaseModel):
    """Sub-model for platform breakdown in topic trends."""
    platform: str = Field(..., description="Name of the social media platform")
    mention_count: int = Field(..., description="Number of mentions on this platform")
    engagement_total: int = Field(..., description="Total engagement count on this platform")
    
    class Config:
        schema_extra = {
            "example": {
                "platform": "twitter",
                "mention_count": 45,
                "engagement_total": 12500
            }
        }


class TopicTrend(BaseModel):
    """
    Schema for topic trends analysis over time periods.
    
    This model represents aggregated data about topic mentions and engagement
    over specific time periods, including breakdowns by entity and platform.
    """
    topic_id: str = Field(..., description="Reference to TopicAnalysis topic_id")
    time_period: str = Field(..., description="Time period for analysis (day, week, month)")
    start_date: datetime = Field(..., description="Start date of the time period")
    end_date: datetime = Field(..., description="End date of the time period")
    frequency: int = Field(..., description="Number of occurrences during time period")
    sentiment_average: Optional[float] = Field(None, description="Average sentiment across occurrences")
    engagement_metrics: Dict[str, int] = Field(..., description="Engagement metrics related to this topic")
    entity_breakdown: List[EntityTopicBreakdown] = Field(default_factory=list, description="Breakdown by political entity")
    platform_breakdown: List[PlatformTopicBreakdown] = Field(default_factory=list, description="Breakdown by platform")
    
    class Config:
        schema_extra = {
            "example": {
                "topic_id": "climate_change_2023",
                "time_period": "week",
                "start_date": "2023-06-01T00:00:00Z",
                "end_date": "2023-06-07T23:59:59Z",
                "frequency": 187,
                "sentiment_average": 0.28,
                "engagement_metrics": {
                    "likes": 3450,
                    "shares": 876,
                    "comments": 532
                },
                "entity_breakdown": [
                    {
                        "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                        "entity_name": "Senator Smith",
                        "mention_count": 15,
                        "sentiment_average": 0.45
                    },
                    {
                        "entity_id": "223e4567-e89b-12d3-a456-426614174001",
                        "entity_name": "EPA",
                        "mention_count": 23,
                        "sentiment_average": 0.12
                    }
                ],
                "platform_breakdown": [
                    {
                        "platform": "twitter",
                        "mention_count": 45,
                        "engagement_total": 12500
                    },
                    {
                        "platform": "facebook",
                        "mention_count": 36,
                        "engagement_total": 8750
                    }
                ]
            }
        } 