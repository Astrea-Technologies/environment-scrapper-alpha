"""Database connection utilities for MongoDB, Redis, and Pinecone.

This module provides connection utilities for the hybrid database architecture used in the
Political Social Media Analysis Platform. It implements connection management for:
- MongoDB: For storing social media content and engagement data
- Redis: For caching and real-time operations (not used in MVP)
- Pinecone: For vector similarity search and semantic analysis
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Union
from functools import lru_cache

import motor.motor_asyncio
import pinecone
from pinecone import Index
import redis.asyncio as redis
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from app.core.config import settings


class MongoDBConnection:
    """MongoDB connection manager using motor for async operations."""
    
    def __init__(self) -> None:
        """Initialize MongoDB connection manager."""
        self._client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self._db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Connect to MongoDB and initialize database."""
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000
            )
            # Test the connection
            await self._client.admin.command('ping')
            self._db = self._client[settings.MONGODB_DB]
            
            # Create indexes for common queries
            await self._create_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")

    async def _create_indexes(self) -> None:
        """Create indexes for common queries."""
        if self._db is None:
            return

        # Posts collection indexes
        await self._db.posts.create_index([("created_at", -1)])
        await self._db.posts.create_index([("platform", 1), ("external_id", 1)], unique=True)
        await self._db.posts.create_index([("content", "text")])
        
        # Comments collection indexes
        await self._db.comments.create_index([("post_id", 1), ("created_at", -1)])
        await self._db.comments.create_index([("content", "text")])

    @property
    def db(self) -> motor.motor_asyncio.AsyncIOMotorDatabase:
        """Get the database instance."""
        if self._db is None:
            raise ConnectionError("MongoDB connection not initialized")
        return self._db

    @property
    def client(self) -> motor.motor_asyncio.AsyncIOMotorClient:
        """Get the client instance."""
        if self._client is None:
            raise ConnectionError("MongoDB client not initialized")
        return self._client

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None


class RedisConnection:
    """
    Redis connection manager for async operations.
    
    NOTE: Not used in MVP - This implementation is reserved for future releases.
    Redis functionality is disabled in the MVP to simplify initial deployment.
    """
    
    def __init__(self) -> None:
        """Initialize Redis connection manager."""
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """
        Connect to Redis.
        
        If USE_REDIS is False, this will not actually establish a connection.
        """
        if not settings.USE_REDIS:
            return
            
        try:
            self._client = redis.from_url(
                settings.REDIS_URI,
                encoding="utf-8",
                decode_responses=True
            )
            # Test the connection
            await self._client.ping()
        except RedisConnectionError as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client instance."""
        if self._client is None:
            raise ConnectionError("Redis connection not initialized or Redis is disabled in MVP")
        return self._client

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None


class MockRedisClient:
    """Mock Redis client used when Redis is disabled (MVP)."""
    
    async def get(self, *args, **kwargs):
        """Mock get that always returns None."""
        return None
        
    async def set(self, *args, **kwargs):
        """Mock set that does nothing."""
        return True
        
    async def ping(self, *args, **kwargs):
        """Mock ping that always succeeds."""
        return True
        
    # Add other mock methods as needed for the MVP
    
    async def close(self):
        """Mock close method."""
        pass


class PineconeConnection:
    """Pinecone connection manager for vector similarity search."""
    
    def __init__(self) -> None:
        """Initialize Pinecone connection manager."""
        self._index: Optional[Index] = None

    def connect(self) -> None:
        """Initialize Pinecone connection and ensure index exists."""
        try:
            # Initialize Pinecone client
            pinecone.init(api_key=settings.PINECONE_API_KEY)
            
            # Create index if it doesn't exist
            if settings.PINECONE_INDEX_NAME not in pinecone.list_indexes():
                pinecone.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=384,  # Dimension for all-MiniLM-L6-v2 embeddings
                    metric="cosine"
                )
            
            # Get the index
            self._index = pinecone.Index(settings.PINECONE_INDEX_NAME)
        except Exception as e:
            raise ConnectionError(f"Failed to initialize Pinecone: {e}")

    @property
    def index(self):
        """Get the Pinecone index instance."""
        if self._index is None:
            raise ConnectionError("Pinecone connection not initialized")
        return self._index

    def close(self) -> None:
        """Clean up Pinecone resources."""
        if self._index is not None:
            self._index = None


# Singleton instances
mongodb = MongoDBConnection()
redis_conn = RedisConnection()
pinecone_conn = PineconeConnection()


@asynccontextmanager
async def get_mongodb() -> AsyncGenerator[motor.motor_asyncio.AsyncIOMotorDatabase, None]:
    """Async context manager for getting MongoDB database instance."""
    if mongodb._client is None:
        await mongodb.connect()
    try:
        yield mongodb.db
    except Exception as e:
        raise ConnectionError(f"Error accessing MongoDB: {e}")


@asynccontextmanager
async def get_redis() -> AsyncGenerator[Union[redis.Redis, MockRedisClient], None]:
    """
    Async context manager for getting Redis client instance.
    
    If Redis is disabled (MVP), returns a mock client that does nothing.
    """
    if not settings.USE_REDIS:
        # In MVP, return a mock client that does nothing
        mock_client = MockRedisClient()
        try:
            yield mock_client
        finally:
            await mock_client.close()
        return
        
    if redis_conn._client is None:
        await redis_conn.connect()
    try:
        yield redis_conn.client
    except RedisError as e:
        raise ConnectionError(f"Error accessing Redis: {e}")


@lru_cache()
def get_pinecone():
    """Get Pinecone index instance with caching."""
    if pinecone_conn._index is None:
        pinecone_conn.connect()
    return pinecone_conn.index


async def close_db_connections() -> None:
    """Close all database connections."""
    await mongodb.close()
    if settings.USE_REDIS:
        await redis_conn.close()
    pinecone_conn.close() 