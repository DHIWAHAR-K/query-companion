"""Stage 7: Policy Enforcement"""
import sqlglot
import structlog
from typing import List, Dict, Any

from app.models.domain import PolicyResult, PerformanceMode
from app.models.database import Connection, Policy, User

logger = structlog.get_logger()


async def enforce_policies(
    sql: str,
    connection: Connection,
    user: User,
    mode: PerformanceMode,
    policies: List[Policy] = None
) -> PolicyResult:
    """
    Apply policies to SQL query before execution.
    
    Policies:
    1. Table Allowlist - restrict which tables user can access
    2. Column Masking - mask PII columns
    3. Row-Level Security - inject WHERE clauses
    4. Query Budgets - enforce limits
    
    Args:
        sql: SQL query to enforce policies on
        connection: Database connection
        user: User making the request
        mode: Performance mode
        policies: List of policies to apply (if None, fetch from connection)
        
    Returns:
        PolicyResult with modified SQL or denial reason
    """
    logger.info("Enforcing policies", connection_id=connection.id, user_id=user.id)
    
    applied_policies = []
    modified_sql = sql
    
    # Skip policy enforcement for admin users
    if user.role.value == "admin":
        logger.debug("Skipping policies for admin user")
        return PolicyResult(
            allowed=True,
            modified_sql=None,
            applied_policies=["admin_bypass"]
        )
    
    # If no policies provided, create default read-only policy
    if not policies:
        policies = []
    
    try:
        # Parse SQL
        parsed = sqlglot.parse_one(sql)
        
        # Policy 1: Block DML/DDL for read-only connections
        if connection.is_read_only:
            sql_upper = sql.upper()
            dangerous_ops = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"]
            
            for op in dangerous_ops:
                if op in sql_upper:
                    logger.warning("Policy blocked dangerous operation", operation=op)
                    return PolicyResult(
                        allowed=False,
                        denial_reason=f"Operation {op} not allowed on read-only connection",
                        applied_policies=["read_only_enforcement"]
                    )
        
        # Policy 2: Table allowlist (if policies exist)
        # TODO: Implement table allowlist from database policies
        
        # Policy 3: Column masking (if policies exist)
        # TODO: Implement column masking from database policies
        
        # Policy 4: Row-level security (if policies exist)
        # TODO: Implement RLS from database policies
        
        # Policy 5: Query budget enforcement
        # Mode-specific limits are already enforced in executor timeout
        applied_policies.append("timeout_enforcement")
        
        logger.info("Policies enforced", applied_count=len(applied_policies))
        
        return PolicyResult(
            allowed=True,
            modified_sql=modified_sql if modified_sql != sql else None,
            applied_policies=applied_policies
        )
        
    except Exception as e:
        logger.error("Policy enforcement failed", error=str(e))
        return PolicyResult(
            allowed=False,
            denial_reason=f"Policy enforcement error: {str(e)}",
            applied_policies=[]
        )


def apply_table_allowlist(
    sql: str,
    allowed_tables: List[str],
    dialect: str
) -> tuple[bool, str]:
    """
    Check if query only accesses allowed tables.
    
    Args:
        sql: SQL query
        allowed_tables: List of allowed table names
        dialect: SQL dialect
        
    Returns:
        Tuple of (is_allowed, reason)
    """
    try:
        parsed = sqlglot.parse_one(sql, read=dialect)
        
        # Extract all table names from query
        tables = set()
        for table in parsed.find_all(sqlglot.exp.Table):
            tables.add(table.name.lower())
        
        # Check if all tables are in allowlist
        disallowed = tables - set(t.lower() for t in allowed_tables)
        
        if disallowed:
            return False, f"Access denied to tables: {', '.join(disallowed)}"
        
        return True, ""
        
    except Exception as e:
        logger.error("Table allowlist check failed", error=str(e))
        return False, f"Policy check error: {str(e)}"


def apply_column_masking(
    sql: str,
    masking_rules: Dict[str, List[str]],
    dialect: str
) -> str:
    """
    Apply column masking to SQL query.
    
    Args:
        sql: SQL query
        masking_rules: Dict of {table: [column_names]} to mask
        dialect: SQL dialect
        
    Returns:
        Modified SQL with masked columns
    """
    try:
        parsed = sqlglot.parse_one(sql, read=dialect)
        
        # TODO: Implement AST rewriting to mask columns
        # For now, return original SQL
        
        return sql
        
    except Exception as e:
        logger.error("Column masking failed", error=str(e))
        return sql


def inject_row_filter(
    sql: str,
    filter_clause: str,
    dialect: str
) -> str:
    """
    Inject row-level security filter into SQL.
    
    Args:
        sql: SQL query
        filter_clause: WHERE clause to inject (e.g., "tenant_id = 'abc'")
        dialect: SQL dialect
        
    Returns:
        Modified SQL with injected filter
    """
    try:
        parsed = sqlglot.parse_one(sql, read=dialect)
        
        # TODO: Implement WHERE clause injection using sqlglot
        # For now, return original SQL
        
        return sql
        
    except Exception as e:
        logger.error("Row filter injection failed", error=str(e))
        return sql
