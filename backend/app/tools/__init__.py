# Tools module - ADK tool implementations

from app.tools.bigquery_tool import (
    get_bigquery_tool_definition,
    query_bigquery,
)
from app.tools.knowledge_tool import (
    KNOWLEDGE_TOOL_DEFINITION,
    search_knowledge_base,
)
from app.tools.context_tool import (
    CONTEXT_TOOL_DEFINITION,
    get_conversation_context,
)
from app.tools.memory_tool import (
    MEMORY_TOOL_DEFINITION,
    save_to_memory,
)


def get_tool_definitions() -> list[dict]:
    """
    Get all tool definitions for registering with the agent.

    Returns resolved definitions at runtime to avoid import-time ADC lookups.
    """
    return [
        get_bigquery_tool_definition(),
        KNOWLEDGE_TOOL_DEFINITION,
        CONTEXT_TOOL_DEFINITION,
        MEMORY_TOOL_DEFINITION,
    ]


__all__ = [
    # Tool definition getters (use these instead of static dicts)
    "get_bigquery_tool_definition",
    "get_tool_definitions",
    # Static tool definitions (don't require ADC at import)
    "KNOWLEDGE_TOOL_DEFINITION",
    "CONTEXT_TOOL_DEFINITION",
    "MEMORY_TOOL_DEFINITION",
    # Tool functions
    "query_bigquery",
    "search_knowledge_base",
    "get_conversation_context",
    "save_to_memory",
]
