"""Convert domain Message list to LangChain BaseMessage list for history injection."""
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.models.domain import Message


def domain_history_to_lc(messages: List[Message]) -> List[BaseMessage]:
    """Convert domain Message objects to LangChain BaseMessage objects."""
    result: List[BaseMessage] = []
    for msg in messages:
        if msg.role == "user":
            result.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            result.append(AIMessage(content=msg.content))
    return result
