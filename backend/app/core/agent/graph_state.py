"""LangGraph AgentState definition."""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State that flows through the LangGraph pipeline and is persisted by the checkpointer."""

    # Input fields (set at invocation time)
    user_message: str
    connection_id: str
    user_id: str
    mode: str
    execute_sql: bool

    # LangGraph-managed message list — add_messages reducer appends rather than replaces
    messages: Annotated[List[BaseMessage], add_messages]

    # Stage outputs accumulated during the pipeline run
    language_code: str
    language_name: str
    schema_tables: List[Dict[str, Any]]
    schema_relationships: List[Dict[str, Any]]
    tool_results: Dict[str, Any]
    tool_events: List[Dict[str, Any]]
    sql_query: str
    sql_dialect: str
    sql_explanation: str
    validation_status: str
    safe_to_execute: bool
    execution_result: Optional[Dict[str, Any]]
    final_content: str
    error: Optional[str]
    schema_used: Optional[List[Dict[str, Any]]]
