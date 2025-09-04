"""
Main FastAPI application entry point.
Configures the app, middleware, routers, and startup/shutdown events.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

# Importación opcional de Sentry
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    logging.warning("Sentry SDK not installed. Sentry monitoring will be disabled.")

from app.config import settings
from app.infrastructure.web.middleware.error_handler import ErrorHandlerMiddleware
from app.infrastructure.web.middleware.auth_middleware import AuthenticationMiddleware
from app.infrastructure.web.routers import (
    auth,
    clients,
    # projects,
    # tasks,
    # time_entries,
    # invoices,
    # shares,
    # templates,
    # uploads,
    # storage_admin,
    # notifications
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    Setup and teardown operations.
    """
    # Startup
    logger.info(f"Starting {settings.api_title} v{settings.api_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Initialize Sentry if configured and available
    if SENTRY_AVAILABLE and settings.sentry_dsn and not settings.is_development:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            environment=settings.environment,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
        )
        logger.info("Sentry initialized")
    elif settings.sentry_dsn and not SENTRY_AVAILABLE:
        logger.warning("Sentry DSN configured but Sentry SDK not installed")
    
    # Initialize event system for notifications
    try:
        from app.infrastructure.events.event_setup import initialize_event_system
        initialize_event_system()
        logger.info("Event system initialized")
    except Exception as e:
        logger.error(f"Failed to initialize event system: {str(e)}")
    
    # Here you can add database connection pool initialization
    # supabase client initialization, etc.
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    # Here you can add cleanup operations
    # Close database connections, etc.


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        debug=settings.debug,
        docs_url=f"{settings.api_prefix}/docs" if settings.debug else None,
        redoc_url=f"{settings.api_prefix}/redoc" if settings.debug else None,
        openapi_url=f"{settings.api_prefix}/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Add trusted host middleware for production
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure with your domain
        )
    
    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware)
    
    # Add custom error handler middleware
    app.add_middleware(ErrorHandlerMiddleware)
    
    # Include routers
    app.include_router(
        auth.router,
        prefix=f"{settings.api_prefix}/auth",
        tags=["Authentication"]
    )
    app.include_router(
        clients.router,
        prefix=f"{settings.api_prefix}/clients",
        tags=["Clients"]
    )
    # app.include_router(
    #     projects.router,
    #     prefix=f"{settings.api_prefix}/projects",
    #     tags=["Projects"]
    # )
    # app.include_router(
    #     tasks.router,
    #     prefix=f"{settings.api_prefix}/tasks",
    #     tags=["Tasks"]
    # )
    # app.include_router(
    #     time_entries.router,
    #     prefix=f"{settings.api_prefix}/time-entries",
    #     tags=["Time Tracking"]
    # )
    # app.include_router(
    #     invoices.router,
    #     prefix=f"{settings.api_prefix}/invoices",
    #     tags=["Invoices"]
    # )
    # app.include_router(
    #     shares.router,
    #     prefix=f"{settings.api_prefix}/shares",
    #     tags=["Sharing"]
    # )
    # app.include_router(
    #     templates.router,
    #     prefix=f"{settings.api_prefix}/templates",
    #     tags=["Templates & PDFs"]
    # )
    # app.include_router(
    #     uploads.router,
    #     prefix=f"{settings.api_prefix}/uploads",
    #     tags=["File Uploads"]
    # )
    # app.include_router(
    #     storage_admin.router,
    #     prefix=f"{settings.api_prefix}/storage",
    #     tags=["Storage Management"]
    # )
    # app.include_router(
    #     notifications.router,
    #     prefix=f"{settings.api_prefix}/notifications",
    #     tags=["Notifications & Events"]
    # )
    
    # Root endpoint
    @app.get("/")
    async def root() -> Dict[str, Any]:
        """Root endpoint with API information."""
        return {
            "name": settings.api_title,
            "version": settings.api_version,
            "environment": settings.environment,
            "docs": f"{settings.api_prefix}/docs" if settings.debug else None,
            "health": f"{settings.api_prefix}/health"
        }
    
    # Health check endpoint
    @app.get(f"{settings.api_prefix}/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "environment": settings.environment,
            "version": settings.api_version
        }
    
    # Custom 404 handler
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Custom 404 error handler."""
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "message": f"The path {request.url.path} was not found",
                "path": request.url.path
            }
        )
    
    return app


# Create the FastAPI app instance
app = create_application()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level="debug" if settings.debug else "info",
    )