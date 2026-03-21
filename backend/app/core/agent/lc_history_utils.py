"""Convert domain Message list to LangChain BaseMessage list for history injection."""
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.models.domain import Message


def domain_history_to_lc(
    messages: List[Message],
    include_sql: bool = True,
    include_results: bool = True,
) -> List[BaseMessage]:
    """Convert domain Message objects to LangChain BaseMessage objects."""
    result: List[BaseMessage] = []
    for msg in messages:
        if msg.role == "user":
            result.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            parts = [msg.content]
            if include_sql and msg.sql and msg.sql.query:
                parts.append(f"\nSQL generated:\n```sql\n{msg.sql.query}\n```")
            if include_results and msg.results is not None:
                row_count = (
                    msg.results.total_rows
                    if msg.results.total_rows is not None
                    else len(msg.results.rows)
                )
                parts.append(f"\nResult: {row_count} row(s) returned")
            result.append(AIMessage(content="\n".join(parts)))
    return result
