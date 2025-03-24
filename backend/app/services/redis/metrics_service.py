"""
Redis metrics service for real-time metrics tracking.

This module provides a service for tracking and retrieving real-time metrics
using Redis data structures such as sorted sets and hashes.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import redis.asyncio as redis

from app.db.schemas.redis_schemas import (
    KeyPatterns,
    TTLValues,
    TimeFrames,
    EntityMetricsFields
)


class MetricsService:
    """Service for Redis metrics operations."""
    
    def __init__(self, redis_client: redis.Redis) -> None:
        """
        Initialize the metrics service with a Redis client.
        
        Args:
            redis_client: The Redis client instance
        """
        self.redis = redis_client
    
    # Entity Metrics Methods
    
    async def update_entity_metrics(
        self,
        entity_id: str,
        metrics: Dict[str, Any],
        ttl: Optional[int] = TTLValues.STANDARD
    ) -> bool:
        """
        Update entity metrics in a hash.
        
        Args:
            entity_id: Entity ID
            metrics: Dictionary of metrics to update
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            True if the operation was successful
        """
        try:
            # Ensure all metrics have appropriate data types
            formatted_metrics = {}
            for field, value in metrics.items():
                if isinstance(value, (dict, list, tuple, set)):
                    formatted_metrics[field] = json.dumps(value)
                else:
                    formatted_metrics[field] = value
            
            # Add timestamp for last update
            if EntityMetricsFields.LAST_UPDATED not in formatted_metrics:
                formatted_metrics[EntityMetricsFields.LAST_UPDATED] = datetime.utcnow().isoformat()
            
            # Update metrics hash
            key = KeyPatterns.ENTITY_METRICS.format(entity_id=entity_id)
            await self.redis.hset(key, mapping=formatted_metrics)
            
            if ttl is not None:
                await self.redis.expire(key, ttl)
            
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error updating entity metrics: {e}")
            return False
    
    async def increment_entity_metrics(
        self,
        entity_id: str,
        metrics: Dict[str, int],
        ttl: Optional[int] = TTLValues.STANDARD
    ) -> Dict[str, int]:
        """
        Increment entity metrics fields.
        
        Args:
            entity_id: Entity ID
            metrics: Dictionary of metrics to increment and their increment values
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            Dictionary of updated metric values
        """
        try:
            key = KeyPatterns.ENTITY_METRICS.format(entity_id=entity_id)
            results = {}
            
            # Increment each metric
            for field, increment in metrics.items():
                new_value = await self.redis.hincrby(key, field, increment)
                results[field] = new_value
            
            # Update last updated timestamp
            await self.redis.hset(
                key,
                EntityMetricsFields.LAST_UPDATED,
                datetime.utcnow().isoformat()
            )
            
            if ttl is not None:
                await self.redis.expire(key, ttl)
            
            return results
        except Exception as e:
            # Log the error in a production environment
            print(f"Error incrementing entity metrics: {e}")
            return {}
    
    async def get_entity_metrics(
        self,
        entity_id: str,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get entity metrics from hash.
        
        Args:
            entity_id: Entity ID
            fields: Specific fields to retrieve (None for all)
            
        Returns:
            Dictionary of metrics
        """
        try:
            key = KeyPatterns.ENTITY_METRICS.format(entity_id=entity_id)
            
            if fields:
                # Get specific fields
                values = await self.redis.hmget(key, fields)
                result = dict(zip(fields, values))
            else:
                # Get all fields
                result = await self.redis.hgetall(key)
            
            # Parse values
            parsed_result = {}
            for field, value in result.items():
                if value is None:
                    parsed_result[field] = None
                    continue
                
                # Try to parse JSON
                try:
                    parsed_result[field] = json.loads(value)
                except (TypeError, json.JSONDecodeError):
                    # Try to convert to number if appropriate
                    try:
                        if value.isdigit():
                            parsed_result[field] = int(value)
                        elif value.replace(".", "", 1).isdigit():
                            parsed_result[field] = float(value)
                        else:
                            parsed_result[field] = value
                    except (AttributeError, ValueError):
                        parsed_result[field] = value
            
            return parsed_result
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting entity metrics: {e}")
            return {}
    
    async def compare_entity_metrics(
        self,
        entity_ids: List[str],
        metrics: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare metrics across multiple entities.
        
        Args:
            entity_ids: List of entity IDs to compare
            metrics: List of metric fields to compare
            
        Returns:
            Dictionary of entity IDs mapped to their metrics
        """
        try:
            results = {}
            
            for entity_id in entity_ids:
                entity_metrics = await self.get_entity_metrics(entity_id, metrics)
                results[entity_id] = entity_metrics
            
            return results
        except Exception as e:
            # Log the error in a production environment
            print(f"Error comparing entity metrics: {e}")
            return {}
    
    # Trending Data Methods
    
    async def update_trending_item(
        self,
        item_type: str,
        item_id: str,
        score: float,
        timeframe: TimeFrames = TimeFrames.HOUR
    ) -> bool:
        """
        Update or add an item to a trending sorted set.
        
        Args:
            item_type: Type of trending item (topics, hashtags, entities)
            item_id: Item identifier
            score: Score to add to the item
            timeframe: Time frame for trending data
            
        Returns:
            True if the operation was successful
        """
        try:
            # Get the appropriate key pattern based on item type
            key_pattern = None
            if item_type == "topics":
                key_pattern = KeyPatterns.TRENDING_TOPICS
            elif item_type == "hashtags":
                key_pattern = KeyPatterns.TRENDING_HASHTAGS
            elif item_type == "entities":
                key_pattern = KeyPatterns.TRENDING_ENTITIES
            else:
                raise ValueError(f"Unknown trending item type: {item_type}")
            
            # Format the key with the timeframe
            key = key_pattern.format(timeframe=timeframe.value)
            
            # Update the sorted set
            await self.redis.zincrby(key, score, item_id)
            
            # Set expiration based on timeframe
            ttl = TTLValues.for_timeframe(timeframe)
            await self.redis.expire(key, ttl)
            
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error updating trending item: {e}")
            return False
    
    async def get_trending_items(
        self,
        item_type: str,
        timeframe: TimeFrames = TimeFrames.HOUR,
        limit: int = 10,
        with_scores: bool = True
    ) -> Union[List[str], List[Tuple[str, float]]]:
        """
        Get trending items from a sorted set.
        
        Args:
            item_type: Type of trending item (topics, hashtags, entities)
            timeframe: Time frame for trending data
            limit: Maximum number of items to return
            with_scores: Whether to include scores in the result
            
        Returns:
            List of trending items, optionally with scores
        """
        try:
            # Get the appropriate key pattern based on item type
            key_pattern = None
            if item_type == "topics":
                key_pattern = KeyPatterns.TRENDING_TOPICS
            elif item_type == "hashtags":
                key_pattern = KeyPatterns.TRENDING_HASHTAGS
            elif item_type == "entities":
                key_pattern = KeyPatterns.TRENDING_ENTITIES
            else:
                raise ValueError(f"Unknown trending item type: {item_type}")
            
            # Format the key with the timeframe
            key = key_pattern.format(timeframe=timeframe.value)
            
            # Get the trending items
            items = await self.redis.zrevrange(
                key,
                0,
                limit - 1,
                withscores=with_scores
            )
            
            # Format the result
            if with_scores:
                return [(item, score) for item, score in items]
            else:
                return items
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting trending items: {e}")
            return []
    
    async def get_trending_item_rank(
        self,
        item_type: str,
        item_id: str,
        timeframe: TimeFrames = TimeFrames.HOUR
    ) -> Optional[int]:
        """
        Get the rank of an item in a trending sorted set.
        
        Args:
            item_type: Type of trending item (topics, hashtags, entities)
            item_id: Item identifier
            timeframe: Time frame for trending data
            
        Returns:
            Rank of the item (0-based, None if not in set)
        """
        try:
            # Get the appropriate key pattern based on item type
            key_pattern = None
            if item_type == "topics":
                key_pattern = KeyPatterns.TRENDING_TOPICS
            elif item_type == "hashtags":
                key_pattern = KeyPatterns.TRENDING_HASHTAGS
            elif item_type == "entities":
                key_pattern = KeyPatterns.TRENDING_ENTITIES
            else:
                raise ValueError(f"Unknown trending item type: {item_type}")
            
            # Format the key with the timeframe
            key = key_pattern.format(timeframe=timeframe.value)
            
            # Get the rank of the item
            rank = await self.redis.zrevrank(key, item_id)
            
            return rank
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting trending item rank: {e}")
            return None
    
    # Counter Methods
    
    async def increment_counter(
        self,
        counter_key: str,
        increment: int = 1,
        ttl: Optional[int] = TTLValues.STANDARD
    ) -> int:
        """
        Increment a counter.
        
        Args:
            counter_key: Counter key
            increment: Increment value
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            New counter value
        """
        try:
            # Increment the counter
            new_value = await self.redis.incrby(counter_key, increment)
            
            # Set expiration if specified
            if ttl is not None:
                await self.redis.expire(counter_key, ttl)
            
            return new_value
        except Exception as e:
            # Log the error in a production environment
            print(f"Error incrementing counter: {e}")
            return 0
    
    async def get_counter(self, counter_key: str) -> int:
        """
        Get a counter value.
        
        Args:
            counter_key: Counter key
            
        Returns:
            Counter value (0 if not found)
        """
        try:
            value = await self.redis.get(counter_key)
            return int(value) if value is not None else 0
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting counter: {e}")
            return 0
    
    # Rate Limiting Methods
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = TTLValues.RATE_LIMIT_WINDOW
    ) -> Tuple[bool, int, int]:
        """
        Check if a rate limit has been exceeded.
        
        Args:
            key: Rate limit key
            limit: Maximum number of requests
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (allowed, current_count, reset_seconds)
        """
        try:
            # Get the current count
            count = await self.get_counter(key)
            
            # Get the TTL to determine reset time
            ttl = await self.redis.ttl(key)
            
            # If key doesn't exist or TTL expired, reset the counter
            if ttl < 0:
                count = 0
                ttl = window_seconds
            
            # Check if limit has been exceeded
            if count >= limit:
                return False, count, ttl
            
            # Increment the counter
            new_count = await self.increment_counter(key, 1, window_seconds)
            
            return True, new_count, ttl
        except Exception as e:
            # Log the error in a production environment
            print(f"Error checking rate limit: {e}")
            return True, 0, window_seconds  # Fail open
    
    # Time Series Methods
    
    async def record_timeseries_data(
        self,
        key_prefix: str,
        value: Union[int, float],
        timestamp: Optional[int] = None,
        resolution: str = "hour",
        ttl: Optional[int] = None
    ) -> bool:
        """
        Record time series data.
        
        Args:
            key_prefix: Prefix for the time series key
            value: Value to record
            timestamp: Unix timestamp (current time if None)
            resolution: Time resolution (minute, hour, day)
            ttl: Time-to-live in seconds (None for resolution-based TTL)
            
        Returns:
            True if the operation was successful
        """
        try:
            # Use current time if timestamp not provided
            if timestamp is None:
                timestamp = int(time.time())
            
            # Format timestamp based on resolution
            dt = datetime.fromtimestamp(timestamp)
            if resolution == "minute":
                time_key = dt.strftime("%Y-%m-%d:%H:%M")
                if ttl is None:
                    ttl = 60 * 60 * 24  # 1 day
            elif resolution == "hour":
                time_key = dt.strftime("%Y-%m-%d:%H")
                if ttl is None:
                    ttl = 60 * 60 * 24 * 7  # 7 days
            elif resolution == "day":
                time_key = dt.strftime("%Y-%m-%d")
                if ttl is None:
                    ttl = 60 * 60 * 24 * 30  # 30 days
            else:
                raise ValueError(f"Unknown resolution: {resolution}")
            
            # Create the key
            key = f"{key_prefix}:{resolution}:{time_key}"
            
            # Record the value
            if isinstance(value, int):
                await self.increment_counter(key, value, ttl)
            else:
                await self.redis.set(key, value, ex=ttl)
            
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error recording time series data: {e}")
            return False
    
    async def get_timeseries_data(
        self,
        key_prefix: str,
        start_time: Union[int, datetime],
        end_time: Union[int, datetime],
        resolution: str = "hour"
    ) -> Dict[str, Union[int, float]]:
        """
        Get time series data within a time range.
        
        Args:
            key_prefix: Prefix for the time series key
            start_time: Start time (unix timestamp or datetime)
            end_time: End time (unix timestamp or datetime)
            resolution: Time resolution (minute, hour, day)
            
        Returns:
            Dictionary of timestamps mapped to values
        """
        try:
            # Convert datetimes to timestamps if necessary
            if isinstance(start_time, datetime):
                start_time = int(start_time.timestamp())
            if isinstance(end_time, datetime):
                end_time = int(end_time.timestamp())
            
            # Generate keys for the time range
            keys = []
            dt = datetime.fromtimestamp(start_time)
            end_dt = datetime.fromtimestamp(end_time)
            
            if resolution == "minute":
                delta = timedelta(minutes=1)
                format_str = "%Y-%m-%d:%H:%M"
            elif resolution == "hour":
                delta = timedelta(hours=1)
                format_str = "%Y-%m-%d:%H"
            elif resolution == "day":
                delta = timedelta(days=1)
                format_str = "%Y-%m-%d"
            else:
                raise ValueError(f"Unknown resolution: {resolution}")
            
            # Generate all keys in the range
            current_dt = dt
            while current_dt <= end_dt:
                time_key = current_dt.strftime(format_str)
                keys.append(f"{key_prefix}:{resolution}:{time_key}")
                current_dt += delta
            
            # Get values for all keys
            result = {}
            for key in keys:
                value = await self.redis.get(key)
                timestamp_str = key.split(":")[-1]
                if resolution == "minute":
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d:%H:%M").timestamp()
                elif resolution == "hour":
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d:%H").timestamp()
                else:  # day
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d").timestamp()
                
                # Try to convert to number
                if value is not None:
                    try:
                        if value.isdigit():
                            value = int(value)
                        else:
                            value = float(value)
                    except (AttributeError, ValueError):
                        pass
                
                result[int(timestamp)] = value or 0
            
            return result
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting time series data: {e}")
            return {}
    
    # Leaderboard Methods
    
    async def update_leaderboard(
        self,
        leaderboard_key: str,
        entry_id: str,
        score: Union[int, float],
        ttl: Optional[int] = TTLValues.STANDARD
    ) -> bool:
        """
        Update a leaderboard entry.
        
        Args:
            leaderboard_key: Leaderboard key
            entry_id: Entry identifier
            score: Score value
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            True if the operation was successful
        """
        try:
            # Update the sorted set
            await self.redis.zadd(leaderboard_key, {entry_id: score})
            
            # Set expiration if specified
            if ttl is not None:
                await self.redis.expire(leaderboard_key, ttl)
            
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error updating leaderboard: {e}")
            return False
    
    async def get_leaderboard(
        self,
        leaderboard_key: str,
        start: int = 0,
        end: int = -1,
        desc: bool = True,
        with_scores: bool = True
    ) -> Union[List[str], List[Tuple[str, float]]]:
        """
        Get leaderboard entries.
        
        Args:
            leaderboard_key: Leaderboard key
            start: Start index (0-based)
            end: End index (-1 for all entries)
            desc: Whether to sort in descending order
            with_scores: Whether to include scores in the result
            
        Returns:
            List of leaderboard entries, optionally with scores
        """
        try:
            # Get the leaderboard entries
            if desc:
                entries = await self.redis.zrevrange(
                    leaderboard_key,
                    start,
                    end,
                    withscores=with_scores
                )
            else:
                entries = await self.redis.zrange(
                    leaderboard_key,
                    start,
                    end,
                    withscores=with_scores
                )
            
            # Format the result
            if with_scores:
                return [(entry, score) for entry, score in entries]
            else:
                return entries
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting leaderboard: {e}")
            return []
    
    async def get_leaderboard_rank(
        self,
        leaderboard_key: str,
        entry_id: str,
        desc: bool = True
    ) -> Optional[int]:
        """
        Get the rank of an entry in a leaderboard.
        
        Args:
            leaderboard_key: Leaderboard key
            entry_id: Entry identifier
            desc: Whether to use descending order for ranking
            
        Returns:
            Rank of the entry (0-based, None if not in leaderboard)
        """
        try:
            # Get the rank of the entry
            if desc:
                rank = await self.redis.zrevrank(leaderboard_key, entry_id)
            else:
                rank = await self.redis.zrank(leaderboard_key, entry_id)
            
            return rank
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting leaderboard rank: {e}")
            return None
    
    async def get_leaderboard_score(
        self,
        leaderboard_key: str,
        entry_id: str
    ) -> Optional[float]:
        """
        Get the score of an entry in a leaderboard.
        
        Args:
            leaderboard_key: Leaderboard key
            entry_id: Entry identifier
            
        Returns:
            Score of the entry (None if not in leaderboard)
        """
        try:
            # Get the score of the entry
            score = await self.redis.zscore(leaderboard_key, entry_id)
            
            return score
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting leaderboard score: {e}")
            return None 