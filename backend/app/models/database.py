"""SQLAlchemy ORM models"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, JSON, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import enum

from app.db.base import Base


class UserRole(str, enum.Enum):
    """User roles enum"""
    USER = "user"
    ADMIN = "admin"


class SQLDialect(str, enum.Enum):
    """SQL dialect enum"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    REDSHIFT = "redshift"
    MSSQL = "mssql"
    SQLITE = "sqlite"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512))
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False),
        default=UserRole.USER,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    connections: Mapped[list["Connection"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Connection(Base):
    """Database connection model"""
    __tablename__ = "connections"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[SQLDialect] = mapped_column(
        SQLEnum(SQLDialect, native_enum=False),
        nullable=False
    )
    credentials: Mapped[dict] = mapped_column(JSON, nullable=False)  # Encrypted
    is_read_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="connections")
    policies: Mapped[list["Policy"]] = relationship(back_populates="connection", cascade="all, delete-orphan")


class Conversation(Base):
    """Conversation model"""
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Message model"""
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tool_events: Mapped[Optional[dict]] = mapped_column(JSON)
    sql: Mapped[Optional[dict]] = mapped_column(JSON)
    results: Mapped[Optional[dict]] = mapped_column(JSON)
    attachments: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Policy(Base):
    """Policy model for governance"""
    __tablename__ = "policies"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(String(36), ForeignKey("connections.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # table_allowlist, column_mask, row_filter, query_budget
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    connection: Mapped["Connection"] = relationship(back_populates="policies")


class AuditLog(Base):
    """Audit log model"""
    __tablename__ = "audit_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    connection_id: Mapped[Optional[str]] = mapped_column(String(36))
    conversation_id: Mapped[Optional[str]] = mapped_column(String(36))
    user_message: Mapped[str] = mapped_column(Text)
    generated_sql: Mapped[Optional[str]] = mapped_column(Text)
    execution_status: Mapped[Optional[str]] = mapped_column(String(50))
    policy_violations: Mapped[Optional[dict]] = mapped_column(JSON)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
