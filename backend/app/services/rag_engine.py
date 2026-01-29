"""
RAG Engine Service for InsightAgent.

Provides knowledge base search using Vertex AI RAG Engine.
Implements retrieval as a custom tool (not ADK's built-in RAG tool
due to single-tool-per-agent limitation).
"""

import logging
from typing import Any

from vertexai import rag
import vertexai

from app.config import get_settings, init_vertex_ai

logger = logging.getLogger(__name__)


class RAGEngineService:
    """Service for knowledge base retrieval using Vertex AI RAG Engine."""

    def __init__(self):
        """Initialize the RAG Engine service."""
        self.settings = get_settings()
        self._corpus_name = self.settings.rag_corpus_name
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure Vertex AI is initialized."""
        if not self._initialized:
            init_vertex_ai()
            self._initialized = True

    @property
    def corpus_name(self) -> str:
        """Get the RAG corpus name."""
        return self._corpus_name

    async def search(
        self,
        query: str,
        top_k: int = 3,
        relevance_threshold: float = 0.3,
    ) -> dict[str, Any]:
        """
        Search the knowledge base for relevant content.

        Args:
            query: The semantic search query
            top_k: Number of results to return
            relevance_threshold: Minimum relevance score (0-1, higher = more relevant).
                Results with relevance below this threshold are filtered out.

        Returns:
            Dict with results containing content, source, and score
        """
        if not query or not query.strip():
            return {
                "success": False,
                "error": "Query cannot be empty",
                "results": [],
                "query": query,
            }

        if not self.corpus_name:
            return {
                "success": False,
                "error": "RAG corpus not configured. Set RAG_CORPUS_NAME in environment.",
                "results": [],
                "query": query,
            }

        # Clamp top_k to valid range
        top_k = max(1, min(top_k, 10))

        # Clamp relevance_threshold to valid range
        relevance_threshold = max(0.0, min(relevance_threshold, 1.0))

        # Convert relevance threshold to distance threshold
        # relevance = 1 - distance, so distance = 1 - relevance
        # Higher relevance threshold means lower distance threshold (stricter filtering)
        distance_threshold = 1.0 - relevance_threshold

        try:
            self._ensure_initialized()

            # Perform RAG retrieval query
            response = rag.retrieval_query(
                rag_resources=[
                    rag.RagResource(rag_corpus=self.corpus_name)
                ],
                text=query,
                rag_retrieval_config=rag.RagRetrievalConfig(
                    top_k=top_k,
                    filter=rag.Filter(
                        vector_distance_threshold=distance_threshold
                    )
                ),
            )

            return self._format_results(response, query)

        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return {
                "success": False,
                "error": f"Knowledge base search failed: {str(e)}",
                "results": [],
                "query": query,
            }

    def _format_results(self, response: Any, query: str) -> dict[str, Any]:
        """
        Format RAG Engine response into standard format.

        Args:
            response: Raw RAG Engine response
            query: Original query string

        Returns:
            Formatted results dict
        """
        results = []

        try:
            # Extract contexts from response
            if hasattr(response, 'contexts') and response.contexts:
                for context in response.contexts.contexts:
                    # Extract source file name from URI
                    source_uri = getattr(context, 'source_uri', '') or ''
                    source_name = source_uri.split('/')[-1] if source_uri else 'unknown'

                    # Get the text content
                    content = getattr(context, 'text', '') or ''

                    # Get relevance score
                    # Note: Vertex AI RAG API returns 'score' (similarity, higher = more relevant)
                    # not 'distance'. Score is typically 0-1 range.
                    score = getattr(context, 'score', None)
                    if score is not None:
                        relevance_score = float(score)
                    else:
                        relevance_score = 0.5  # Default when score not provided

                    results.append({
                        "content": content,
                        "source": source_name,
                        "relevance_score": round(relevance_score, 3),
                        "source_uri": source_uri,
                    })

            logger.info(f"RAG search returned {len(results)} results for query: {query[:50]}...")

            return {
                "success": True,
                "results": results,
                "query": query,
                "total_results": len(results),
            }

        except Exception as e:
            logger.error(f"Error formatting RAG results: {e}")
            return {
                "success": False,
                "error": f"Error processing search results: {str(e)}",
                "results": [],
                "query": query,
            }


# Singleton instance
_rag_service: RAGEngineService | None = None


def get_rag_service() -> RAGEngineService:
    """Get the RAG Engine service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGEngineService()
    return _rag_service
