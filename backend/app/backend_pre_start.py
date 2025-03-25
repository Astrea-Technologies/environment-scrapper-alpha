import logging
import motor.motor_asyncio
import asyncio
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from sqlalchemy import Engine
from sqlmodel import Session, select
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core.db import engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init(db_engine: Engine) -> None:
    try:
        with Session(db_engine) as session:
            # Try to create session to check if DB is awake
            session.exec(select(1))
    except Exception as e:
        logger.error(e)
        raise e


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
async def init_mongodb() -> None:
    """Check if MongoDB is awake and ready to accept connections."""
    try:
        # Construct the MongoDB URI
        auth_part = ""
        if settings.MONGODB_USER and settings.MONGODB_PASSWORD:
            auth_part = f"{settings.MONGODB_USER}:{settings.MONGODB_PASSWORD}@"
        
        auth_source = f"?authSource={settings.MONGODB_AUTH_SOURCE}" if auth_part else ""
        mongo_uri = f"mongodb://{auth_part}{settings.MONGODB_SERVER}:{settings.MONGODB_PORT}/{settings.MONGODB_DB}{auth_source}"
        
        # Try to connect to MongoDB
        client = motor.motor_asyncio.AsyncIOMotorClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000
        )
        
        # Check the connection
        await client.admin.command('ping')
        logger.info("MongoDB connection successful")
        
        # Close the connection
        client.close()
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection error: {e}")
        raise e


def main() -> None:
    logger.info("Initializing service")
    init(engine)
    logger.info("PostgreSQL database initialization complete")
    
    # Check MongoDB connection
    logger.info("Checking MongoDB connection...")
    asyncio.run(init_mongodb())
    logger.info("MongoDB initialization complete")
    
    logger.info("Service finished initializing")


if __name__ == "__main__":
    main()
