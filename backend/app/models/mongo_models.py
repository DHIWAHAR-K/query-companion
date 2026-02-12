"""MongoDB document models for chat history"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field, BeforeValidator
from bson import ObjectId


def _coerce_object_id(v: Any) -> Optional[str]:
    """Coerce ObjectId or str to str for Pydantic v2."""
    if v is None:
        return None
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError("Invalid ObjectId")


# Pydantic v2: use Annotated + BeforeValidator so MongoDB docs load without validator signature errors
PyObjectId = Annotated[str, BeforeValidator(_coerce_object_id)]


class MongoBaseModel(BaseModel):
    """Base model for MongoDB documents"""
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "protected_namespaces": (),  # allow fields like model_used
    }


class MessageDocument(MongoBaseModel):
    """MongoDB document for a chat message"""
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
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
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
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
