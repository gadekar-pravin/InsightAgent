"""
Conversation Context Tool for InsightAgent.

Retrieves context from current session, user preferences,
or past analyses to provide personalized responses.
"""

from typing import Any, Literal

from app.services.firestore_service import get_firestore_service
from app.services.tool_middleware import log_tool_call


# Tool definition for ADK/Gemini function calling
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
    # Log tool call
    log_tool_call(
        tool_name="get_conversation_context",
        parameters={"context_type": context_type},
        user_id=user_id,
        session_id=session_id,
    )

    service = get_firestore_service()

    try:
        if context_type == "current_session":
            # Get current session context
            context_data = await service.get_session_context(user_id, session_id)
            return {
                "success": True,
                "context_type": context_type,
                "data": context_data,
                "last_updated": context_data.get("last_updated"),
            }

        elif context_type == "user_preferences":
            # Get user preferences and findings from memory
            memory = await service.get_user_memory(user_id)
            preferences = memory.get("preferences", {})
            findings = memory.get("findings", {})
            return {
                "success": True,
                "context_type": context_type,
                "data": {
                    "preferences": preferences,
                    "regions_of_interest": preferences.get("regions_of_interest", []),
                    "role": preferences.get("role"),
                    "preferred_format": preferences.get("preferred_format"),
                    "saved_findings": findings,
                },
                "last_updated": memory.get("last_updated"),
            }

        elif context_type == "past_analyses":
            # Get past session summaries
            past_sessions = await service.get_past_analyses(user_id, limit=5)
            return {
                "success": True,
                "context_type": context_type,
                "data": {
                    "sessions": past_sessions,
                    "total_sessions": len(past_sessions),
                },
                "last_updated": past_sessions[0].get("date") if past_sessions else None,
            }

        else:
            return {
                "success": False,
                "error": f"Unknown context_type: {context_type}",
                "context_type": context_type,
                "data": None,
                "last_updated": None,
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve context: {str(e)}",
            "context_type": context_type,
            "data": None,
            "last_updated": None,
        }
