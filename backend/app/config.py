"""
Configuration management for InsightAgent.
Uses Vertex AI Gemini API with Application Default Credentials (ADC).
No API keys needed - all access via IAM service account roles.
"""

import os
from functools import lru_cache
from typing import Optional

import google.auth
import vertexai
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # GCP Project
    gcp_project_id: str = ""
    vertex_location: str = "us-central1"

    # BigQuery
    bq_dataset_id: str = "insightagent_data"

    # Firestore
    firestore_collection_prefix: str = "insightagent"

    # Vertex AI
    gemini_model: str = "gemini-2.5-flash"
    rag_corpus_name: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    # Security
    demo_api_key: str = ""
    allowed_cors_origin: str = "http://localhost:5173"

    # Environment
    environment: str = "development"

    # Query limits
    max_query_bytes: int = 10_000_000_000  # 10GB max bytes processed
    query_timeout_seconds: int = 30
    max_result_rows: int = 1000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def init_vertex_ai() -> tuple[str, str]:
    """
    Initialize Vertex AI with Application Default Credentials.

    For local development: run `gcloud auth application-default login` once
    For Cloud Run: automatically uses the attached service account

    Returns:
        Tuple of (project_id, location)
    """
    settings = get_settings()

    # Get credentials via ADC
    credentials, project = google.auth.default()

    # Use project from settings if specified, otherwise use ADC project
    project_id = settings.gcp_project_id or project

    if not project_id:
        raise ValueError(
            "GCP project ID not found. Either set GCP_PROJECT_ID env var "
            "or configure gcloud with a default project."
        )

    # Initialize Vertex AI
    vertexai.init(
        project=project_id,
        location=settings.vertex_location,
        credentials=credentials
    )

    return project_id, settings.vertex_location


def get_bigquery_dataset() -> str:
    """Get fully qualified BigQuery dataset ID."""
    settings = get_settings()
    project_id = settings.gcp_project_id
    if not project_id:
        credentials, project_id = google.auth.default()
    return f"{project_id}.{settings.bq_dataset_id}"


def is_production() -> bool:
    """Check if running in production environment."""
    return get_settings().environment == "production"
