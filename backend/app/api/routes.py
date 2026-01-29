"""
API Routes for InsightAgent.

Implements the REST API endpoints with SSE streaming support.
"""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.api.auth import verify_api_key
from app.models.schemas import (
    SessionCreate,
    SessionResponse,
    MessageRequest,
    ConversationHistory,
    UserMemory,
    MemoryResetResponse,
    ErrorResponse,
)
from app.agent.insight_agent import InsightAgent
from app.services.firestore_service import get_firestore_service


router = APIRouter()


# =============================================================================
# Session Endpoints
# =============================================================================

@router.post(
    "/chat/session",
    response_model=SessionResponse,
    responses={403: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
)
async def create_session(request: SessionCreate) -> SessionResponse:
    """
    Create a new chat session.

    This endpoint:
    1. Generates a new session ID
    2. Loads user memory from Firestore
    3. Creates session record with injected memory snapshot
    """
    session_id = str(uuid.uuid4())

    firestore = get_firestore_service()

    # Create session in Firestore
    session_data = await firestore.create_session(request.user_id, session_id)

    # Check if user has existing memory
    memory = await firestore.get_user_memory(request.user_id)
    has_memory = bool(memory.get("summary") or memory.get("findings"))

    return SessionResponse(
        session_id=session_id,
        user_id=request.user_id,
        created_at=datetime.now(timezone.utc),
        has_memory=has_memory,
    )


# =============================================================================
# Message Endpoints
# =============================================================================

@router.post(
    "/chat/message",
    responses={403: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
)
async def send_message(request: MessageRequest) -> StreamingResponse:
    """
    Send a message and receive streaming response via SSE.

    Event types:
    - reasoning: Tool call trace (started, completed, error)
    - content: Response text delta
    - memory: Memory save notification
    - done: Completion with suggested followups
    """
    firestore = get_firestore_service()

    # Get user memory for system prompt injection
    memory_summary = await firestore.get_user_memory_summary(request.user_id)

    # Create agent instance
    agent = InsightAgent(
        user_id=request.user_id,
        session_id=request.session_id,
        memory_summary=memory_summary,
    )

    async def generate_sse() -> AsyncGenerator[str, None]:
        """Generate SSE events from agent response."""
        seq = 0

        try:
            await agent.initialize()

            async for event in agent.chat(request.content):
                seq += 1
                event_type = event.get("type", "content")
                event_data = event.get("data", {})
                event_data["seq"] = seq

                # Format as SSE
                yield f"id: {seq}\n"
                yield f"event: {event_type}\n"
                yield f"data: {_json_dumps(event_data)}\n\n"

        except Exception as e:
            # Send error event
            seq += 1
            yield f"id: {seq}\n"
            yield f"event: error\n"
            yield f"data: {_json_dumps({'seq': seq, 'error': str(e)})}\n\n"

        finally:
            await agent.close()

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# =============================================================================
# History Endpoints
# =============================================================================

@router.get(
    "/chat/history/{session_id}",
    response_model=ConversationHistory,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    dependencies=[Depends(verify_api_key)],
)
async def get_history(session_id: str, user_id: str) -> ConversationHistory:
    """
    Retrieve conversation history for a session.
    """
    # TODO: Phase 2 implementation
    raise HTTPException(
        status_code=501,
        detail="History retrieval not yet implemented. Coming in Phase 2.",
    )


# =============================================================================
# Memory Endpoints
# =============================================================================

@router.get(
    "/user/memory",
    response_model=UserMemory,
    responses={403: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
)
async def get_user_memory(user_id: str) -> UserMemory:
    """
    Retrieve user's persistent memory.
    """
    firestore = get_firestore_service()
    memory = await firestore.get_user_memory(user_id)

    return UserMemory(
        user_id=user_id,
        summary=memory.get("summary"),
        preferences=memory.get("preferences", {}),
        findings=memory.get("findings", {}),
        recent_sessions=await firestore.get_past_analyses(user_id, limit=5),
        last_updated=memory.get("last_updated"),
    )


@router.delete(
    "/user/memory/reset",
    response_model=MemoryResetResponse,
    responses={403: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
)
async def reset_user_memory(user_id: str) -> MemoryResetResponse:
    """
    Reset user memory (demo feature).

    Clears all stored preferences, findings, and session history.
    """
    firestore = get_firestore_service()
    result = await firestore.reset_user_memory(user_id)

    if result.get("success"):
        return MemoryResetResponse(
            success=True,
            message="Memory reset successfully",
        )
    else:
        return MemoryResetResponse(
            success=False,
            message=result.get("error", "Failed to reset memory"),
        )


# =============================================================================
# Helpers
# =============================================================================

def _json_dumps(data: dict) -> str:
    """JSON serialize data for SSE."""
    import json
    return json.dumps(data, default=str)
