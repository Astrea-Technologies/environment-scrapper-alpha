"""
Redis cache service for general-purpose caching operations.

This module provides a service for interacting with Redis for caching operations.
It implements methods for setting, getting, and invalidating cache entries.
"""

import json
from typing import Any, Dict, List, Optional, Set, Union, TypeVar, Generic
import redis.asyncio as redis

from app.db.schemas.redis_schemas import KeyPatterns, TTLValues

T = TypeVar('T')


class CacheService:
    """Service for Redis caching operations."""
    
    def __init__(self, redis_client: redis.Redis) -> None:
        """
        Initialize the cache service with a Redis client.
        
        Args:
            redis_client: The Redis client instance
        """
        self.redis = redis_client
    
    async def set_value(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = TTLValues.STANDARD
    ) -> bool:
        """
        Set a string value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache (will be JSON serialized if not a string)
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            bool: True if the operation was successful
        """
        try:
            # Serialize value if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value)
                
            await self.redis.set(key, value, ex=ttl)
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error setting cache value: {e}")
            return False
    
    async def get_value(self, key: str, default: Optional[T] = None) -> Union[str, T]:
        """
        Get a string value from the cache.
        
        Args:
            key: The cache key
            default: Default value to return if key doesn't exist
            
        Returns:
            The cached value or the default value
        """
        try:
            value = await self.redis.get(key)
            if value is None:
                return default
            
            # Try to deserialize as JSON, return as string if it fails
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting cache value: {e}")
            return default
    
    async def delete_key(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: The cache key to delete
            
        Returns:
            bool: True if the key was deleted, False otherwise
        """
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            # Log the error in a production environment
            print(f"Error deleting cache key: {e}")
            return False
    
    async def set_hash(
        self,
        key: str,
        hash_map: Dict[str, Any],
        ttl: Optional[int] = TTLValues.STANDARD
    ) -> bool:
        """
        Set multiple fields in a hash.
        
        Args:
            key: The hash key
            hash_map: Dictionary of field-value pairs
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            bool: True if the operation was successful
        """
        try:
            # Serialize any non-string values
            serialized_map = {}
            for field, value in hash_map.items():
                if not isinstance(value, (str, int, float, bool)):
                    serialized_map[field] = json.dumps(value)
                else:
                    serialized_map[field] = value
            
            await self.redis.hset(key, mapping=serialized_map)
            
            if ttl is not None:
                await self.redis.expire(key, ttl)
            
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error setting hash: {e}")
            return False
    
    async def get_hash_field(
        self,
        key: str,
        field: str,
        default: Optional[T] = None
    ) -> Union[Any, T]:
        """
        Get a single field from a hash.
        
        Args:
            key: The hash key
            field: The field to retrieve
            default: Default value to return if field doesn't exist
            
        Returns:
            The field value or the default value
        """
        try:
            value = await self.redis.hget(key, field)
            if value is None:
                return default
            
            # Try to deserialize as JSON, return as is if it fails
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting hash field: {e}")
            return default
    
    async def get_hash_all(self, key: str) -> Dict[str, Any]:
        """
        Get all fields and values from a hash.
        
        Args:
            key: The hash key
            
        Returns:
            Dictionary of field-value pairs
        """
        try:
            hash_data = await self.redis.hgetall(key)
            
            # Try to deserialize JSON values
            result = {}
            for field, value in hash_data.items():
                try:
                    result[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[field] = value
            
            return result
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting hash: {e}")
            return {}
    
    async def increment_hash_field(
        self,
        key: str,
        field: str,
        increment: int = 1,
        ttl: Optional[int] = None
    ) -> int:
        """
        Increment a numeric field in a hash.
        
        Args:
            key: The hash key
            field: The field to increment
            increment: The increment value
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            The new value of the field after increment
        """
        try:
            new_value = await self.redis.hincrby(key, field, increment)
            
            if ttl is not None:
                await self.redis.expire(key, ttl)
            
            return new_value
        except Exception as e:
            # Log the error in a production environment
            print(f"Error incrementing hash field: {e}")
            return 0
    
    async def add_to_set(
        self,
        key: str,
        members: Union[str, List[str], Set[str]],
        ttl: Optional[int] = TTLValues.STANDARD
    ) -> int:
        """
        Add one or more members to a set.
        
        Args:
            key: The set key
            members: Member(s) to add
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            Number of members added to the set
        """
        try:
            if isinstance(members, (list, set)):
                if not members:
                    return 0
                result = await self.redis.sadd(key, *members)
            else:
                result = await self.redis.sadd(key, members)
            
            if ttl is not None:
                await self.redis.expire(key, ttl)
            
            return result
        except Exception as e:
            # Log the error in a production environment
            print(f"Error adding to set: {e}")
            return 0
    
    async def get_set_members(self, key: str) -> Set[str]:
        """
        Get all members of a set.
        
        Args:
            key: The set key
            
        Returns:
            Set of members
        """
        try:
            members = await self.redis.smembers(key)
            return members
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting set members: {e}")
            return set()
    
    async def is_member_of_set(self, key: str, member: str) -> bool:
        """
        Check if a value is a member of a set.
        
        Args:
            key: The set key
            member: The member to check
            
        Returns:
            True if the member exists in the set, False otherwise
        """
        try:
            return await self.redis.sismember(key, member)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error checking set membership: {e}")
            return False
    
    async def remove_from_set(self, key: str, members: Union[str, List[str]]) -> int:
        """
        Remove one or more members from a set.
        
        Args:
            key: The set key
            members: Member(s) to remove
            
        Returns:
            Number of members removed from the set
        """
        try:
            if isinstance(members, list):
                if not members:
                    return 0
                return await self.redis.srem(key, *members)
            else:
                return await self.redis.srem(key, members)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error removing from set: {e}")
            return 0
    
    async def add_to_list(
        self,
        key: str,
        items: Union[str, List[str]],
        prepend: bool = True,
        ttl: Optional[int] = TTLValues.STANDARD,
        max_length: Optional[int] = None
    ) -> int:
        """
        Add one or more items to a list.
        
        Args:
            key: The list key
            items: Item(s) to add
            prepend: If True, add items to the beginning of the list
            ttl: Time-to-live in seconds (None for no expiration)
            max_length: Maximum length to maintain (trim if exceeded)
            
        Returns:
            The new length of the list
        """
        try:
            # Serialize non-string items
            if isinstance(items, list):
                serialized_items = [
                    json.dumps(item) if not isinstance(item, str) else item
                    for item in items
                ]
            else:
                serialized_items = json.dumps(items) if not isinstance(items, str) else items
            
            # Add to list
            if prepend:
                if isinstance(serialized_items, list):
                    result = await self.redis.lpush(key, *serialized_items)
                else:
                    result = await self.redis.lpush(key, serialized_items)
            else:
                if isinstance(serialized_items, list):
                    result = await self.redis.rpush(key, *serialized_items)
                else:
                    result = await self.redis.rpush(key, serialized_items)
            
            # Trim list if max_length is specified
            if max_length is not None and result > max_length:
                await self.redis.ltrim(key, 0, max_length - 1)
            
            # Set TTL if specified
            if ttl is not None:
                await self.redis.expire(key, ttl)
            
            return result
        except Exception as e:
            # Log the error in a production environment
            print(f"Error adding to list: {e}")
            return 0
    
    async def get_list_items(
        self,
        key: str,
        start: int = 0,
        end: int = -1
    ) -> List[Any]:
        """
        Get items from a list within the specified range.
        
        Args:
            key: The list key
            start: Start index (0-based)
            end: End index (-1 for all items)
            
        Returns:
            List of items
        """
        try:
            items = await self.redis.lrange(key, start, end)
            
            # Try to deserialize JSON values
            result = []
            for item in items:
                try:
                    result.append(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    result.append(item)
            
            return result
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting list items: {e}")
            return []
    
    async def get_list_length(self, key: str) -> int:
        """
        Get the length of a list.
        
        Args:
            key: The list key
            
        Returns:
            Length of the list
        """
        try:
            return await self.redis.llen(key)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting list length: {e}")
            return 0
    
    async def trim_list(self, key: str, start: int, end: int) -> bool:
        """
        Trim a list to the specified range.
        
        Args:
            key: The list key
            start: Start index to keep (0-based)
            end: End index to keep
            
        Returns:
            True if the operation was successful
        """
        try:
            await self.redis.ltrim(key, start, end)
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error trimming list: {e}")
            return False
    
    async def set_key_ttl(self, key: str, ttl: int) -> bool:
        """
        Set the time-to-live for a key.
        
        Args:
            key: The key to set TTL for
            ttl: Time-to-live in seconds
            
        Returns:
            True if the TTL was set, False if the key doesn't exist
        """
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error setting TTL: {e}")
            return False
    
    async def get_key_ttl(self, key: str) -> int:
        """
        Get the remaining time-to-live for a key.
        
        Args:
            key: The key to get TTL for
            
        Returns:
            TTL in seconds, -1 if the key exists but has no TTL, 
            -2 if the key doesn't exist
        """
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting TTL: {e}")
            return -2
    
    async def key_exists(self, key: str) -> bool:
        """
        Check if a key exists.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            # Log the error in a production environment
            print(f"Error checking key existence: {e}")
            return False
    
    async def find_keys(self, pattern: str) -> List[str]:
        """
        Find keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "user:*")
            
        Returns:
            List of matching keys
        """
        try:
            return await self.redis.keys(pattern)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error finding keys: {e}")
            return []
    
    async def delete_keys(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = await self.find_keys(pattern)
            if not keys:
                return 0
            
            return await self.redis.delete(*keys)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error deleting keys: {e}")
            return 0
    
    async def clear_entity_cache(self, entity_id: str) -> int:
        """
        Clear all cache entries for a specific entity.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            Number of keys deleted
        """
        try:
            # Get all keys related to this entity
            pattern = f"{KeyPatterns.NAMESPACE}:entity:{entity_id}:*"
            return await self.delete_keys(pattern)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error clearing entity cache: {e}")
            return 0
    
    async def invalidate_trending_data(self, timeframe: Optional[str] = None) -> int:
        """
        Invalidate trending data cache.
        
        Args:
            timeframe: Specific timeframe to invalidate (None for all)
            
        Returns:
            Number of keys deleted
        """
        try:
            if timeframe:
                pattern = f"{KeyPatterns.NAMESPACE}:trending:*:{timeframe}"
            else:
                pattern = f"{KeyPatterns.NAMESPACE}:trending:*"
            
            return await self.delete_keys(pattern)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error invalidating trending data: {e}")
            return 0 