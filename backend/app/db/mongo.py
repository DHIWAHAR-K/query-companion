"""MongoDB connection and client for chat history"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import structlog

from app.config import settings

logger = structlog.get_logger()


class MongoDB:
    """MongoDB connection manager"""
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls):
        """Connect to MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # Test connection
            await cls.client.admin.command('ping')
            
            # Create indexes
            await cls.create_indexes()
            
            logger.info(
                "MongoDB connected",
                url=settings.MONGODB_URL,
                database=settings.MONGODB_DB_NAME
            )
        except Exception as e:
            logger.error("MongoDB connection failed", error=str(e))
            raise
    
    @classmethod
    async def close(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    async def create_indexes(cls):
        """Create MongoDB indexes for optimal performance"""
        if cls.db is None:
            return
        
        # Conversations indexes
        await cls.db.conversations.create_index("user_id")
        await cls.db.conversations.create_index("connection_id")
        await cls.db.conversations.create_index([("user_id", 1), ("updated_at", -1)])
        await cls.db.conversations.create_index("conversation_id", unique=True)
        
        # Messages indexes
        await cls.db.messages.create_index("conversation_id")
        await cls.db.messages.create_index([("conversation_id", 1), ("timestamp", 1)])
        await cls.db.messages.create_index("timestamp")
        
        logger.info("MongoDB indexes created")
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if cls.db is None:
            raise RuntimeError("MongoDB not connected. Call MongoDB.connect() first.")
        return cls.db
    
    @classmethod
    def get_collection(cls, name: str):
        """Get collection by name"""
        return cls.get_db()[name]


# Convenience accessors
async def get_mongo_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency for MongoDB database"""
    return MongoDB.get_db()


# Initialize on import for convenience
mongo_db = MongoDB
