"""Stage 6: SQL Validation"""
import sqlglot
import structlog

from app.models.domain import ValidationResult, SQLDialect, Schema

logger = structlog.get_logger()


def validate_sql(
    sql: str,
    schema: Schema,
    dialect: SQLDialect
) -> ValidationResult:
    """
    Validate SQL query for syntax and basic safety checks.
    
    For MVP, this performs basic parsing validation.
    Will be enhanced with table/column existence checks and unsafe operation
    detection in Phase 5.
    
    Args:
        sql: SQL query to validate
        schema: Database schema
        dialect: SQL dialect
        
    Returns:
        ValidationResult with status and messages
    """
    logger.debug("Validating SQL", dialect=dialect.value)
    
    messages = []
    status = "valid"
    safe_to_execute = True
    
    # sqlglot uses "postgres" not "postgresql"
    read_dialect = "postgres" if dialect.value == "postgresql" else dialect.value
    
    try:
        # Parse SQL with sqlglot
        parsed = sqlglot.parse_one(sql, read=read_dialect)
        
        # Basic validation - check if parsing succeeded
        if parsed is None:
            status = "error"
            safe_to_execute = False
            messages.append("Failed to parse SQL query")
            logger.warning("SQL parsing failed")
        else:
            logger.debug("SQL parsing successful")
            
            # Check for potentially dangerous operations
            sql_upper = sql.upper()
            
            # Check for DML/DDL operations
            dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE"]
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    status = "warning"
                    messages.append(f"Query contains {keyword} operation - requires admin privileges")
                    logger.warning("Dangerous operation detected", operation=keyword)
            
            # Check for SELECT *
            if "SELECT *" in sql_upper or "SELECT*" in sql_upper:
                messages.append("Using SELECT * - consider specifying columns explicitly")
            
            # Check for CROSS JOIN
            if "CROSS JOIN" in sql_upper:
                if "LIMIT" not in sql_upper:
                    status = "warning"
                    messages.append("CROSS JOIN without LIMIT may return very large result sets")
    
    except Exception as e:
        status = "error"
        safe_to_execute = False
        messages.append(f"Validation error: {str(e)}")
        logger.error("SQL validation error", error=str(e))
    
    result = ValidationResult(
        status=status,
        messages=messages,
        safe_to_execute=safe_to_execute
    )
    
    logger.info("Validation complete", status=status, message_count=len(messages))
    return result
