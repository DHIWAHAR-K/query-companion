"""Chat endpoints using MongoDB for history"""
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
from app.services.mongo_conversation_service import MongoConversationService
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
    Non-streaming version with MongoDB storage.
    """
    logger.info(
        "Processing chat message",
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        mode=request.mode.value
    )
    
    # Get connection from PostgreSQL
    connection = await get_connection(request.connection_id, current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Get or create conversation in MongoDB
    conversation = await MongoConversationService.get_conversation(
        request.conversation_id,
        str(current_user.id)
    )
    
    if not conversation:
        # Create new conversation
        conversation = await MongoConversationService.create_conversation(
            user_id=str(current_user.id),
            connection_id=str(request.connection_id),
            title=f"Conversation at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        )
        logger.info("Created new conversation", conversation_id=conversation.conversation_id)
    
    # Get conversation history from MongoDB
    message_docs = await MongoConversationService.get_messages(
        conversation_id=request.conversation_id,
        limit=10  # Last 10 messages for context
    )
    
    # Convert to domain Message objects
    history = []
    for msg_doc in message_docs:
        history.append(Message(
            id=msg_doc.message_id,
            role=msg_doc.role,
            content=msg_doc.content,
            timestamp=msg_doc.timestamp
        ))
    
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
        
        # Save user message to MongoDB
        await MongoConversationService.add_message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.message.content
        )
        
        # Save assistant message to MongoDB
        await MongoConversationService.add_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=response.content,
            metadata={
                "sql_query": response.sql_query,
                "explanation": response.explanation,
                "results": response.results,
                "sql_valid": response.sql_valid,
                "policy_allowed": response.policy_allowed
            },
            mode=request.mode.value if request.mode else "achillies",
            tool_events=[
                {
                    "tool": event.tool,
                    "label": event.label,
                    "duration_ms": event.duration_ms
                }
                for event in (response.tool_events or [])
            ]
        )
        
        logger.info("Message processed and saved to MongoDB", response_id=response.id)
        
        return ChatMessageResponse(
            conversation_id=request.conversation_id,
            message=response
        )
        
    except Exception as e:
        logger.error("Message processing failed", error=str(e), exc_info=True)
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
        mode=request.mode.value if request.mode else "achillies"
    )
    
    # Get connection from PostgreSQL
    connection = await get_connection(request.connection_id, current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Get or create conversation in MongoDB
    conversation = await MongoConversationService.get_conversation(
        request.conversation_id,
        str(current_user.id)
    )
    
    if not conversation:
        conversation = await MongoConversationService.create_conversation(
            user_id=str(current_user.id),
            connection_id=str(request.connection_id),
            title=f"Conversation at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        )
    
    # Get conversation history from MongoDB
    message_docs = await MongoConversationService.get_messages(
        conversation_id=request.conversation_id,
        limit=10
    )
    
    history = []
    for msg_doc in message_docs:
        history.append(Message(
            id=msg_doc.message_id,
            role=msg_doc.role,
            content=msg_doc.content,
            timestamp=msg_doc.timestamp
        ))
    
    # Initialize agent runtime
    runtime = AgentRuntime(mode=request.mode or PerformanceMode.ACHILLIES)
    
    async def event_generator():
        """Generate SSE events for streaming response"""
        try:
            # Save user message
            await MongoConversationService.add_message(
                conversation_id=request.conversation_id,
                role="user",
                content=request.message.content
            )
            
            # Stream agent pipeline events
            final_response = None
            async for event in runtime.process_request_stream(
                user_message=request.message.content,
                connection=connection,
                conversation_history=history,
                execute_sql=request.execute_sql,
                attachments=request.message.attachments if hasattr(request.message, 'attachments') else None
            ):
                # Send event to client
                yield f"data: {json.dumps(event)}\n\n"
                
                # Capture final response
                if event.get("type") == "complete":
                    final_response = event.get("response")
            
            # Save assistant message to MongoDB
            if final_response:
                await MongoConversationService.add_message(
                    conversation_id=request.conversation_id,
                    role="assistant",
                    content=final_response.get("content", ""),
                    metadata={
                        "sql_query": final_response.get("sql_query"),
                        "explanation": final_response.get("explanation"),
                        "results": final_response.get("results"),
                        "sql_valid": final_response.get("sql_valid"),
                        "policy_allowed": final_response.get("policy_allowed")
                    },
                    mode=request.mode.value if request.mode else "achillies",
                    tool_events=final_response.get("tool_events")
                )
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            logger.error("Streaming failed", error=str(e), exc_info=True)
            error_event = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    connection_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all conversations for the current user from MongoDB.
    Optionally filter by connection_id.
    """
    logger.info(
        "Fetching conversations",
        user_id=current_user.id,
        connection_id=connection_id
    )
    
    # Get conversations from MongoDB
    conversations = await MongoConversationService.list_conversations(
        user_id=str(current_user.id),
        connection_id=connection_id,
        limit=100
    )
    
    # Convert to response schema
    result = []
    for conv in conversations:
        result.append(ConversationResponse(
            id=conv.conversation_id,
            connection_id=conv.connection_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=conv.message_count,
            last_message_preview=conv.last_message_preview or ""
        ))
    
    return result


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a conversation and all its messages from MongoDB"""
    logger.info(
        "Deleting conversation",
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    
    deleted = await MongoConversationService.delete_conversation(
        conversation_id=conversation_id,
        user_id=str(current_user.id)
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return {"status": "deleted", "conversation_id": conversation_id}


@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    title: str,
    current_user: User = Depends(get_current_user)
):
    """Update conversation title in MongoDB"""
    logger.info(
        "Updating conversation title",
        conversation_id=conversation_id,
        title=title
    )
    
    updated = await MongoConversationService.update_conversation_title(
        conversation_id=conversation_id,
        user_id=str(current_user.id),
        title=title
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return {"status": "updated", "conversation_id": conversation_id, "title": title}
