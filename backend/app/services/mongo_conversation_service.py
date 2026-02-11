"""Conversation service using MongoDB for chat history"""
from typing import List, Optional
from datetime import datetime
import uuid
import structlog

from app.db.mongo import mongo_db
from app.models.mongo_models import ConversationDocument, MessageDocument

logger = structlog.get_logger()


class MongoConversationService:
    """Service for managing conversations and messages in MongoDB"""
    
    @staticmethod
    async def create_conversation(
        user_id: str,
        connection_id: str,
        title: str = "New Conversation"
    ) -> ConversationDocument:
        """Create a new conversation"""
        conversation = ConversationDocument(
            conversation_id=str(uuid.uuid4()),
            user_id=user_id,
            connection_id=connection_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            message_count=0
        )
        
        db = mongo_db.get_db()
        result = await db.conversations.insert_one(
            conversation.model_dump(by_alias=True, exclude={"id"})
        )
        
        conversation.id = result.inserted_id
        
        logger.info(
            "Conversation created",
            conversation_id=conversation.conversation_id,
            user_id=user_id
        )
        
        return conversation
    
    @staticmethod
    async def get_conversation(conversation_id: str, user_id: str) -> Optional[ConversationDocument]:
        """Get conversation by ID"""
        db = mongo_db.get_db()
        doc = await db.conversations.find_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        
        if doc:
            return ConversationDocument(**doc)
        return None
    
    @staticmethod
    async def list_conversations(
        user_id: str,
        connection_id: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[ConversationDocument]:
        """List conversations for a user"""
        db = mongo_db.get_db()
        
        query = {"user_id": user_id}
        if connection_id:
            query["connection_id"] = connection_id
        
        cursor = db.conversations.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        conversations = []
        
        async for doc in cursor:
            conversations.append(ConversationDocument(**doc))
        
        return conversations
    
    @staticmethod
    async def add_message(
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
        attachments: Optional[List[str]] = None,
        mode: Optional[str] = None,
        model_used: Optional[str] = None,
        generation_time_ms: Optional[int] = None,
        tool_events: Optional[List[dict]] = None
    ) -> MessageDocument:
        """Add a message to a conversation"""
        message = MessageDocument(
            message_id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata,
            attachments=attachments,
            mode=mode,
            model_used=model_used,
            generation_time_ms=generation_time_ms,
            tool_events=tool_events
        )
        
        db = mongo_db.get_db()
        
        # Insert message
        result = await db.messages.insert_one(
            message.model_dump(by_alias=True, exclude={"id"})
        )
        message.id = result.inserted_id
        
        # Update conversation
        preview = content[:100] if len(content) > 100 else content
        await db.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "updated_at": datetime.utcnow(),
                    "last_message_preview": preview
                },
                "$inc": {"message_count": 1}
            }
        )
        
        logger.info(
            "Message added",
            conversation_id=conversation_id,
            role=role,
            message_id=message.message_id
        )
        
        return message
    
    @staticmethod
    async def get_messages(
        conversation_id: str,
        limit: int = 100,
        skip: int = 0
    ) -> List[MessageDocument]:
        """Get messages for a conversation"""
        db = mongo_db.get_db()
        
        cursor = db.messages.find(
            {"conversation_id": conversation_id}
        ).sort("timestamp", 1).skip(skip).limit(limit)
        
        messages = []
        async for doc in cursor:
            messages.append(MessageDocument(**doc))
        
        return messages
    
    @staticmethod
    async def delete_conversation(conversation_id: str, user_id: str) -> bool:
        """Delete a conversation and all its messages"""
        db = mongo_db.get_db()
        
        # Delete messages first
        await db.messages.delete_many({"conversation_id": conversation_id})
        
        # Delete conversation
        result = await db.conversations.delete_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        
        if result.deleted_count > 0:
            logger.info("Conversation deleted", conversation_id=conversation_id)
            return True
        
        return False
    
    @staticmethod
    async def update_conversation_title(
        conversation_id: str,
        user_id: str,
        title: str
    ) -> bool:
        """Update conversation title"""
        db = mongo_db.get_db()
        
        result = await db.conversations.update_one(
            {"conversation_id": conversation_id, "user_id": user_id},
            {"$set": {"title": title, "updated_at": datetime.utcnow()}}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    async def get_conversation_stats(user_id: str) -> dict:
        """Get conversation statistics for a user"""
        db = mongo_db.get_db()
        
        total_conversations = await db.conversations.count_documents({"user_id": user_id})
        total_messages = await db.messages.count_documents({
            "conversation_id": {"$in": [
                doc["conversation_id"] async for doc in 
                db.conversations.find({"user_id": user_id}, {"conversation_id": 1})
            ]}
        })
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "avg_messages_per_conversation": total_messages / total_conversations if total_conversations > 0 else 0
        }
