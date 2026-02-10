"""Audit logging service"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime
import structlog

from app.models.database import AuditLog

logger = structlog.get_logger()


async def log_query_execution(
    db: AsyncSession,
    user_id: str,
    connection_id: str,
    conversation_id: str,
    user_message: str,
    generated_sql: str,
    execution_status: str,
    policy_violations: list = None,
    duration_ms: int = 0
) -> AuditLog:
    """
    Log a query execution for audit purposes.
    
    Args:
        db: Database session
        user_id: User ID
        connection_id: Connection ID
        conversation_id: Conversation ID
        user_message: User's natural language query
        generated_sql: Generated SQL query
        execution_status: Status (success, failed, blocked)
        policy_violations: List of policy violations if any
        duration_ms: Execution duration in milliseconds
        
    Returns:
        Created audit log entry
    """
    audit_log = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        connection_id=connection_id,
        conversation_id=conversation_id,
        user_message=user_message,
        generated_sql=generated_sql,
        execution_status=execution_status,
        policy_violations=policy_violations or [],
        duration_ms=duration_ms,
        timestamp=datetime.utcnow()
    )
    
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)
    
    logger.info(
        "Query execution audited",
        audit_id=audit_log.id,
        user_id=user_id,
        status=execution_status
    )
    
    return audit_log


async def get_user_audit_logs(
    db: AsyncSession,
    user_id: str,
    limit: int = 100,
    offset: int = 0
) -> list[AuditLog]:
    """Get audit logs for a specific user"""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    
    return result.scalars().all()


async def get_connection_audit_logs(
    db: AsyncSession,
    connection_id: str,
    limit: int = 100,
    offset: int = 0
) -> list[AuditLog]:
    """Get audit logs for a specific connection"""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.connection_id == connection_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    
    return result.scalars().all()


async def get_policy_violations(
    db: AsyncSession,
    days: int = 7,
    limit: int = 100
) -> list[AuditLog]:
    """Get recent policy violations"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.timestamp >= cutoff,
            AuditLog.execution_status == "blocked"
        )
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    
    return result.scalars().all()
