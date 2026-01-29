# Tools module - ADK tool implementations

from app.tools.bigquery_tool import (
    BIGQUERY_TOOL_DEFINITION,
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

# All tool definitions for registering with the agent
TOOL_DEFINITIONS = [
    BIGQUERY_TOOL_DEFINITION,
    KNOWLEDGE_TOOL_DEFINITION,
    CONTEXT_TOOL_DEFINITION,
    MEMORY_TOOL_DEFINITION,
]

__all__ = [
    # Tool definitions
    "BIGQUERY_TOOL_DEFINITION",
    "KNOWLEDGE_TOOL_DEFINITION",
    "CONTEXT_TOOL_DEFINITION",
    "MEMORY_TOOL_DEFINITION",
    "TOOL_DEFINITIONS",
    # Tool functions
    "query_bigquery",
    "search_knowledge_base",
    "get_conversation_context",
    "save_to_memory",
]
