"""LangGraph StateGraph builder and compiled-graph singleton."""
import structlog
from langgraph.graph import StateGraph, END

from app.core.agent.graph_state import AgentState
from app.core.agent.graph_nodes import (
    language_detection_node,
    context_assembly_node,
    tool_execution_node,
    sql_generation_node,
    validation_node,
    policy_node,
    execution_node,
    response_composition_node,
)

logger = structlog.get_logger()

# Singleton set at application startup via compile_agent_graph_with_checkpointer()
_compiled_graph = None


def build_agent_graph() -> StateGraph:
    """Build the StateGraph with all 8 pipeline nodes."""
    graph = StateGraph(AgentState)

    graph.add_node("language_detection", language_detection_node)
    graph.add_node("context_assembly", context_assembly_node)
    graph.add_node("tool_execution", tool_execution_node)
    graph.add_node("sql_generation", sql_generation_node)
    graph.add_node("validation", validation_node)
    graph.add_node("policy", policy_node)
    graph.add_node("execution", execution_node)
    graph.add_node("response_composition", response_composition_node)

    graph.set_entry_point("language_detection")
    graph.add_edge("language_detection", "context_assembly")
    graph.add_edge("context_assembly", "tool_execution")
    graph.add_edge("tool_execution", "sql_generation")
    graph.add_edge("sql_generation", "validation")
    graph.add_edge("validation", "policy")
    graph.add_edge("policy", "execution")
    graph.add_edge("execution", "response_composition")
    graph.add_edge("response_composition", END)

    return graph


async def compile_agent_graph_with_checkpointer():
    """Compile the graph with the MongoDB-backed checkpointer."""
    from app.db.mongo import mongo_db

    checkpointer = mongo_db.get_langgraph_checkpointer()
    compiled = build_agent_graph().compile(checkpointer=checkpointer)
    logger.info("LangGraph agent graph compiled with MongoDB checkpointer")
    return compiled


def get_agent_graph():
    """Return the compiled graph singleton (available after startup)."""
    return _compiled_graph
