"""
Redis schema definitions and key pattern constants.

This module defines the key patterns and data structures used for Redis caching
and real-time operations in the Political Social Media Analysis Platform.

NOTE: NOT USED IN MVP - This implementation is reserved for future releases.
Redis functionality is disabled in the MVP to simplify initial deployment.
When activating Redis, ensure the appropriate dependencies are installed
and the feature flags are enabled in the application configuration.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Any


# Key pattern constants with namespaces
class KeyPatterns:
    """Constants for Redis key patterns with appropriate namespaces."""
    
    # Namespace prefix for all keys to avoid collisions
    NAMESPACE = "psm"  # Political Social Media prefix
    
    # Entity metrics cache keys
    ENTITY_METRICS = f"{NAMESPACE}:entity:{{entity_id}}:metrics"  # Hash
    ENTITY_ENGAGEMENT = f"{NAMESPACE}:entity:{{entity_id}}:engagement"  # Hash
    ENTITY_MENTIONS = f"{NAMESPACE}:entity:{{entity_id}}:mentions"  # Sorted Set
    ENTITY_SENTIMENT = f"{NAMESPACE}:entity:{{entity_id}}:sentiment"  # Hash
    
    # Trending topics keys
    TRENDING_TOPICS = f"{NAMESPACE}:trending:topics:{{timeframe}}"  # Sorted Set
    TRENDING_HASHTAGS = f"{NAMESPACE}:trending:hashtags:{{timeframe}}"  # Sorted Set
    TRENDING_ENTITIES = f"{NAMESPACE}:trending:entities:{{timeframe}}"  # Sorted Set
    
    # Activity stream keys
    ACTIVITY_ENTITY = f"{NAMESPACE}:activity:entity:{{entity_id}}"  # List
    ACTIVITY_USER = f"{NAMESPACE}:activity:user:{{user_id}}"  # List
    ACTIVITY_GLOBAL = f"{NAMESPACE}:activity:global"  # List
    
    # Real-time alerts keys
    ALERTS_ENTITY = f"{NAMESPACE}:alerts:entity:{{entity_id}}"  # Sorted Set
    ALERTS_USER = f"{NAMESPACE}:alerts:user:{{user_id}}"  # Sorted Set
    ALERTS_TOPIC = f"{NAMESPACE}:alerts:topic:{{topic}}"  # Pub/Sub Channel
    
    # API rate limiting
    RATE_LIMIT_IP = f"{NAMESPACE}:ratelimit:ip:{{ip_address}}"  # String with counter
    RATE_LIMIT_USER = f"{NAMESPACE}:ratelimit:user:{{user_id}}"  # String with counter


class TimeFrames(Enum):
    """Time frames for trending data and expiration."""
    HOUR = "1h"
    SIX_HOURS = "6h"
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1m"


class TTLValues:
    """TTL (Time To Live) values in seconds for different types of data."""
    # Short-lived caches
    SHORT = 60 * 5  # 5 minutes
    MEDIUM = 60 * 30  # 30 minutes
    STANDARD = 60 * 60  # 1 hour
    
    # Time-frame specific TTLs
    HOUR_DATA = 60 * 60  # 1 hour
    SIX_HOUR_DATA = 60 * 60 * 6  # 6 hours
    DAY_DATA = 60 * 60 * 24  # 24 hours
    WEEK_DATA = 60 * 60 * 24 * 7  # 7 days
    MONTH_DATA = 60 * 60 * 24 * 30  # 30 days
    
    # Rate limiting TTLs
    RATE_LIMIT_WINDOW = 60 * 15  # 15 minutes
    
    @classmethod
    def for_timeframe(cls, timeframe: TimeFrames) -> int:
        """Get TTL value for a specific timeframe."""
        mapping = {
            TimeFrames.HOUR: cls.HOUR_DATA,
            TimeFrames.SIX_HOURS: cls.SIX_HOUR_DATA,
            TimeFrames.DAY: cls.DAY_DATA,
            TimeFrames.WEEK: cls.WEEK_DATA,
            TimeFrames.MONTH: cls.MONTH_DATA,
        }
        return mapping.get(timeframe, cls.STANDARD)


class StreamConfig:
    """Configuration for Redis Stream and List data structures."""
    # Maximum number of items in activity streams
    MAX_STREAM_LENGTH = 1000
    # Trim strategy: "~" means approximate trimming (faster)
    TRIM_STRATEGY = "~"
    # When to trigger trimming (percentage of MAX_STREAM_LENGTH)
    TRIM_THRESHOLD = 1.2


class EntityMetricsFields:
    """Field names for entity metrics Redis Hash."""
    # Engagement metrics
    POSTS_COUNT = "posts_count"
    TOTAL_LIKES = "total_likes"
    TOTAL_SHARES = "total_shares"
    TOTAL_COMMENTS = "total_comments"
    TOTAL_VIEWS = "total_views"
    AVG_ENGAGEMENT_RATE = "avg_engagement_rate"
    
    # Sentiment metrics
    AVG_SENTIMENT = "avg_sentiment"
    SENTIMENT_POSITIVE = "sentiment_positive"
    SENTIMENT_NEUTRAL = "sentiment_neutral"
    SENTIMENT_NEGATIVE = "sentiment_negative"
    
    # Temporal metrics
    LAST_ACTIVE = "last_active"
    LAST_UPDATED = "last_updated"
    
    # All field names as a set for convenience
    ALL_FIELDS = {
        POSTS_COUNT, TOTAL_LIKES, TOTAL_SHARES, TOTAL_COMMENTS, TOTAL_VIEWS, 
        AVG_ENGAGEMENT_RATE, AVG_SENTIMENT, SENTIMENT_POSITIVE, 
        SENTIMENT_NEUTRAL, SENTIMENT_NEGATIVE, LAST_ACTIVE, LAST_UPDATED
    }


class AlertPriority(Enum):
    """Priority levels for real-time alerts."""
    LOW = 1
    MEDIUM = 5
    HIGH = 10
    CRITICAL = 20


class RedisSchemas:
    """
    Schema definitions for Redis data structures.
    
    This class provides documentation about the Redis data structures
    used for different types of data in the application.
    """
    
    @staticmethod
    def entity_metrics_schema() -> Dict[str, str]:
        """
        Entity metrics schema using Redis Hash.
        
        Key pattern: KeyPatterns.ENTITY_METRICS
        Data structure: Hash
        TTL: TTLValues.STANDARD
        Operations: HSET, HGET, HINCRBY, HGETALL
        
        Returns:
            Dict mapping field names to descriptions
        """
        return {
            EntityMetricsFields.POSTS_COUNT: "Total number of posts by the entity",
            EntityMetricsFields.TOTAL_LIKES: "Sum of likes across all posts",
            EntityMetricsFields.TOTAL_SHARES: "Sum of shares across all posts",
            EntityMetricsFields.TOTAL_COMMENTS: "Sum of comments across all posts",
            EntityMetricsFields.TOTAL_VIEWS: "Sum of views across all posts",
            EntityMetricsFields.AVG_ENGAGEMENT_RATE: "Average engagement rate across all posts",
            EntityMetricsFields.AVG_SENTIMENT: "Average sentiment score (-1 to 1)",
            EntityMetricsFields.SENTIMENT_POSITIVE: "Count of positive sentiment posts",
            EntityMetricsFields.SENTIMENT_NEUTRAL: "Count of neutral sentiment posts",
            EntityMetricsFields.SENTIMENT_NEGATIVE: "Count of negative sentiment posts",
            EntityMetricsFields.LAST_ACTIVE: "Timestamp of last activity",
            EntityMetricsFields.LAST_UPDATED: "Timestamp when metrics were last updated",
        }
    
    @staticmethod
    def trending_topics_schema() -> Dict[str, Any]:
        """
        Trending topics schema using Redis Sorted Set.
        
        Key pattern: KeyPatterns.TRENDING_TOPICS
        Data structure: Sorted Set
        TTL: Based on timeframe (e.g., TTLValues.HOUR_DATA for hourly trends)
        Operations: ZADD, ZINCRBY, ZREVRANGE, ZREVRANGEBYSCORE
        Score: Engagement score or mention count
        
        Returns:
            Dict with schema information
        """
        return {
            "data_structure": "Sorted Set",
            "members": "Topic identifiers or hashtags",
            "score": "Engagement score calculated from mentions, likes, shares, etc.",
            "sort_order": "Descending by score (highest score first)",
            "expiration": "Based on timeframe (hour, day, week, etc.)",
            "operations": ["ZADD", "ZINCRBY", "ZREVRANGE", "ZREVRANGEBYSCORE"],
            "use_cases": [
                "Display trending topics for a time period",
                "Track topic momentum (rate of score increase)",
                "Identify viral content in early stages",
            ],
        }
    
    @staticmethod
    def activity_stream_schema() -> Dict[str, Any]:
        """
        Activity stream schema using Redis List.
        
        Key pattern: KeyPatterns.ACTIVITY_ENTITY
        Data structure: List
        TTL: None (manual trimming via LTRIM)
        Operations: LPUSH, LRANGE, LTRIM
        Max length: StreamConfig.MAX_STREAM_LENGTH
        
        Returns:
            Dict with schema information
        """
        return {
            "data_structure": "List",
            "elements": "JSON-serialized activity events",
            "order": "Newest first (LPUSH for adding new items)",
            "trim_strategy": f"Manual trimming when length exceeds {StreamConfig.MAX_STREAM_LENGTH * StreamConfig.TRIM_THRESHOLD}",
            "operations": ["LPUSH", "LRANGE", "LTRIM"],
            "event_format": {
                "id": "Unique event ID",
                "type": "Activity type (post, comment, mention, etc.)",
                "timestamp": "ISO-8601 timestamp",
                "actor": "Entity or user who performed the action",
                "object": "Target of the action",
                "metadata": "Additional activity-specific information",
            },
            "use_cases": [
                "Generate activity feeds for users or entities",
                "Track recent events for monitoring",
                "Power real-time dashboards",
            ],
        }
    
    @staticmethod
    def real_time_alerts_schema() -> Dict[str, Any]:
        """
        Real-time alerts schema using Redis Sorted Set and Pub/Sub.
        
        Key patterns: 
        - KeyPatterns.ALERTS_ENTITY (Sorted Set)
        - KeyPatterns.ALERTS_TOPIC (Pub/Sub Channel)
        
        Data structures:
        - Sorted Set for persistent alerts
        - Pub/Sub for immediate notifications
        
        TTL: None for Sorted Set (manual cleanup), N/A for Pub/Sub
        Operations: 
        - Sorted Set: ZADD, ZREVRANGE, ZREM
        - Pub/Sub: PUBLISH, SUBSCRIBE
        
        Returns:
            Dict with schema information
        """
        return {
            "data_structures": ["Sorted Set", "Pub/Sub Channels"],
            "sorted_set": {
                "members": "JSON-serialized alert objects",
                "score": "Priority level combined with timestamp for time-based ordering",
                "operations": ["ZADD", "ZREVRANGE", "ZREM"],
                "cleanup": "Manual removal of acknowledged or expired alerts",
            },
            "pub_sub": {
                "channels": [
                    f"{KeyPatterns.NAMESPACE}:alerts:entity:*",
                    f"{KeyPatterns.NAMESPACE}:alerts:topic:*",
                ],
                "message_format": {
                    "id": "Unique alert ID",
                    "priority": "Alert priority (LOW, MEDIUM, HIGH, CRITICAL)",
                    "type": "Alert type (mention, trend, engagement_spike, etc.)",
                    "timestamp": "ISO-8601 timestamp",
                    "subject": "Entity or topic that triggered the alert",
                    "message": "Human-readable alert message",
                    "data": "Additional alert-specific data",
                },
                "operations": ["PUBLISH", "SUBSCRIBE", "UNSUBSCRIBE"],
            },
            "use_cases": [
                "Send notifications about important events",
                "Alert monitoring systems about anomalies",
                "Trigger automated responses to specific events",
            ],
        } 