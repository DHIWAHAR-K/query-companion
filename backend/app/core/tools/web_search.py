"""Web search tool using Tavily API"""
import httpx
import structlog
from typing import List, Dict, Any
import time

from app.config import settings

logger = structlog.get_logger()


async def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using Tavily API.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        Dict with search results
    """
    if not settings.ENABLE_WEB_SEARCH or not settings.TAVILY_API_KEY:
        logger.warning("Web search disabled or API key not configured")
        return {
            "results": [],
            "message": "Web search is disabled"
        }
    
    logger.info("Performing web search", query=query)
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": True,
                    "include_raw_content": False
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info("Web search completed", 
                       result_count=len(data.get("results", [])),
                       duration_ms=duration_ms)
            
            return {
                "results": data.get("results", []),
                "answer": data.get("answer"),
                "duration_ms": duration_ms
            }
            
    except httpx.HTTPStatusError as e:
        logger.error("Web search API error", status_code=e.response.status_code, error=str(e))
        return {
            "results": [],
            "error": f"Search API error: {e.response.status_code}"
        }
    except Exception as e:
        logger.error("Web search failed", error=str(e))
        return {
            "results": [],
            "error": str(e)
        }


# Tool definition for Claude function calling
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for information about unknown terms, external data, or context that may help generate accurate SQL queries. Use this when the user's question references concepts, metrics, or data sources not found in the database schema.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up"
            },
            "reason": {
                "type": "string",
                "description": "Brief explanation of why this search is needed"
            }
        },
        "required": ["query", "reason"]
    }
}
