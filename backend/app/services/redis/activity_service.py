"""
Redis activity service for managing activity streams.

This module provides a service for tracking and retrieving activity streams
using Redis data structures.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

import redis.asyncio as redis

from app.db.schemas.redis_schemas import KeyPatterns, StreamConfig, TTLValues


class ActivityService:
    """Service for Redis activity streams operations."""
    
    def __init__(self, redis_client: redis.Redis) -> None:
        """
        Initialize the activity service with a Redis client.
        
        Args:
            redis_client: The Redis client instance
        """
        self.redis = redis_client
    
    async def add_activity(
        self,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        activity_type: str = "general",
        activity_data: Dict[str, Any] = None,
        add_to_global: bool = True
    ) -> Dict[str, str]:
        """
        Add a new activity to streams.
        
        Args:
            entity_id: Optional entity ID (for entity-specific streams)
            user_id: Optional user ID (for user-specific streams)
            activity_type: Type of activity (post, comment, mention, etc.)
            activity_data: Additional activity data
            add_to_global: Whether to add to global activity stream
            
        Returns:
            Dictionary with the IDs of the added activities
        """
        try:
            # Prepare activity data
            if activity_data is None:
                activity_data = {}
            
            activity = {
                "type": activity_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": json.dumps(activity_data)
            }
            
            if entity_id:
                activity["entity_id"] = entity_id
            if user_id:
                activity["user_id"] = user_id
            
            result_ids = {}
            
            # Add to entity stream if entity_id is provided
            if entity_id:
                entity_key = KeyPatterns.ACTIVITY_ENTITY.format(entity_id=entity_id)
                entity_id = await self._add_to_list(entity_key, activity)
                result_ids["entity"] = entity_id
            
            # Add to user stream if user_id is provided
            if user_id:
                user_key = KeyPatterns.ACTIVITY_USER.format(user_id=user_id)
                user_id = await self._add_to_list(user_key, activity)
                result_ids["user"] = user_id
            
            # Add to global stream if requested
            if add_to_global:
                global_key = KeyPatterns.ACTIVITY_GLOBAL
                global_id = await self._add_to_list(global_key, activity)
                result_ids["global"] = global_id
            
            return result_ids
        except Exception as e:
            # Log the error in a production environment
            print(f"Error adding activity: {e}")
            return {}
    
    async def _add_to_list(self, key: str, activity: Dict[str, Any]) -> str:
        """
        Add an activity to a list and handle trimming.
        
        Args:
            key: The list key
            activity: Activity data
            
        Returns:
            Generated activity ID
        """
        try:
            # Generate a unique ID
            activity_id = f"{int(time.time() * 1000)}-{hash(str(activity)) % 1000000}"
            
            # Add ID to activity
            activity["id"] = activity_id
            
            # Serialize activity
            serialized = json.dumps(activity)
            
            # Add to list (prepend)
            await self.redis.lpush(key, serialized)
            
            # Check if we need to trim the list
            length = await self.redis.llen(key)
            if length > StreamConfig.MAX_STREAM_LENGTH * StreamConfig.TRIM_THRESHOLD:
                await self.redis.ltrim(key, 0, StreamConfig.MAX_STREAM_LENGTH - 1)
            
            return activity_id
        except Exception as e:
            # Log the error in a production environment
            print(f"Error adding to list: {e}")
            return ""
    
    async def get_entity_activities(
        self,
        entity_id: str,
        start: int = 0,
        limit: int = 20,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get activities for a specific entity.
        
        Args:
            entity_id: Entity ID
            start: Start index
            limit: Maximum number of activities to return
            activity_type: Filter by activity type
            
        Returns:
            List of activities
        """
        try:
            key = KeyPatterns.ACTIVITY_ENTITY.format(entity_id=entity_id)
            return await self._get_activities(key, start, limit, activity_type)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting entity activities: {e}")
            return []
    
    async def get_user_activities(
        self,
        user_id: str,
        start: int = 0,
        limit: int = 20,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get activities for a specific user.
        
        Args:
            user_id: User ID
            start: Start index
            limit: Maximum number of activities to return
            activity_type: Filter by activity type
            
        Returns:
            List of activities
        """
        try:
            key = KeyPatterns.ACTIVITY_USER.format(user_id=user_id)
            return await self._get_activities(key, start, limit, activity_type)
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting user activities: {e}")
            return []
    
    async def get_global_activities(
        self,
        start: int = 0,
        limit: int = 20,
        activity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get global activities, optionally filtered.
        
        Args:
            start: Start index
            limit: Maximum number of activities to return
            activity_type: Filter by activity type
            entity_id: Filter by entity ID
            
        Returns:
            List of activities
        """
        try:
            key = KeyPatterns.ACTIVITY_GLOBAL
            activities = await self._get_activities(key, start, limit, activity_type)
            
            # Filter by entity_id if provided
            if entity_id:
                activities = [
                    activity for activity in activities
                    if activity.get("entity_id") == entity_id
                ]
            
            return activities
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting global activities: {e}")
            return []
    
    async def _get_activities(
        self,
        key: str,
        start: int = 0,
        limit: int = 20,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get activities from a list with filtering.
        
        Args:
            key: The list key
            start: Start index
            limit: Maximum number of activities to return
            activity_type: Filter by activity type
            
        Returns:
            List of activities
        """
        try:
            # Get items from list
            items = await self.redis.lrange(key, start, start + limit - 1)
            
            # Parse activities
            activities = []
            for item in items:
                try:
                    activity = json.loads(item)
                    
                    # Parse nested JSON data
                    if "data" in activity and isinstance(activity["data"], str):
                        activity["data"] = json.loads(activity["data"])
                    
                    # Filter by activity type if provided
                    if activity_type and activity.get("type") != activity_type:
                        continue
                    
                    activities.append(activity)
                except json.JSONDecodeError:
                    # Skip invalid JSON
                    continue
            
            return activities
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting activities: {e}")
            return []
    
    async def get_activity_by_id(
        self,
        activity_id: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find an activity by its ID.
        
        Args:
            activity_id: Activity ID
            entity_id: Optional entity ID to narrow search
            user_id: Optional user ID to narrow search
            
        Returns:
            Activity data if found, None otherwise
        """
        try:
            # Determine which streams to search
            keys = []
            
            if entity_id:
                keys.append(KeyPatterns.ACTIVITY_ENTITY.format(entity_id=entity_id))
            if user_id:
                keys.append(KeyPatterns.ACTIVITY_USER.format(user_id=user_id))
            
            # Add global stream if no specific streams provided
            if not keys:
                keys.append(KeyPatterns.ACTIVITY_GLOBAL)
            
            # Search for the activity
            for key in keys:
                # Get all activities from the stream
                # In a real implementation, you might want to paginate through the stream
                activities = await self._get_activities(key, 0, 1000)
                
                # Find the activity by ID
                for activity in activities:
                    if activity.get("id") == activity_id:
                        return activity
            
            return None
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting activity by ID: {e}")
            return None
    
    async def delete_activity(
        self,
        activity_id: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        delete_from_global: bool = True
    ) -> Dict[str, bool]:
        """
        Delete an activity from streams.
        
        Args:
            activity_id: Activity ID
            entity_id: Optional entity ID
            user_id: Optional user ID
            delete_from_global: Whether to delete from global stream
            
        Returns:
            Dictionary of stream keys and deletion success
        """
        try:
            # Determine which streams to delete from
            keys = []
            
            if entity_id:
                keys.append(KeyPatterns.ACTIVITY_ENTITY.format(entity_id=entity_id))
            if user_id:
                keys.append(KeyPatterns.ACTIVITY_USER.format(user_id=user_id))
            if delete_from_global:
                keys.append(KeyPatterns.ACTIVITY_GLOBAL)
            
            # Delete from each stream
            results = {}
            for key in keys:
                success = await self._delete_from_list(key, activity_id)
                results[key] = success
            
            return results
        except Exception as e:
            # Log the error in a production environment
            print(f"Error deleting activity: {e}")
            return {}
    
    async def _delete_from_list(self, key: str, activity_id: str) -> bool:
        """
        Delete an activity from a list by ID.
        
        Args:
            key: The list key
            activity_id: Activity ID to delete
            
        Returns:
            True if activity was deleted, False otherwise
        """
        try:
            # Get all activities from the list
            activities = await self._get_activities(key, 0, 1000)
            
            # Find the activity and its index
            for i, activity in enumerate(activities):
                if activity.get("id") == activity_id:
                    # Get the serialized activity
                    serialized = await self.redis.lindex(key, i)
                    if serialized:
                        # Remove the activity
                        await self.redis.lrem(key, 1, serialized)
                        return True
            
            return False
        except Exception as e:
            # Log the error in a production environment
            print(f"Error deleting from list: {e}")
            return False
    
    async def clear_entity_activities(self, entity_id: str) -> bool:
        """
        Clear all activities for an entity.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            True if operation was successful
        """
        try:
            key = KeyPatterns.ACTIVITY_ENTITY.format(entity_id=entity_id)
            await self.redis.delete(key)
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error clearing entity activities: {e}")
            return False
    
    async def clear_user_activities(self, user_id: str) -> bool:
        """
        Clear all activities for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if operation was successful
        """
        try:
            key = KeyPatterns.ACTIVITY_USER.format(user_id=user_id)
            await self.redis.delete(key)
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error clearing user activities: {e}")
            return False
    
    async def clear_global_activities(self) -> bool:
        """
        Clear all global activities.
        
        Returns:
            True if operation was successful
        """
        try:
            await self.redis.delete(KeyPatterns.ACTIVITY_GLOBAL)
            return True
        except Exception as e:
            # Log the error in a production environment
            print(f"Error clearing global activities: {e}")
            return False
    
    async def get_activity_count(
        self,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        is_global: bool = False
    ) -> int:
        """
        Get the count of activities in a stream.
        
        Args:
            entity_id: Optional entity ID
            user_id: Optional user ID
            is_global: Whether to count global activities
            
        Returns:
            Number of activities
        """
        try:
            key = None
            
            if entity_id:
                key = KeyPatterns.ACTIVITY_ENTITY.format(entity_id=entity_id)
            elif user_id:
                key = KeyPatterns.ACTIVITY_USER.format(user_id=user_id)
            elif is_global:
                key = KeyPatterns.ACTIVITY_GLOBAL
            
            if key:
                return await self.redis.llen(key)
            
            return 0
        except Exception as e:
            # Log the error in a production environment
            print(f"Error getting activity count: {e}")
            return 0 