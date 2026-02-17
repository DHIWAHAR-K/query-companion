"""Chat endpoints using MongoDB for history"""
from types import SimpleNamespace
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid
from datetime import datetime
import json

from app.db.session import get_db
from app.models.database import User, SQLDialect
from app.models.schemas import ChatMessageRequest, ChatMessageResponse, ConversationResponse
from app.models.domain import Message, PerformanceMode
from app.api.dependencies import get_current_user
from app.services.mongo_conversation_service import MongoConversationService
from app.services.connection_service import get_connection
from app.services.data_file_service import get_first_data_file_parsed
from app.core.agent.runtime import AgentRuntime
from app.core.agent.simulated_agent import process_simulated

router = APIRouter(prefix="/chat")
logger = structlog.get_logger()

DEMO_CONNECTION_ID = "demo"


def _last_generated_schema_from_messages(message_docs) -> str | None:
    """From conversation messages, get the last assistant message's schema_used and serialize to text."""
    for msg in reversed(message_docs):
        if msg.role != "assistant" or not getattr(msg, "metadata", None):
            continue
        schema_used = msg.metadata.get("schema_used") if isinstance(msg.metadata, dict) else None
        if not schema_used or not isinstance(schema_used, list):
            continue
        lines = []
        for t in schema_used:
            if not isinstance(t, dict):
                continue
            schema_name = t.get("schema_name") or "public"
            table_name = t.get("table_name") or ""
            cols = t.get("columns") or []
            if not table_name:
                continue
            lines.append(f"{schema_name}.{table_name}")
            lines.append("column  type  key/notes")
            for c in cols:
                name = c.get("name") if isinstance(c, dict) else ""
                typ = c.get("type") if isinstance(c, dict) else "text"
                if name:
                    lines.append(f"{name}  {typ}")
            lines.append("")
        if lines:
            return "\n".join(lines).strip()
    return None


def _schema_text_from_schema_used(schema_used: list) -> str:
    """Build schema text from a list of schema_used dicts (for file-upload path)."""
    if not schema_used or not isinstance(schema_used, list):
        return ""
    lines = []
    for t in schema_used:
        if not isinstance(t, dict):
            continue
        schema_name = t.get("schema_name") or "public"
        table_name = t.get("table_name") or ""
        cols = t.get("columns") or []
        if not table_name:
            continue
        lines.append(f"{schema_name}.{table_name}")
        lines.append("column  type  key/notes")
        for c in cols:
            name = c.get("name") if isinstance(c, dict) else ""
            typ = c.get("type") if isinstance(c, dict) else "text"
            if name:
                lines.append(f"{name}  {typ}")
        lines.append("")
    return "\n".join(lines).strip() if lines else ""


async def _get_connection_for_request(connection_id, user_id, db):
    """Resolve connection: real DB row or None (caller uses demo when None)."""
    if connection_id and str(connection_id).strip():
        return await get_connection(connection_id, user_id, db)
    return None


def _demo_connection(user_id: str):
    """In-memory connection object for demo mode (text-to-SQL only, no real DB)."""
    return SimpleNamespace(
        id=DEMO_CONNECTION_ID,
        user_id=user_id,
        type=SQLDialect.POSTGRESQL,
    )


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
    
    # Resolve connection: real DB or demo (when no connection selected)
    connection = await _get_connection_for_request(request.connection_id, current_user.id, db)
    if request.connection_id and str(request.connection_id).strip():
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found"
            )
    else:
        connection = _demo_connection(str(current_user.id))

    # Get or create conversation in MongoDB
    conversation = await MongoConversationService.get_conversation(
        request.conversation_id,
        str(current_user.id)
    )
    
    if not conversation:
        # Create new conversation
        conversation = await MongoConversationService.create_conversation(
            user_id=str(current_user.id),
            connection_id=str(connection.id),
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
    
    try:
        if getattr(connection, "id", None) == DEMO_CONNECTION_ID:
            # Simulated DB: dual-mode (plan/code) with conversation schema memory
            last_schema = _last_generated_schema_from_messages(message_docs)
            response = await process_simulated(
                user_message=request.message.content,
                conversation_history=history,
                last_generated_schema=last_schema,
            )
        else:
            # Real DB: full pipeline
            runtime = AgentRuntime(mode=request.mode or PerformanceMode.ACHILLIES)
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
        metadata = {
            "sql_query": response.sql.get("query") if isinstance(response.sql, dict) and response.sql else None,
            "explanation": response.content[:500] if response.content else None,
            "results": response.results,
            "sql_valid": None,
            "policy_allowed": None,
        }
        if response.schema_used:
            metadata["schema_used"] = [s.model_dump() for s in response.schema_used]
        if getattr(response, "explanation_after_schema", None):
            metadata["explanation_after_schema"] = response.explanation_after_schema
        if getattr(response, "explanation_before_result", None):
            metadata["explanation_before_result"] = response.explanation_before_result
        await MongoConversationService.add_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=response.content,
            metadata=metadata,
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
    
    # Resolve connection: real DB or demo (when no connection selected)
    connection = await _get_connection_for_request(request.connection_id, current_user.id, db)
    if request.connection_id and str(request.connection_id).strip():
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found"
            )
    else:
        connection = _demo_connection(str(current_user.id))

    # Get or create conversation in MongoDB
    conversation = await MongoConversationService.get_conversation(
        request.conversation_id,
        str(current_user.id)
    )
    
    if not conversation:
        conversation = await MongoConversationService.create_conversation(
            user_id=str(current_user.id),
            connection_id=str(connection.id),
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
    
    is_demo = getattr(connection, "id", None) == DEMO_CONNECTION_ID
    attachments = getattr(request.message, "attachments", None) or []
    file_data = get_first_data_file_parsed(attachments)
    
    async def event_generator():
        """Generate SSE events for streaming response"""
        try:
            await MongoConversationService.add_message(
                conversation_id=request.conversation_id,
                role="user",
                content=request.message.content
            )
            
            final_response = None
            if file_data:
                # Data file attached: use file schema + preview, generate SQL with process_simulated
                last_schema = _schema_text_from_schema_used(file_data.get("schema_used") or [])
                response = await process_simulated(
                    user_message=request.message.content,
                    conversation_history=history,
                    last_generated_schema=last_schema or None,
                )
                schema_used_serialized = file_data.get("schema_used") or []
                sql_serialized = response.sql.model_dump() if response.sql else None
                results_serialized = response.results.model_dump() if response.results else None
                data_preview = {
                    "columns": file_data.get("columns") or [],
                    "rows": file_data.get("rows") or [],
                    "label": file_data.get("label") or "Data preview",
                }
                final_response = {
                    "id": response.id,
                    "role": response.role,
                    "content": response.content,
                    "timestamp": response.timestamp.isoformat(),
                    "sql": sql_serialized,
                    "results": results_serialized,
                    "tool_events": response.tool_events,
                    "schema_used": schema_used_serialized,
                    "explanation_after_schema": getattr(response, "explanation_after_schema", None),
                    "explanation_before_result": getattr(response, "explanation_before_result", None),
                    "data_preview": data_preview,
                }
                yield f"data: {json.dumps({'type': 'message_complete', 'message': final_response})}\n\n"
            elif is_demo:
                # Simulated DB: single call, then one message_complete event (no file)
                last_schema = _last_generated_schema_from_messages(message_docs)
                response = await process_simulated(
                    user_message=request.message.content,
                    conversation_history=history,
                    last_generated_schema=last_schema,
                )
                schema_used_serialized = [s.model_dump() for s in (response.schema_used or [])]
                sql_serialized = response.sql.model_dump() if response.sql else None
                results_serialized = response.results.model_dump() if response.results else None
                final_response = {
                    "id": response.id,
                    "role": response.role,
                    "content": response.content,
                    "timestamp": response.timestamp.isoformat(),
                    "sql": sql_serialized,
                    "results": results_serialized,
                    "tool_events": response.tool_events,
                    "schema_used": schema_used_serialized,
                    "explanation_after_schema": getattr(response, "explanation_after_schema", None),
                    "explanation_before_result": getattr(response, "explanation_before_result", None),
                }
                yield f"data: {json.dumps({'type': 'message_complete', 'message': final_response})}\n\n"
            else:
                runtime = AgentRuntime(mode=request.mode or PerformanceMode.ACHILLIES)
                async for event in runtime.process_request_streaming(
                    user_message=request.message.content,
                    connection=connection,
                    conversation_history=history,
                    execute_sql=request.execute_sql,
                    attachments=request.message.attachments if hasattr(request.message, 'attachments') else None
                ):
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") == "message_complete":
                        final_response = event.get("message")
                    elif event.get("type") == "complete":
                        final_response = event.get("response")
            
            if final_response:
                meta = {
                    "sql_query": final_response.get("sql", {}).get("query") if final_response.get("sql") else final_response.get("sql_query"),
                    "explanation": final_response.get("explanation"),
                    "results": final_response.get("results"),
                    "sql_valid": final_response.get("sql_valid"),
                    "policy_allowed": final_response.get("policy_allowed"),
                }
                if final_response.get("schema_used") is not None:
                    meta["schema_used"] = final_response.get("schema_used")
                if final_response.get("explanation_after_schema") is not None:
                    meta["explanation_after_schema"] = final_response.get("explanation_after_schema")
                if final_response.get("explanation_before_result") is not None:
                    meta["explanation_before_result"] = final_response.get("explanation_before_result")
                if final_response.get("data_preview") is not None:
                    meta["data_preview"] = final_response.get("data_preview")
                await MongoConversationService.add_message(
                    conversation_id=request.conversation_id,
                    role="assistant",
                    content=final_response.get("content", ""),
                    metadata=meta,
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
    
    # Convert to response schema (include last N messages per conversation for list view)
    result = []
    for conv in conversations:
        message_docs = await MongoConversationService.get_messages(
            conversation_id=conv.conversation_id,
            limit=50
        )
        messages = [
            Message(
                id=msg.message_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                tool_events=msg.tool_events,
            )
            for msg in message_docs
        ]
        result.append(ConversationResponse(
            id=conv.conversation_id,
            title=conv.title,
            messages=messages,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
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
