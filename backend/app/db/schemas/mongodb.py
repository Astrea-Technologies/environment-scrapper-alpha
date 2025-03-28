"""
MongoDB schema definitions using Pydantic models.

This module defines Pydantic models for MongoDB collections used for
storing social media content and engagement data in the Political
Social Media Analysis Platform.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
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
                "text": "Hoy tuve el honor de participar en la inauguración del Foro de Alianzas para el Hábitat capítulo Monterrey, un espacio clave para construir la ciudad del futuro.",
                "media": ["https://scontent-iad3-1.cdninstagram.com/v/t51.2885-15/481585399_18485585482052530_5292288465090866871_n.jpg"],
                "links": [],
                "hashtags": ["AquíSeResuelve"],
                "mentions": []
            }
        }


class Dimensions(BaseModel):
    """Image or video dimensions."""
    height: int
    width: int


class LocationInfo(BaseModel):
    """Location information for social media posts."""
    name: Optional[str] = None
    id: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None


class Owner(BaseModel):
    """Account owner information."""
    username: str
    id: str
    verified: bool = False


class TaggedUser(BaseModel):
    """User tagged in a post."""
    username: str
    id: str
    full_name: Optional[str] = None
    is_verified: bool = False


class PostMetadata(BaseModel):
    """Metadata sub-schema for social media posts."""
    created_at: datetime
    language: str
    location: Optional[LocationInfo] = None
    client: Optional[str] = None
    is_repost: bool = False
    is_reply: bool = False
    dimensions: Optional[Dimensions] = None
    alt_text: Optional[str] = None
    product_type: Optional[str] = None
    owner: Optional[Owner] = None
    tagged_users: List[TaggedUser] = []
    
    class Config:
        schema_extra = {
            "example": {
                "created_at": "2025-02-26T20:35:33.000Z",
                "language": "es",
                "location": {
                    "name": "U-ERRE Universidad Regiomontana",
                    "id": "1954214947989485",
                    "country": "Mexico",
                    "state": "Nuevo León",
                    "city": "Monterrey"
                },
                "client": "Instagram Web",
                "is_repost": False,
                "is_reply": False,
                "dimensions": {
                    "height": 717,
                    "width": 1080
                },
                "alt_text": "Photo by Adrián de la Garza on February 26, 2025. May be an image of 10 people and text.",
                "product_type": None,
                "owner": {
                    "username": "adriandelagarzas",
                    "id": "1483444529",
                    "verified": True
                },
                "tagged_users": [
                    {
                        "username": "userexample",
                        "id": "123456789",
                        "full_name": "User Example",
                        "is_verified": False
                    }
                ]
            }
        }


class PostEngagement(BaseModel):
    """Engagement metrics sub-schema for social media posts."""
    likes_count: int = 0
    shares_count: Optional[int] = None
    comments_count: int = 0
    views_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    saves_count: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "likes_count": 153,
                "shares_count": None,
                "comments_count": 16,
                "views_count": None,
                "engagement_rate": 0.97,
                "saves_count": None
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
                "sentiment_score": None,
                "topics": [],
                "entities_mentioned": [],
                "key_phrases": [],
                "emotional_tone": None
            }
        }


class ChildPost(BaseModel):
    """Child post in a carousel/sidecar post."""
    id: str
    type: str  # Image, Video
    url: Optional[HttpUrl] = None
    display_url: HttpUrl
    dimensions: Optional[Dimensions] = None
    alt_text: Optional[str] = None


class VideoData(BaseModel):
    """Video-specific data for video posts."""
    duration: Optional[float] = None  # In seconds
    video_url: Optional[HttpUrl] = None
    thumbnail_url: Optional[HttpUrl] = None
    is_muted: bool = False


class SocialMediaPost(BaseModel):
    """
    Schema for social media posts stored in MongoDB.
    
    This model represents a post from various social media platforms
    including its content, metadata, engagement metrics, and analysis.
    """
    platform_id: str = Field(..., description="Original ID from the social media platform")
    platform: str = Field(..., description="Social media platform name (e.g., twitter, facebook)")
    account_id: UUID = Field(..., description="Reference to PostgreSQL SocialMediaAccount UUID")
    content_type: str = Field(..., description="Type of post (e.g., post, sidecar, video)")
    short_code: Optional[str] = Field(None, description="Platform shortcode for URL (e.g., Instagram)")
    url: Optional[HttpUrl] = Field(None, description="Direct URL to the post")
    
    content: PostContent
    metadata: PostMetadata
    engagement: PostEngagement
    analysis: Optional[PostAnalysis] = None
    child_posts: Optional[List[ChildPost]] = None
    video_data: Optional[VideoData] = None
    vector_id: Optional[str] = Field(None, description="Reference to vector database entry")
    
    class Config:
        schema_extra = {
            "example": {
                "platform_id": "3576752389826611363",
                "platform": "instagram",
                "account_id": "123e4567-e89b-12d3-a456-426614174000",
                "content_type": "sidecar",
                "short_code": "DGjLVkdJQij",
                "url": "https://www.instagram.com/p/DGjLVkdJQij/",
                "content": {
                    "text": "Hoy tuve el honor de participar en la inauguración del Foro de Alianzas para el Hábitat capítulo Monterrey, un espacio clave para construir la ciudad del futuro.",
                    "media": ["https://scontent-iad3-1.cdninstagram.com/v/t51.2885-15/481585399_18485585482052530_5292288465090866871_n.jpg"],
                    "links": [],
                    "hashtags": ["AquíSeResuelve"],
                    "mentions": []
                },
                "metadata": {
                    "created_at": "2025-02-26T20:35:33.000Z",
                    "language": "es",
                    "location": {
                        "name": "U-ERRE Universidad Regiomontana",
                        "id": "1954214947989485",
                        "country": "Mexico",
                        "state": "Nuevo León",
                        "city": "Monterrey"
                    },
                    "client": "Instagram Web",
                    "is_repost": False,
                    "is_reply": False,
                    "dimensions": {
                        "height": 717,
                        "width": 1080
                    },
                    "alt_text": "Photo by Adrián de la Garza on February 26, 2025. May be an image of 10 people and text.",
                    "product_type": None,
                    "owner": {
                        "username": "adriandelagarzas",
                        "id": "1483444529",
                        "verified": True
                    },
                    "tagged_users": [
                        {
                            "username": "userexample",
                            "id": "123456789",
                            "full_name": "User Example",
                            "is_verified": False
                        }
                    ]
                },
                "engagement": {
                    "likes_count": 153,
                    "shares_count": None,
                    "comments_count": 16,
                    "views_count": None,
                    "engagement_rate": 0.97,
                    "saves_count": None
                },
                "child_posts": [
                    {
                        "id": "3576752376539157068",
                        "type": "Image",
                        "url": "https://www.instagram.com/p/DGjLVYFJpJM/",
                        "display_url": "https://scontent-iad3-1.cdninstagram.com/v/t51.2885-15/481585399_18485585482052530_5292288465090866871_n.jpg",
                        "dimensions": {
                            "height": 717,
                            "width": 1080
                        },
                        "alt_text": "Photo by Adrián de la Garza on February 26, 2025."
                    }
                ],
                "analysis": {
                    "sentiment_score": None,
                    "topics": [],
                    "entities_mentioned": [],
                    "key_phrases": [],
                    "emotional_tone": None
                },
                "video_data": {
                    "duration": None,
                    "video_url": None,
                    "thumbnail_url": None,
                    "is_muted": False
                },
                "vector_id": None
            }
        }


class CommentContent(BaseModel):
    """Content sub-schema for social media comments."""
    text: str
    media: List[HttpUrl] = []
    mentions: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "text": "👏👏",
                "media": [],
                "mentions": []
            }
        }


class CommentMetadata(BaseModel):
    """Metadata sub-schema for social media comments."""
    created_at: datetime
    language: str
    location: Optional[Dict[str, Any]] = None
    is_reply: bool = False
    parent_comment_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "created_at": "2025-02-27T01:31:50.000Z",
                "language": "es",
                "location": None,
                "is_reply": False,
                "parent_comment_id": None
            }
        }


class CommentEngagement(BaseModel):
    """Engagement metrics sub-schema for social media comments."""
    likes_count: int = 0
    replies_count: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "likes_count": 2,
                "replies_count": 1
            }
        }


class CommentAnalysis(BaseModel):
    """Content analysis sub-schema for social media comments."""
    sentiment_score: Optional[float] = None
    emotional_tone: Optional[str] = None
    toxicity_flag: Optional[bool] = None
    entities_mentioned: List[str] = []
    language_detected: Optional[str] = None
    contains_question: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "sentiment_score": None,
                "emotional_tone": None,
                "toxicity_flag": False,
                "entities_mentioned": [],
                "language_detected": None,
                "contains_question": False
            }
        }


class CommentUserDetails(BaseModel):
    """Additional user information for comment authors."""
    fbid_v2: Optional[int] = None
    is_mentionable: Optional[bool] = None
    latest_reel_media: Optional[int] = None
    profile_pic_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "fbid_v2": 17841415278525780,
                "is_mentionable": True,
                "latest_reel_media": 0,
                "profile_pic_id": "3422370971825093335"
            }
        }


class CommentReply(BaseModel):
    """Reply to a comment."""
    platform_id: str
    user_id: str
    user_name: str
    user_full_name: Optional[str] = None
    user_profile_pic: Optional[HttpUrl] = None
    user_verified: bool = False
    text: str
    created_at: datetime
    likes_count: int = 0
    replies_count: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "platform_id": "17917498377065887",
                "user_id": "1483444529",
                "user_name": "adriandelagarzas",
                "user_full_name": "Adrián de la Garza",
                "user_profile_pic": "https://scontent-ber1-1.cdninstagram.com/v/t51.2885-19/476009956_676359164713921_5513413720214908264_n.jpg",
                "user_verified": True,
                "text": "@oscarcuellocoronado 🙌🏼😄",
                "created_at": "2025-02-27T01:39:10.000Z",
                "likes_count": 0,
                "replies_count": 0
            }
        }


class SocialMediaComment(BaseModel):
    """
    Schema for social media comments stored in MongoDB.
    
    This model represents a comment on a social media post including
    its content, metadata, engagement metrics, replies, and analysis.
    """
    platform_id: str = Field(..., description="Original ID from the social media platform")
    platform: str = Field(..., description="Social media platform name (e.g., twitter, facebook)")
    post_id: str = Field(..., description="Reference to MongoDB post ID")
    post_url: Optional[HttpUrl] = Field(None, description="URL of the original post")
    
    user_id: str = Field(..., description="ID of the commenter")
    user_name: str = Field(..., description="Username of the commenter")
    user_full_name: Optional[str] = Field(None, description="Full display name of the commenter")
    user_profile_pic: Optional[HttpUrl] = Field(None, description="Profile picture URL of the commenter")
    user_verified: bool = Field(False, description="Whether the user has a verification badge")
    user_private: bool = Field(False, description="Whether the user's account is private")
    
    content: CommentContent
    metadata: CommentMetadata
    engagement: CommentEngagement
    
    replies: List[CommentReply] = []
    
    analysis: Optional[CommentAnalysis] = None
    user_details: Optional[CommentUserDetails] = None
    vector_id: Optional[str] = Field(None, description="Reference to vector database entry")
    
    class Config:
        schema_extra = {
            "example": {
                "platform_id": "18021118748474094",
                "platform": "instagram",
                "post_id": "3576752389826611363",
                "post_url": "https://www.instagram.com/p/DGjLVkdJQij/",
                
                "user_id": "15166237284",
                "user_name": "oscarcuellocoronado",
                "user_full_name": "Oscar Cuello",
                "user_profile_pic": "https://scontent-ber1-1.cdninstagram.com/v/t51.2885-19/453036863_994371468987224_3689516965341685068_n.jpg",
                "user_verified": False,
                "user_private": False,
                
                "content": {
                    "text": "👏👏",
                    "media": [],
                    "mentions": []
                },
                
                "metadata": {
                    "created_at": "2025-02-27T01:31:50.000Z",
                    "language": "es",
                    "location": None,
                    "is_reply": False,
                    "parent_comment_id": None
                },
                
                "engagement": {
                    "likes_count": 2,
                    "replies_count": 1
                },
                
                "replies": [
                    {
                        "platform_id": "17917498377065887",
                        "user_id": "1483444529",
                        "user_name": "adriandelagarzas",
                        "user_full_name": "Adrián de la Garza",
                        "user_profile_pic": "https://scontent-ber1-1.cdninstagram.com/v/t51.2885-19/476009956_676359164713921_5513413720214908264_n.jpg",
                        "user_verified": True,
                        "text": "@oscarcuellocoronado 🙌🏼😄",
                        "created_at": "2025-02-27T01:39:10.000Z",
                        "likes_count": 0,
                        "replies_count": 0
                    }
                ],
                
                "analysis": {
                    "sentiment_score": None,
                    "emotional_tone": None,
                    "toxicity_flag": False,
                    "entities_mentioned": [],
                    "language_detected": None,
                    "contains_question": False
                },
                
                "user_details": {
                    "fbid_v2": 17841415278525780,
                    "is_mentionable": True,
                    "latest_reel_media": 0,
                    "profile_pic_id": "3422370971825093335"
                },
                
                "vector_id": None
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