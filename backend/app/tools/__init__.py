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


# Backward compatibility - lazy list that resolves on access
class _LazyToolDefinitions:
    """Lazy wrapper for tool definitions list."""
    _cached = None

    def __iter__(self):
        if self._cached is None:
            self._cached = get_tool_definitions()
        return iter(self._cached)

    def __getitem__(self, index):
        if self._cached is None:
            self._cached = get_tool_definitions()
        return self._cached[index]

    def __len__(self):
        if self._cached is None:
            self._cached = get_tool_definitions()
        return len(self._cached)


TOOL_DEFINITIONS = _LazyToolDefinitions()

__all__ = [
    # Tool definition getters
    "get_bigquery_tool_definition",
    "get_tool_definitions",
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
