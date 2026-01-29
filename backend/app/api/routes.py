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
    - heartbeat: Keep-alive event (every 15s)
    - done: Completion with suggested followups
    """
    firestore = get_firestore_service()

    # Save user message to history
    await firestore.add_message(
        user_id=request.user_id,
        session_id=request.session_id,
        role="user",
        content=request.content,
    )

    # Get user memory for system prompt injection
    memory_summary = await firestore.get_user_memory_summary(request.user_id)

    # Create agent instance
    agent = InsightAgent(
        user_id=request.user_id,
        session_id=request.session_id,
        memory_summary=memory_summary,
    )

    async def generate_sse() -> AsyncGenerator[str, None]:
        """Generate SSE events from agent response with background heartbeats."""
        import asyncio
        import time

        seq = 0
        response_content: list[str] = []
        reasoning_trace: list[dict] = []
        heartbeat_interval = 15  # seconds
        done = False

        # Queue for events (agent events + heartbeats)
        event_queue: asyncio.Queue = asyncio.Queue()

        async def agent_producer():
            """Produce events from agent.chat() into the queue."""
            nonlocal done
            try:
                async for event in agent.chat(request.content):
                    await event_queue.put(("event", event))
                await event_queue.put(("done", None))
            except Exception as e:
                await event_queue.put(("error", str(e)))
            finally:
                done = True

        async def heartbeat_producer():
            """Produce heartbeat events every 15s until done."""
            while not done:
                await asyncio.sleep(heartbeat_interval)
                if not done:
                    await event_queue.put(("heartbeat", time.time()))

        # Start both producers
        agent_task = asyncio.create_task(agent_producer())
        heartbeat_task = asyncio.create_task(heartbeat_producer())

        try:
            while True:
                try:
                    # Wait for next event with timeout
                    msg_type, msg_data = await asyncio.wait_for(
                        event_queue.get(), timeout=heartbeat_interval + 5
                    )
                except asyncio.TimeoutError:
                    # Safety timeout - send heartbeat
                    seq += 1
                    yield f"id: {seq}\n"
                    yield "event: heartbeat\n"
                    yield f"data: {_json_dumps({'seq': seq, 'timestamp': time.time()})}\n\n"
                    continue

                if msg_type == "heartbeat":
                    seq += 1
                    yield f"id: {seq}\n"
                    yield "event: heartbeat\n"
                    yield f"data: {_json_dumps({'seq': seq, 'timestamp': msg_data})}\n\n"

                elif msg_type == "event":
                    event = msg_data
                    seq += 1
                    event_type = event.get("type", "content")
                    event_data = event.get("data", {})
                    event_data["seq"] = seq

                    # Collect content for history
                    if event_type == "content":
                        delta = event_data.get("delta", "")
                        if delta:
                            response_content.append(delta)
                    elif event_type == "reasoning":
                        reasoning_trace.append(event_data)

                    # Format as SSE
                    yield f"id: {seq}\n"
                    yield f"event: {event_type}\n"
                    yield f"data: {_json_dumps(event_data)}\n\n"

                elif msg_type == "error":
                    seq += 1
                    yield f"id: {seq}\n"
                    yield "event: error\n"
                    yield f"data: {_json_dumps({'seq': seq, 'error': msg_data})}\n\n"
                    break

                elif msg_type == "done":
                    # Save assistant response to history
                    full_response = "".join(response_content)
                    if full_response:
                        await firestore.add_message(
                            user_id=request.user_id,
                            session_id=request.session_id,
                            role="assistant",
                            content=full_response,
                            reasoning_trace=reasoning_trace if reasoning_trace else None,
                        )
                    break

        except Exception as e:
            seq += 1
            yield f"id: {seq}\n"
            yield "event: error\n"
            yield f"data: {_json_dumps({'seq': seq, 'error': str(e)})}\n\n"

        finally:
            # Best-effort cleanup (important on client disconnects)
            for task in (heartbeat_task, agent_task):
                task.cancel()
            for task in (heartbeat_task, agent_task):
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
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
    firestore = get_firestore_service()
    history = await firestore.get_session_history(user_id, session_id)

    if "error" in history:
        if history["error"] == "Session not found":
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=500, detail=history["error"])

    # Parse ISO strings to datetime objects for Pydantic
    from datetime import datetime as dt

    messages = []
    for msg in history.get("messages", []):
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
            "timestamp": dt.fromisoformat(msg["timestamp"].replace("Z", "+00:00")),
            "reasoning_trace": msg.get("reasoning_trace"),
        })

    created_at = history.get("created_at", "")
    last_updated = history.get("last_updated", created_at)

    return ConversationHistory(
        session_id=session_id,
        user_id=user_id,
        messages=messages,
        created_at=dt.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else dt.now(timezone.utc),
        last_updated=dt.fromisoformat(last_updated.replace("Z", "+00:00")) if last_updated else dt.now(timezone.utc),
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
