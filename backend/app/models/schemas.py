"""API request/response schemas"""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any
from datetime import datetime

from app.models.domain import (
    PerformanceMode, Message, AssistantMessage, 
    SQLDialect, ToolEvent, SQLArtifact, QueryResult
)


# Auth Schemas
class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Chat Schemas
class ChatMessageRequest(BaseModel):
    """Chat message request"""
    conversation_id: str
    message: Message
    connection_id: Optional[str] = None  # Optional: when missing, use demo schema (no real DB)
    mode: Optional[PerformanceMode] = PerformanceMode.ACHILLIES
    execute_sql: bool = False
    stream: bool = False


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    conversation_id: str
    message: AssistantMessage


class ConversationResponse(BaseModel):
    """Conversation response"""
    id: str
    title: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime


# Connection Schemas
class CreateConnectionRequest(BaseModel):
    """Create connection request"""
    name: str
    type: SQLDialect
    credentials: dict
    is_read_only: bool = True


class ConnectionResponse(BaseModel):
    """Connection response"""
    id: str
    name: str
    type: str
    is_read_only: bool
    created_at: datetime
    last_used: Optional[datetime]
    
    class Config:
        from_attributes = True


class ConnectionTestRequest(BaseModel):
    """Test connection request"""
    type: SQLDialect
    credentials: dict


class ConnectionTestResponse(BaseModel):
    """Test connection response"""
    success: bool
    message: str
    details: Optional[dict] = None


# Schema Schemas
class SchemaTreeResponse(BaseModel):
    """Schema tree response"""
    schemas: List[dict]
    relationships: List[dict] = []


class SampleDataRequest(BaseModel):
    """Sample data request"""
    table: str
    limit: int = 10


class SampleDataResponse(BaseModel):
    """Sample data response"""
    columns: List[dict]
    rows: List[List[Any]]
    total_rows: int
