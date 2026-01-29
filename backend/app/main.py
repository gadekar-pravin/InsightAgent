"""
InsightAgent FastAPI Application Entry Point.

This is the main entry point for the InsightAgent backend API.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Security, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from app.config import get_settings, init_vertex_ai
from app.api.routes import router as api_router


# API Key authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Verify the API key for demo authentication."""
    settings = get_settings()

    # Skip auth in development if no key is set
    if settings.environment == "development" and not settings.demo_api_key:
        return "dev-mode"

    if not api_key or api_key != settings.demo_api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    settings = get_settings()

    # Initialize Vertex AI
    try:
        project_id, location = init_vertex_ai()
        print(f"Initialized Vertex AI: project={project_id}, location={location}")
    except Exception as e:
        print(f"Warning: Could not initialize Vertex AI: {e}")

    yield

    # Shutdown
    print("Shutting down InsightAgent...")


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
