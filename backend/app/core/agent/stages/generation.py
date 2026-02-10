"""Stage 5: SQL Generation"""
from anthropic import AsyncAnthropic
import structlog
from typing import Dict, Any

from app.models.domain import (
    Context, SQLArtifact, SQLDialect, PerformanceMode
)
from app.config import settings

logger = structlog.get_logger()


def _build_system_prompt(dialect: SQLDialect, mode: PerformanceMode) -> str:
    """Build system prompt for SQL generation"""
    
    mode_instructions = {
        PerformanceMode.VALTRYEK: "Always add LIMIT 100 to SELECT queries for safety.",
        PerformanceMode.ACHILLIES: "Add LIMIT 1000 unless user specifies otherwise.",
        PerformanceMode.SPRYZEN: "No automatic limits - follow user's intent precisely."
    }
    
    return f"""You are an expert SQL query generator for {dialect.value} databases.

Your task is to convert natural language questions into accurate, efficient SQL queries.

Guidelines:
- Generate syntactically correct {dialect.value} SQL
- Use proper table and column names from the provided schema
- Include appropriate JOINs when querying multiple tables
- Add WHERE clauses for filtering when needed
- Use aggregate functions (COUNT, SUM, AVG) when appropriate
- {mode_instructions[mode]}
- Always format queries with proper indentation
- Explain your reasoning briefly

Return your response in this exact format:
SQL:
```sql
[your SQL query here]
```

EXPLANATION:
[Brief explanation of what the query does and why you structured it this way]

ASSUMPTIONS:
- [Any assumptions you made about the data or user intent]
"""


def _build_user_prompt(user_message: str, context: Context, image_context: Any = None) -> str:
    """Build user prompt with schema context"""
    
    # Format schema information
    schema_text = "Available tables:\n\n"
    for table in context.schema.tables:
        schema_text += f"Table: {table['name']}\n"
        schema_text += "Columns:\n"
        for col in table['columns']:
            nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
            pk = " (PRIMARY KEY)" if col.get('primary_key', False) else ""
            schema_text += f"  - {col['name']}: {col['type']} {nullable}{pk}\n"
        schema_text += "\n"
    
    # Add relationships if any
    if context.schema.relationships:
        schema_text += "Relationships:\n"
        for rel in context.schema.relationships:
            schema_text += f"  - {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']} ({rel['type']})\n"
        schema_text += "\n"
    
    # Add image context if available
    image_info = ""
    if image_context:
        image_info = "\n\nInformation extracted from attached image:\n"
        if image_context.entities:
            image_info += f"Tables/Entities mentioned: {', '.join(image_context.entities)}\n"
        if image_context.relationships:
            image_info += "Relationships:\n"
            for rel in image_context.relationships:
                image_info += f"  - {rel.get('description', '')}\n"
        if image_context.metrics:
            image_info += "Metrics/Calculations:\n"
            for metric in image_context.metrics:
                image_info += f"  - {metric.get('name', '')}: {metric.get('calculation', '')}\n"
        image_info += "\n"
    
    return f"""{schema_text}{image_info}

User question: {user_message}

Generate an appropriate SQL query to answer this question."""


async def generate_sql(
    user_message: str,
    context: Context,
    tool_results: Dict[str, Any],
    dialect: SQLDialect,
    mode: PerformanceMode,
    client: AsyncAnthropic,
    model: str,
    image_context: Any = None
) -> SQLArtifact:
    """
    Generate SQL query using Claude API.
    
    Args:
        user_message: User's natural language query
        context: Assembled context with schema
        tool_results: Results from tool execution (empty for MVP)
        dialect: Target SQL dialect
        mode: Performance mode
        client: Anthropic API client
        model: Model name to use
        
    Returns:
        SQLArtifact with generated query and metadata
    """
    logger.info("Generating SQL", mode=mode.value, model=model)
    
    system_prompt = _build_system_prompt(dialect, mode)
    user_prompt = _build_user_prompt(user_message, context, image_context)
    
    try:
        # Call Claude API
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Parse response
        content = response.content[0].text
        
        # Extract SQL query
        sql_query = ""
        if "```sql" in content:
            start = content.find("```sql") + 6
            end = content.find("```", start)
            sql_query = content[start:end].strip()
        elif "SQL:" in content:
            # Fallback parsing
            start = content.find("SQL:") + 4
            end = content.find("EXPLANATION:", start) if "EXPLANATION:" in content else len(content)
            sql_query = content[start:end].strip().replace("```", "").replace("sql", "").strip()
        
        # Extract explanation
        explanation = ""
        if "EXPLANATION:" in content:
            start = content.find("EXPLANATION:") + 12
            end = content.find("ASSUMPTIONS:", start) if "ASSUMPTIONS:" in content else len(content)
            explanation = content[start:end].strip()
        
        # Extract assumptions
        assumptions = []
        if "ASSUMPTIONS:" in content:
            start = content.find("ASSUMPTIONS:") + 12
            assumptions_text = content[start:].strip()
            # Parse bullet points
            for line in assumptions_text.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("•"):
                    assumptions.append(line[1:].strip())
        
        logger.info("SQL generated successfully", length=len(sql_query))
        
        return SQLArtifact(
            query=sql_query,
            dialect=dialect,
            explanation=explanation or "Query generated successfully.",
            assumptions=assumptions,
            confidence=0.9
        )
        
    except Exception as e:
        logger.error("SQL generation failed", error=str(e))
        raise
