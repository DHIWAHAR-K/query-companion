"""Agent Runtime - Main orchestrator for the SQL generation pipeline"""
from typing import List, Dict, Any, Optional, AsyncGenerator
import structlog

from app.models.domain import (
    Message, PerformanceMode, AssistantMessage
)
from app.models.database import Connection
from app.core.agent.stages import (
    detect_language,
    assemble_context,
    process_attachments,
    plan_tools,
    execute_tools_with_claude,
    generate_sql,
    validate_sql,
    compose_response
)
from app.services.llm_service import LLMService
from app.config import settings

logger = structlog.get_logger()


class AgentRuntime:
    """
    Orchestrates the multi-stage pipeline for SQL generation.
    
    Pipeline stages:
    1. Language Detection
    2. Context Assembly
    5. SQL Generation
    6. Validation
    9. Response Composition
    
    (Stages 3, 4, 7, 8 will be added in later phases)
    """
    
    def __init__(self, mode: PerformanceMode):
        self.mode = mode
        self.llm_service = LLMService()
        self.model = self.llm_service.get_model_name(mode.value)
    
    async def process_request(
        self,
        user_message: str,
        connection: Connection,
        conversation_history: List[Message],
        execute_sql: bool = False,
        attachments: Optional[List[bytes]] = None
    ) -> AssistantMessage:
        """
        Main orchestration method - runs all pipeline stages.
        
        Args:
            user_message: User's natural language query
            connection: Database connection to use
            conversation_history: Previous messages in conversation
            execute_sql: Whether to execute the generated SQL (not in MVP)
            attachments: File attachments (not in MVP)
            
        Returns:
            AssistantMessage with generated SQL and results
        """
        logger.info(
            "Processing request",
            mode=self.mode.value,
            connection_id=connection.id,
            connection_type=connection.type.value
        )
        
        try:
            # Stage 1: Language detection
            language = detect_language(user_message)
            logger.debug("Language detected", language=language.code)
            
            # Stage 2: Context assembly
            context = await assemble_context(
                user_message=user_message,
                connection=connection,
                conversation_history=conversation_history,
                mode=self.mode,
                language=language
            )
            logger.debug("Context assembled", table_count=len(context.tables))
            
            # Stage 3: Multimodal ingestion (if images attached)
            image_context = None
            if attachments:
                image_context = await process_attachments(attachments, self.llm_service)
                logger.debug("Image context extracted", entities=len(image_context.entities) if image_context else 0)
            
            # Stage 4: Tool planning and execution
            # Use LLM's tool use for intelligent tool selection
            tool_results, tool_events = await execute_tools_with_claude(
                user_message=user_message,
                context=context,
                mode=self.mode,
                client=self.llm_service,
                model=self.model
            )
            
            if tool_events:
                logger.debug("Tools executed", count=len(tool_events))
            
            # Stage 5: SQL generation
            
            sql_generation = await generate_sql(
                user_message=user_message,
                context=context,
                tool_results=tool_results,
                dialect=connection.type,
                mode=self.mode,
                client=self.client,
                model=self.model
            )
            logger.info("SQL generated", length=len(sql_generation.query))
            
            # Stage 6: Validation
            validation_result = validate_sql(
                sql=sql_generation.query,
                schema=context.db_schema,
                dialect=connection.type
            )
            logger.debug("Validation complete", status=validation_result.status)
            
            # Stage 7: Policy enforcement
            from app.core.security.policies import enforce_policies
            from app.models.database import User as DBUser
            from sqlalchemy import select
            from app.db.session import AsyncSessionLocal
            
            # Get user object for policy enforcement
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(DBUser).where(DBUser.id == connection.user_id))
                user = result.scalar_one_or_none()
            
            policy_result = await enforce_policies(
                sql=sql_generation.query,
                connection=connection,
                user=user,
                mode=self.mode
            )
            
            if not policy_result.allowed:
                logger.warning("Policy blocked query", reason=policy_result.denial_reason)
                response = compose_response(
                    language=language,
                    sql_generation=sql_generation,
                    validation=validation_result,
                    execution=None,
                    tool_events=tool_events if 'tool_events' in locals() else None,
                    error=policy_result.denial_reason
                )
                return response
            
            # Stage 8: Query execution
            execution_result = None
            if execute_sql and validation_result.safe_to_execute:
                from app.core.sql.executor import execute_query
                from app.config import settings
                
                timeout = self._get_timeout()
                
                try:
                    execution_result = await execute_query(
                        sql=sql_generation.query,
                        connection=connection,
                        timeout_seconds=timeout,
                        max_rows=settings.MAX_RESULT_ROWS
                    )
                    logger.info(
                        "Query executed",
                        rows=execution_result.total_rows,
                        duration_ms=execution_result.execution_time_ms
                    )
                except Exception as e:
                    logger.error("Query execution failed", error=str(e))
                    from app.models.domain import QueryResult
                    execution_result = QueryResult(
                        columns=[],
                        rows=[],
                        total_rows=0,
                        execution_time_ms=0,
                        error=str(e)
                    )
            
            # Stage 9: Response composition
            response = compose_response(
                language=language,
                sql_generation=sql_generation,
                validation=validation_result,
                execution=execution_result,
                tool_events=tool_events if 'tool_events' in locals() else None,
                error=None
            )
            
            logger.info("Request processing complete")
            return response
            
        except Exception as e:
            logger.error("Request processing failed", error=str(e))
            
            # Return error response
            return compose_response(
                language=language if 'language' in locals() else None,
                sql_generation=None,
                validation=None,
                execution=None,
                tool_events=None,
                error=str(e)
            )
    
    async def process_request_streaming(
        self,
        user_message: str,
        connection: Connection,
        conversation_history: List[Message],
        execute_sql: bool = False,
        attachments: Optional[List[bytes]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming version that yields events as they happen.
        
        Args:
            user_message: User's natural language query
            connection: Database connection to use
            conversation_history: Previous messages in conversation
            execute_sql: Whether to execute the generated SQL
            attachments: File attachments
            
        Yields:
            Dict events for each pipeline stage
        """
        logger.info(
            "Processing streaming request",
            mode=self.mode.value,
            connection_id=connection.id
        )
        
        try:
            # Stage 1: Language detection
            yield {"type": "stage_start", "stage": "language_detection"}
            language = detect_language(user_message)
            yield {
                "type": "language_detected",
                "language": language.code,
                "language_name": language.name,
                "confidence": language.confidence
            }
            
            # Stage 2: Context assembly
            yield {"type": "stage_start", "stage": "context_assembly"}
            context = await assemble_context(
                user_message=user_message,
                connection=connection,
                conversation_history=conversation_history,
                mode=self.mode,
                language=language
            )
            yield {
                "type": "context_assembled",
                "table_count": len(context.tables),
                "tables": context.tables
            }
            
            # Stage 4: Tool execution
            yield {"type": "stage_start", "stage": "tool_execution"}
            tool_results, tool_events = await execute_tools_with_claude(
                user_message=user_message,
                context=context,
                mode=self.mode,
                client=self.llm_service,
                model=self.model
            )
            
            if tool_events:
                for event in tool_events:
                    yield {
                        "type": "tool_complete",
                        "tool": event.tool,
                        "label": event.label,
                        "duration_ms": event.duration_ms
                    }
            
            # Stage 5: SQL generation
            yield {"type": "stage_start", "stage": "sql_generation"}
            sql_generation = await generate_sql(
                user_message=user_message,
                context=context,
                tool_results=tool_results,
                dialect=connection.type,
                mode=self.mode,
                llm_service=self.llm_service,
                model=self.model
            )
            yield {
                "type": "sql_generated",
                "sql": sql_generation.query,
                "dialect": sql_generation.dialect.value,
                "explanation": sql_generation.explanation
            }
            
            # Stage 6: Validation
            yield {"type": "stage_start", "stage": "validation"}
            validation_result = validate_sql(
                sql=sql_generation.query,
                schema=context.db_schema,
                dialect=connection.type
            )
            yield {
                "type": "validation_complete",
                "status": validation_result.status,
                "messages": validation_result.messages,
                "safe_to_execute": validation_result.safe_to_execute
            }
            
            # Stage 8: Execution (if requested)
            execution_result = None
            if execute_sql and validation_result.safe_to_execute:
                yield {"type": "stage_start", "stage": "execution"}
                
                from app.core.sql.executor import execute_query
                
                try:
                    execution_result = await execute_query(
                        sql=sql_generation.query,
                        connection=connection,
                        timeout_seconds=self._get_timeout(),
                        max_rows=settings.MAX_RESULT_ROWS
                    )
                    
                    yield {
                        "type": "execution_complete",
                        "total_rows": execution_result.total_rows,
                        "execution_time_ms": execution_result.execution_time_ms,
                        "columns": [{"name": col.name, "type": col.type} for col in execution_result.columns],
                        "rows": execution_result.rows
                    }
                    
                except Exception as e:
                    logger.error("Query execution failed", error=str(e))
                    yield {
                        "type": "execution_error",
                        "error": str(e)
                    }
            
            # Stage 9: Final message
            response = compose_response(
                language=language,
                sql_generation=sql_generation,
                validation=validation_result,
                execution=execution_result,
                tool_events=tool_events,
                error=None
            )
            
            yield {
                "type": "message_complete",
                "message": {
                    "id": response.id,
                    "role": response.role,
                    "content": response.content,
                    "timestamp": response.timestamp.isoformat(),
                    "sql": response.sql,
                    "results": response.results,
                    "tool_events": response.tool_events
                }
            }
            
        except Exception as e:
            logger.error("Streaming request failed", error=str(e))
            yield {
                "type": "error",
                "message": str(e)
            }
