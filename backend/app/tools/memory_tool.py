"""
Memory Tool for InsightAgent.

Saves important findings, user preferences, or contextual information
to Firestore for future reference.
"""

from typing import Any, Literal

from app.services.firestore_service import get_firestore_service
from app.services.tool_middleware import log_tool_call


# Tool definition for ADK/Gemini function calling
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

Note: The UI displays a separate notification when memory is saved. Do not mention the save in your response text.
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
    # Log tool call
    log_tool_call(
        tool_name="save_to_memory",
        parameters={"memory_type": memory_type, "key": key, "value": value},
        user_id=user_id,
        session_id=session_id,
    )

    service = get_firestore_service()

    # Save to user memory
    result = await service.save_memory(
        user_id=user_id,
        memory_type=memory_type,
        key=key,
        value=value,
    )

    # Also update session context if it's a finding
    if result.get("success") and memory_type == "finding":
        await service.update_session_context(
            user_id=user_id,
            session_id=session_id,
            finding=f"{key}: {value}",
        )

    return result
