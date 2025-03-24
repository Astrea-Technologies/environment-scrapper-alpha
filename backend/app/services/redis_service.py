"""
Redis service for handling caching and real-time operations.

This module provides service classes for interacting with Redis,
implementing key generation, common operations, and caching strategies
for the Political Social Media Analysis Platform.

NOTE: NOT USED IN MVP - This implementation is reserved for future releases.
Redis functionality is disabled in the MVP to simplify initial deployment.
When activating Redis, ensure the appropriate dependencies are installed
and the feature flags are enabled in the application configuration.
"""

import json
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID

import redis.asyncio as redis
from fastapi import Depends

from app.core.config import settings
from app.db.connections import get_redis
from app.db.schemas.redis_schemas import (
    AlertPriority,
    EntityMetricsFields,
    KeyPatterns,
    StreamConfig,
    TTLValues,
    TimeFrames,
)


class CachingStrategy(Enum):
    """Caching strategies for Redis operations."""
    WRITE_THROUGH = "write_through"  # Write to cache and source simultaneously
    WRITE_BACK = "write_back"  # Write to cache and asynchronously update source
    WRITE_AROUND = "write_around"  # Write directly to source, bypassing cache
    CACHE_ASIDE = "cache_aside"  # Application manages both cache and source


class RedisService:
    """
    Base Redis service for interacting with Redis cache.
    
    This service provides methods for key generation using the defined patterns
    and helper methods for common Redis operations.
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize the Redis service.
        
        Args:
            redis_client: Redis client from the connection pool
        """
        self.redis = redis_client
        self.default_caching_strategy = CachingStrategy.WRITE_THROUGH
    
    @classmethod
    async def create(cls, redis_client: redis.Redis = Depends(get_redis)) -> "RedisService":
        """
        Factory method to create a RedisService instance with dependency injection.
        
        Args:
            redis_client: Redis client from dependency injection
            
        Returns:
            Initialized RedisService instance
        """
        return cls(redis_client)
    
    # Key generation methods
    
    def entity_metrics_key(self, entity_id: Union[str, UUID]) -> str:
        """
        Generate a key for entity metrics.
        
        Args:
            entity_id: Entity UUID
            
        Returns:
            Redis key for entity metrics
        """
        return KeyPatterns.ENTITY_METRICS.format(entity_id=str(entity_id))
    
    def entity_engagement_key(self, entity_id: Union[str, UUID]) -> str:
        """
        Generate a key for entity engagement metrics.
        
        Args:
            entity_id: Entity UUID
            
        Returns:
            Redis key for entity engagement
        """
        return KeyPatterns.ENTITY_ENGAGEMENT.format(entity_id=str(entity_id))
    
    def entity_mentions_key(self, entity_id: Union[str, UUID]) -> str:
        """
        Generate a key for entity mentions tracking.
        
        Args:
            entity_id: Entity UUID
            
        Returns:
            Redis key for entity mentions
        """
        return KeyPatterns.ENTITY_MENTIONS.format(entity_id=str(entity_id))
    
    def trending_topics_key(self, timeframe: TimeFrames) -> str:
        """
        Generate a key for trending topics.
        
        Args:
            timeframe: Time frame for trending data
            
        Returns:
            Redis key for trending topics
        """
        return KeyPatterns.TRENDING_TOPICS.format(timeframe=timeframe.value)
    
    def trending_hashtags_key(self, timeframe: TimeFrames) -> str:
        """
        Generate a key for trending hashtags.
        
        Args:
            timeframe: Time frame for trending data
            
        Returns:
            Redis key for trending hashtags
        """
        return KeyPatterns.TRENDING_HASHTAGS.format(timeframe=timeframe.value)
    
    def activity_entity_key(self, entity_id: Union[str, UUID]) -> str:
        """
        Generate a key for entity activity stream.
        
        Args:
            entity_id: Entity UUID
            
        Returns:
            Redis key for entity activity stream
        """
        return KeyPatterns.ACTIVITY_ENTITY.format(entity_id=str(entity_id))
    
    def alerts_entity_key(self, entity_id: Union[str, UUID]) -> str:
        """
        Generate a key for entity alerts.
        
        Args:
            entity_id: Entity UUID
            
        Returns:
            Redis key for entity alerts
        """
        return KeyPatterns.ALERTS_ENTITY.format(entity_id=str(entity_id))
    
    def alerts_topic_channel(self, topic: str) -> str:
        """
        Generate a pub/sub channel name for topic alerts.
        
        Args:
            topic: Topic name
            
        Returns:
            Redis pub/sub channel for topic alerts
        """
        return KeyPatterns.ALERTS_TOPIC.format(topic=topic)
    
    # Hash operations
    
    async def hash_set(self, key: str, field: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a field in a Redis Hash.
        
        Args:
            key: Redis key
            field: Hash field
            value: Field value
            ttl: Optional TTL in seconds
            
        Returns:
            True if the operation was successful
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        result = await self.redis.hset(key, field, value)
        if ttl is not None:
            await self.redis.expire(key, ttl)
        return result > 0
    
    async def hash_get(self, key: str, field: str, default: Any = None) -> Any:
        """
        Get a field from a Redis Hash.
        
        Args:
            key: Redis key
            field: Hash field
            default: Default value if field does not exist
            
        Returns:
            Field value or default
        """
        value = await self.redis.hget(key, field)
        if value is None:
            return default
        
        # Try to decode JSON if the value looks like JSON
        try:
            if value.startswith(b'{') or value.startswith(b'['):
                return json.loads(value)
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            pass
        
        # Return as string or original value
        try:
            return value.decode('utf-8')
        except (AttributeError, UnicodeDecodeError):
            return value
    
    async def hash_get_all(self, key: str) -> Dict[str, Any]:
        """
        Get all fields from a Redis Hash.
        
        Args:
            key: Redis key
            
        Returns:
            Dictionary of all fields and values
        """
        result = await self.redis.hgetall(key)
        if not result:
            return {}
        
        # Process values and try to decode JSON
        decoded = {}
        for field, value in result.items():
            if isinstance(field, bytes):
                field = field.decode('utf-8')
            
            if isinstance(value, bytes):
                try:
                    value = value.decode('utf-8')
                    # Try to parse JSON
                    if value.startswith('{') or value.startswith('['):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                except UnicodeDecodeError:
                    pass
            
            decoded[field] = value
        
        return decoded
    
    async def hash_increment(self, key: str, field: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """
        Increment a numeric field in a Redis Hash.
        
        Args:
            key: Redis key
            field: Hash field
            amount: Amount to increment by
            ttl: Optional TTL in seconds
            
        Returns:
            New value of the field
        """
        result = await self.redis.hincrby(key, field, amount)
        if ttl is not None:
            await self.redis.expire(key, ttl)
        return result
    
    async def hash_increment_float(self, key: str, field: str, amount: float, ttl: Optional[int] = None) -> float:
        """
        Increment a floating-point field in a Redis Hash.
        
        Args:
            key: Redis key
            field: Hash field
            amount: Amount to increment by
            ttl: Optional TTL in seconds
            
        Returns:
            New value of the field
        """
        result = await self.redis.hincrbyfloat(key, field, amount)
        if ttl is not None:
            await self.redis.expire(key, ttl)
        return float(result)
    
    # Sorted set operations
    
    async def sorted_set_add(self, key: str, member: str, score: float, ttl: Optional[int] = None) -> int:
        """
        Add a member to a Redis Sorted Set.
        
        Args:
            key: Redis key
            member: Set member
            score: Score for the member
            ttl: Optional TTL in seconds
            
        Returns:
            Number of new members added
        """
        result = await self.redis.zadd(key, {member: score})
        if ttl is not None:
            await self.redis.expire(key, ttl)
        return result
    
    async def sorted_set_add_dict(self, key: str, member_dict: Dict[str, float], ttl: Optional[int] = None) -> int:
        """
        Add multiple members to a Redis Sorted Set.
        
        Args:
            key: Redis key
            member_dict: Dictionary mapping members to scores
            ttl: Optional TTL in seconds
            
        Returns:
            Number of new members added
        """
        result = await self.redis.zadd(key, member_dict)
        if ttl is not None:
            await self.redis.expire(key, ttl)
        return result
    
    async def sorted_set_increment(self, key: str, member: str, increment: float, ttl: Optional[int] = None) -> float:
        """
        Increment the score of a member in a Redis Sorted Set.
        
        Args:
            key: Redis key
            member: Set member
            increment: Amount to increment by
            ttl: Optional TTL in seconds
            
        Returns:
            New score of the member
        """
        result = await self.redis.zincrby(key, increment, member)
        if ttl is not None:
            await self.redis.expire(key, ttl)
        return float(result)
    
    async def sorted_set_range(
        self, key: str, start: int = 0, end: int = -1, withscores: bool = False
    ) -> Union[List[str], List[Tuple[str, float]]]:
        """
        Get members from a Redis Sorted Set by rank range.
        
        Args:
            key: Redis key
            start: Start rank (0-based)
            end: End rank (-1 means last element)
            withscores: Whether to include scores in the result
            
        Returns:
            List of members or list of (member, score) tuples
        """
        result = await self.redis.zrange(key, start, end, withscores=withscores)
        
        # Process bytes to strings
        if withscores:
            return [(m.decode('utf-8') if isinstance(m, bytes) else m, s) for m, s in result]
        else:
            return [m.decode('utf-8') if isinstance(m, bytes) else m for m in result]
    
    async def sorted_set_rev_range(
        self, key: str, start: int = 0, end: int = -1, withscores: bool = False
    ) -> Union[List[str], List[Tuple[str, float]]]:
        """
        Get members from a Redis Sorted Set by rank range in reverse order.
        
        Args:
            key: Redis key
            start: Start rank (0-based)
            end: End rank (-1 means last element)
            withscores: Whether to include scores in the result
            
        Returns:
            List of members or list of (member, score) tuples
        """
        result = await self.redis.zrevrange(key, start, end, withscores=withscores)
        
        # Process bytes to strings
        if withscores:
            return [(m.decode('utf-8') if isinstance(m, bytes) else m, s) for m, s in result]
        else:
            return [m.decode('utf-8') if isinstance(m, bytes) else m for m in result]
    
    # List operations
    
    async def list_push(self, key: str, value: Any, ttl: Optional[int] = None) -> int:
        """
        Push a value to the beginning of a Redis List.
        
        Args:
            key: Redis key
            value: Value to push (will be JSON-serialized if dict or list)
            ttl: Optional TTL in seconds
            
        Returns:
            New length of the list
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        result = await self.redis.lpush(key, value)
        if ttl is not None:
            await self.redis.expire(key, ttl)
        
        # Check if we need to trim the list
        if result > (StreamConfig.MAX_STREAM_LENGTH * StreamConfig.TRIM_THRESHOLD):
            await self.redis.ltrim(key, 0, StreamConfig.MAX_STREAM_LENGTH - 1)
        
        return result
    
    async def list_range(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """
        Get elements from a Redis List by index range.
        
        Args:
            key: Redis key
            start: Start index (0-based)
            end: End index (-1 means last element)
            
        Returns:
            List of elements
        """
        result = await self.redis.lrange(key, start, end)
        
        # Process results
        processed = []
        for item in result:
            if isinstance(item, bytes):
                try:
                    item = item.decode('utf-8')
                    # Try to parse JSON
                    if item.startswith('{') or item.startswith('['):
                        try:
                            item = json.loads(item)
                        except json.JSONDecodeError:
                            pass
                except UnicodeDecodeError:
                    pass
            
            processed.append(item)
        
        return processed
    
    # Pub/Sub operations
    
    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish a message to a Redis Pub/Sub channel.
        
        Args:
            channel: Channel name
            message: Message to publish (will be JSON-serialized if dict or list)
            
        Returns:
            Number of clients that received the message
        """
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        
        return await self.redis.publish(channel, message)
    
    # General operations
    
    async def set_with_ttl(self, key: str, value: Any, ttl: int) -> bool:
        """
        Set a key with a TTL.
        
        Args:
            key: Redis key
            value: Value to set (will be JSON-serialized if dict or list)
            ttl: TTL in seconds
            
        Returns:
            True if the operation was successful
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        return await self.redis.setex(key, ttl, value)
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from Redis.
        
        Args:
            key: Redis key
            default: Default value if key does not exist
            
        Returns:
            Value or default
        """
        value = await self.redis.get(key)
        if value is None:
            return default
        
        # Try to decode JSON if the value looks like JSON
        try:
            if value.startswith(b'{') or value.startswith(b'['):
                return json.loads(value)
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            pass
        
        # Return as string or original value
        try:
            return value.decode('utf-8')
        except (AttributeError, UnicodeDecodeError):
            return value
    
    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from Redis.
        
        Args:
            keys: Redis keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0
        return await self.redis.delete(*keys)
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Redis key
            
        Returns:
            True if the key exists
        """
        return await self.redis.exists(key) > 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set a TTL for a key.
        
        Args:
            key: Redis key
            ttl: TTL in seconds
            
        Returns:
            True if the operation was successful
        """
        return await self.redis.expire(key, ttl)
    
    async def ttl(self, key: str) -> int:
        """
        Get the TTL of a key.
        
        Args:
            key: Redis key
            
        Returns:
            TTL in seconds, -1 if the key has no TTL, -2 if the key does not exist
        """
        return await self.redis.ttl(key)
    
    # Caching strategies
    
    async def get_or_set(
        self, key: str, getter_func: callable, ttl: Optional[int] = TTLValues.STANDARD
    ) -> Any:
        """
        Get a value from cache or set it if it doesn't exist (Cache-Aside pattern).
        
        Args:
            key: Redis key
            getter_func: Async function to call to get the value if not in cache
            ttl: TTL for the cached value in seconds
            
        Returns:
            Cached or retrieved value
        """
        # Try to get from cache first
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Get from source
        value = await getter_func()
        
        # Store in cache if value is not None
        if value is not None and ttl is not None:
            await self.set_with_ttl(key, value, ttl)
        
        return value


class EntityMetricsService(RedisService):
    """
    Service for managing entity metrics in Redis.
    
    This service provides specialized methods for working with entity metrics,
    including aggregation, update, and retrieval operations.
    """
    
    async def get_entity_metrics(self, entity_id: Union[str, UUID]) -> Dict[str, Any]:
        """
        Get all metrics for an entity.
        
        Args:
            entity_id: Entity UUID
            
        Returns:
            Dictionary of entity metrics
        """
        key = self.entity_metrics_key(entity_id)
        return await self.hash_get_all(key)
    
    async def update_entity_metric(
        self, entity_id: Union[str, UUID], field: str, value: Any, ttl: int = TTLValues.STANDARD
    ) -> bool:
        """
        Update a single entity metric.
        
        Args:
            entity_id: Entity UUID
            field: Metric field name
            value: New metric value
            ttl: TTL for the cache key
            
        Returns:
            True if the operation was successful
        """
        key = self.entity_metrics_key(entity_id)
        return await self.hash_set(key, field, value, ttl)
    
    async def increment_entity_metric(
        self, entity_id: Union[str, UUID], field: str, amount: int = 1, ttl: int = TTLValues.STANDARD
    ) -> int:
        """
        Increment a numeric entity metric.
        
        Args:
            entity_id: Entity UUID
            field: Metric field name
            amount: Amount to increment by
            ttl: TTL for the cache key
            
        Returns:
            New metric value
        """
        key = self.entity_metrics_key(entity_id)
        return await self.hash_increment(key, field, amount, ttl)
    
    async def update_timestamp(
        self, entity_id: Union[str, UUID], field: str = EntityMetricsFields.LAST_UPDATED, ttl: int = TTLValues.STANDARD
    ) -> bool:
        """
        Update a timestamp field for an entity.
        
        Args:
            entity_id: Entity UUID
            field: Timestamp field name
            ttl: TTL for the cache key
            
        Returns:
            True if the operation was successful
        """
        key = self.entity_metrics_key(entity_id)
        timestamp = datetime.utcnow().isoformat()
        return await self.hash_set(key, field, timestamp, ttl)
    
    async def get_engagement_rate(self, entity_id: Union[str, UUID]) -> float:
        """
        Get the average engagement rate for an entity.
        
        Args:
            entity_id: Entity UUID
            
        Returns:
            Average engagement rate or 0 if not available
        """
        key = self.entity_metrics_key(entity_id)
        rate = await self.hash_get(key, EntityMetricsFields.AVG_ENGAGEMENT_RATE, 0)
        return float(rate)


class TrendingService(RedisService):
    """
    Service for managing trending topics and hashtags in Redis.
    
    This service provides specialized methods for working with trending data,
    including tracking, scoring, and retrieval operations.
    """
    
    async def increment_topic_score(
        self, topic: str, timeframe: TimeFrames, score_increment: float = 1.0
    ) -> float:
        """
        Increment the score of a topic for a specific timeframe.
        
        Args:
            topic: Topic name
            timeframe: Time frame for trending data
            score_increment: Amount to increment the score by
            
        Returns:
            New topic score
        """
        key = self.trending_topics_key(timeframe)
        ttl = TTLValues.for_timeframe(timeframe)
        return await self.sorted_set_increment(key, topic, score_increment, ttl)
    
    async def increment_hashtag_score(
        self, hashtag: str, timeframe: TimeFrames, score_increment: float = 1.0
    ) -> float:
        """
        Increment the score of a hashtag for a specific timeframe.
        
        Args:
            hashtag: Hashtag (without the # symbol)
            timeframe: Time frame for trending data
            score_increment: Amount to increment the score by
            
        Returns:
            New hashtag score
        """
        key = self.trending_hashtags_key(timeframe)
        ttl = TTLValues.for_timeframe(timeframe)
        return await self.sorted_set_increment(key, hashtag, score_increment, ttl)
    
    async def get_trending_topics(
        self, timeframe: TimeFrames, limit: int = 10, with_scores: bool = False
    ) -> Union[List[str], List[Tuple[str, float]]]:
        """
        Get trending topics for a specific timeframe.
        
        Args:
            timeframe: Time frame for trending data
            limit: Maximum number of topics to return
            with_scores: Whether to include scores in the result
            
        Returns:
            List of topics or list of (topic, score) tuples
        """
        key = self.trending_topics_key(timeframe)
        return await self.sorted_set_rev_range(key, 0, limit - 1, withscores=with_scores)
    
    async def get_trending_hashtags(
        self, timeframe: TimeFrames, limit: int = 10, with_scores: bool = False
    ) -> Union[List[str], List[Tuple[str, float]]]:
        """
        Get trending hashtags for a specific timeframe.
        
        Args:
            timeframe: Time frame for trending data
            limit: Maximum number of hashtags to return
            with_scores: Whether to include scores in the result
            
        Returns:
            List of hashtags or list of (hashtag, score) tuples
        """
        key = self.trending_hashtags_key(timeframe)
        return await self.sorted_set_rev_range(key, 0, limit - 1, withscores=with_scores)
    
    async def calculate_topic_velocity(
        self, topic: str, timeframes: List[TimeFrames] = [TimeFrames.HOUR, TimeFrames.DAY]
    ) -> float:
        """
        Calculate the velocity of a topic's popularity (rate of change).
        
        Args:
            topic: Topic name
            timeframes: List of timeframes to compare (should be ordered from shortest to longest)
            
        Returns:
            Velocity score (higher means faster growth)
        """
        if len(timeframes) < 2:
            return 0.0
        
        # Get scores for each timeframe
        scores = []
        for tf in timeframes:
            key = self.trending_topics_key(tf)
            score = await self.redis.zscore(key, topic)
            scores.append(float(score) if score is not None else 0.0)
        
        # Calculate weighted score differences
        total_velocity = 0.0
        weight_sum = 0.0
        
        for i in range(len(scores) - 1):
            short_term = scores[i]
            long_term = scores[i + 1]
            
            # Skip if both scores are 0
            if short_term == 0 and long_term == 0:
                continue
            
            # Calculate normalized difference (short-term vs long-term)
            if long_term > 0:
                velocity = (short_term / long_term) - 1
            else:
                velocity = short_term
            
            # Apply weight (earlier comparisons get higher weight)
            weight = 1.0 / (i + 1)
            total_velocity += velocity * weight
            weight_sum += weight
        
        return total_velocity / weight_sum if weight_sum > 0 else 0.0


class ActivityStreamService(RedisService):
    """
    Service for managing activity streams in Redis.
    
    This service provides specialized methods for working with activity streams,
    including adding activities, retrieving recent activities, and managing stream size.
    """
    
    async def add_entity_activity(
        self, entity_id: Union[str, UUID], activity_data: Dict[str, Any]
    ) -> int:
        """
        Add an activity to an entity's activity stream.
        
        Args:
            entity_id: Entity UUID
            activity_data: Activity data dictionary
            
        Returns:
            New length of the activity stream
        """
        # Ensure timestamp is included
        if "timestamp" not in activity_data:
            activity_data["timestamp"] = datetime.utcnow().isoformat()
        
        key = self.activity_entity_key(entity_id)
        return await self.list_push(key, activity_data)
    
    async def get_entity_activities(
        self, entity_id: Union[str, UUID], limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent activities for an entity.
        
        Args:
            entity_id: Entity UUID
            limit: Maximum number of activities to return
            
        Returns:
            List of activity data dictionaries
        """
        key = self.activity_entity_key(entity_id)
        return await self.list_range(key, 0, limit - 1)
    
    async def trim_activity_stream(self, entity_id: Union[str, UUID], max_length: int = StreamConfig.MAX_STREAM_LENGTH) -> bool:
        """
        Trim an entity's activity stream to a maximum length.
        
        Args:
            entity_id: Entity UUID
            max_length: Maximum number of activities to keep
            
        Returns:
            True if the operation was successful
        """
        key = self.activity_entity_key(entity_id)
        await self.redis.ltrim(key, 0, max_length - 1)
        return True
    
    async def add_global_activity(self, activity_data: Dict[str, Any]) -> int:
        """
        Add an activity to the global activity stream.
        
        Args:
            activity_data: Activity data dictionary
            
        Returns:
            New length of the activity stream
        """
        # Ensure timestamp is included
        if "timestamp" not in activity_data:
            activity_data["timestamp"] = datetime.utcnow().isoformat()
        
        key = KeyPatterns.ACTIVITY_GLOBAL
        return await self.list_push(key, activity_data)
    
    async def get_global_activities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent activities from the global activity stream.
        
        Args:
            limit: Maximum number of activities to return
            
        Returns:
            List of activity data dictionaries
        """
        key = KeyPatterns.ACTIVITY_GLOBAL
        return await self.list_range(key, 0, limit - 1)


class AlertService(RedisService):
    """
    Service for managing real-time alerts in Redis.
    
    This service provides specialized methods for working with alerts,
    including creating alerts, retrieving pending alerts, and publishing notifications.
    """
    
    async def create_entity_alert(
        self,
        entity_id: Union[str, UUID],
        alert_type: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        data: Optional[Dict[str, Any]] = None,
        publish: bool = True,
    ) -> str:
        """
        Create an alert for an entity.
        
        Args:
            entity_id: Entity UUID
            alert_type: Type of alert
            message: Human-readable alert message
            priority: Alert priority
            data: Additional alert-specific data
            publish: Whether to publish the alert to the entity's alert channel
            
        Returns:
            Alert ID
        """
        # Generate alert ID
        alert_id = f"alert:{int(time.time() * 1000)}:{entity_id}"
        
        # Create alert data
        alert_data = {
            "id": alert_id,
            "type": alert_type,
            "priority": priority.name,
            "timestamp": datetime.utcnow().isoformat(),
            "entity_id": str(entity_id),
            "message": message,
        }
        
        if data:
            alert_data["data"] = data
        
        # Add to entity's alerts sorted set
        key = self.alerts_entity_key(entity_id)
        # Use priority as score, higher priority = higher score
        score = time.time() + (priority.value * 10000)  # Combine time with priority
        await self.sorted_set_add(key, json.dumps(alert_data), score)
        
        # Publish to entity's alert channel if requested
        if publish:
            channel = f"{KeyPatterns.NAMESPACE}:alerts:entity:{entity_id}"
            await self.publish(channel, alert_data)
        
        return alert_id
    
    async def get_entity_alerts(
        self, entity_id: Union[str, UUID], limit: int = 20, min_priority: AlertPriority = AlertPriority.LOW
    ) -> List[Dict[str, Any]]:
        """
        Get pending alerts for an entity.
        
        Args:
            entity_id: Entity UUID
            limit: Maximum number of alerts to return
            min_priority: Minimum alert priority to include
            
        Returns:
            List of alert data dictionaries
        """
        key = self.alerts_entity_key(entity_id)
        alerts_json = await self.sorted_set_rev_range(key, 0, limit - 1)
        
        alerts = []
        for alert_json in alerts_json:
            try:
                alert = json.loads(alert_json)
                # Filter by priority if needed
                if AlertPriority[alert.get("priority", "LOW")].value >= min_priority.value:
                    alerts.append(alert)
            except (json.JSONDecodeError, KeyError):
                continue
        
        return alerts
    
    async def acknowledge_alert(self, entity_id: Union[str, UUID], alert_id: str) -> bool:
        """
        Acknowledge (remove) an alert for an entity.
        
        Args:
            entity_id: Entity UUID
            alert_id: Alert ID to acknowledge
            
        Returns:
            True if the alert was removed
        """
        key = self.alerts_entity_key(entity_id)
        
        # Find and remove the alert with the matching ID
        alerts_json = await self.sorted_set_rev_range(key, 0, -1)
        removed = False
        
        for alert_json in alerts_json:
            try:
                alert = json.loads(alert_json)
                if alert.get("id") == alert_id:
                    await self.redis.zrem(key, alert_json)
                    removed = True
                    break
            except json.JSONDecodeError:
                continue
        
        return removed
    
    async def publish_topic_alert(
        self,
        topic: str,
        alert_type: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Publish an alert to a topic channel.
        
        Args:
            topic: Topic name
            alert_type: Type of alert
            message: Human-readable alert message
            priority: Alert priority
            data: Additional alert-specific data
            
        Returns:
            Number of clients that received the message
        """
        # Generate alert ID
        alert_id = f"alert:{int(time.time() * 1000)}:{topic}"
        
        # Create alert data
        alert_data = {
            "id": alert_id,
            "type": alert_type,
            "priority": priority.name,
            "timestamp": datetime.utcnow().isoformat(),
            "topic": topic,
            "message": message,
        }
        
        if data:
            alert_data["data"] = data
        
        # Publish to topic's alert channel
        channel = self.alerts_topic_channel(topic)
        return await self.publish(channel, alert_data) 