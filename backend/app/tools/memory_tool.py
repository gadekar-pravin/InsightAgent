"""
Memory Tool for InsightAgent.

Saves important findings, user preferences, or contextual information
to Firestore for future reference.
"""

from typing import Any, Literal

from app.config import get_settings


# Tool definition for ADK
MEMORY_TOOL_DEFINITION = {
    "name": "save_to_memory",
    "description": """Save important information for future reference.

Use this tool to persist:
- Key findings from data analysis
- User preferences discovered during conversation
- Important context that should be remembered

MEMORY TYPES:
1. "finding": A key insight or data point (e.g., "Q4 revenue was $12.4M")
2. "preference": User preference (e.g., "User focuses on West region")
3. "context": Important context (e.g., "Investigating Q4 underperformance")

WHEN TO USE:
- After discovering an important data insight
- When user expresses a preference (region, format, focus area)
- When establishing context for ongoing analysis
- At the end of an analysis session to summarize findings

The save will be confirmed with a 💾 indicator in the response.
""",
    "parameters": {
        "type": "object",
        "properties": {
            "memory_type": {
                "type": "string",
                "enum": ["finding", "preference", "context"],
                "description": "The type of information being saved"
            },
            "key": {
                "type": "string",
                "description": "A short identifier for the memory (e.g., 'q4_revenue', 'preferred_region')"
            },
            "value": {
                "type": "string",
                "description": "The information to save"
            }
        },
        "required": ["memory_type", "key", "value"]
    }
}


async def save_to_memory(
    memory_type: Literal["finding", "preference", "context"],
    key: str,
    value: str,
    user_id: str,
    session_id: str,
) -> dict[str, Any]:
    """
    Save information to Firestore memory.

    Args:
        memory_type: Type of memory (finding, preference, context)
        key: Short identifier for the memory
        value: The information to save
        user_id: The user's ID
        session_id: The current session ID

    Returns:
        Dict with success status and saved details
    """
    # TODO: Phase 2 implementation
    # This will:
    # 1. Validate key and value
    # 2. Write to appropriate Firestore collection
    # 3. Return confirmation

    settings = get_settings()

    return {
        "success": False,
        "error": "Memory tool not yet implemented. Coming in Phase 2.",
        "memory_type": memory_type,
        "key": key,
        "saved": False,
    }
