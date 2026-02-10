"""Schema introspection service"""
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.engine import Engine
import structlog
from typing import Dict, Any, List, Optional
import json

from app.models.database import Connection
from app.models.domain import Schema, SQLDialect, PerformanceMode
from app.core.security.encryption import decrypt_credentials
from app.db.cache import redis_client
from app.config import settings

logger = structlog.get_logger()


def _build_connection_url(connection: Connection) -> str:
    """Build SQLAlchemy connection URL from connection credentials"""
    try:
        # Decrypt credentials
        creds = decrypt_credentials(connection.credentials["encrypted"])
        
        # Build URL based on dialect
        if connection.type == SQLDialect.POSTGRESQL:
            return f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds.get('port', 5432)}/{creds['database']}"
        
        elif connection.type == SQLDialect.MYSQL:
            return f"mysql+pymysql://{creds['username']}:{creds['password']}@{creds['host']}:{creds.get('port', 3306)}/{creds['database']}"
        
        elif connection.type == SQLDialect.SNOWFLAKE:
            account = creds['account']
            user = creds['username']
            password = creds['password']
            warehouse = creds.get('warehouse', '')
            database = creds['database']
            schema = creds.get('schema', 'PUBLIC')
            return f"snowflake://{user}:{password}@{account}/{database}/{schema}?warehouse={warehouse}"
        
        elif connection.type == SQLDialect.SQLITE:
            return f"sqlite:///{creds['database']}"
        
        else:
            raise ValueError(f"Unsupported dialect: {connection.type}")
            
    except Exception as e:
        logger.error("Failed to build connection URL", error=str(e))
        raise


async def introspect_schema(connection: Connection) -> Schema:
    """
    Introspect database schema using SQLAlchemy reflection.
    
    Args:
        connection: Database connection
        
    Returns:
        Schema object with tables and relationships
    """
    logger.info("Introspecting schema", connection_id=connection.id, type=connection.type.value)
    
    try:
        # Build connection URL
        url = _build_connection_url(connection)
        
        # Create engine (synchronous for reflection)
        engine = create_engine(url, echo=False)
        
        # Use inspector to get metadata
        inspector = inspect(engine)
        
        tables = []
        relationships = []
        
        # Get all schemas/databases
        schemas = inspector.get_schema_names()
        
        # Default schema based on dialect
        default_schema = None
        if connection.type == SQLDialect.POSTGRESQL:
            default_schema = "public"
        elif connection.type == SQLDialect.MYSQL:
            default_schema = connection.credentials.get("database")
        
        # Iterate through schemas
        for schema_name in schemas:
            # Skip system schemas
            if schema_name in ['information_schema', 'pg_catalog', 'pg_toast', 'mysql', 'performance_schema', 'sys']:
                continue
            
            try:
                table_names = inspector.get_table_names(schema=schema_name)
                
                for table_name in table_names:
                    # Get columns
                    columns = []
                    for col in inspector.get_columns(table_name, schema=schema_name):
                        columns.append({
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                            "primary_key": col.get("primary_key", False),
                            "pii": False  # TODO: Implement PII detection
                        })
                    
                    # Get row count (approximation)
                    try:
                        with engine.connect() as conn:
                            if schema_name:
                                result = conn.execute(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"')
                            else:
                                result = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                            row_count = result.scalar()
                    except:
                        row_count = None
                    
                    tables.append({
                        "name": table_name,
                        "schema": schema_name,
                        "row_count": row_count,
                        "columns": columns
                    })
                    
                    # Get foreign keys for relationships
                    fks = inspector.get_foreign_keys(table_name, schema=schema_name)
                    for fk in fks:
                        relationships.append({
                            "from_table": table_name,
                            "from_column": fk["constrained_columns"][0] if fk["constrained_columns"] else None,
                            "to_table": fk["referred_table"],
                            "to_column": fk["referred_columns"][0] if fk["referred_columns"] else None,
                            "type": "many_to_one"
                        })
                        
            except Exception as e:
                logger.warning("Failed to introspect schema", schema=schema_name, error=str(e))
                continue
        
        # Close engine
        engine.dispose()
        
        schema = Schema(tables=tables, relationships=relationships)
        
        logger.info("Schema introspection complete", table_count=len(tables))
        return schema
        
    except Exception as e:
        logger.error("Schema introspection failed", error=str(e))
        raise


async def get_cached_schema(connection_id: str, connection: Connection) -> Schema:
    """
    Get schema from cache or introspect and cache it.
    
    Args:
        connection_id: Connection ID
        connection: Connection object
        
    Returns:
        Schema object
    """
    cache_key = f"schema:{connection_id}"
    
    try:
        # Try to get from cache
        cached = await redis_client.get(cache_key)
        if cached:
            logger.debug("Schema cache hit", connection_id=connection_id)
            data = json.loads(cached)
            return Schema(**data)
        
        logger.debug("Schema cache miss", connection_id=connection_id)
        
    except Exception as e:
        logger.warning("Cache read failed", error=str(e))
    
    # Introspect schema
    schema = await introspect_schema(connection)
    
    # Cache it
    try:
        await redis_client.setex(
            cache_key,
            settings.SCHEMA_CACHE_TTL,
            schema.model_dump_json()
        )
        logger.debug("Schema cached", connection_id=connection_id)
    except Exception as e:
        logger.warning("Cache write failed", error=str(e))
    
    return schema


async def invalidate_schema_cache(connection_id: str):
    """Invalidate cached schema for a connection"""
    cache_key = f"schema:{connection_id}"
    try:
        await redis_client.delete(cache_key)
        logger.debug("Schema cache invalidated", connection_id=connection_id)
    except Exception as e:
        logger.warning("Cache invalidation failed", error=str(e))


def filter_schema_by_mode(schema: Schema, mode: PerformanceMode, query: str = "") -> Schema:
    """
    Filter schema tables based on performance mode and query relevance.
    
    Args:
        schema: Full schema
        mode: Performance mode
        query: User query for relevance matching
        
    Returns:
        Filtered schema
    """
    max_tables = {
        PerformanceMode.VALTRYEK: 5,
        PerformanceMode.ACHILLIES: 15,
        PerformanceMode.SPRYZEN: 30
    }[mode]
    
    # Simple relevance scoring - check if table name appears in query
    query_lower = query.lower()
    tables_with_scores = []
    
    for table in schema.tables:
        score = 0
        table_name_lower = table["name"].lower()
        
        # Check if table name is in query
        if table_name_lower in query_lower:
            score += 10
        
        # Check if any column name is in query
        for col in table.get("columns", []):
            if col["name"].lower() in query_lower:
                score += 5
        
        tables_with_scores.append((score, table))
    
    # Sort by score (descending) and take top N
    tables_with_scores.sort(key=lambda x: x[0], reverse=True)
    filtered_tables = [t for _, t in tables_with_scores[:max_tables]]
    
    # Filter relationships to only include those between filtered tables
    filtered_table_names = {t["name"] for t in filtered_tables}
    filtered_relationships = [
        rel for rel in schema.relationships
        if rel["from_table"] in filtered_table_names and rel["to_table"] in filtered_table_names
    ]
    
    return Schema(tables=filtered_tables, relationships=filtered_relationships)
