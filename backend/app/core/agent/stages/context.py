"""Stage 2: Context Assembly"""
from typing import List
import structlog

from app.models.domain import (
    Context, Language, Schema, Message, PerformanceMode
)
from app.models.database import Connection
from app.services.schema_service import get_cached_schema, filter_schema_by_mode

logger = structlog.get_logger()


async def assemble_context(
    user_message: str,
    connection: Connection,
    conversation_history: List[Message],
    mode: PerformanceMode,
    language: Language
) -> Context:
    """
    Assemble context for SQL generation.
    
    Args:
        user_message: User's natural language query
        connection: Database connection
        conversation_history: Previous messages in conversation
        mode: Performance mode (valtryek, achillies, spryzen)
        language: Detected language
        
    Returns:
        Context object with schema and metadata
    """
    logger.debug(
        "Assembling context",
        mode=mode.value,
        connection_type=connection.type.value,
        history_length=len(conversation_history)
    )

    # Demo mode: no real connection, use built-in schema for text-to-SQL only
    if getattr(connection, "id", None) == "demo":
        logger.debug("Using demo schema (no database connection)")
        schema = Schema(
            tables=[
                {
                    "name": "customers",
                    "schema": "public",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                        {"name": "email", "type": "VARCHAR", "nullable": False},
                        {"name": "name", "type": "VARCHAR", "nullable": True},
                        {"name": "created_at", "type": "TIMESTAMP", "nullable": False}
                    ]
                },
                {
                    "name": "orders",
                    "schema": "public",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                        {"name": "customer_id", "type": "INTEGER", "nullable": False},
                        {"name": "total_amount", "type": "DECIMAL", "nullable": False},
                        {"name": "created_at", "type": "TIMESTAMP", "nullable": False}
                    ]
                },
                {
                    "name": "products",
                    "schema": "public",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                        {"name": "name", "type": "VARCHAR", "nullable": False},
                        {"name": "price", "type": "DECIMAL", "nullable": False},
                        {"name": "category", "type": "VARCHAR", "nullable": True}
                    ]
                }
            ],
            relationships=[
                {
                    "from_table": "orders",
                    "from_column": "customer_id",
                    "to_table": "customers",
                    "to_column": "id",
                    "type": "many_to_one"
                }
            ]
        )
    else:
        try:
            # Get cached schema
            full_schema = await get_cached_schema(connection.id, connection)

            # Filter schema based on mode and query relevance
            schema = filter_schema_by_mode(full_schema, mode, user_message)

            logger.debug("Real schema retrieved", table_count=len(schema.tables))

        except Exception as e:
            # Fallback to mock schema if introspection fails
            logger.warning("Schema introspection failed, using mock schema", error=str(e))
            schema = Schema(
        tables=[
            {
                "name": "customers",
                "schema": "public",
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                    {"name": "email", "type": "VARCHAR", "nullable": False},
                    {"name": "name", "type": "VARCHAR", "nullable": True},
                    {"name": "created_at", "type": "TIMESTAMP", "nullable": False}
                ]
            },
            {
                "name": "orders",
                "schema": "public",
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                    {"name": "customer_id", "type": "INTEGER", "nullable": False},
                    {"name": "total_amount", "type": "DECIMAL", "nullable": False},
                    {"name": "created_at", "type": "TIMESTAMP", "nullable": False}
                ]
            },
            {
                "name": "products",
                "schema": "public",
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                    {"name": "name", "type": "VARCHAR", "nullable": False},
                    {"name": "price", "type": "DECIMAL", "nullable": False},
                    {"name": "category", "type": "VARCHAR", "nullable": True}
                ]
            }
        ],
        relationships=[
            {
                "from_table": "orders",
                "from_column": "customer_id",
                "to_table": "customers",
                "to_column": "id",
                "type": "many_to_one"
            }
        ]
    )
    
    
    table_names = [t["name"] for t in schema.tables]
    
    context = Context(
        user_id=connection.user_id,
        language=language,
        db_schema=schema,
        tables=table_names,
        conversation_history=conversation_history[-5:]  # Last 5 messages for context
    )
    
    logger.debug("Context assembled", table_count=len(table_names))
    return context
