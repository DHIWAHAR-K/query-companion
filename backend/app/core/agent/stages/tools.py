"""Stage 4: Tool Planning and Execution"""
from anthropic import AsyncAnthropic
import structlog
from typing import List, Dict, Any, Tuple
import uuid
from datetime import datetime
import time

from app.models.domain import Context, PerformanceMode, ToolEvent
from app.core.tools.web_search import search_web, WEB_SEARCH_TOOL
from app.config import settings

logger = structlog.get_logger()


def plan_tools(
    user_message: str,
    context: Context,
    mode: PerformanceMode
) -> List[Dict[str, Any]]:
    """
    Plan which tools to invoke based on user message and context.
    
    For Phase 3, this returns a simple heuristic-based tool plan.
    In later phases, this could use Claude's tool use capabilities.
    
    Args:
        user_message: User's query
        context: Assembled context
        mode: Performance mode
        
    Returns:
        List of tool invocations to execute
    """
    tool_plan = []
    
    # Check if web search might be helpful
    if settings.ENABLE_WEB_SEARCH and settings.TAVILY_API_KEY:
        # Simple heuristics for when to use web search
        keywords = ["what is", "define", "explain", "meaning of", "calculate", "metric"]
        
        user_lower = user_message.lower()
        if any(keyword in user_lower for keyword in keywords):
            # Extract terms that might need definition
            # This is a simple implementation - could be enhanced
            tool_plan.append({
                "tool": "web_search",
                "query": user_message,
                "reason": "Query contains terms that may need clarification"
            })
            
            logger.debug("Planned web search tool", query=user_message[:50])
    
    # Mode-specific tool call limits
    max_tools = {
        PerformanceMode.VALTRYEK: 1,
        PerformanceMode.ACHILLIES: 3,
        PerformanceMode.SPRYZEN: 10
    }[mode]
    
    return tool_plan[:max_tools]


async def execute_tools(
    tool_plan: List[Dict[str, Any]],
    client: AsyncAnthropic
) -> Tuple[Dict[str, Any], List[ToolEvent]]:
    """
    Execute planned tools.
    
    Args:
        tool_plan: List of tool invocations
        client: Anthropic client (for future tool use)
        
    Returns:
        Tuple of (tool_results, tool_events)
    """
    tool_results = {}
    tool_events = []
    
    for tool_call in tool_plan:
        tool_name = tool_call["tool"]
        
        if tool_name == "web_search":
            logger.info("Executing web search", query=tool_call["query"])
            start_time = time.time()
            
            # Execute web search
            result = await search_web(tool_call["query"])
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Store results
            tool_results["web_search"] = result
            
            # Create tool event
            event = ToolEvent(
                id=str(uuid.uuid4()),
                tool="web_search",
                label=f"Searched: {tool_call['query'][:50]}...",
                icon="🔍",
                input={"query": tool_call["query"]},
                output={"result_count": len(result.get("results", []))},
                duration_ms=duration_ms,
                timestamp=datetime.utcnow()
            )
            
            tool_events.append(event)
            
            logger.debug("Web search completed", 
                        result_count=len(result.get("results", [])),
                        duration_ms=duration_ms)
    
    return tool_results, tool_events


async def execute_tools_with_claude(
    user_message: str,
    context: Context,
    mode: PerformanceMode,
    client: AsyncAnthropic,
    model: str
) -> Tuple[Dict[str, Any], List[ToolEvent]]:
    """
    Execute tools using Claude's native tool use capability.
    
    This is a more advanced version that lets Claude decide which tools to use.
    
    Args:
        user_message: User's query
        context: Assembled context
        mode: Performance mode
        client: Anthropic client
        model: Model name
        
    Returns:
        Tuple of (tool_results, tool_events)
    """
    if not settings.ENABLE_WEB_SEARCH or not settings.TAVILY_API_KEY:
        return {}, []
    
    logger.info("Using Claude tool use for tool planning")
    
    tool_results = {}
    tool_events = []
    
    try:
        # Build prompt for tool planning
        schema_summary = f"Available tables: {', '.join(context.tables)}"
        
        system = f"""You are helping generate a SQL query. You have access to a web search tool.
        
Database schema: {schema_summary}

Only use web_search if the user's question references terms, metrics, or concepts that are NOT in the database schema and require external knowledge to understand."""

        # Call Claude with tools
        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            tools=[WEB_SEARCH_TOOL],
            messages=[
                {"role": "user", "content": f"User question: {user_message}\n\nDo you need to search for any external information to help answer this?"}
            ]
        )
        
        # Process tool uses
        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input
                
                if tool_name == "web_search":
                    logger.info("Claude requested web search", query=tool_input.get("query"))
                    start_time = time.time()
                    
                    result = await search_web(tool_input["query"])
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    tool_results["web_search"] = result
                    
                    event = ToolEvent(
                        id=str(uuid.uuid4()),
                        tool="web_search",
                        label=f"Searched: {tool_input['query'][:50]}",
                        icon="🔍",
                        input=tool_input,
                        output={"result_count": len(result.get("results", []))},
                        duration_ms=duration_ms,
                        timestamp=datetime.utcnow()
                    )
                    
                    tool_events.append(event)
        
    except Exception as e:
        logger.error("Claude tool use failed", error=str(e))
    
    return tool_results, tool_events
