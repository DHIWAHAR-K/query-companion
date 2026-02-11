"""FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
import structlog

from app.config import settings
from app.utils.logging import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Queryus API", version=settings.VERSION)
    
    # Initialize PostgreSQL connection pool
    from app.db.session import engine
    async with engine.begin() as conn:
        logger.info("PostgreSQL connection established")
    
    # Test Redis connection
    from app.db.cache import redis_client
    await redis_client.ping()
    logger.info("Redis connected")
    
    # Connect to MongoDB
    from app.db.mongo import mongo_db
    await mongo_db.connect()
    logger.info("MongoDB connected")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Queryus API")
    await engine.dispose()
    await redis_client.close()
    await mongo_db.close()


app = FastAPI(
    title="Queryus API",
    description="Conversational SQL Assistant with AI-powered query generation",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
from app.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")

# Setup Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_config=None  # Use structlog instead
    )
