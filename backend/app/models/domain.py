"""Pydantic domain models for business logic"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PerformanceMode(str, Enum):
    """Performance mode enum"""
    VALTRYEK = "valtryek"
    ACHILLIES = "achillies"
    SPRYZEN = "spryzen"


class SQLDialect(str, Enum):
    """SQL dialect enum"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    REDSHIFT = "redshift"
    MSSQL = "mssql"
    SQLITE = "sqlite"


class Language(BaseModel):
    """Language detection result"""
    code: str
    name: str
    confidence: float = 1.0


class ToolEvent(BaseModel):
    """Tool execution event"""
    id: str
    tool: str
    label: str
    icon: str
    input: Dict[str, Any] = {}
    output: Dict[str, Any] = {}
    duration_ms: int
    timestamp: datetime


class SQLArtifact(BaseModel):
    """SQL generation result"""
    query: str
    dialect: SQLDialect
    explanation: str
    assumptions: List[str] = []
    confidence: float = 1.0
    validation_status: str = "valid"  # valid, warning, error
    validation_messages: List[str] = []


class Column(BaseModel):
    """Column metadata"""
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    pii: bool = False


class QueryResult(BaseModel):
    """Query execution result"""
    columns: List[Column]
    rows: List[List[Any]]
    total_rows: int
    execution_time_ms: int
    warnings: List[str] = []
    error: Optional[str] = None


class Attachment(BaseModel):
    """Message attachment"""
    type: str  # image, file
    data: str  # base64 encoded
    filename: str


class SchemaTableUsed(BaseModel):
    """Schema table used for an answer - payload for frontend"""
    table_name: str
    schema_name: Optional[str] = None
    columns: List[Dict[str, str]]  # [ {"name": "...", "type": "..."} ]


class Message(BaseModel):
    """Message model"""
    id: str
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    attachments: Optional[List[Attachment]] = None
    tool_events: Optional[List[ToolEvent]] = None
    sql: Optional[SQLArtifact] = None
    results: Optional[QueryResult] = None
    schema_used: Optional[List[SchemaTableUsed]] = None
    explanation_after_schema: Optional[str] = None
    explanation_before_result: Optional[str] = None


class AssistantMessage(Message):
    """Assistant message with additional fields"""
    role: str = "assistant"


class Connection(BaseModel):
    """Database connection"""
    id: str
    user_id: str
    name: str
    type: SQLDialect
    credentials: Dict[str, Any]
    is_read_only: bool = True
    created_at: datetime
    last_used: Optional[datetime] = None


class Policy(BaseModel):
    """Policy configuration"""
    id: str
    connection_id: str
    type: str  # table_allowlist, column_mask, row_filter, query_budget
    config: Dict[str, Any]
    is_active: bool = True


class ValidationResult(BaseModel):
    """SQL validation result"""
    status: str  # valid, warning, error
    messages: List[str] = []
    safe_to_execute: bool = True


class PolicyResult(BaseModel):
    """Policy enforcement result"""
    allowed: bool
    modified_sql: Optional[str] = None
    denial_reason: Optional[str] = None
    applied_policies: List[str] = []


class Schema(BaseModel):
    """Database schema metadata"""
    tables: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]] = []


class Context(BaseModel):
    """Request context for agent runtime"""
    user_id: str
    language: Language
    db_schema: Schema
    tables: List[str]
    conversation_history: List[Message] = []
