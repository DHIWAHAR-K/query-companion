"""MongoDB document models for chat history"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class MongoBaseModel(BaseModel):
    """Base model for MongoDB documents"""
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class MessageDocument(MongoBaseModel):
    """MongoDB document for a chat message"""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    message_id: str = Field(..., description="UUID for the message")
    conversation_id: str = Field(..., description="UUID of conversation")
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata (only for assistant messages)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="SQL, execution time, etc.")
    attachments: Optional[List[str]] = Field(default=None, description="File attachments")
    
    # Performance tracking
    mode: Optional[str] = Field(default=None, description="valtryek, achillies, spryzen")
    model_used: Optional[str] = Field(default=None, description="LLM model name")
    generation_time_ms: Optional[int] = Field(default=None, description="Time to generate")
    
    # Tool events
    tool_events: Optional[List[Dict[str, Any]]] = Field(default=None, description="Web search, vision, etc.")


class ConversationDocument(MongoBaseModel):
    """MongoDB document for a conversation"""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    conversation_id: str = Field(..., description="UUID for conversation")
    user_id: str = Field(..., description="UUID of user")
    connection_id: str = Field(..., description="UUID of database connection")
    
    title: str = Field(default="New Conversation", description="Conversation title")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Summary stats
    message_count: int = Field(default=0, description="Total messages")
    last_message_preview: Optional[str] = Field(default=None, description="Preview of last message")
    
    # Tags and metadata
    tags: List[str] = Field(default_factory=list, description="User tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


# Export models
__all__ = [
    "MessageDocument",
    "ConversationDocument",
    "PyObjectId",
    "MongoBaseModel"
]
