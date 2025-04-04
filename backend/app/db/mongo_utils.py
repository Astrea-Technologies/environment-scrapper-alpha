import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from app.core.config import settings
from typing import Optional

logger = logging.getLogger(__name__)

_mongo_client: Optional[AsyncIOMotorClient] = None

async def get_mongo_client() -> AsyncIOMotorClient:
    """
    Returns the MongoDB client instance, initializing it if necessary.
    """
    global _mongo_client
    if _mongo_client is None:
        logger.info("Initializing MongoDB client...")
        try:
            _mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
            # The ismaster command is cheap and does not require auth.
            await _mongo_client.admin.command('ismaster')
            logger.info("MongoDB client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}")
            _mongo_client = None # Reset on failure
            raise
    return _mongo_client

async def close_mongo_connection():
    """
    Closes the MongoDB client connection if it exists.
    """
    global _mongo_client
    if _mongo_client:
        logger.info("Closing MongoDB connection...")
        _mongo_client.close()
        _mongo_client = None
        logger.info("MongoDB connection closed.")

async def get_mongo_database() -> AsyncIOMotorDatabase:
    """
    Returns the MongoDB database instance using the initialized client.
    """
    client = await get_mongo_client()
    if not settings.MONGODB_DB_NAME:
        raise ValueError("MONGODB_DB_NAME must be set in settings")
    return client[settings.MONGODB_DB_NAME]

async def get_mongo_collection(collection_name: str) -> AsyncIOMotorCollection:
    """
    Returns a specific MongoDB collection instance from the database.

    Args:
        collection_name: The name of the collection to retrieve.

    Returns:
        An instance of AsyncIOMotorCollection.
    """
    db = await get_mongo_database()
    return db[collection_name] 