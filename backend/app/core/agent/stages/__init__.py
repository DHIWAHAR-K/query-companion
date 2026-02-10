"""Pipeline stages package"""
from app.core.agent.stages.language import detect_language
from app.core.agent.stages.context import assemble_context
from app.core.agent.stages.multimodal import process_attachments
from app.core.agent.stages.tools import plan_tools, execute_tools, execute_tools_with_claude
from app.core.agent.stages.generation import generate_sql
from app.core.agent.stages.validation import validate_sql
from app.core.agent.stages.response import compose_response

__all__ = [
    "detect_language",
    "assemble_context",
    "process_attachments",
    "plan_tools",
    "execute_tools",
    "execute_tools_with_claude",
    "generate_sql",
    "validate_sql",
    "compose_response"
]
