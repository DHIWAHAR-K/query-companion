"""Connection service for managing database connections"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import structlog

from app.models.database import Connection as DBConnection

logger = structlog.get_logger()


async def get_connection(
    connection_id: str,
    user_id: str,
    db: AsyncSession
) -> Optional[DBConnection]:
    """
    Get a connection by ID for a specific user.
    
    Args:
        connection_id: Connection ID
        user_id: User ID for authorization
        db: Database session
        
    Returns:
        Connection object or None if not found
    """
    result = await db.execute(
        select(DBConnection).where(
            DBConnection.id == connection_id,
            DBConnection.user_id == user_id
        )
    )
    
    connection = result.scalar_one_or_none()
    
    if connection:
        logger.debug("Connection retrieved", connection_id=connection_id)
    else:
        logger.warning("Connection not found", connection_id=connection_id)
    
    return connection


async def get_user_connections(
    user_id: str,
    db: AsyncSession
) -> list[DBConnection]:
    """Get all connections for a user"""
    result = await db.execute(
        select(DBConnection)
        .where(DBConnection.user_id == user_id)
        .order_by(DBConnection.created_at.desc())
    )
    
    return result.scalars().all()
