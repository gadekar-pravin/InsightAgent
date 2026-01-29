"""
Knowledge Base Tool for InsightAgent.

Searches the company's internal knowledge base using Vertex AI RAG Engine
for metric definitions, targets, strategies, and policies.
"""

from typing import Any

from app.services.rag_engine import get_rag_service
from app.services.tool_middleware import log_tool_call, sanitize_tool_output


# Tool definition for ADK/Gemini function calling
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


async def search_knowledge_base(
    query: str,
    top_k: int = 3,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Search the knowledge base using Vertex AI RAG Engine.

    Args:
        query: The semantic search query
        top_k: Number of results to return (default 3)
        user_id: Optional user ID for logging
        session_id: Optional session ID for logging

    Returns:
        Dict with success status and list of results with content, source, score
    """
    # Log tool call
    if user_id and session_id:
        log_tool_call(
            tool_name="search_knowledge_base",
            parameters={"query": query, "top_k": top_k},
            user_id=user_id,
            session_id=session_id,
        )

    # Clamp top_k
    top_k = max(1, min(top_k, 5))

    # Get RAG service and search
    service = get_rag_service()
    result = await service.search(query=query, top_k=top_k)

    # Sanitize output before returning
    return sanitize_tool_output("search_knowledge_base", result)
