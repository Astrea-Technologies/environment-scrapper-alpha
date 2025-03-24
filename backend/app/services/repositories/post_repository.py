"""
Repository for social media posts stored in MongoDB.

This module provides a repository for CRUD operations and queries on social media posts
stored in MongoDB as part of the Political Social Media Analysis Platform.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

import motor.motor_asyncio
from bson import ObjectId
from fastapi import Depends

from app.db.connections import get_mongodb
from app.db.schemas.mongodb import SocialMediaPost


class PostRepository:
    """
    Repository for social media posts stored in MongoDB.
    
    This repository provides methods for CRUD operations and specialized queries
    on social media posts stored in the MongoDB database.
    """
    
    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase = None):
        """
        Initialize the repository with a MongoDB database connection.
        
        Args:
            db: MongoDB database connection. If None, a connection will be
                established when methods are called.
        """
        self._db = db
        self._collection_name = "posts"
    
    @property
    async def collection(self) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """Get the posts collection, ensuring a database connection exists."""
        db = self._db
        if db is None:
            async with get_mongodb() as db:
                return db[self._collection_name]
        return db[self._collection_name]
    
    async def create(self, post_data: Dict[str, Any]) -> str:
        """
        Create a new social media post.
        
        Args:
            post_data: Dictionary with post data following the SocialMediaPost schema
            
        Returns:
            The ID of the created post
        """
        collection = await self.collection
        post_data["metadata"]["created_at"] = datetime.fromisoformat(
            post_data["metadata"]["created_at"].replace("Z", "+00:00")
        ) if isinstance(post_data["metadata"]["created_at"], str) else post_data["metadata"]["created_at"]
        
        result = await collection.insert_one(post_data)
        return str(result.inserted_id)
    
    async def get(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a post by ID.
        
        Args:
            post_id: The ID of the post to retrieve
            
        Returns:
            The post data if found, None otherwise
        """
        collection = await self.collection
        post = await collection.find_one({"_id": ObjectId(post_id)})
        return post
    
    async def get_by_platform_id(self, platform: str, platform_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a post by platform and platform-specific ID.
        
        Args:
            platform: The social media platform (e.g., twitter, facebook)
            platform_id: The platform-specific ID of the post
            
        Returns:
            The post data if found, None otherwise
        """
        collection = await self.collection
        post = await collection.find_one({
            "platform": platform,
            "platform_id": platform_id
        })
        return post
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "metadata.created_at",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Get a list of posts with pagination and sorting options.
        
        Args:
            skip: Number of posts to skip
            limit: Maximum number of posts to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of posts
        """
        collection = await self.collection
        cursor = collection.find().skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def find_by_account(
        self,
        account_id: Union[UUID, str],
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "metadata.created_at",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Find posts by account ID.
        
        Args:
            account_id: The UUID of the social media account
            skip: Number of posts to skip
            limit: Maximum number of posts to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of posts for the specified account
        """
        collection = await self.collection
        account_id_str = str(account_id)
        cursor = collection.find(
            {"account_id": account_id_str}
        ).skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def find_by_platform(
        self,
        platform: str,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "metadata.created_at",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Find posts by platform.
        
        Args:
            platform: The social media platform (e.g., twitter, facebook)
            skip: Number of posts to skip
            limit: Maximum number of posts to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of posts for the specified platform
        """
        collection = await self.collection
        cursor = collection.find(
            {"platform": platform}
        ).skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        account_id: Optional[Union[UUID, str]] = None,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "metadata.created_at",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Find posts within a date range with optional filtering by account and platform.
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            account_id: Optional account ID to filter by
            platform: Optional platform to filter by
            skip: Number of posts to skip
            limit: Maximum number of posts to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of posts within the date range
        """
        collection = await self.collection
        query = {
            "metadata.created_at": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        if account_id:
            query["account_id"] = str(account_id)
        
        if platform:
            query["platform"] = platform
        
        cursor = collection.find(query).skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def search_by_content(
        self,
        text: str,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "score",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Search posts by content text.
        
        Args:
            text: Text to search for in post content
            skip: Number of posts to skip
            limit: Maximum number of posts to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of posts matching the search text
        """
        collection = await self.collection
        cursor = collection.find(
            {"$text": {"$search": text}},
            {"score": {"$meta": "textScore"}}
        ).skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def find_by_engagement_metric(
        self,
        metric: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Find posts by engagement metric value range.
        
        Args:
            metric: The engagement metric to filter by (e.g., 'likes_count', 'shares_count')
            min_value: Minimum value for the metric (inclusive)
            max_value: Maximum value for the metric (inclusive)
            platform: Optional platform to filter by
            skip: Number of posts to skip
            limit: Maximum number of posts to return
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of posts with engagement metrics in the specified range
        """
        collection = await self.collection
        metric_field = f"engagement.{metric}"
        query = {}
        
        if min_value is not None or max_value is not None:
            query[metric_field] = {}
            if min_value is not None:
                query[metric_field]["$gte"] = min_value
            if max_value is not None:
                query[metric_field]["$lte"] = max_value
        
        if platform:
            query["platform"] = platform
        
        cursor = collection.find(query).skip(skip).limit(limit).sort(metric_field, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def update_engagement_metrics(
        self,
        post_id: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        Update engagement metrics for a post.
        
        Args:
            post_id: The ID of the post to update
            metrics: Dictionary of engagement metrics to update
            
        Returns:
            True if the update was successful, False otherwise
        """
        collection = await self.collection
        result = await collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {"engagement": metrics}}
        )
        return result.modified_count > 0
    
    async def update_analysis_results(
        self,
        post_id: str,
        analysis: Dict[str, Any]
    ) -> bool:
        """
        Update analysis results for a post.
        
        Args:
            post_id: The ID of the post to update
            analysis: Dictionary of analysis results to update
            
        Returns:
            True if the update was successful, False otherwise
        """
        collection = await self.collection
        result = await collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {"analysis": analysis}}
        )
        return result.modified_count > 0
    
    async def update_vector_id(
        self,
        post_id: str,
        vector_id: str
    ) -> bool:
        """
        Update vector database reference ID for a post.
        
        Args:
            post_id: The ID of the post to update
            vector_id: The vector database reference ID
            
        Returns:
            True if the update was successful, False otherwise
        """
        collection = await self.collection
        result = await collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {"vector_id": vector_id}}
        )
        return result.modified_count > 0
    
    async def update(
        self,
        post_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update a post with new data.
        
        Args:
            post_id: The ID of the post to update
            update_data: Dictionary with fields to update
            
        Returns:
            True if the update was successful, False otherwise
        """
        collection = await self.collection
        
        # Handle datetime conversion if needed
        if "metadata" in update_data and "created_at" in update_data["metadata"]:
            if isinstance(update_data["metadata"]["created_at"], str):
                update_data["metadata"]["created_at"] = datetime.fromisoformat(
                    update_data["metadata"]["created_at"].replace("Z", "+00:00")
                )
        
        result = await collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def delete(self, post_id: str) -> bool:
        """
        Delete a post.
        
        Args:
            post_id: The ID of the post to delete
            
        Returns:
            True if the deletion was successful, False otherwise
        """
        collection = await self.collection
        result = await collection.delete_one({"_id": ObjectId(post_id)})
        return result.deleted_count > 0
    
    async def count(self, query: Dict[str, Any] = None) -> int:
        """
        Count posts matching a query.
        
        Args:
            query: Query dictionary to filter posts
            
        Returns:
            Number of posts matching the query
        """
        collection = await self.collection
        return await collection.count_documents(query or {}) 