"""
Authentication utilities for InsightAgent API.

Separated to avoid circular imports between main.py and routes.py.
"""

from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

from app.config import get_settings


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
