"""Stage 9: Response Composition"""
from datetime import datetime
import uuid
import structlog

from app.models.domain import (
    Language, SQLArtifact, ValidationResult, 
    QueryResult, AssistantMessage, ToolEvent
)
from typing import List, Optional

logger = structlog.get_logger()


def compose_response(
    language: Language,
    sql_generation: SQLArtifact,
    validation: ValidationResult,
    execution: Optional[QueryResult] = None,
    tool_events: List[ToolEvent] = None,
    error: Optional[str] = None
) -> AssistantMessage:
    """
    Compose final assistant response.
    
    Args:
        language: Detected language
        sql_generation: Generated SQL artifact
        validation: Validation result
        execution: Query execution result (if executed)
        tool_events: List of tool execution events
        error: Error message if any
        
    Returns:
        AssistantMessage ready to send to user
    """
    logger.debug("Composing response", has_execution=execution is not None)
    
    # Build content message
    if error:
        content = f"I encountered an error: {error}"
    elif not validation.safe_to_execute:
        content = "I generated a query, but it contains operations that cannot be executed:\n\n"
        content += "\n".join(f"- {msg}" for msg in validation.messages)
    elif execution and execution.error:
        content = f"Query generated successfully, but execution failed: {execution.error}"
    elif execution:
        content = f"{sql_generation.explanation}\n\n"
        content += f"The query returned {execution.total_rows} row(s) in {execution.execution_time_ms}ms."
    else:
        content = f"{sql_generation.explanation}\n\n"
        if validation.messages:
            content += "Notes:\n" + "\n".join(f"- {msg}" for msg in validation.messages)
    
    # Update SQL artifact with validation
    sql_generation.validation_status = validation.status
    sql_generation.validation_messages = validation.messages
    
    # Convert to dict format matching frontend expectations
    sql_dict = {
        "query": sql_generation.query,
        "dialect": sql_generation.dialect.value
    }
    
    results_dict = None
    if execution:
        results_dict = {
            "columns": [{"name": col.name, "type": col.type} for col in execution.columns],
            "rows": execution.rows,
            "totalRows": execution.total_rows,
            "executionTimeMs": execution.execution_time_ms
        }
    
    tool_events_dict = None
    if tool_events:
        tool_events_dict = [
            {
                "id": event.id,
                "label": event.label,
                "icon": event.icon,
                "durationMs": event.duration_ms
            }
            for event in tool_events
        ]
    
    message = AssistantMessage(
        id=str(uuid.uuid4()),
        role="assistant",
        content=content,
        timestamp=datetime.utcnow(),
        sql=sql_dict,
        results=results_dict,
        tool_events=tool_events_dict
    )
    
    logger.info("Response composed", content_length=len(content))
    return message
