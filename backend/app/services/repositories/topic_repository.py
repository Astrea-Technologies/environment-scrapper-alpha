"""
Repository for topic analysis stored in MongoDB.

This module provides a repository for CRUD operations and queries on topic analysis data
stored in MongoDB as part of the Political Social Media Analysis Platform.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Literal
from uuid import UUID

import motor.motor_asyncio
from bson import ObjectId
from fastapi import Depends
from pymongo import ReturnDocument

from app.db.connections import get_mongodb
from app.db.schemas.mongodb import TopicAnalysis, TopicOccurrence, TopicTrend


class TopicRepository:
    """
    Repository for topic analysis data stored in MongoDB.
    
    This repository provides methods for CRUD operations and specialized queries
    on topic analysis data stored in the MongoDB database, including topics,
    topic occurrences, and topic trends.
    """
    
    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase = None):
        """
        Initialize the repository with a MongoDB database connection.
        
        Args:
            db: MongoDB database connection. If None, a connection will be
                established when methods are called.
        """
        self._db = db
        self._topics_collection = "topics"
        self._occurrences_collection = "topic_occurrences"
        self._trends_collection = "topic_trends"
    
    @property
    async def topics_collection(self) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """Get the topics collection, ensuring a database connection exists."""
        db = self._db
        if db is None:
            async with get_mongodb() as db:
                return db[self._topics_collection]
        return db[self._topics_collection]
    
    @property
    async def occurrences_collection(self) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """Get the topic occurrences collection, ensuring a database connection exists."""
        db = self._db
        if db is None:
            async with get_mongodb() as db:
                return db[self._occurrences_collection]
        return db[self._occurrences_collection]
    
    @property
    async def trends_collection(self) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """Get the topic trends collection, ensuring a database connection exists."""
        db = self._db
        if db is None:
            async with get_mongodb() as db:
                return db[self._trends_collection]
        return db[self._trends_collection]
    
    # --- Topic CRUD Operations ---
    
    async def create_topic(self, topic_data: Dict[str, Any]) -> str:
        """
        Create a new topic for analysis.
        
        Args:
            topic_data: Dictionary with topic data following the TopicAnalysis schema
            
        Returns:
            The ID of the created topic
        """
        collection = await self.topics_collection
        
        # Set timestamps if not provided
        if "created_at" not in topic_data:
            topic_data["created_at"] = datetime.utcnow()
        if "updated_at" not in topic_data:
            topic_data["updated_at"] = datetime.utcnow()
            
        # Convert timestamps from string format if necessary
        if isinstance(topic_data.get("created_at"), str):
            topic_data["created_at"] = datetime.fromisoformat(
                topic_data["created_at"].replace("Z", "+00:00")
            )
        if isinstance(topic_data.get("updated_at"), str):
            topic_data["updated_at"] = datetime.fromisoformat(
                topic_data["updated_at"].replace("Z", "+00:00")
            )
        
        result = await collection.insert_one(topic_data)
        return str(result.inserted_id)
    
    async def get_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a topic by ID.
        
        Args:
            topic_id: The ID of the topic to retrieve
            
        Returns:
            The topic data if found, None otherwise
        """
        collection = await self.topics_collection
        try:
            # Try to find by MongoDB ObjectId
            topic = await collection.find_one({"_id": ObjectId(topic_id)})
            if topic:
                return topic
        except:
            pass
        
        # Try to find by custom topic_id field
        topic = await collection.find_one({"topic_id": topic_id})
        return topic
    
    async def get_topic_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a topic by name (exact match).
        
        Args:
            name: The name of the topic to retrieve
            
        Returns:
            The topic data if found, None otherwise
        """
        collection = await self.topics_collection
        topic = await collection.find_one({"name": name})
        return topic
    
    async def list_topics(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "name",
        sort_direction: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get a list of topics with pagination and sorting options.
        
        Args:
            skip: Number of topics to skip
            limit: Maximum number of topics to return
            sort_by: Field to sort by
            sort_direction: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of topics
        """
        collection = await self.topics_collection
        cursor = collection.find().skip(skip).limit(limit).sort(sort_by, sort_direction)
        return await cursor.to_list(length=limit)
    
    async def update_topic(
        self,
        topic_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a topic.
        
        Args:
            topic_id: The ID of the topic to update
            update_data: Dictionary with updated topic data
            
        Returns:
            The updated topic data if found and updated, None otherwise
        """
        collection = await self.topics_collection
        
        # Always update the updated_at timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        try:
            # Try to update by MongoDB ObjectId
            updated_topic = await collection.find_one_and_update(
                {"_id": ObjectId(topic_id)},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            if updated_topic:
                return updated_topic
        except:
            pass
        
        # Try to update by custom topic_id field
        updated_topic = await collection.find_one_and_update(
            {"topic_id": topic_id},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )
        return updated_topic
    
    async def delete_topic(self, topic_id: str) -> bool:
        """
        Delete a topic.
        
        Args:
            topic_id: The ID of the topic to delete
            
        Returns:
            True if the topic was found and deleted, False otherwise
        """
        collection = await self.topics_collection
        
        try:
            # Try to delete by MongoDB ObjectId
            result = await collection.delete_one({"_id": ObjectId(topic_id)})
            if result.deleted_count > 0:
                return True
        except:
            pass
        
        # Try to delete by custom topic_id field
        result = await collection.delete_one({"topic_id": topic_id})
        return result.deleted_count > 0
    
    # --- Topic Search and Filtering ---
    
    async def find_topics_by_keywords(
        self,
        keywords: List[str],
        match_all: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find topics by matching keywords.
        
        Args:
            keywords: List of keywords to match
            match_all: If True, all keywords must match; if False, any keyword can match
            skip: Number of topics to skip
            limit: Maximum number of topics to return
            
        Returns:
            List of matching topics
        """
        collection = await self.topics_collection
        
        if match_all:
            # All keywords must be in the keywords array
            query = {"keywords": {"$all": keywords}}
        else:
            # Any of the keywords can be in the keywords array
            query = {"keywords": {"$in": keywords}}
        
        cursor = collection.find(query).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def find_topics_by_text_search(
        self,
        search_text: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find topics using full-text search across names, keywords, and descriptions.
        
        Args:
            search_text: Text to search for
            skip: Number of topics to skip
            limit: Maximum number of topics to return
            
        Returns:
            List of matching topics with search score
        """
        collection = await self.topics_collection
        
        # Ensure text index exists
        await collection.create_index([
            ("name", "text"),
            ("keywords", "text"),
            ("description", "text")
        ])
        
        cursor = collection.find(
            {"$text": {"$search": search_text}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def get_topics_by_category(
        self,
        category: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get topics by category.
        
        Args:
            category: Category to filter by
            skip: Number of topics to skip
            limit: Maximum number of topics to return
            
        Returns:
            List of topics in the specified category
        """
        collection = await self.topics_collection
        cursor = collection.find({"category": category}).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    # --- Topic Occurrence Operations ---
    
    async def record_topic_occurrence(
        self,
        occurrence_data: Dict[str, Any]
    ) -> str:
        """
        Record a topic occurrence in content.
        
        Args:
            occurrence_data: Dictionary with occurrence data following the TopicOccurrence schema
            
        Returns:
            The ID of the created occurrence record
        """
        collection = await self.occurrences_collection
        
        # Set detected_at if not provided
        if "detected_at" not in occurrence_data:
            occurrence_data["detected_at"] = datetime.utcnow()
            
        # Convert timestamp from string format if necessary
        if isinstance(occurrence_data.get("detected_at"), str):
            occurrence_data["detected_at"] = datetime.fromisoformat(
                occurrence_data["detected_at"].replace("Z", "+00:00")
            )
        
        result = await collection.insert_one(occurrence_data)
        return str(result.inserted_id)
    
    async def get_topic_occurrences(
        self,
        topic_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        content_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get occurrences of a topic with optional filtering.
        
        Args:
            topic_id: ID of the topic
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            content_type: Optional content type filter (post or comment)
            skip: Number of occurrences to skip
            limit: Maximum number of occurrences to return
            
        Returns:
            List of topic occurrences
        """
        collection = await self.occurrences_collection
        
        # Build query with required filters
        query = {"topic_id": topic_id}
        
        # Add optional date range filter
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            if date_filter:
                query["detected_at"] = date_filter
        
        # Add optional content type filter
        if content_type:
            query["content_type"] = content_type
        
        cursor = collection.find(query).skip(skip).limit(limit).sort("detected_at", -1)
        return await cursor.to_list(length=limit)
    
    async def delete_topic_occurrences(self, topic_id: str) -> int:
        """
        Delete all occurrences of a topic.
        
        Args:
            topic_id: ID of the topic
            
        Returns:
            Number of deleted occurrence records
        """
        collection = await self.occurrences_collection
        result = await collection.delete_many({"topic_id": topic_id})
        return result.deleted_count
    
    # --- Topic Trend Operations ---
    
    async def create_or_update_topic_trend(
        self,
        trend_data: Dict[str, Any]
    ) -> str:
        """
        Create or update a topic trend record.
        
        Args:
            trend_data: Dictionary with trend data following the TopicTrend schema
            
        Returns:
            The ID of the created or updated trend record
        """
        collection = await self.trends_collection
        
        # Convert dates from string format if necessary
        if isinstance(trend_data.get("start_date"), str):
            trend_data["start_date"] = datetime.fromisoformat(
                trend_data["start_date"].replace("Z", "+00:00")
            )
        if isinstance(trend_data.get("end_date"), str):
            trend_data["end_date"] = datetime.fromisoformat(
                trend_data["end_date"].replace("Z", "+00:00")
            )
        
        # Check if a trend record already exists for this topic and time period
        existing_trend = await collection.find_one({
            "topic_id": trend_data["topic_id"],
            "time_period": trend_data["time_period"],
            "start_date": trend_data["start_date"],
            "end_date": trend_data["end_date"]
        })
        
        if existing_trend:
            # Update existing trend
            result = await collection.update_one(
                {"_id": existing_trend["_id"]},
                {"$set": trend_data}
            )
            return str(existing_trend["_id"])
        else:
            # Create new trend
            result = await collection.insert_one(trend_data)
            return str(result.inserted_id)
    
    async def get_topic_trend(
        self,
        topic_id: str,
        time_period: str,
        start_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific topic trend.
        
        Args:
            topic_id: ID of the topic
            time_period: Time period (day, week, month)
            start_date: Start date of the time period
            
        Returns:
            The topic trend data if found, None otherwise
        """
        collection = await self.trends_collection
        trend = await collection.find_one({
            "topic_id": topic_id,
            "time_period": time_period,
            "start_date": start_date
        })
        return trend
    
    async def get_topic_trends(
        self,
        topic_id: str,
        time_period: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trends for a topic over time.
        
        Args:
            topic_id: ID of the topic
            time_period: Time period (day, week, month)
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of trend records to return
            
        Returns:
            List of topic trend records
        """
        collection = await self.trends_collection
        
        # Build query with required filters
        query = {
            "topic_id": topic_id,
            "time_period": time_period
        }
        
        # Add optional date range filter
        if start_date or end_date:
            if start_date:
                query["start_date"] = {"$gte": start_date}
            if end_date:
                query["end_date"] = {"$lte": end_date}
        
        cursor = collection.find(query).limit(limit).sort("start_date", -1)
        return await cursor.to_list(length=limit)
    
    # --- Aggregation and Analysis Methods ---
    
    async def aggregate_topic_occurrences_by_time(
        self,
        topic_id: str,
        time_period: Literal["day", "week", "month"],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Aggregate topic occurrences by time period.
        
        Args:
            topic_id: ID of the topic
            time_period: Time period for aggregation (day, week, month)
            start_date: Start date for the aggregation period
            end_date: End date for the aggregation period
            
        Returns:
            Aggregated data for the specified time period
        """
        collection = await self.occurrences_collection
        
        # Determine the date grouping format based on time period
        date_format = None
        if time_period == "day":
            date_format = "%Y-%m-%d"
        elif time_period == "week":
            date_format = "%Y-%U"  # Year and week number
        elif time_period == "month":
            date_format = "%Y-%m"
        
        # Create aggregation pipeline
        pipeline = [
            {
                "$match": {
                    "topic_id": topic_id,
                    "detected_at": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": date_format, "date": "$detected_at"}}
                    },
                    "count": {"$sum": 1},
                    "avg_sentiment": {"$avg": "$sentiment_context"},
                    "content_ids": {"$push": "$content_id"}
                }
            },
            {
                "$sort": {
                    "_id.date": 1
                }
            }
        ]
        
        results = await collection.aggregate(pipeline).to_list(None)
        
        # Format the results
        formatted_results = {
            "topic_id": topic_id,
            "time_period": time_period,
            "start_date": start_date,
            "end_date": end_date,
            "data_points": []
        }
        
        for result in results:
            formatted_results["data_points"].append({
                "date": result["_id"]["date"],
                "count": result["count"],
                "avg_sentiment": result.get("avg_sentiment"),
                "content_count": len(result.get("content_ids", []))
            })
        
        return formatted_results
    
    async def find_trending_topics(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10,
        min_occurrences: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find trending topics within a given timeframe.
        
        Args:
            start_date: Start date for the trend period
            end_date: End date for the trend period
            limit: Maximum number of trending topics to return
            min_occurrences: Minimum number of occurrences to be considered trending
            
        Returns:
            List of trending topics with occurrence counts and growth rate
        """
        collection = await self.occurrences_collection
        topics_collection = await self.topics_collection
        
        # Define the comparison periods
        current_period = {
            "start": start_date,
            "end": end_date
        }
        
        period_duration = end_date - start_date
        previous_period = {
            "start": start_date - period_duration,
            "end": start_date
        }
        
        # Aggregate current period
        current_pipeline = [
            {
                "$match": {
                    "detected_at": {
                        "$gte": current_period["start"],
                        "$lte": current_period["end"]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$topic_id",
                    "current_count": {"$sum": 1},
                    "avg_sentiment": {"$avg": "$sentiment_context"},
                    "content_ids": {"$addToSet": "$content_id"}
                }
            },
            {
                "$match": {
                    "current_count": {"$gte": min_occurrences}
                }
            }
        ]
        
        current_results = await collection.aggregate(current_pipeline).to_list(None)
        
        # Create a mapping of topic_id to current data
        topic_data = {result["_id"]: result for result in current_results}
        
        # Aggregate previous period for the same topics
        if topic_data:
            topic_ids = list(topic_data.keys())
            
            previous_pipeline = [
                {
                    "$match": {
                        "topic_id": {"$in": topic_ids},
                        "detected_at": {
                            "$gte": previous_period["start"],
                            "$lte": previous_period["end"]
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$topic_id",
                        "previous_count": {"$sum": 1}
                    }
                }
            ]
            
            previous_results = await collection.aggregate(previous_pipeline).to_list(None)
            
            # Add previous data to the mapping
            for result in previous_results:
                if result["_id"] in topic_data:
                    topic_data[result["_id"]]["previous_count"] = result["previous_count"]
            
            # Calculate growth rates and add default previous_count if missing
            for topic_id, data in topic_data.items():
                if "previous_count" not in data:
                    data["previous_count"] = 0
                
                previous = data["previous_count"] or 1  # Avoid division by zero
                data["growth_rate"] = (data["current_count"] - previous) / previous
                data["engagement"] = len(data.get("content_ids", []))
                
                # Get topic details
                topic = await topics_collection.find_one({"topic_id": topic_id})
                if not topic:
                    topic = await topics_collection.find_one({"_id": ObjectId(topic_id)})
                
                if topic:
                    data["name"] = topic.get("name", "Unknown Topic")
                    data["category"] = topic.get("category", "Uncategorized")
                
                # Clean up content_ids to reduce response size
                if "content_ids" in data:
                    del data["content_ids"]
            
            # Sort by growth rate and then by current count
            sorted_data = sorted(
                topic_data.values(),
                key=lambda x: (x["growth_rate"], x["current_count"]),
                reverse=True
            )
            
            return sorted_data[:limit]
        
        return []
    
    async def get_topic_sentiment_analysis(
        self,
        topic_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get sentiment analysis for a topic.
        
        Args:
            topic_id: ID of the topic
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Sentiment analysis data for the topic
        """
        collection = await self.occurrences_collection
        
        # Build query with required filters
        query = {"topic_id": topic_id}
        
        # Add optional date range filter
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            if date_filter:
                query["detected_at"] = date_filter
        
        # Create aggregation pipeline for sentiment analysis
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "avg_sentiment": {"$avg": "$sentiment_context"},
                    "count": {"$sum": 1},
                    "sentiments": {"$push": "$sentiment_context"}
                }
            }
        ]
        
        results = await collection.aggregate(pipeline).to_list(None)
        
        if not results:
            return {
                "topic_id": topic_id,
                "count": 0,
                "avg_sentiment": None,
                "sentiment_distribution": {}
            }
        
        result = results[0]
        
        # Calculate sentiment distribution
        sentiments = [s for s in result.get("sentiments", []) if s is not None]
        distribution = {
            "positive": 0,
            "neutral": 0,
            "negative": 0
        }
        
        for sentiment in sentiments:
            if sentiment > 0.3:
                distribution["positive"] += 1
            elif sentiment < -0.3:
                distribution["negative"] += 1
            else:
                distribution["neutral"] += 1
        
        # Convert to percentages
        total = len(sentiments) or 1  # Avoid division by zero
        for key in distribution:
            distribution[key] = round((distribution[key] / total) * 100, 2)
        
        return {
            "topic_id": topic_id,
            "count": result["count"],
            "avg_sentiment": result.get("avg_sentiment"),
            "sentiment_distribution": distribution
        }
    
    async def find_related_topics(
        self,
        topic_id: str,
        min_co_occurrences: int = 3,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find related topics based on content co-occurrence.
        
        Args:
            topic_id: ID of the topic
            min_co_occurrences: Minimum number of co-occurrences to be considered related
            limit: Maximum number of related topics to return
            
        Returns:
            List of related topics with co-occurrence counts
        """
        occurrences_collection = await self.occurrences_collection
        topics_collection = await self.topics_collection
        
        # Get content IDs where the topic occurs
        query = {"topic_id": topic_id}
        cursor = occurrences_collection.find(query, {"content_id": 1})
        topic_content_ids = [doc["content_id"] for doc in await cursor.to_list(None)]
        
        if not topic_content_ids:
            return []
        
        # Find other topics that occur in the same content
        pipeline = [
            {
                "$match": {
                    "content_id": {"$in": topic_content_ids},
                    "topic_id": {"$ne": topic_id}
                }
            },
            {
                "$group": {
                    "_id": "$topic_id",
                    "co_occurrence_count": {"$sum": 1},
                    "content_ids": {"$addToSet": "$content_id"}
                }
            },
            {
                "$match": {
                    "co_occurrence_count": {"$gte": min_co_occurrences}
                }
            },
            {
                "$sort": {
                    "co_occurrence_count": -1
                }
            },
            {
                "$limit": limit
            }
        ]
        
        related_topics = await occurrences_collection.aggregate(pipeline).to_list(None)
        
        # Get topic details for the related topics
        for related_topic in related_topics:
            topic = await topics_collection.find_one({"topic_id": related_topic["_id"]})
            if not topic:
                topic = await topics_collection.find_one({"_id": ObjectId(related_topic["_id"])})
            
            if topic:
                related_topic["name"] = topic.get("name", "Unknown Topic")
                related_topic["category"] = topic.get("category", "Uncategorized")
                related_topic["keywords"] = topic.get("keywords", [])
            
            # Calculate correlation strength (percentage of content overlap)
            related_topic["correlation_strength"] = round(
                len(related_topic.get("content_ids", [])) / len(topic_content_ids) * 100, 2
            )
            
            # Clean up content_ids to reduce response size
            if "content_ids" in related_topic:
                del related_topic["content_ids"]
        
        return related_topics
    
    async def aggregate_topics_by_entity(
        self,
        entity_id: Union[UUID, str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Aggregate topics by political entity.
        
        Args:
            entity_id: UUID of the political entity
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of topics to return
            
        Returns:
            List of topics with occurrence and sentiment data for the entity
        """
        # Implementation would require joining data from PostgreSQL entities
        # with MongoDB topic occurrences, which is beyond the scope of this implementation
        # This would involve first getting posts from the entity, then analyzing topics
        # For now, we'll return a placeholder result
        
        return [
            {
                "topic_id": "sample_topic_1",
                "topic_name": "Sample Topic 1",
                "category": "Economy",
                "occurrences": 25,
                "avg_sentiment": 0.45,
                "most_recent_occurrence": datetime.utcnow() - timedelta(days=1)
            }
        ] 