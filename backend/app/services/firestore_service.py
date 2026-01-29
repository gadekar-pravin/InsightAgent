"""
Firestore Service for InsightAgent.

Provides user memory CRUD operations, session management,
and cross-session memory retrieval.
"""

import re
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings


# Validation pattern for user IDs
VALID_USER_ID = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


class FirestoreService:
    """Service for Firestore operations including memory and sessions."""

    def __init__(self):
        """Initialize the Firestore service."""
        self.settings = get_settings()
        self._db = None
        self._collection_prefix = self.settings.firestore_collection_prefix

    @property
    def db(self):
        """Lazy initialization of Firestore client."""
        if self._db is None:
            # TODO: Phase 2 - initialize firebase_admin
            # import firebase_admin
            # from firebase_admin import firestore
            # if not firebase_admin._apps:
            #     firebase_admin.initialize_app()
            # self._db = firestore.client()
            pass
        return self._db

    def _validate_user_id(self, user_id: str) -> None:
        """Validate user ID format to prevent path traversal."""
        if not VALID_USER_ID.match(user_id):
            raise ValueError(f"Invalid user_id format: {user_id}")

    def _user_doc_path(self, user_id: str) -> str:
        """Get the document path for a user."""
        self._validate_user_id(user_id)
        return f"{self._collection_prefix}_users/{user_id}"

    async def get_user_memory(self, user_id: str) -> dict[str, Any]:
        """
        Get all memory for a user.

        Args:
            user_id: The user's ID

        Returns:
            Dict with summary, preferences, findings
        """
        # TODO: Phase 2 implementation
        self._validate_user_id(user_id)

        return {
            "summary": None,
            "preferences": {},
            "findings": {},
            "last_updated": None,
        }

    async def get_user_memory_summary(self, user_id: str) -> str | None:
        """
        Get the condensed memory summary for system prompt injection.

        Args:
            user_id: The user's ID

        Returns:
            Memory summary string or None
        """
        # TODO: Phase 2 implementation
        self._validate_user_id(user_id)
        return None

    async def save_memory(
        self,
        user_id: str,
        memory_type: str,
        key: str,
        value: str,
    ) -> dict[str, Any]:
        """
        Save a memory item for a user.

        Args:
            user_id: The user's ID
            memory_type: Type of memory (finding, preference, context)
            key: Memory key
            value: Memory value

        Returns:
            Dict with success status
        """
        # TODO: Phase 2 implementation
        self._validate_user_id(user_id)

        return {
            "success": False,
            "error": "Memory save not yet implemented. Coming in Phase 2.",
        }

    async def create_session(self, user_id: str, session_id: str) -> dict[str, Any]:
        """
        Create a new chat session.

        Args:
            user_id: The user's ID
            session_id: The session ID

        Returns:
            Dict with session details and injected memory
        """
        # TODO: Phase 2 implementation
        self._validate_user_id(user_id)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "injected_memory_snapshot": None,
        }

    async def get_session_context(
        self,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Get context from the current session.

        Args:
            user_id: The user's ID
            session_id: The session ID

        Returns:
            Dict with session context
        """
        # TODO: Phase 2 implementation
        self._validate_user_id(user_id)

        return {
            "topics": [],
            "metrics_queried": [],
            "findings": [],
            "last_updated": None,
        }

    async def get_past_analyses(self, user_id: str, limit: int = 5) -> list[dict]:
        """
        Get summaries of past analysis sessions.

        Args:
            user_id: The user's ID
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries
        """
        # TODO: Phase 2 implementation
        self._validate_user_id(user_id)

        return []

    async def reset_user_memory(self, user_id: str) -> dict[str, Any]:
        """
        Reset all memory for a user (demo feature).

        Args:
            user_id: The user's ID

        Returns:
            Dict with success status
        """
        # TODO: Phase 2 implementation
        self._validate_user_id(user_id)

        return {
            "success": False,
            "error": "Memory reset not yet implemented. Coming in Phase 2.",
        }


# Singleton instance
_firestore_service: FirestoreService | None = None


def get_firestore_service() -> FirestoreService:
    """Get the Firestore service singleton."""
    global _firestore_service
    if _firestore_service is None:
        _firestore_service = FirestoreService()
    return _firestore_service
