"""Chat endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid
from datetime import datetime
import json

from app.db.session import get_db
from app.models.database import User
from app.models.schemas import ChatMessageRequest, ChatMessageResponse, ConversationResponse
from app.models.domain import Message, PerformanceMode
from app.api.dependencies import get_current_user
from app.services.conversation_service import (
    get_conversation_history,
    save_message,
    get_user_conversations
)
from app.services.connection_service import get_connection
from app.core.agent.runtime import AgentRuntime

router = APIRouter(prefix="/chat")
logger = structlog.get_logger()


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and get SQL generation + optional execution.
    Non-streaming version.
    """
    logger.info(
        "Processing chat message",
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        mode=request.mode.value
    )
    
    # Get connection
    connection = await get_connection(request.connection_id, current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Get conversation history
    history = await get_conversation_history(
        request.conversation_id,
        current_user.id,
        db
    )
    
    # Initialize agent runtime
    runtime = AgentRuntime(mode=request.mode or PerformanceMode.ACHILLIES)
    
    try:
        # Process request
        response = await runtime.process_request(
            user_message=request.message.content,
            connection=connection,
            conversation_history=history,
            execute_sql=request.execute_sql,
            attachments=request.message.attachments if hasattr(request.message, 'attachments') else None
        )
        
        # Save user message
        await save_message(request.conversation_id, request.message, current_user.id, db)
        
        # Save assistant message
        await save_message(request.conversation_id, response, current_user.id, db)
        
        logger.info("Message processed successfully", response_id=response.id)
        
        return ChatMessageResponse(
            conversation_id=request.conversation_id,
            message=response
        )
        
    except Exception as e:
        logger.error("Message processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.post("/message/stream")
async def send_message_stream(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Streaming version using Server-Sent Events.
    Sends real-time updates for each pipeline stage.
    """
    logger.info(
        "Processing streaming chat message",
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        mode=request.mode.value
    )
    
    # Get connection
    connection = await get_connection(request.connection_id, current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Get conversation history
    history = await get_conversation_history(
        request.conversation_id,
        current_user.id,
        db
    )
    
    # Initialize agent runtime
    runtime = AgentRuntime(mode=request.mode or PerformanceMode.ACHILLIES)
    
    async def event_generator():
        """Generate SSE events"""
        try:
            # Save user message
            await save_message(request.conversation_id, request.message, current_user.id, db)
            
            # Stream pipeline events
            async for event in runtime.process_request_streaming(
                user_message=request.message.content,
                connection=connection,
                conversation_history=history,
                execute_sql=request.execute_sql,
                attachments=request.message.attachments if hasattr(request.message, 'attachments') else None
            ):
                # Format as SSE
                event_json = json.dumps(event)
                yield f"data: {event_json}\n\n"
            
            # Final done event
            yield 'data: {"type": "done"}\n\n'
            
        except Exception as e:
            logger.error("Streaming error", error=str(e))
            error_event = json.dumps({
                "type": "error",
                "message": str(e)
            })
            yield f"data: {error_event}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all conversations for the current user"""
    conversations = await get_user_conversations(current_user.id, db)
    
    # Convert to response format
    response = []
    for conv in conversations:
        messages = await get_conversation_history(conv.id, current_user.id, db)
        response.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            messages=messages,
            created_at=conv.created_at,
            updated_at=conv.updated_at
        ))
    
    return response


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific conversation"""
    messages = await get_conversation_history(conversation_id, current_user.id, db)
    
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get conversation metadata
    from sqlalchemy import select
    from app.models.database import Conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        messages=messages,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )
