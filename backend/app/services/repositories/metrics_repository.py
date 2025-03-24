"""
Repository for analytics metrics stored in MongoDB.

This module provides a repository for aggregating and storing metrics
for social media content analysis in the Political Social Media Analysis Platform.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

import motor.motor_asyncio
from bson import ObjectId
from fastapi import Depends

from app.db.connections import get_mongodb


class MetricsRepository:
    """
    Repository for analytics metrics stored in MongoDB.
    
    This repository provides methods for aggregating and querying metrics
    related to social media content analysis.
    """
    
    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase = None):
        """
        Initialize the repository with a MongoDB database connection.
        
        Args:
            db: MongoDB database connection. If None, a connection will be
                established when methods are called.
        """
        self._db = db
        self._metrics_collection_name = "metrics"
        self._posts_collection_name = "posts"
        self._comments_collection_name = "comments"
    
    @property
    async def metrics_collection(self) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """Get the metrics collection, ensuring a database connection exists."""
        db = self._db
        if db is None:
            async with get_mongodb() as db:
                return db[self._metrics_collection_name]
        return db[self._metrics_collection_name]
    
    @property
    async def posts_collection(self) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """Get the posts collection, ensuring a database connection exists."""
        db = self._db
        if db is None:
            async with get_mongodb() as db:
                return db[self._posts_collection_name]
        return db[self._posts_collection_name]
    
    @property
    async def comments_collection(self) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """Get the comments collection, ensuring a database connection exists."""
        db = self._db
        if db is None:
            async with get_mongodb() as db:
                return db[self._comments_collection_name]
        return db[self._comments_collection_name]
    
    async def aggregate_engagement_by_account(
        self,
        account_id: Union[UUID, str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Aggregate engagement metrics for a specific account.
        
        Args:
            account_id: The UUID of the social media account
            start_date: Optional start date for filtering metrics
            end_date: Optional end date for filtering metrics
            
        Returns:
            Dictionary of aggregated engagement metrics
        """
        posts_collection = await self.posts_collection
        account_id_str = str(account_id)
        
        # Build the match stage for the aggregation pipeline
        match_stage = {"account_id": account_id_str}
        if start_date or end_date:
            match_stage["metadata.created_at"] = {}
            if start_date:
                match_stage["metadata.created_at"]["$gte"] = start_date
            if end_date:
                match_stage["metadata.created_at"]["$lte"] = end_date
        
        # Aggregation pipeline for engagement metrics
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": None,
                "total_posts": {"$sum": 1},
                "total_likes": {"$sum": "$engagement.likes_count"},
                "total_comments": {"$sum": "$engagement.comments_count"},
                "total_shares": {"$sum": "$engagement.shares_count"},
                "avg_likes": {"$avg": "$engagement.likes_count"},
                "avg_comments": {"$avg": "$engagement.comments_count"},
                "avg_shares": {"$avg": "$engagement.shares_count"},
                "first_post_date": {"$min": "$metadata.created_at"},
                "last_post_date": {"$max": "$metadata.created_at"}
            }}
        ]
        
        result = await posts_collection.aggregate(pipeline).to_list(length=1)
        if result:
            metrics = result[0]
            metrics.pop("_id", None)
            
            # Calculate average engagement per post
            if metrics.get("total_posts", 0) > 0:
                total_engagements = (
                    metrics.get("total_likes", 0) +
                    metrics.get("total_comments", 0) +
                    metrics.get("total_shares", 0)
                )
                metrics["avg_engagement_per_post"] = total_engagements / metrics["total_posts"]
            else:
                metrics["avg_engagement_per_post"] = 0
                
            return metrics
        
        return {
            "total_posts": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "avg_likes": 0,
            "avg_comments": 0,
            "avg_shares": 0,
            "avg_engagement_per_post": 0
        }
    
    async def aggregate_engagement_by_platform(
        self,
        platform: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Aggregate engagement metrics for a specific platform.
        
        Args:
            platform: The social media platform (e.g., twitter, facebook)
            start_date: Optional start date for filtering metrics
            end_date: Optional end date for filtering metrics
            
        Returns:
            Dictionary of aggregated engagement metrics
        """
        posts_collection = await self.posts_collection
        
        # Build the match stage for the aggregation pipeline
        match_stage = {"platform": platform}
        if start_date or end_date:
            match_stage["metadata.created_at"] = {}
            if start_date:
                match_stage["metadata.created_at"]["$gte"] = start_date
            if end_date:
                match_stage["metadata.created_at"]["$lte"] = end_date
        
        # Aggregation pipeline for engagement metrics
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": None,
                "total_posts": {"$sum": 1},
                "total_likes": {"$sum": "$engagement.likes_count"},
                "total_comments": {"$sum": "$engagement.comments_count"},
                "total_shares": {"$sum": "$engagement.shares_count"},
                "avg_likes": {"$avg": "$engagement.likes_count"},
                "avg_comments": {"$avg": "$engagement.comments_count"},
                "avg_shares": {"$avg": "$engagement.shares_count"}
            }}
        ]
        
        result = await posts_collection.aggregate(pipeline).to_list(length=1)
        if result:
            metrics = result[0]
            metrics.pop("_id", None)
            
            # Calculate average engagement per post
            if metrics.get("total_posts", 0) > 0:
                total_engagements = (
                    metrics.get("total_likes", 0) +
                    metrics.get("total_comments", 0) +
                    metrics.get("total_shares", 0)
                )
                metrics["avg_engagement_per_post"] = total_engagements / metrics["total_posts"]
            else:
                metrics["avg_engagement_per_post"] = 0
                
            return metrics
        
        return {
            "total_posts": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "avg_likes": 0,
            "avg_comments": 0,
            "avg_shares": 0,
            "avg_engagement_per_post": 0
        }
    
    async def aggregate_sentiment_by_account(
        self,
        account_id: Union[UUID, str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Aggregate sentiment metrics for a specific account.
        
        Args:
            account_id: The UUID of the social media account
            start_date: Optional start date for filtering metrics
            end_date: Optional end date for filtering metrics
            
        Returns:
            Dictionary of aggregated sentiment metrics
        """
        posts_collection = await self.posts_collection
        comments_collection = await self.comments_collection
        account_id_str = str(account_id)
        
        # Build the match stage for the aggregation pipeline
        post_match_stage = {"account_id": account_id_str, "analysis.sentiment_score": {"$exists": True}}
        if start_date or end_date:
            post_match_stage["metadata.created_at"] = {}
            if start_date:
                post_match_stage["metadata.created_at"]["$gte"] = start_date
            if end_date:
                post_match_stage["metadata.created_at"]["$lte"] = end_date
        
        # Aggregation pipeline for post sentiment metrics
        post_pipeline = [
            {"$match": post_match_stage},
            {"$group": {
                "_id": None,
                "avg_sentiment": {"$avg": "$analysis.sentiment_score"},
                "max_sentiment": {"$max": "$analysis.sentiment_score"},
                "min_sentiment": {"$min": "$analysis.sentiment_score"},
                "total_analyzed_posts": {"$sum": 1}
            }}
        ]
        
        # Aggregation for comment sentiment on this account's posts
        posts_with_id = await posts_collection.find(
            {"account_id": account_id_str},
            {"_id": 1}
        ).to_list(length=None)
        
        post_ids = [str(post["_id"]) for post in posts_with_id]
        
        comment_match_stage = {
            "post_id": {"$in": post_ids},
            "analysis.sentiment_score": {"$exists": True}
        }
        if start_date or end_date:
            comment_match_stage["metadata.created_at"] = {}
            if start_date:
                comment_match_stage["metadata.created_at"]["$gte"] = start_date
            if end_date:
                comment_match_stage["metadata.created_at"]["$lte"] = end_date
        
        comment_pipeline = [
            {"$match": comment_match_stage},
            {"$group": {
                "_id": None,
                "avg_comment_sentiment": {"$avg": "$analysis.sentiment_score"},
                "total_analyzed_comments": {"$sum": 1},
                "positive_comments": {"$sum": {"$cond": [{"$gt": ["$analysis.sentiment_score", 0.5]}, 1, 0]}},
                "negative_comments": {"$sum": {"$cond": [{"$lt": ["$analysis.sentiment_score", 0.5]}, 1, 0]}},
                "neutral_comments": {"$sum": {"$cond": [{"$eq": ["$analysis.sentiment_score", 0.5]}, 1, 0]}}
            }}
        ]
        
        post_result = await posts_collection.aggregate(post_pipeline).to_list(length=1)
        comment_result = await comments_collection.aggregate(comment_pipeline).to_list(length=1)
        
        # Combine results
        metrics = {}
        
        if post_result:
            post_metrics = post_result[0]
            post_metrics.pop("_id", None)
            metrics.update(post_metrics)
        else:
            metrics.update({
                "avg_sentiment": 0,
                "max_sentiment": 0,
                "min_sentiment": 0,
                "total_analyzed_posts": 0
            })
        
        if comment_result:
            comment_metrics = comment_result[0]
            comment_metrics.pop("_id", None)
            metrics.update(comment_metrics)
        else:
            metrics.update({
                "avg_comment_sentiment": 0,
                "total_analyzed_comments": 0,
                "positive_comments": 0,
                "negative_comments": 0,
                "neutral_comments": 0
            })
        
        return metrics
    
    async def aggregate_topics_by_account(
        self,
        account_id: Union[UUID, str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Aggregate top topics for a specific account.
        
        Args:
            account_id: The UUID of the social media account
            start_date: Optional start date for filtering metrics
            end_date: Optional end date for filtering metrics
            limit: Maximum number of topics to return
            
        Returns:
            List of top topics with counts
        """
        posts_collection = await self.posts_collection
        account_id_str = str(account_id)
        
        # Build the match stage for the aggregation pipeline
        match_stage = {"account_id": account_id_str, "analysis.topics": {"$exists": True, "$ne": []}}
        if start_date or end_date:
            match_stage["metadata.created_at"] = {}
            if start_date:
                match_stage["metadata.created_at"]["$gte"] = start_date
            if end_date:
                match_stage["metadata.created_at"]["$lte"] = end_date
        
        # Aggregation pipeline for topic extraction
        pipeline = [
            {"$match": match_stage},
            {"$unwind": "$analysis.topics"},
            {"$group": {
                "_id": "$analysis.topics",
                "count": {"$sum": 1},
                "avg_sentiment": {"$avg": "$analysis.sentiment_score"},
                "posts": {"$push": {"$toString": "$_id"}}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "topic": "$_id",
                "count": 1,
                "avg_sentiment": 1,
                "post_sample": {"$slice": ["$posts", 5]}
            }}
        ]
        
        result = await posts_collection.aggregate(pipeline).to_list(length=limit)
        return result if result else []
    
    async def aggregate_engagement_over_time(
        self,
        account_id: Optional[Union[UUID, str]] = None,
        platform: Optional[str] = None,
        interval: str = "day",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Aggregate engagement metrics over time with specified intervals.
        
        Args:
            account_id: Optional UUID of the social media account to filter by
            platform: Optional platform to filter by
            interval: Time interval for grouping ('hour', 'day', 'week', 'month')
            start_date: Optional start date for filtering metrics
            end_date: Optional end date for filtering metrics
            
        Returns:
            List of engagement metrics aggregated by time interval
        """
        posts_collection = await self.posts_collection
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            if interval == "hour":
                start_date = end_date - timedelta(days=1)
            elif interval == "day":
                start_date = end_date - timedelta(days=30)
            elif interval == "week":
                start_date = end_date - timedelta(days=90)
            else:  # month
                start_date = end_date - timedelta(days=365)
        
        # Build the match stage for the aggregation pipeline
        match_stage = {"metadata.created_at": {"$gte": start_date, "$lte": end_date}}
        if account_id:
            match_stage["account_id"] = str(account_id)
        if platform:
            match_stage["platform"] = platform
        
        # Define the date grouping format based on the interval
        date_format = {
            "hour": "%Y-%m-%d %H:00",
            "day": "%Y-%m-%d",
            "week": "%Y-W%U",
            "month": "%Y-%m"
        }
        
        # Aggregation pipeline for time-based metrics
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": {
                    "date": {
                        "$dateToString": {
                            "format": date_format.get(interval, "%Y-%m-%d"),
                            "date": "$metadata.created_at"
                        }
                    }
                },
                "posts": {"$sum": 1},
                "likes": {"$sum": "$engagement.likes_count"},
                "comments": {"$sum": "$engagement.comments_count"},
                "shares": {"$sum": "$engagement.shares_count"},
                "avg_sentiment": {"$avg": "$analysis.sentiment_score"},
                "date": {"$first": "$metadata.created_at"}
            }},
            {"$sort": {"date": 1}},
            {"$project": {
                "_id": 0,
                "date": "$_id.date",
                "timestamp": "$date",
                "posts": 1,
                "likes": 1,
                "comments": 1,
                "shares": 1,
                "total_engagement": {"$sum": ["$likes", "$comments", "$shares"]},
                "avg_sentiment": 1
            }}
        ]
        
        result = await posts_collection.aggregate(pipeline).to_list(length=None)
        return result if result else []
    
    async def store_aggregated_metrics(
        self,
        metrics_type: str,
        entity_id: Optional[Union[UUID, str]] = None,
        platform: Optional[str] = None,
        time_period: Optional[str] = None,
        metrics_data: Dict[str, Any] = None
    ) -> str:
        """
        Store aggregated metrics for later retrieval.
        
        Args:
            metrics_type: Type of metrics (engagement, sentiment, topics)
            entity_id: Optional UUID of the entity these metrics relate to
            platform: Optional platform these metrics relate to
            time_period: Optional time period description for these metrics
            metrics_data: The metrics data to store
            
        Returns:
            The ID of the stored metrics document
        """
        metrics_collection = await self.metrics_collection
        
        metrics_doc = {
            "type": metrics_type,
            "calculated_at": datetime.utcnow(),
            "data": metrics_data
        }
        
        if entity_id:
            metrics_doc["entity_id"] = str(entity_id)
        
        if platform:
            metrics_doc["platform"] = platform
        
        if time_period:
            metrics_doc["time_period"] = time_period
        
        result = await metrics_collection.insert_one(metrics_doc)
        return str(result.inserted_id)
    
    async def get_stored_metrics(
        self,
        metrics_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve previously stored metrics by ID.
        
        Args:
            metrics_id: The ID of the metrics document
            
        Returns:
            The stored metrics document if found, None otherwise
        """
        metrics_collection = await self.metrics_collection
        metrics = await metrics_collection.find_one({"_id": ObjectId(metrics_id)})
        return metrics
    
    async def find_latest_metrics(
        self,
        metrics_type: str,
        entity_id: Optional[Union[UUID, str]] = None,
        platform: Optional[str] = None,
        max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Find the latest metrics of a specified type.
        
        Args:
            metrics_type: Type of metrics to find
            entity_id: Optional entity ID to filter by
            platform: Optional platform to filter by
            max_age_hours: Maximum age of metrics in hours
            
        Returns:
            The latest metrics document if found, None otherwise
        """
        metrics_collection = await self.metrics_collection
        min_date = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        query = {
            "type": metrics_type,
            "calculated_at": {"$gte": min_date}
        }
        
        if entity_id:
            query["entity_id"] = str(entity_id)
        
        if platform:
            query["platform"] = platform
        
        metrics = await metrics_collection.find_one(
            query,
            sort=[("calculated_at", -1)]
        )
        
        return metrics 