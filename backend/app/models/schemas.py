"""
Pydantic models for InsightAgent API.

Defines request/response schemas with validation.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# Validation pattern for user IDs
VALID_USER_ID = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


# =============================================================================
# Session Models
# =============================================================================

class SessionCreate(BaseModel):
    """Request to create a new chat session."""
    user_id: str = Field(..., min_length=1, max_length=64)

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not VALID_USER_ID.match(v):
            raise ValueError('Invalid user_id format. Use alphanumeric, underscore, or hyphen.')
        return v


class SessionResponse(BaseModel):
    """Response when creating a new session."""
    session_id: str
    user_id: str
    created_at: datetime
    has_memory: bool = False


# =============================================================================
# Message Models
# =============================================================================

class MessageRequest(BaseModel):
    """Request to send a chat message."""
    session_id: str = Field(..., min_length=36, max_length=36)
    user_id: str = Field(..., min_length=1, max_length=64)
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not VALID_USER_ID.match(v):
            raise ValueError('Invalid user_id format')
        return v

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError('Invalid session_id format. Must be UUID v4.')
        return v

    @field_validator('content')
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        # Strip excessive whitespace
        return ' '.join(v.split())


class MessageResponse(BaseModel):
    """Non-streaming response for a message."""
    session_id: str
    content: str
    reasoning_trace: list[dict] = Field(default_factory=list)
    memory_saved: list[dict] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)


# =============================================================================
# SSE Event Models
# =============================================================================

class ReasoningEvent(BaseModel):
    """Event for tool reasoning trace."""
    seq: int
    trace_id: str
    tool_name: str
    status: Literal["started", "completed", "error"]
    summary: str | None = None
    error: str | None = None


class ContentEvent(BaseModel):
    """Event for content delta."""
    seq: int
    delta: str


class MemoryEvent(BaseModel):
    """Event for memory save."""
    seq: int
    memory_type: str
    key: str
    value: str


class DoneEvent(BaseModel):
    """Event signaling completion."""
    seq: int
    suggested_followups: list[str] = Field(default_factory=list)


# =============================================================================
# History Models
# =============================================================================

class HistoryMessage(BaseModel):
    """A message in conversation history."""
    message_id: str | None = None
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    reasoning_trace: list[dict] | None = None
    metadata: dict[str, Any] | None = None


class ConversationHistory(BaseModel):
    """Full conversation history for a session."""
    session_id: str
    user_id: str
    messages: list[HistoryMessage]
    created_at: datetime
    last_updated: datetime


# =============================================================================
# Memory Models
# =============================================================================

class MemoryItem(BaseModel):
    """A single memory item."""
    key: str
    value: str
    memory_type: Literal["finding", "preference", "context"]
    created_at: datetime
    session_id: str | None = None


class UserMemory(BaseModel):
    """Complete user memory state."""
    user_id: str
    summary: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    findings: dict[str, Any] = Field(default_factory=dict)
    recent_sessions: list[dict] = Field(default_factory=list)
    last_updated: datetime | None = None


class MemoryResetResponse(BaseModel):
    """Response when resetting user memory."""
    success: bool
    message: str


# =============================================================================
# Error Models
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str | None = None
    code: str | None = None
