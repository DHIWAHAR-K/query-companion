"""Conversation service for managing chats and messages"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
from datetime import datetime

from app.models.database import Conversation, Message as DBMessage
from app.models.domain import Message

async def get_conversation_history(
    conversation_id: str,
    user_id: str,
    db: AsyncSession
) -> List[Message]:
    """
    Get conversation history.
    
    Args:
        conversation_id: Conversation ID
        user_id: User ID for authorization
        db: Database session
        
    Returns:
        List of messages in the conversation
    """
    # Get conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        return []
    
    # Get messages
    result = await db.execute(
        select(DBMessage)
        .where(DBMessage.conversation_id == conversation_id)
        .order_by(DBMessage.timestamp)
    )
    db_messages = result.scalars().all()
    
    # Convert to domain models
    messages = []
    for db_msg in db_messages:
        messages.append(Message(
            id=db_msg.id,
            role=db_msg.role,
            content=db_msg.content,
            timestamp=db_msg.timestamp,
            tool_events=db_msg.tool_events,
            sql=db_msg.sql,
            results=db_msg.results,
            attachments=db_msg.attachments
        ))
    
    return messages


async def save_message(
    conversation_id: str,
    message: Message,
    user_id: str,
    db: AsyncSession
) -> DBMessage:
    """
    Save a message to the database.
    
    Args:
        conversation_id: Conversation ID
        message: Message to save
        user_id: User ID for authorization
        db: Database session
        
    Returns:
        Saved database message
    """
    # Ensure conversation exists or create it
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        # Create new conversation
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            title="New conversation",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conversation)
    else:
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
    
    # Create message
    db_message = DBMessage(
        id=message.id,
        conversation_id=conversation_id,
        role=message.role,
        content=message.content,
        timestamp=message.timestamp,
        tool_events=message.tool_events if hasattr(message, 'tool_events') else None,
        sql=message.sql if hasattr(message, 'sql') else None,
        results=message.results if hasattr(message, 'results') else None,
        attachments=message.attachments if hasattr(message, 'attachments') else None
    )
    
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    
    return db_message


async def create_conversation(
    user_id: str,
    title: str,
    db: AsyncSession
) -> Conversation:
    """Create a new conversation"""
    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


async def get_user_conversations(
    user_id: str,
    db: AsyncSession,
    limit: int = 50
) -> List[Conversation]:
    """Get all conversations for a user"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    
    return result.scalars().all()
