"""
Application configuration using Pydantic Settings.
Loads environment variables and provides type-safe configuration.
"""

from typing import List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
import os
from pathlib import Path

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Environment
    environment: str = Field(default="development", description="Current environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # API Configuration
    api_title: str = Field(default="Freelancer Management System")
    api_version: str = Field(default="1.0.0")
    api_prefix: str = Field(default="/api/v1")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    # Supabase Configuration
    supabase_url: str = Field(default="https://example.supabase.co", description="Supabase project URL")
    supabase_anon_key: str = Field(default="temp-key", description="Supabase anonymous key")
    supabase_service_key: str = Field(default="temp-key", description="Supabase service role key")
    
    # Database (for direct connection if needed)
    database_url: Optional[str] = Field(default=None, description="Direct database URL")
    
    # JWT Configuration
    jwt_secret_key: str = Field(default="development-secret-key-change-in-production", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)
    jwt_refresh_token_expire_days: int = Field(default=7)
    
    # CORS
    cors_origins: str | List[str] = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:8081"
    )
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(default=["*"])
    cors_allow_headers: List[str] = Field(default=["*"])
    
    # Pagination
    default_page_size: int = Field(default=20)
    max_page_size: int = Field(default=100)
    
    # File Upload
    max_upload_size_mb: int = Field(default=10)
    allowed_upload_extensions: str | List[str] = Field(
        default=".pdf,.png,.jpg,.jpeg,.doc,.docx"
    )
    
    # PDF Generation
    pdf_storage_bucket: str = Field(default="invoices")
    pdf_base_url: str = Field(default="")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100)
    rate_limit_period: int = Field(default=60)  # seconds
    
    # Sentry (Optional)
    sentry_dsn: Optional[str] = Field(default=None)
    sentry_traces_sample_rate: float = Field(default=0.1)
    
    # Email Configuration (for future use)
    smtp_host: Optional[str] = Field(default=None)
    smtp_port: int = Field(default=587)
    smtp_user: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    email_from_name: str = Field(default="Freelancer System")
    email_from_address: str = Field(default="noreply@example.com")
    
    # Localization
    timezone: str = Field(default="America/Santiago")
    default_currency: str = Field(default="USD")
    default_locale: str = Field(default="es-CL")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            # Si es una cadena vacía, devolver lista con valores por defecto
            if not v or v.strip() == "":
                return ["http://localhost:3000", "http://localhost:5173", "http://localhost:8081"]
            # Si es una cadena con comas, dividir
            return [origin.strip() for origin in v.split(",")]
        elif v is None:
            return ["http://localhost:3000", "http://localhost:5173", "http://localhost:8081"]
        return v
    
    @validator("allowed_upload_extensions", pre=True)
    def parse_upload_extensions(cls, v):
        """Parse upload extensions from comma-separated string or list."""
        if isinstance(v, str):
            if not v or v.strip() == "":
                return [".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"]
            return [ext.strip() for ext in v.split(",")]
        elif v is None:
            return [".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"]
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment.lower() == "testing"
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024
    
    @property
    def database_url_async(self) -> Optional[str]:
        """Get async database URL for SQLAlchemy."""
        if self.database_url:
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return None
    
    def get_supabase_headers(self) -> dict:
        """Get headers for Supabase requests."""
        return {
            "apikey": self.supabase_anon_key,
            "Authorization": f"Bearer {self.supabase_anon_key}"
        }
    
    def validate_environment(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            "supabase_url",
            "supabase_anon_key",
            "supabase_service_key",
            "jwt_secret_key"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(self, var, None):
                missing_vars.append(var.upper())
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use this function to get settings throughout the application.
    """
    settings = Settings()
    
    # Validate environment in production
    if settings.is_production:
        settings.validate_environment()
    
    return settings


# Create a global settings instance
settings = get_settings()

# Validate on module import if in production
if settings.is_production:
    settings.validate_environment()