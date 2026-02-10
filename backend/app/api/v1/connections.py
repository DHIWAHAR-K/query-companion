"""Connection management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime
import structlog

from app.db.session import get_db
from app.models.database import User, Connection
from app.models.schemas import (
    CreateConnectionRequest,
    ConnectionResponse,
    ConnectionTestRequest,
    ConnectionTestResponse
)
from app.api.dependencies import get_current_user
from app.core.security.encryption import encrypt_credentials, decrypt_credentials

router = APIRouter(prefix="/connections")
logger = structlog.get_logger()


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    request: CreateConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new database connection"""
    logger.info("Creating connection", user_id=current_user.id, type=request.type.value)
    
    try:
        # Encrypt credentials
        encrypted_creds = encrypt_credentials(request.credentials)
        
        # Create connection
        connection = Connection(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            name=request.name,
            type=request.type,
            credentials={"encrypted": encrypted_creds},
            is_read_only=request.is_read_only,
            created_at=datetime.utcnow()
        )
        
        db.add(connection)
        await db.commit()
        await db.refresh(connection)
        
        logger.info("Connection created", connection_id=connection.id)
        
        return ConnectionResponse(
            id=connection.id,
            name=connection.name,
            type=connection.type.value,
            is_read_only=connection.is_read_only,
            created_at=connection.created_at,
            last_used=connection.last_used
        )
        
    except Exception as e:
        logger.error("Connection creation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connection: {str(e)}"
        )


@router.get("", response_model=list[ConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all connections for the current user"""
    result = await db.execute(
        select(Connection)
        .where(Connection.user_id == current_user.id)
        .order_by(Connection.created_at.desc())
    )
    
    connections = result.scalars().all()
    
    return [
        ConnectionResponse(
            id=conn.id,
            name=conn.name,
            type=conn.type.value,
            is_read_only=conn.is_read_only,
            created_at=conn.created_at,
            last_used=conn.last_used
        )
        for conn in connections
    ]


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific connection"""
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == current_user.id
        )
    )
    
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    return ConnectionResponse(
        id=connection.id,
        name=connection.name,
        type=connection.type.value,
        is_read_only=connection.is_read_only,
        created_at=connection.created_at,
        last_used=connection.last_used
    )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a connection"""
    result = await db.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == current_user.id
        )
    )
    
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    await db.delete(connection)
    await db.commit()
    
    logger.info("Connection deleted", connection_id=connection_id)


@router.post("/test", response_model=ConnectionTestResponse)
async def test_connection(
    request: ConnectionTestRequest,
    current_user: User = Depends(get_current_user)
):
    """Test a database connection"""
    logger.info("Testing connection", type=request.type.value)
    
    # TODO: Implement actual connection testing in Phase 2
    # For now, return success for MVP
    
    return ConnectionTestResponse(
        success=True,
        message="Connection test successful (mock response)",
        details={"type": request.type.value}
    )
