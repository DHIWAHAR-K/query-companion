"""Stage 8: Query Execution"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import asyncio
import structlog
from typing import List, Any
from datetime import datetime
import time

from app.models.domain import QueryResult, Column, SQLDialect
from app.models.database import Connection
from app.core.security.encryption import decrypt_credentials
from app.config import settings

logger = structlog.get_logger()

# Connection pool cache
_connection_pools = {}


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


def _get_or_create_engine(connection: Connection) -> Engine:
    """Get or create a connection pool for a connection"""
    connection_id = connection.id
    
    if connection_id not in _connection_pools:
        url = _build_connection_url(connection)
        
        # Create engine with connection pooling
        engine = create_engine(
            url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        _connection_pools[connection_id] = engine
        logger.debug("Created connection pool", connection_id=connection_id)
    
    return _connection_pools[connection_id]


async def execute_query(
    sql: str,
    connection: Connection,
    timeout_seconds: int = 300,
    max_rows: int = 10000
) -> QueryResult:
    """
    Execute SQL query with timeout and result limiting.
    
    Args:
        sql: SQL query to execute
        connection: Database connection
        timeout_seconds: Maximum execution time in seconds
        max_rows: Maximum number of rows to return
        
    Returns:
        QueryResult with columns, rows, and execution metadata
    """
    logger.info(
        "Executing query",
        connection_id=connection.id,
        connection_type=connection.type.value,
        timeout=timeout_seconds
    )
    
    start_time = time.time()
    
    try:
        # Get or create engine
        engine = _get_or_create_engine(connection)
        
        # Execute query in thread pool with timeout
        def _execute():
            with engine.connect() as conn:
                # Execute query
                result = conn.execute(text(sql))
                
                # Get column metadata
                columns = []
                if result.returns_rows:
                    for col in result.keys():
                        # Get column type
                        col_type = str(result.cursor.description[result.keys().index(col)][1]) if hasattr(result.cursor, 'description') else "UNKNOWN"
                        
                        columns.append(Column(
                            name=col,
                            type=col_type,
                            nullable=True
                        ))
                    
                    # Fetch rows (limited)
                    rows = []
                    for i, row in enumerate(result):
                        if i >= max_rows:
                            logger.warning("Row limit reached", max_rows=max_rows)
                            break
                        rows.append(list(row))
                    
                    total_rows = len(rows)
                else:
                    # DML query (INSERT, UPDATE, DELETE)
                    rows = []
                    total_rows = result.rowcount
                    columns = []
                
                return columns, rows, total_rows
        
        # Run in thread pool with timeout
        try:
            columns, rows, total_rows = await asyncio.wait_for(
                asyncio.to_thread(_execute),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error("Query execution timeout", timeout=timeout_seconds)
            raise TimeoutError(f"Query execution exceeded {timeout_seconds} seconds")
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Build warnings
        warnings = []
        if total_rows >= max_rows:
            warnings.append(f"Results limited to {max_rows} rows")
        
        result = QueryResult(
            columns=columns,
            rows=rows,
            total_rows=total_rows,
            execution_time_ms=execution_time_ms,
            warnings=warnings
        )
        
        logger.info(
            "Query executed successfully",
            rows=total_rows,
            execution_time_ms=execution_time_ms
        )
        
        return result
        
    except TimeoutError as e:
        raise
    except Exception as e:
        logger.error("Query execution failed", error=str(e))
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Return error result
        return QueryResult(
            columns=[],
            rows=[],
            total_rows=0,
            execution_time_ms=execution_time_ms,
            warnings=[],
            error=str(e)
        )


def dispose_connection_pool(connection_id: str):
    """Dispose of a connection pool"""
    if connection_id in _connection_pools:
        _connection_pools[connection_id].dispose()
        del _connection_pools[connection_id]
        logger.debug("Disposed connection pool", connection_id=connection_id)
