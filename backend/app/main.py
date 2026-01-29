"""
InsightAgent FastAPI Application Entry Point.

This is the main entry point for the InsightAgent backend API.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings, init_vertex_ai
from app.api.routes import router as api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("insightagent")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses with timing."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"(client: {request.client.host if request.client else 'unknown'})"
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response (don't log SSE streaming responses as they're long-lived)
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("text/event-stream"):
            logger.info(
                f"[{request_id}] {response.status_code} ({duration_ms:.1f}ms)"
            )
        else:
            logger.info(
                f"[{request_id}] SSE stream started ({duration_ms:.1f}ms to first byte)"
            )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    settings = get_settings()

    # Initialize Vertex AI
    try:
        project_id, location = init_vertex_ai()
        logger.info(f"Initialized Vertex AI: project={project_id}, location={location}")
    except Exception as e:
        logger.warning(f"Could not initialize Vertex AI: {e}")

    logger.info("InsightAgent API started")
    yield

    # Shutdown
    logger.info("Shutting down InsightAgent...")


# Create FastAPI application
app = FastAPI(
    title="InsightAgent API",
    description="AI-powered Business Intelligence Agent using Google ADK",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
allowed_origins = [settings.allowed_cors_origin]

# In development, also allow localhost variations
if settings.environment == "development":
    allowed_origins.extend([
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "service": "insightagent"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "InsightAgent API",
        "version": "1.0.0",
        "docs": "/docs",
    }
