"""LangGraph node functions — one per pipeline stage, wrapping existing stage functions."""
from typing import Dict, Any
import structlog

from langchain_core.messages import AIMessage

from app.core.agent.graph_state import AgentState
from app.core.agent.stages import (
    detect_language,
    assemble_context,
    execute_tools_with_claude,
    generate_sql,
    validate_sql,
    compose_response,
)
from app.models.domain import (
    Language, Schema, Context, PerformanceMode, SQLDialect
)
from app.services.llm_service import LLMService

logger = structlog.get_logger()


def _get_connection_sync(connection_id: str, user_id: str):
    """Fetch Connection from PostgreSQL (sync wrapper called inside async nodes)."""
    # Import here to avoid circular imports at module load time
    from app.services.connection_service import get_connection as _get_conn
    from app.db.session import AsyncSessionLocal
    import asyncio

    async def _fetch():
        async with AsyncSessionLocal() as db:
            return await _get_conn(connection_id, user_id, db)

    return asyncio.get_event_loop().run_until_complete(_fetch())


async def _fetch_connection(connection_id: str, user_id: str):
    """Async fetch of Connection from PostgreSQL."""
    from app.services.connection_service import get_connection as _get_conn
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return await _get_conn(connection_id, user_id, db)


def _rebuild_context(state: AgentState) -> Context:
    """Reconstruct a Context domain object from serialised state fields."""
    return Context(
        user_id=state["user_id"],
        language=Language(
            code=state.get("language_code", "en"),
            name=state.get("language_name", "English"),
        ),
        db_schema=Schema(
            tables=state.get("schema_tables", []),
            relationships=state.get("schema_relationships", []),
        ),
        tables=[t["name"] for t in state.get("schema_tables", [])],
        conversation_history=[],
    )


# ---------------------------------------------------------------------------
# Node 1 — Language detection
# ---------------------------------------------------------------------------

async def language_detection_node(state: AgentState) -> Dict[str, Any]:
    language = detect_language(state["user_message"])
    return {"language_code": language.code, "language_name": language.name}


# ---------------------------------------------------------------------------
# Node 2 — Context assembly (fetches real schema)
# ---------------------------------------------------------------------------

async def context_assembly_node(state: AgentState) -> Dict[str, Any]:
    connection = await _fetch_connection(state["connection_id"], state["user_id"])
    if connection is None:
        return {"error": f"Connection {state['connection_id']} not found", "schema_tables": [], "schema_relationships": []}

    mode = PerformanceMode(state["mode"])
    language = Language(code=state["language_code"], name=state["language_name"])

    context = await assemble_context(
        user_message=state["user_message"],
        connection=connection,
        conversation_history=[],
        mode=mode,
        language=language,
    )

    return {
        "schema_tables": context.db_schema.tables,
        "schema_relationships": context.db_schema.relationships,
    }


# ---------------------------------------------------------------------------
# Node 3 — Tool execution
# ---------------------------------------------------------------------------

async def tool_execution_node(state: AgentState) -> Dict[str, Any]:
    connection = await _fetch_connection(state["connection_id"], state["user_id"])
    if connection is None:
        return {"tool_results": {}, "tool_events": []}

    llm_service = LLMService()
    mode = PerformanceMode(state["mode"])
    model = llm_service.get_model_name(state["mode"])
    context = _rebuild_context(state)

    tool_results, tool_events = await execute_tools_with_claude(
        user_message=state["user_message"],
        context=context,
        mode=mode,
        client=llm_service,
        model=model,
    )

    serialised_events = [
        {
            "id": e.id,
            "tool": e.tool,
            "label": e.label,
            "icon": e.icon,
            "input": e.input,
            "output": e.output,
            "duration_ms": e.duration_ms,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in (tool_events or [])
    ]

    return {"tool_results": tool_results or {}, "tool_events": serialised_events}


# ---------------------------------------------------------------------------
# Node 4 — SQL generation (uses lc_history from state["messages"])
# ---------------------------------------------------------------------------

async def sql_generation_node(state: AgentState) -> Dict[str, Any]:
    connection = await _fetch_connection(state["connection_id"], state["user_id"])
    if connection is None:
        return {"error": f"Connection {state['connection_id']} not found", "sql_query": "", "sql_dialect": "", "sql_explanation": ""}

    llm_service = LLMService()
    mode = PerformanceMode(state["mode"])
    model = llm_service.get_model_name(state["mode"])
    context = _rebuild_context(state)

    # All messages except the last one (the current HumanMessage) are prior-turn history
    lc_history = list(state.get("messages", []))[:-1]

    sql_artifact = await generate_sql(
        user_message=state["user_message"],
        context=context,
        tool_results=state.get("tool_results", {}),
        dialect=connection.type,
        mode=mode,
        llm_service=llm_service,
        model=model,
        lc_history=lc_history if lc_history else None,
    )

    return {
        "sql_query": sql_artifact.query,
        "sql_dialect": sql_artifact.dialect.value,
        "sql_explanation": sql_artifact.explanation,
    }


# ---------------------------------------------------------------------------
# Node 5 — Validation
# ---------------------------------------------------------------------------

async def validation_node(state: AgentState) -> Dict[str, Any]:
    connection = await _fetch_connection(state["connection_id"], state["user_id"])
    if connection is None:
        return {"validation_status": "error", "safe_to_execute": False}

    context = _rebuild_context(state)
    result = validate_sql(
        sql=state.get("sql_query", ""),
        schema=context.db_schema,
        dialect=connection.type,
    )

    return {"validation_status": result.status, "safe_to_execute": result.safe_to_execute}


# ---------------------------------------------------------------------------
# Node 6 — Policy enforcement
# ---------------------------------------------------------------------------

async def policy_node(state: AgentState) -> Dict[str, Any]:
    from app.core.security.policies import enforce_policies
    from app.models.database import User as DBUser
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.domain import PerformanceMode

    connection = await _fetch_connection(state["connection_id"], state["user_id"])
    if connection is None:
        return {"error": "Connection not found"}

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DBUser).where(DBUser.id == state["user_id"]))
        user = result.scalar_one_or_none()

    mode = PerformanceMode(state["mode"])
    policy_result = await enforce_policies(
        sql=state.get("sql_query", ""),
        connection=connection,
        user=user,
        mode=mode,
    )

    if not policy_result.allowed:
        return {"error": policy_result.denial_reason}

    return {}


# ---------------------------------------------------------------------------
# Node 7 — Query execution (optional)
# ---------------------------------------------------------------------------

async def execution_node(state: AgentState) -> Dict[str, Any]:
    if not state.get("execute_sql") or not state.get("safe_to_execute"):
        return {"execution_result": None}

    from app.core.sql.executor import execute_query
    from app.config import settings as app_settings

    connection = await _fetch_connection(state["connection_id"], state["user_id"])
    if connection is None:
        return {"execution_result": None}

    try:
        result = await execute_query(
            sql=state.get("sql_query", ""),
            connection=connection,
            timeout_seconds=120,
            max_rows=app_settings.MAX_RESULT_ROWS,
        )
        execution_result = {
            "columns": [{"name": c.name, "type": c.type} for c in result.columns],
            "rows": result.rows,
            "total_rows": result.total_rows,
            "execution_time_ms": result.execution_time_ms,
        }
    except Exception as e:
        execution_result = {"columns": [], "rows": [], "total_rows": 0, "execution_time_ms": 0, "error": str(e)}

    return {"execution_result": execution_result}


# ---------------------------------------------------------------------------
# Node 8 — Response composition + append AIMessage to messages list
# ---------------------------------------------------------------------------

async def response_composition_node(state: AgentState) -> Dict[str, Any]:
    from app.models.domain import (
        SQLArtifact, SQLDialect, ValidationResult, QueryResult, Column, SchemaTableUsed
    )

    sql_artifact = None
    if state.get("sql_query"):
        sql_artifact = SQLArtifact(
            query=state["sql_query"],
            dialect=SQLDialect(state.get("sql_dialect", "postgresql")),
            explanation=state.get("sql_explanation", ""),
        )

    validation = ValidationResult(
        status=state.get("validation_status", "valid"),
        safe_to_execute=state.get("safe_to_execute", True),
    )

    execution = None
    if state.get("execution_result"):
        er = state["execution_result"]
        execution = QueryResult(
            columns=[Column(name=c["name"], type=c["type"]) for c in er.get("columns", [])],
            rows=er.get("rows", []),
            total_rows=er.get("total_rows", 0),
            execution_time_ms=er.get("execution_time_ms", 0),
            error=er.get("error"),
        )

    schema_used_domain = None
    if state.get("schema_tables"):
        schema_used_domain = [
            SchemaTableUsed(
                table_name=t["name"],
                schema_name=t.get("schema"),
                columns=[{"name": c["name"], "type": c.get("type", "?")} for c in t.get("columns", [])],
            )
            for t in state["schema_tables"]
        ]

    language = Language(code=state.get("language_code", "en"), name=state.get("language_name", "English"))

    response = compose_response(
        language=language,
        sql_generation=sql_artifact,
        validation=validation,
        execution=execution,
        tool_events=None,
        error=state.get("error"),
        schema_used=schema_used_domain,
    )

    # Append the assistant reply to the LangGraph messages list so the checkpointer saves it
    ai_msg = AIMessage(content=response.content)

    schema_used_serialised = [s.model_dump() for s in (response.schema_used or [])]
    sql_serialised = response.sql.model_dump() if response.sql else None

    return {
        "final_content": response.content,
        "schema_used": schema_used_serialised,
        "messages": [ai_msg],  # add_messages reducer will append this
        "error": state.get("error"),
        "_response": {
            "id": response.id,
            "role": response.role,
            "content": response.content,
            "timestamp": response.timestamp.isoformat(),
            "sql": sql_serialised,
            "schema_used": schema_used_serialised,
        },
    }
