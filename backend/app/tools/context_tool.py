"""
Conversation Context Tool for InsightAgent.

Retrieves context from current session, user preferences,
or past analyses to provide personalized responses.
"""

from typing import Any, Literal

from app.config import get_settings


# Tool definition for ADK
CONTEXT_TOOL_DEFINITION = {
    "name": "get_conversation_context",
    "description": """Retrieve context from the current session or user history.

Use this tool to:
- Remember what was discussed earlier in the conversation
- Access user preferences (preferred regions, formats, role)
- Recall findings from past analysis sessions

CONTEXT TYPES:
1. "current_session": Topics discussed, metrics queried, findings made
2. "user_preferences": User's preferred formats, regions of interest, role, style
3. "past_analyses": Summaries of previous sessions with dates and topics

WHEN TO USE:
- When the user says "as we discussed" or refers to earlier conversation
- When personalizing responses based on user role/preferences
- When the user asks to "continue where we left off"
- For follow-up questions that reference previous findings

Returns context with last_updated timestamp.
""",
    "parameters": {
        "type": "object",
        "properties": {
            "context_type": {
                "type": "string",
                "enum": ["current_session", "user_preferences", "past_analyses"],
                "description": "The type of context to retrieve"
            }
        },
        "required": ["context_type"]
    }
}


async def get_conversation_context(
    context_type: Literal["current_session", "user_preferences", "past_analyses"],
    user_id: str,
    session_id: str,
) -> dict[str, Any]:
    """
    Retrieve conversation context from Firestore.

    Args:
        context_type: Type of context to retrieve
        user_id: The user's ID
        session_id: The current session ID

    Returns:
        Dict with context data and last_updated timestamp
    """
    # TODO: Phase 2 implementation
    # This will:
    # 1. Query Firestore for the appropriate context type
    # 2. Return formatted context with timestamps

    settings = get_settings()

    return {
        "success": False,
        "error": "Context tool not yet implemented. Coming in Phase 2.",
        "context_type": context_type,
        "data": None,
        "last_updated": None,
    }
