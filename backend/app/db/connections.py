"""Database connection utilities for MongoDB, Redis, and Pinecone.

This module provides connection utilities for the hybrid database architecture used in the
Political Social Media Analysis Platform. It implements connection management for:
- MongoDB: For storing social media content and engagement data
- Redis: For caching and real-time operations (not used in MVP)
- Pinecone: For vector similarity search and semantic analysis
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Union, Any
from functools import lru_cache
import logging
import importlib
import sys

import motor.motor_asyncio
# Import pinecone dynamically only when needed
import redis.asyncio as redis
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from app.core.config import settings


logger = logging.getLogger(__name__)


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
        self._index = None
        self._pinecone_client = None
        self._available = False
        self._api_version = None

    def connect(self) -> None:
        """
        Initialize Pinecone connection and ensure index exists.
        
        If Pinecone is not available or API key is not provided, 
        this will log a warning but not fail.
        """
        if not settings.PINECONE_API_KEY:
            logger.warning("Skipping Pinecone connection - API key not provided")
            return

        try:
            # Try to import pinecone dynamically to avoid module-level import issues
            if 'pinecone' in sys.modules:
                del sys.modules['pinecone']
                
            pinecone_module = importlib.import_module('pinecone')
            
            # First try the new API (pinecone package)
            try:
                # Check if we have new Pinecone API (v6+)
                if hasattr(pinecone_module, 'Pinecone'):
                    logger.info("Using Pinecone v6+ API")
                    self._api_version = "v6+"
                    Pinecone = getattr(pinecone_module, 'Pinecone')
                    ServerlessSpec = getattr(pinecone_module, 'ServerlessSpec', None)
                    
                    client = Pinecone(api_key=settings.PINECONE_API_KEY)
                    self._pinecone_client = client
                    
                    try:
                        # Try to get the index
                        self._index = client.Index(settings.PINECONE_INDEX_NAME)
                        self._available = True
                        logger.info(f"Connected to Pinecone index: {settings.PINECONE_INDEX_NAME}")
                    except Exception as e:
                        logger.info(f"Creating new Pinecone index: {settings.PINECONE_INDEX_NAME}")
                        # Create a new index
                        if ServerlessSpec:
                            client.create_index(
                                name=settings.PINECONE_INDEX_NAME,
                                dimension=settings.OPENAI_EMBEDDING_DIMENSION,
                                metric="cosine",
                                spec=ServerlessSpec(cloud="aws", region="us-west-2")
                            )
                        else:
                            client.create_index(
                                name=settings.PINECONE_INDEX_NAME,
                                dimension=settings.OPENAI_EMBEDDING_DIMENSION,
                                metric="cosine"
                            )
                        self._index = client.Index(settings.PINECONE_INDEX_NAME)
                        self._available = True
                
                # Fall back to old pinecone-client API
                else:
                    logger.info("Using pinecone-client legacy API")
                    self._api_version = "legacy"
                    # Old API style using pinecone.init()
                    pinecone_module.init(api_key=settings.PINECONE_API_KEY, 
                                        environment=settings.PINECONE_ENVIRONMENT)
                    self._pinecone_client = pinecone_module
                    
                    # Create index if it doesn't exist
                    existing_indexes = pinecone_module.list_indexes()
                    if settings.PINECONE_INDEX_NAME not in existing_indexes:
                        logger.info(f"Creating new Pinecone index: {settings.PINECONE_INDEX_NAME}")
                        pinecone_module.create_index(
                            name=settings.PINECONE_INDEX_NAME,
                            dimension=settings.OPENAI_EMBEDDING_DIMENSION,
                            metric="cosine"
                        )
                    
                    # Get the index
                    self._index = pinecone_module.Index(settings.PINECONE_INDEX_NAME)
                    self._available = True
                    logger.info(f"Connected to Pinecone index: {settings.PINECONE_INDEX_NAME}")
            
            except Exception as e:
                logger.warning(f"Failed to initialize Pinecone: {str(e)}")
                self._available = False
                
        except ImportError as e:
            logger.warning(f"Pinecone package not available: {str(e)}")
            self._available = False
        except Exception as e:
            logger.warning(f"Failed to initialize Pinecone: {str(e)}")
            self._available = False

    @property
    def index(self):
        """Get the Pinecone index instance."""
        if not self._available or self._index is None:
            logger.warning("Pinecone connection not initialized or not available")
            return None
        return self._index
    
    @property
    def available(self) -> bool:
        """Check if Pinecone is available."""
        return self._available and self._index is not None
    
    @property
    def api_version(self) -> Optional[str]:
        """Get the Pinecone API version being used."""
        return self._api_version

    def close(self) -> None:
        """Clean up Pinecone resources."""
        if self._index is not None:
            self._index = None
            self._pinecone_client = None
            self._available = False


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
    """
    Get Pinecone index instance with caching.
    
    Returns None if Pinecone is not available or not initialized.
    This function allows the application to work even when Pinecone is not properly configured.
    """
    if pinecone_conn._index is None:
        pinecone_conn.connect()
    return pinecone_conn.index


async def close_db_connections() -> None:
    """Close all database connections."""
    await mongodb.close()
    if settings.USE_REDIS:
        await redis_conn.close()
    pinecone_conn.close() 