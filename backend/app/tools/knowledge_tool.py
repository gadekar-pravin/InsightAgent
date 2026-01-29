"""
Knowledge Base Tool for InsightAgent.

Searches the company's internal knowledge base using Vertex AI RAG Engine
for metric definitions, targets, strategies, and policies.
"""

from typing import Any

from app.config import get_settings


# Tool definition for ADK
KNOWLEDGE_TOOL_DEFINITION = {
    "name": "search_knowledge_base",
    "description": """Search the company's internal knowledge base for business context.

Use this tool to find:
- Metric definitions (how we calculate churn, LTV, CAC, MRR, etc.)
- Company targets (quarterly and annual goals by region)
- Regional strategies (market conditions, competitive landscape)
- Pricing policies (recent changes, regional variations)
- Customer segment definitions (Enterprise, SMB, Consumer)

WHEN TO USE:
- BEFORE querying BigQuery: to understand metric definitions
- AFTER querying BigQuery: to explain the "why" behind the numbers
- When the user asks about company policies or strategies

EXAMPLE QUERIES:
- "churn rate definition" → Returns how we calculate churn (90-day window)
- "Q4 targets" → Returns quarterly targets by region
- "West region strategy" → Returns competitive landscape and market conditions
- "pricing policy changes" → Returns recent price adjustments

Results include content, source document name, and relevance score.
Always cite the source document in your response.
""",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The semantic search query for the knowledge base"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default: 3, max: 5)",
                "default": 3
            }
        },
        "required": ["query"]
    }
}


async def search_knowledge_base(query: str, top_k: int = 3) -> dict[str, Any]:
    """
    Search the knowledge base using Vertex AI RAG Engine.

    Args:
        query: The semantic search query
        top_k: Number of results to return (default 3)

    Returns:
        Dict with success status and list of results with content, source, score
    """
    # TODO: Phase 2 implementation
    # This will:
    # 1. Call Vertex AI RAG Engine retrieval API
    # 2. Filter by relevance threshold (0.7)
    # 3. Format results with source attribution

    settings = get_settings()

    return {
        "success": False,
        "error": "Knowledge base tool not yet implemented. Coming in Phase 2.",
        "results": [],
        "query": query,
    }
