"""Vision tool for extracting SQL context from images"""
import structlog
from typing import List, Dict, Any
import base64

from app.config import settings

logger = structlog.get_logger()


class ImageContext:
    """Extracted context from image"""
    def __init__(
        self,
        entities: List[str] = None,
        metrics: List[Dict[str, Any]] = None,
        relationships: List[Dict[str, Any]] = None,
        filters: List[Dict[str, Any]] = None,
        diagram_type: str = "unknown",
        raw_description: str = ""
    ):
        self.entities = entities or []
        self.metrics = metrics or []
        self.relationships = relationships or []
        self.filters = filters or []
        self.diagram_type = diagram_type
        self.raw_description = raw_description


async def extract_from_images(
    images: List[bytes],
    client  # LLMService
) -> ImageContext:
    """
    Extract SQL-relevant context from images using Claude vision.
    
    Supports:
    - ER diagrams
    - Table screenshots
    - Dashboard/report images
    - Handwritten notes
    
    Args:
        images: List of image data (bytes)
        client: Anthropic API client
        
    Returns:
        ImageContext with extracted entities, relationships, etc.
    """
    if not settings.ENABLE_VISION:
        logger.warning("Vision is disabled")
        return ImageContext()
    
    logger.info("Extracting context from images", image_count=len(images))
    
    try:
        # Build prompt for extraction
        prompt = """Analyze this image and extract SQL-relevant information.

Look for:
1. **Tables/Entities**: Names of database tables or entities
2. **Columns/Fields**: Column names and their data types
3. **Relationships**: Foreign key relationships, JOIN conditions
4. **Metrics/Calculations**: Aggregations, formulas, calculated fields
5. **Filters/Conditions**: WHERE clauses, date ranges, filters
6. **Diagram Type**: Is this an ER diagram, table screenshot, dashboard, or notes?

Return your analysis in this format:

DIAGRAM_TYPE: [er_diagram|table_screenshot|dashboard|notes]

ENTITIES:
- [table/entity name 1]
- [table/entity name 2]

COLUMNS:
- [table.column: data_type]

RELATIONSHIPS:
- [table1.column -> table2.column (type)]

METRICS:
- [metric name: calculation/aggregation]

FILTERS:
- [filter description]

DESCRIPTION:
[Brief description of what you see]
"""
        
        # Use first image for simplicity (could process multiple)
        image_data = images[0]
        
        # Call LLM vision API
        model = client.get_model_name("achillies")  # Use balanced model for vision
        content = await client.extract_from_image(
            image_data=image_data,
            prompt=prompt,
            model=model
        )
        logger.debug("Vision response received", length=len(content))
        
        # Extract structured data from response
        entities = []
        metrics = []
        relationships = []
        filters = []
        diagram_type = "unknown"
        raw_description = content
        
        # Parse DIAGRAM_TYPE
        if "DIAGRAM_TYPE:" in content:
            type_line = content.split("DIAGRAM_TYPE:")[1].split("\n")[0].strip()
            diagram_type = type_line.lower()
        
        # Parse ENTITIES
        if "ENTITIES:" in content:
            entities_section = content.split("ENTITIES:")[1].split("\n\n")[0]
            for line in entities_section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    entity = line[1:].strip()
                    if entity:
                        entities.append(entity)
        
        # Parse RELATIONSHIPS
        if "RELATIONSHIPS:" in content:
            rel_section = content.split("RELATIONSHIPS:")[1].split("\n\n")[0]
            for line in rel_section.split("\n"):
                line = line.strip()
                if line.startswith("-") and "->" in line:
                    relationships.append({"description": line[1:].strip()})
        
        # Parse METRICS
        if "METRICS:" in content:
            metrics_section = content.split("METRICS:")[1].split("\n\n")[0]
            for line in metrics_section.split("\n"):
                line = line.strip()
                if line.startswith("-") and ":" in line:
                    parts = line[1:].split(":", 1)
                    if len(parts) == 2:
                        metrics.append({
                            "name": parts[0].strip(),
                            "calculation": parts[1].strip()
                        })
        
        # Parse FILTERS
        if "FILTERS:" in content:
            filters_section = content.split("FILTERS:")[1].split("\n\n")[0]
            for line in filters_section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    filters.append({"description": line[1:].strip()})
        
        image_context = ImageContext(
            entities=entities,
            metrics=metrics,
            relationships=relationships,
            filters=filters,
            diagram_type=diagram_type,
            raw_description=raw_description
        )
        
        logger.info(
            "Image context extracted",
            entities=len(entities),
            relationships=len(relationships),
            metrics=len(metrics),
            diagram_type=diagram_type
        )
        
        return image_context
        
    except Exception as e:
        logger.error("Image extraction failed", error=str(e))
        return ImageContext(raw_description=f"Error: {str(e)}")
