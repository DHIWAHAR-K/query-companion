"""Schema introspection endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_db
from app.models.database import User
from app.models.schemas import SchemaTreeResponse, SampleDataRequest, SampleDataResponse
from app.api.dependencies import get_current_user
from app.services.connection_service import get_connection
from app.services.schema_service import get_cached_schema, invalidate_schema_cache, fetch_sample_data

router = APIRouter(prefix="/schema")
logger = structlog.get_logger()


@router.get("/{connection_id}/tree", response_model=SchemaTreeResponse)
async def get_schema_tree(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get database schema tree for a connection"""
    logger.info("Getting schema tree", connection_id=connection_id, user_id=current_user.id)
    
    # Get connection
    connection = await get_connection(connection_id, current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    try:
        # Get cached schema
        schema = await get_cached_schema(connection_id, connection)
        
        # Group tables by schema
        schemas_dict = {}
        for table in schema.tables:
            schema_name = table.get("schema", "default")
            if schema_name not in schemas_dict:
                schemas_dict[schema_name] = {
                    "name": schema_name,
                    "tables": []
                }
            
            schemas_dict[schema_name]["tables"].append({
                "name": table["name"],
                "row_count": table.get("row_count"),
                "columns": table["columns"]
            })
        
        return SchemaTreeResponse(
            schemas=list(schemas_dict.values()),
            relationships=schema.relationships
        )
        
    except Exception as e:
        logger.error("Failed to get schema tree", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve schema: {str(e)}"
        )


@router.post("/{connection_id}/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def refresh_schema(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refresh cached schema for a connection"""
    logger.info("Refreshing schema", connection_id=connection_id)
    
    # Get connection
    connection = await get_connection(connection_id, current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Invalidate cache
    await invalidate_schema_cache(connection_id)
    logger.info("Schema cache invalidated", connection_id=connection_id)


@router.post("/{connection_id}/sample", response_model=SampleDataResponse)
async def get_sample_data(
    connection_id: str,
    request: SampleDataRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get sample data from a table (first N rows, df.head-style)."""
    logger.info(
        "Getting sample data",
        connection_id=connection_id,
        table=request.table,
        schema=request.schema_name,
    )
    connection = await get_connection(connection_id, current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    try:
        data = fetch_sample_data(
            connection=connection,
            table_name=request.table,
            schema_name=request.schema_name,
            limit=request.limit,
        )
        return SampleDataResponse(
            columns=data["columns"],
            rows=data["rows"],
            total_rows=data["total_rows"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Sample data fetch failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sample: {str(e)}"
        )
