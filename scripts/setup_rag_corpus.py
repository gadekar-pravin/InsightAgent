#!/usr/bin/env python3
"""
Set up Vertex AI RAG Engine corpus for InsightAgent.

This script:
1. Creates a RAG corpus in Vertex AI
2. Imports knowledge base documents
3. Verifies the corpus is ready for queries

Usage:
    python scripts/setup_rag_corpus.py
"""

import os
import sys
import time
from pathlib import Path

from google.cloud import storage
from vertexai import rag
import vertexai

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "insightagent-adk")
LOCATION = os.getenv("VERTEX_LOCATION", "asia-south1")
CORPUS_DISPLAY_NAME = "insightagent-knowledge-base"
BUCKET_NAME = f"{PROJECT_ID}-rag-docs"

# Paths
SCRIPT_DIR = Path(__file__).parent
KNOWLEDGE_BASE_DIR = SCRIPT_DIR.parent / "knowledge_base"


def init_vertexai():
    """Initialize Vertex AI."""
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    print(f"Initialized Vertex AI: project={PROJECT_ID}, location={LOCATION}")


def upload_to_gcs(bucket_name: str, source_dir: Path) -> list[str]:
    """Upload knowledge base files to GCS bucket."""
    storage_client = storage.Client(project=PROJECT_ID)

    # Create bucket if it doesn't exist
    try:
        bucket = storage_client.get_bucket(bucket_name)
        print(f"Using existing bucket: {bucket_name}")
    except Exception:
        bucket = storage_client.create_bucket(bucket_name, location=LOCATION)
        print(f"Created bucket: {bucket_name}")

    # Upload files
    gcs_paths = []
    for file_path in source_dir.glob("*.md"):
        blob_name = f"knowledge_base/{file_path.name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(file_path))
        gcs_path = f"gs://{bucket_name}/{blob_name}"
        gcs_paths.append(gcs_path)
        print(f"  Uploaded: {file_path.name} -> {gcs_path}")

    return gcs_paths


def get_existing_corpus() -> rag.RagCorpus | None:
    """Check if corpus already exists."""
    try:
        corpora = list(rag.list_corpora())
        for corpus in corpora:
            if corpus.display_name == CORPUS_DISPLAY_NAME:
                return corpus
    except Exception as e:
        print(f"Error listing corpora: {e}")
    return None


def create_corpus() -> rag.RagCorpus:
    """Create a new RAG corpus."""
    # Check if corpus already exists
    existing = get_existing_corpus()
    if existing:
        print(f"Using existing corpus: {existing.name}")
        return existing

    # Create new corpus
    corpus = rag.create_corpus(
        display_name=CORPUS_DISPLAY_NAME,
        description="Company knowledge base for InsightAgent - contains metrics definitions, targets, strategy documents, and policies."
    )
    print(f"Created corpus: {corpus.name}")
    return corpus


def import_documents(corpus: rag.RagCorpus, gcs_paths: list[str]) -> None:
    """Import documents into the RAG corpus."""
    print(f"\nImporting {len(gcs_paths)} documents into corpus...")

    # Import files with chunking configuration
    # Note: Using folder path instead of individual files
    gcs_folder = f"gs://{BUCKET_NAME}/knowledge_base/"

    response = rag.import_files(
        corpus_name=corpus.name,
        paths=[gcs_folder],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(
                chunk_size=512,  # 512 tokens per chunk
                chunk_overlap=50  # 50 token overlap
            )
        )
    )

    print(f"Import completed: {response}")


def verify_corpus(corpus: rag.RagCorpus) -> bool:
    """Verify the corpus is ready and can answer queries."""
    print("\nVerifying corpus...")

    # Wait a bit for indexing
    print("  Waiting for indexing to complete...")
    time.sleep(5)

    # Test query
    test_queries = [
        "What is the company's churn rate target?",
        "What are the Q4 2024 revenue targets by region?",
        "What is CompetitorX doing in the West region?",
    ]

    all_passed = True
    for query in test_queries:
        try:
            response = rag.retrieval_query(
                rag_resources=[rag.RagResource(rag_corpus=corpus.name)],
                text=query,
                rag_retrieval_config=rag.RagRetrievalConfig(
                    top_k=3,
                    filter=rag.Filter(vector_distance_threshold=0.7)
                )
            )

            # Check if we got results
            if response.contexts and response.contexts.contexts:
                num_results = len(response.contexts.contexts)
                print(f"  ✓ Query: '{query[:50]}...' -> {num_results} results")
            else:
                print(f"  ✗ Query: '{query[:50]}...' -> No results")
                all_passed = False

        except Exception as e:
            print(f"  ✗ Query failed: {e}")
            all_passed = False

    return all_passed


def save_corpus_name(corpus: rag.RagCorpus) -> None:
    """Save the corpus name to .env file for later use."""
    env_path = SCRIPT_DIR.parent / "backend" / ".env"

    if env_path.exists():
        content = env_path.read_text()

        # Update or add RAG_CORPUS_NAME
        if "RAG_CORPUS_NAME=" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("RAG_CORPUS_NAME="):
                    lines[i] = f"RAG_CORPUS_NAME={corpus.name}"
                    break
            content = "\n".join(lines)
        else:
            content += f"\nRAG_CORPUS_NAME={corpus.name}\n"

        env_path.write_text(content)
        print(f"\nUpdated .env with RAG_CORPUS_NAME={corpus.name}")


def main():
    """Main function to set up RAG corpus."""
    print("Setting up Vertex AI RAG Engine corpus")
    print("=" * 50)

    # Initialize
    init_vertexai()
    print()

    # Upload documents to GCS
    print("Uploading knowledge base to GCS...")
    if not KNOWLEDGE_BASE_DIR.exists():
        print(f"Error: Knowledge base directory not found: {KNOWLEDGE_BASE_DIR}")
        sys.exit(1)

    gcs_paths = upload_to_gcs(BUCKET_NAME, KNOWLEDGE_BASE_DIR)
    if not gcs_paths:
        print("Error: No documents found to upload")
        sys.exit(1)
    print()

    # Create corpus
    print("Creating RAG corpus...")
    corpus = create_corpus()
    print()

    # Import documents
    import_documents(corpus, gcs_paths)

    # Verify
    if verify_corpus(corpus):
        print("\n✓ RAG corpus setup complete!")
        save_corpus_name(corpus)
    else:
        print("\n⚠ RAG corpus created but verification had issues")
        print("  This may be due to indexing delay. Try querying later.")
        save_corpus_name(corpus)


if __name__ == "__main__":
    main()
