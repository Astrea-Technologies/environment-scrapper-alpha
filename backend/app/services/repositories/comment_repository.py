"""
Repository for social media comments stored in MongoDB.

This module provides a repository for CRUD operations and queries on social media comments
stored in MongoDB as part of the Political Social Media Analysis Platform.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

import motor.motor_asyncio
from bson import ObjectId
from fastapi import Depends

from app.db.connections import get_mongodb
from app.db.schemas.mongodb import SocialMediaComment


class CommentRepository:
    """
    Repository for social media comments stored in MongoDB.
    
    This repository provides methods for CRUD operations and specialized queries
    on social media comments stored in the MongoDB database.
    """
    
    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase = None):
        """
        Initialize the repository with a MongoDB database connection.
        
        Args:
            db: MongoDB database connection. If None, a connection will be
                established when methods are called.
        """
        self._db = db
        self._collection_name = "comments"
    
    @property
    async def collection(self) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """Get the comments collection, ensuring a database connection exists."""
        db = self._db
        if db is None:
            async with get_mongodb() as db:
                return db[self._collection_name]
        return db[self._collection_name]
    
    async def create(self, comment_data: Dict[str, Any]) -> str:
        """
        Create a new social media comment.
        
        Args:
            comment_data: Dictionary with comment data following the SocialMediaComment schema
            
        Returns:
            The ID of the created comment
        """
        collection = await self.collection
        comment_data["metadata"]["created_at"] = datetime.fromisoformat(
            comment_data["metadata"]["created_at"].replace("Z", "+00:00")
        ) if isinstance(comment_data["metadata"]["created_at"], str) else comment_data["metadata"]["created_at"]
        
        result = await collection.insert_one(comment_data)
        return str(result.inserted_id)
    
    async def get(self, comment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a comment by ID.
        
        Args:
            comment_id: The ID of the comment to retrieve
            
        Returns:
            The comment data if found, None otherwise
        """
        collection = await self.collection
        comment = await collection.find_one({"_id": ObjectId(comment_id)})
        return comment
    
    async def get_by_platform_id(self, platform: str, platform_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a comment by platform and platform-specific ID.
        
        Args:
            platform: The social media platform (e.g., twitter, facebook)
            platform_id: The platform-specific ID of the comment
            
        Returns:
            The comment data if found, None otherwise
        """
        collection = await self.collection
        comment = await collection.find_one({
            "platform": platform,
            "platform_id": platform_id
        })
        return comment
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "metadata.created_at",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Get a list of comments with pagination and sorting options.
        
        Args:
            skip: Number of comments to skip
            limit: Maximum number of comments to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of comments
        """
        collection = await self.collection
        cursor = collection.find().skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def find_by_post_id(
        self,
        post_id: str,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "metadata.created_at",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Find comments for a specific post.
        
        Args:
            post_id: The ID of the post
            skip: Number of comments to skip
            limit: Maximum number of comments to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of comments for the specified post
        """
        collection = await self.collection
        cursor = collection.find(
            {"post_id": post_id}
        ).skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def find_by_user_id(
        self,
        user_id: str,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "metadata.created_at",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Find comments by a specific user.
        
        Args:
            user_id: The platform-specific user ID
            platform: Optional platform to filter by
            skip: Number of comments to skip
            limit: Maximum number of comments to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of comments by the specified user
        """
        collection = await self.collection
        query = {"user_id": user_id}
        
        if platform:
            query["platform"] = platform
        
        cursor = collection.find(query).skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def find_by_sentiment(
        self,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        post_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "analysis.sentiment_score",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Find comments by sentiment score range.
        
        Args:
            min_score: Minimum sentiment score (inclusive)
            max_score: Maximum sentiment score (inclusive)
            post_id: Optional post ID to filter by
            skip: Number of comments to skip
            limit: Maximum number of comments to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of comments with sentiment scores in the specified range
        """
        collection = await self.collection
        query = {}
        
        if min_score is not None or max_score is not None:
            query["analysis.sentiment_score"] = {}
            if min_score is not None:
                query["analysis.sentiment_score"]["$gte"] = min_score
            if max_score is not None:
                query["analysis.sentiment_score"]["$lte"] = max_score
        
        if post_id:
            query["post_id"] = post_id
        
        cursor = collection.find(query).skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def find_by_toxicity(
        self,
        is_toxic: bool,
        post_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "metadata.created_at",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Find comments by toxicity flag.
        
        Args:
            is_toxic: Whether to find toxic (True) or non-toxic (False) comments
            post_id: Optional post ID to filter by
            skip: Number of comments to skip
            limit: Maximum number of comments to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of comments matching the toxicity criteria
        """
        collection = await self.collection
        query = {"analysis.toxicity_flag": is_toxic}
        
        if post_id:
            query["post_id"] = post_id
        
        cursor = collection.find(query).skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def search_by_content(
        self,
        text: str,
        post_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "score",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Search comments by content text.
        
        Args:
            text: Text to search for in comment content
            post_id: Optional post ID to filter by
            skip: Number of comments to skip
            limit: Maximum number of comments to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of comments matching the search text
        """
        collection = await self.collection
        query = {"$text": {"$search": text}}
        
        if post_id:
            query["post_id"] = post_id
        
        cursor = collection.find(
            query,
            {"score": {"$meta": "textScore"}}
        ).skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def update_engagement_metrics(
        self,
        comment_id: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        Update engagement metrics for a comment.
        
        Args:
            comment_id: The ID of the comment to update
            metrics: Dictionary of engagement metrics to update
            
        Returns:
            True if the update was successful, False otherwise
        """
        collection = await self.collection
        result = await collection.update_one(
            {"_id": ObjectId(comment_id)},
            {"$set": {"engagement": metrics}}
        )
        return result.modified_count > 0
    
    async def update_analysis_results(
        self,
        comment_id: str,
        analysis: Dict[str, Any]
    ) -> bool:
        """
        Update analysis results for a comment.
        
        Args:
            comment_id: The ID of the comment to update
            analysis: Dictionary of analysis results to update
            
        Returns:
            True if the update was successful, False otherwise
        """
        collection = await self.collection
        result = await collection.update_one(
            {"_id": ObjectId(comment_id)},
            {"$set": {"analysis": analysis}}
        )
        return result.modified_count > 0
    
    async def update_vector_id(
        self,
        comment_id: str,
        vector_id: str
    ) -> bool:
        """
        Update vector database reference ID for a comment.
        
        Args:
            comment_id: The ID of the comment to update
            vector_id: The vector database reference ID
            
        Returns:
            True if the update was successful, False otherwise
        """
        collection = await self.collection
        result = await collection.update_one(
            {"_id": ObjectId(comment_id)},
            {"$set": {"vector_id": vector_id}}
        )
        return result.modified_count > 0
    
    async def update(
        self,
        comment_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update a comment with new data.
        
        Args:
            comment_id: The ID of the comment to update
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
            {"_id": ObjectId(comment_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def delete(self, comment_id: str) -> bool:
        """
        Delete a comment.
        
        Args:
            comment_id: The ID of the comment to delete
            
        Returns:
            True if the deletion was successful, False otherwise
        """
        collection = await self.collection
        result = await collection.delete_one({"_id": ObjectId(comment_id)})
        return result.deleted_count > 0
    
    async def count(self, query: Dict[str, Any] = None) -> int:
        """
        Count comments matching a query.
        
        Args:
            query: Query dictionary to filter comments
            
        Returns:
            Number of comments matching the query
        """
        collection = await self.collection
        return await collection.count_documents(query or {}) 