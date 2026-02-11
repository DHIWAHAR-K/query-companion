"""Application configuration using Pydantic Settings"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache
from pydantic import computed_field, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENCRYPTION_KEY: str

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str
    SCHEMA_CACHE_TTL: int = 3600  # 1 hour

    # LLM Provider Selection
    LLM_PROVIDER: str = "google"  # "anthropic" or "google"

    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str | None = None
    VALTRYEK_MODEL: str = "claude-haiku-3-5-20241022"
    ACHILLIES_MODEL: str = "claude-sonnet-4-20250514"
    SPRYZEN_MODEL: str = "claude-opus-4-5-20251101"

    # Google (Gemini)
    GOOGLE_API_KEY: str | None = None
    GOOGLE_VALTRYEK_MODEL: str = "gemini-1.5-flash"
    GOOGLE_ACHILLIES_MODEL: str = "gemini-1.5-pro"
    GOOGLE_SPRYZEN_MODEL: str = "gemini-1.5-pro"

    # Tools
    ENABLE_WEB_SEARCH: bool = True
    TAVILY_API_KEY: str | None = None
    ENABLE_VISION: bool = True

    # Query Execution
    MAX_CONCURRENT_QUERIES: int = 10
    DEFAULT_QUERY_TIMEOUT: int = 300
    MAX_RESULT_ROWS: int = 10000

    # CORS: env holds comma-separated string so pydantic-settings won't try to JSON-decode it
    cors_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        validation_alias="CORS_ORIGINS",
    )

    @computed_field
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parsed CORS origins list from comma-separated env value."""
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
