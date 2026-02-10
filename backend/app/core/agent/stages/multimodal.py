"""Stage 3: Multimodal Ingestion"""
from typing import List, Optional
import structlog
from anthropic import AsyncAnthropic

from app.core.tools.vision import extract_from_images, ImageContext

logger = structlog.get_logger()


async def process_attachments(
    attachments: Optional[List[bytes]],
    client: AsyncAnthropic
) -> Optional[ImageContext]:
    """
    Process image attachments to extract SQL-relevant context.
    
    Args:
        attachments: List of image data
        client: Anthropic API client
        
    Returns:
        ImageContext if images provided, None otherwise
    """
    if not attachments:
        return None
    
    logger.info("Processing attachments", count=len(attachments))
    
    # Extract context from images
    image_context = await extract_from_images(attachments, client)
    
    logger.debug(
        "Attachment processing complete",
        entities=len(image_context.entities),
        diagram_type=image_context.diagram_type
    )
    
    return image_context
