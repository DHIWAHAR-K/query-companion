"""Simulated DB agent: single LLM call with dual-mode (plan/code) prompt and response parsing."""
import re
import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Any
import structlog

from app.models.domain import (
    AssistantMessage,
    SchemaTableUsed,
    SQLArtifact,
    SQLDialect,
    QueryResult,
    Column,
)
from app.core.agent.simulated_prompts import get_simulated_system_prompt
from app.services.llm_service import LLMService

logger = structlog.get_logger()


def _build_user_prompt(
    user_message: str,
    last_generated_schema: Optional[str] = None,
) -> str:
    """Build user prompt; include previous schema for continuity when provided."""
    parts = []
    if last_generated_schema and last_generated_schema.strip():
        parts.append(
            "Previously generated schema (reuse unless the user changes context):\n"
            f"{last_generated_schema.strip()}\n\n"
        )
    parts.append(f"User question: {user_message.strip()}")
    return "\n".join(parts)


def _parse_tables_section(text: str) -> List[SchemaTableUsed]:
    """Parse 'Tables (generated)' section into List[SchemaTableUsed]."""
    tables: List[SchemaTableUsed] = []
    block = text.strip()
    # Extract only the tables block (between Tables (generated) and SQL or Result)
    for marker in ("Tables (generated)", "tables (generated)"):
        if marker in block:
            idx = block.lower().index(marker.lower()) + len(marker)
            block = block[idx:].strip()
            break
    for end_marker in ("\nSQL", "\nResult (generated)", "\nResult "):
        lower = block.lower()
        em = end_marker.lower()
        if em in lower:
            block = block[: block.lower().index(em)].strip()
            break
    lines = block.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^(\w+)\.(\w+)\s*$", line)
        if m:
            schema_name, table_name = m.group(1), m.group(2)
            columns = []
            i += 1
            if i < len(lines) and lines[i].strip().lower().startswith("column"):
                i += 1
            while i < len(lines):
                row = lines[i].strip()
                if not row:
                    i += 1
                    continue
                if re.match(r"^\w+\.\w+\s*$", row):
                    break
                parts = re.split(r"\s{2,}|\t", row, maxsplit=2)
                col_name = (parts[0] or "").strip()
                col_type = (parts[1] if len(parts) > 1 else "text").strip()
                if col_name:
                    columns.append({"name": col_name, "type": col_type})
                i += 1
            if columns:
                tables.append(
                    SchemaTableUsed(
                        table_name=table_name,
                        schema_name=schema_name,
                        columns=columns,
                    )
                )
            continue
        i += 1
    return tables


def _parse_sql_section(text: str) -> Optional[str]:
    """Extract SQL from section after 'SQL' until 'Result' or end."""
    text = text.strip()
    # After "SQL" or "SQL\n" take until "Result (generated)" or ``` or end
    for marker in ("\nSQL\n", "\nSQL\r\n", "SQL\n", "SQL\r\n"):
        if marker in text:
            idx = text.index(marker) + len(marker)
            rest = text[idx:].strip()
            # Remove optional ```sql ... ```
            if rest.startswith("```"):
                rest = re.sub(r"^```\w*\n?", "", rest)
                rest = re.sub(r"\n?```\s*$", "", rest)
            # Stop at Result (generated)
            result_marker = "Result (generated)"
            if result_marker.lower() in rest.lower():
                pos = rest.lower().index(result_marker.lower())
                rest = rest[:pos]
            return rest.strip() if rest else None
    return None


def _parse_result_section(text: str) -> Optional[dict]:
    """Parse 'Result (generated)' into { columns, rows, totalRows, executionTimeMs }."""
    text = text.strip()
    marker = "Result (generated)"
    if marker.lower() not in text.lower():
        return None
    idx = text.lower().index(marker.lower()) + len(marker)
    rest = text[idx:].strip()
    lines = [ln for ln in rest.split("\n") if ln.strip()]
    if not lines:
        return {"columns": [], "rows": [], "totalRows": 0, "executionTimeMs": 0}
    # First non-empty line = header
    header_line = lines[0]
    headers = re.split(r"\s{2,}|\t", header_line.strip())
    columns = [{"name": h.strip(), "type": "text"} for h in headers if h.strip()]
    rows = []
    for line in lines[1:]:
        cells = re.split(r"\s{2,}|\t", line.strip())
        rows.append(cells[: len(columns)] if len(cells) >= len(columns) else cells + [""] * (len(columns) - len(cells)))
    return {
        "columns": columns,
        "rows": rows,
        "totalRows": len(rows),
        "executionTimeMs": 0,
    }


def _parse_llm_response(raw: str) -> Tuple[str, Optional[List[SchemaTableUsed]], Optional[dict], Optional[dict]]:
    """
    Parse LLM response into content, schema_used, sql dict, results dict.
    Returns (content, schema_used, sql_dict, results_dict).
    Plan mode: schema_used, sql_dict, results_dict are None.
    """
    raw = raw.strip()
    has_tables = "Tables (generated)" in raw or "tables (generated)" in raw.lower()
    has_sql = re.search(r"\bSQL\b", raw, re.IGNORECASE) is not None
    has_result = "Result (generated)" in raw or "result (generated)" in raw.lower()

    if not has_tables and not has_sql:
        # Plan mode: entire response is content
        return (raw, None, None, None)

    # Code mode: parse sections
    schema_used = _parse_tables_section(raw) if has_tables else None
    sql_query = _parse_sql_section(raw) if has_sql else None
    sql_dict = {"query": sql_query, "dialect": "postgresql"} if sql_query else None
    results_dict = _parse_result_section(raw) if has_result else None

    # Content: short summary for code mode (or we could use the full raw; plan says "Do not add extra commentary")
    content_parts = []
    if schema_used:
        content_parts.append("Generated schema and query as requested.")
    if sql_query:
        content_parts.append("SQL executed against the simulated database.")
    content = " ".join(content_parts) if content_parts else raw[:500]

    return (content, schema_used, sql_dict, results_dict)


async def process_simulated(
    user_message: str,
    conversation_history: List[Any],
    last_generated_schema: Optional[str] = None,
) -> AssistantMessage:
    """
    Run simulated DB flow: one LLM call with dual-mode prompt, then parse response
    into AssistantMessage (content, sql, results, schema_used).
    """
    system_prompt = get_simulated_system_prompt()
    user_prompt = _build_user_prompt(user_message, last_generated_schema)

    llm = LLMService()
    model = llm.get_model_name("achillies")
    raw = await llm.generate_sql(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        max_tokens=4096,
    )

    content, schema_used, sql_dict, results_dict = _parse_llm_response(raw or "")

    # Code mode: set explanation text between the three blocks
    explanation_after_schema = None
    explanation_before_result = None
    if schema_used or sql_dict:
        explanation_after_schema = (
            "The tables above define the structure used for this answer. "
            "The following SQL query was generated to answer your question and is executed against the simulated database."
        )
        explanation_before_result = (
            "The query above returns the following result. "
            "Rows and columns match the SELECT clause; values are simulated and consistent with the schema."
        )

    # Build SQLArtifact and QueryResult to match Message schema (explanation, total_rows, execution_time_ms)
    sql_artifact = None
    if sql_dict and sql_dict.get("query"):
        sql_artifact = SQLArtifact(
            query=sql_dict["query"],
            dialect=SQLDialect(sql_dict.get("dialect", "postgresql")),
            explanation=sql_dict.get("explanation") or content or "Generated SQL for the simulated database.",
        )

    query_result = None
    if results_dict:
        columns = [
            Column(name=c.get("name", ""), type=c.get("type", "text"))
            for c in results_dict.get("columns", [])
        ]
        query_result = QueryResult(
            columns=columns,
            rows=results_dict.get("rows", []),
            total_rows=results_dict.get("totalRows", len(results_dict.get("rows", []))),
            execution_time_ms=results_dict.get("executionTimeMs", 0),
        )

    return AssistantMessage(
        id=str(uuid.uuid4()),
        role="assistant",
        content=content,
        timestamp=datetime.utcnow(),
        sql=sql_artifact,
        results=query_result,
        tool_events=None,
        schema_used=schema_used,
        explanation_after_schema=explanation_after_schema,
        explanation_before_result=explanation_before_result,
    )
