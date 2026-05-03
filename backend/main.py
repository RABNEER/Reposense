"""
RepoSense Backend API
FastAPI application for repository analysis powered by IBM Bob
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from backend.config import Config
from backend.routers import analyze, ask, task, export

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info(
        "application_startup",
        environment=Config.ENVIRONMENT,
        mock_mode=Config.is_mock_mode(),
        cors_origins=Config.CORS_ORIGINS
    )
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")


# Create FastAPI application
app = FastAPI(
    title="RepoSense API",
    description="AI-powered repository onboarding powered by IBM Bob",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analyze.router)
app.include_router(ask.router)
app.include_router(task.router)
app.include_router(export.router)


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": "RepoSense API",
        "version": "1.0.0",
        "description": "AI-powered repository onboarding powered by IBM Bob",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "analyze": "POST /api/v1/analyze",
            "ask": "POST /api/v1/ask",
            "task": "POST /api/v1/task",
            "export_markdown": "POST /api/v1/export/markdown",
            "export_json": "POST /api/v1/export/json"
        }
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint
    Returns service status and configuration
    """
    return {
        "status": "healthy",
        "environment": Config.ENVIRONMENT,
        "mock_mode": Config.is_mock_mode(),
        "version": "1.0.0"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors
    """
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if Config.ENVIRONMENT == "development" else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=Config.ENVIRONMENT == "development",
        log_level="info"
    )

# Made with Bob
