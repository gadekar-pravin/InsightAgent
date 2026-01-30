"""
Firestore Service for InsightAgent.

Provides user memory CRUD operations, session management,
and cross-session memory retrieval.
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.config import get_settings

logger = logging.getLogger(__name__)

# Validation pattern for user IDs
VALID_USER_ID = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

# Memory compaction limits
MAX_FINDINGS_IN_SUMMARY = 5
MAX_PREFERENCES_IN_SUMMARY = 5
MAX_SUMMARY_TOKENS = 500  # Approximate limit


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
            # Initialize firebase_admin if not already done
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            self._db = firestore.client()
        return self._db

    def _validate_user_id(self, user_id: str) -> None:
        """Validate user ID format to prevent path traversal."""
        if not VALID_USER_ID.match(user_id):
            raise ValueError(f"Invalid user_id format: {user_id}")

    def _users_collection(self) -> str:
        """Get the users collection name."""
        return f"{self._collection_prefix}_users"

    def _sessions_collection(self, user_id: str) -> str:
        """Get the sessions subcollection path."""
        return f"{self._users_collection()}/{user_id}/sessions"

    async def get_user_memory(self, user_id: str) -> dict[str, Any]:
        """
        Get all memory for a user.

        Args:
            user_id: The user's ID

        Returns:
            Dict with summary, preferences, findings
        """
        self._validate_user_id(user_id)

        try:
            doc_ref = self.db.collection(self._users_collection()).document(user_id)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                return {
                    "summary": data.get("summary"),
                    "preferences": data.get("preferences", {}),
                    "findings": data.get("findings", {}),
                    "last_updated": data.get("last_updated"),
                }
            else:
                return {
                    "summary": None,
                    "preferences": {},
                    "findings": {},
                    "last_updated": None,
                }

        except Exception as e:
            logger.error(f"Error getting user memory: {e}")
            return {
                "summary": None,
                "preferences": {},
                "findings": {},
                "last_updated": None,
            }

    async def get_user_memory_summary(self, user_id: str) -> str | None:
        """
        Get the condensed memory summary for system prompt injection.

        Implements memory compaction rule:
        - Last N findings (5 most recent)
        - Top user preferences
        - Last session summary only
        - Total < 500 tokens

        Args:
            user_id: The user's ID

        Returns:
            Memory summary string or None
        """
        self._validate_user_id(user_id)

        try:
            memory = await self.get_user_memory(user_id)

            if not memory["summary"] and not memory["preferences"] and not memory["findings"]:
                return None

            parts = []

            # Add stored summary if exists
            if memory.get("summary"):
                parts.append(memory["summary"])

            # Add recent preferences
            if memory.get("preferences"):
                prefs = memory["preferences"]
                pref_items = list(prefs.items())[:MAX_PREFERENCES_IN_SUMMARY]
                if pref_items:
                    pref_str = ", ".join([f"{k}: {v}" for k, v in pref_items])
                    parts.append(f"User preferences: {pref_str}")

            # Add recent findings
            if memory.get("findings"):
                findings = memory["findings"]
                finding_items = list(findings.items())[:MAX_FINDINGS_IN_SUMMARY]
                if finding_items:
                    findings_str = "; ".join([f"{k}: {v}" for k, v in finding_items])
                    parts.append(f"Previous findings: {findings_str}")

            if not parts:
                return None

            summary = "\n".join(parts)

            # Truncate if too long (rough approximation of tokens)
            max_chars = MAX_SUMMARY_TOKENS * 4  # ~4 chars per token
            if len(summary) > max_chars:
                summary = summary[:max_chars] + "..."

            return summary

        except Exception as e:
            logger.error(f"Error getting memory summary: {e}")
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
        self._validate_user_id(user_id)

        if not key or not key.strip():
            return {"success": False, "error": "Memory key cannot be empty"}

        if not value or not value.strip():
            return {"success": False, "error": "Memory value cannot be empty"}

        # Sanitize key (alphanumeric and underscores only)
        safe_key = re.sub(r'[^a-zA-Z0-9_]', '_', key.strip())[:64]

        try:
            doc_ref = self.db.collection(self._users_collection()).document(user_id)
            now = datetime.now(timezone.utc).isoformat()

            # Determine which field to update based on memory_type
            if memory_type == "finding":
                field_path = f"findings.{safe_key}"
            elif memory_type == "preference":
                field_path = f"preferences.{safe_key}"
            elif memory_type == "context":
                # Context updates the summary field
                field_path = "summary"
            else:
                return {"success": False, "error": f"Invalid memory_type: {memory_type}"}

            # Use transaction for atomic update of nested field
            # This ensures either both last_updated and value are set, or neither
            @firestore.transactional
            def update_in_transaction(transaction, doc_ref, field_path, value, now):
                doc = doc_ref.get(transaction=transaction)
                if doc.exists:
                    # Document exists - update only the specific nested field
                    transaction.update(doc_ref, {
                        field_path: value,
                        "last_updated": now,
                    })
                else:
                    # Document doesn't exist - create with nested structure
                    if '.' in field_path:
                        # e.g., "findings.q4_revenue" -> {"findings": {"q4_revenue": value}}
                        parts = field_path.split('.')
                        data = {parts[0]: {parts[1]: value}, "last_updated": now}
                    else:
                        data = {field_path: value, "last_updated": now}
                    transaction.set(doc_ref, data)

            # Run transaction (Firestore client is sync, but we're in async context)
            transaction = self.db.transaction()
            update_in_transaction(transaction, doc_ref, field_path, value, now)

            logger.info(f"Saved memory for user {user_id[:4]}***: {memory_type}/{safe_key}")

            return {
                "success": True,
                "memory_type": memory_type,
                "key": safe_key,
                "saved_at": now,
            }

        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return {
                "success": False,
                "error": f"Failed to save memory: {str(e)}",
            }

    async def create_session(self, user_id: str, session_id: str) -> dict[str, Any]:
        """
        Create a new chat session.

        Loads user memory and creates session with injected memory snapshot.

        Args:
            user_id: The user's ID
            session_id: The session ID

        Returns:
            Dict with session details and injected memory
        """
        self._validate_user_id(user_id)

        try:
            now = datetime.now(timezone.utc)

            # Get memory summary for injection
            memory_summary = await self.get_user_memory_summary(user_id)

            # Calculate session expiry (24 hours)
            expire_at = now + timedelta(hours=24)

            # Create session document
            session_data = {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": now.isoformat(),
                "expire_at": expire_at.isoformat(),
                "injected_memory_snapshot": memory_summary,
                "topics": [],
                "metrics_queried": [],
                "findings": [],
            }

            # Save to Firestore
            session_ref = self.db.collection(
                self._sessions_collection(user_id)
            ).document(session_id)
            session_ref.set(session_data)

            logger.info(f"Created session {session_id[:8]}... for user {user_id[:4]}***")

            return session_data

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            # Return minimal session data even on error
            return {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "injected_memory_snapshot": None,
                "error": str(e),
            }

    async def update_session_context(
        self,
        user_id: str,
        session_id: str,
        topic: str | None = None,
        metric: str | None = None,
        finding: str | None = None,
    ) -> None:
        """
        Update session context with new information.

        Args:
            user_id: The user's ID
            session_id: The session ID
            topic: Topic discussed (optional)
            metric: Metric queried (optional)
            finding: Finding made (optional)
        """
        self._validate_user_id(user_id)

        try:
            session_ref = self.db.collection(
                self._sessions_collection(user_id)
            ).document(session_id)

            updates = {"last_updated": datetime.now(timezone.utc).isoformat()}

            if topic:
                updates["topics"] = firestore.ArrayUnion([topic])
            if metric:
                updates["metrics_queried"] = firestore.ArrayUnion([metric])
            if finding:
                updates["findings"] = firestore.ArrayUnion([finding])

            session_ref.update(updates)

        except Exception as e:
            logger.error(f"Error updating session context: {e}")

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
        self._validate_user_id(user_id)

        try:
            session_ref = self.db.collection(
                self._sessions_collection(user_id)
            ).document(session_id)
            doc = session_ref.get()

            if doc.exists:
                data = doc.to_dict()
                return {
                    "topics": data.get("topics", []),
                    "metrics_queried": data.get("metrics_queried", []),
                    "findings": data.get("findings", []),
                    "last_updated": data.get("last_updated"),
                }
            else:
                return {
                    "topics": [],
                    "metrics_queried": [],
                    "findings": [],
                    "last_updated": None,
                }

        except Exception as e:
            logger.error(f"Error getting session context: {e}")
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
        self._validate_user_id(user_id)

        try:
            sessions_ref = self.db.collection(self._sessions_collection(user_id))
            query = sessions_ref.order_by(
                "created_at", direction=firestore.Query.DESCENDING
            ).limit(limit)

            docs = query.stream()

            sessions = []
            for doc in docs:
                data = doc.to_dict()
                sessions.append({
                    "session_id": data.get("session_id"),
                    "date": data.get("created_at"),
                    "topics": data.get("topics", []),
                    "findings": data.get("findings", []),
                })

            return sessions

        except Exception as e:
            logger.error(f"Error getting past analyses: {e}")
            return []

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """
        Get user preferences.

        Args:
            user_id: The user's ID

        Returns:
            Dict with user preferences
        """
        self._validate_user_id(user_id)

        memory = await self.get_user_memory(user_id)
        return memory.get("preferences", {})

    async def reset_user_memory(self, user_id: str) -> dict[str, Any]:
        """
        Reset all memory for a user (demo feature).

        Args:
            user_id: The user's ID

        Returns:
            Dict with success status
        """
        self._validate_user_id(user_id)

        try:
            # Delete user document
            user_ref = self.db.collection(self._users_collection()).document(user_id)
            user_ref.delete()

            # Delete all sessions (batch delete)
            sessions_ref = self.db.collection(self._sessions_collection(user_id))
            docs = sessions_ref.stream()

            batch = self.db.batch()
            count = 0
            for doc in docs:
                batch.delete(doc.reference)
                count += 1

            if count > 0:
                batch.commit()

            logger.info(f"Reset memory for user {user_id[:4]}***: deleted {count} sessions")

            return {
                "success": True,
                "sessions_deleted": count,
            }

        except Exception as e:
            logger.error(f"Error resetting memory: {e}")
            return {
                "success": False,
                "error": f"Failed to reset memory: {str(e)}",
            }

    async def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        reasoning_trace: list[dict] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Add a message to session history.

        Args:
            user_id: The user's ID
            session_id: The session ID
            role: Message role ('user' or 'assistant')
            content: Message content
            reasoning_trace: Optional reasoning trace for assistant messages

        Returns:
            Dict with message details
        """
        self._validate_user_id(user_id)

        try:
            now = datetime.now(timezone.utc)
            message_data = {
                "role": role,
                "content": content,
                "timestamp": now.isoformat(),
            }
            if reasoning_trace:
                message_data["reasoning_trace"] = reasoning_trace
            if metadata:
                message_data["metadata"] = metadata

            # Add to messages subcollection within the session
            messages_ref = self.db.collection(
                f"{self._sessions_collection(user_id)}/{session_id}/messages"
            )
            add_result = messages_ref.add(message_data)
            # google-cloud-firestore has returned both (update_time, doc_ref) and
            # (doc_ref, update_time) across versions. Extract the DocumentReference
            # defensively to avoid runtime failures.
            doc_ref = None
            if isinstance(add_result, tuple) and len(add_result) == 2:
                first, second = add_result
                if hasattr(first, "id"):
                    doc_ref = first
                elif hasattr(second, "id"):
                    doc_ref = second
            elif hasattr(add_result, "id"):
                doc_ref = add_result

            # Update session last_updated
            session_ref = self.db.collection(self._sessions_collection(user_id)).document(session_id)
            session_ref.update({"last_updated": now.isoformat()})

            logger.debug(f"Added {role} message to session {session_id[:8]}...")

            return {
                "message_id": getattr(doc_ref, "id", None),
                "role": role,
                "timestamp": now.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return {"error": str(e)}

    async def add_gemini_usage(
        self,
        user_id: str,
        session_id: str,
        usage: dict[str, Any],
        *,
        user_message_id: str | None = None,
        assistant_message_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Record Gemini usage for a single user turn.

        This writes to a `usage` subcollection under the session so it can be
        aggregated later (e.g., daily totals, per-user costs, error rates).
        """
        self._validate_user_id(user_id)

        try:
            now = datetime.now(timezone.utc)
            usage_data = {
                "timestamp": now.isoformat(),
                "usage": usage,
                "user_message_id": user_message_id,
                "assistant_message_id": assistant_message_id,
            }

            usage_ref = self.db.collection(
                f"{self._sessions_collection(user_id)}/{session_id}/usage"
            )
            add_result = usage_ref.add(usage_data)

            doc_ref = None
            if isinstance(add_result, tuple) and len(add_result) == 2:
                first, second = add_result
                if hasattr(first, "id"):
                    doc_ref = first
                elif hasattr(second, "id"):
                    doc_ref = second
            elif hasattr(add_result, "id"):
                doc_ref = add_result

            logger.debug(f"Recorded Gemini usage for session {session_id[:8]}...")
            return {"usage_id": getattr(doc_ref, "id", None), "timestamp": now.isoformat()}

        except Exception as e:
            logger.error(f"Error recording Gemini usage: {e}")
            return {"error": str(e)}

    async def get_session_history(
        self,
        user_id: str,
        session_id: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Get conversation history for a session.

        Args:
            user_id: The user's ID
            session_id: The session ID
            limit: Optional maximum number of recent messages to return.
                   If None, returns all messages.

        Returns:
            Dict with session metadata and messages
        """
        self._validate_user_id(user_id)

        try:
            # Get session document
            session_ref = self.db.collection(
                self._sessions_collection(user_id)
            ).document(session_id)
            session_doc = session_ref.get()

            if not session_doc.exists:
                return {"error": "Session not found"}

            session_data = session_doc.to_dict()

            # Get messages from subcollection
            messages_ref = self.db.collection(
                f"{self._sessions_collection(user_id)}/{session_id}/messages"
            )

            if limit:
                # Get most recent N messages: order DESC, limit, then reverse
                query = messages_ref.order_by(
                    "timestamp", direction=firestore.Query.DESCENDING
                ).limit(limit)
                message_docs = list(query.stream())
                message_docs.reverse()  # Restore chronological order
            else:
                # Get all messages in chronological order
                query = messages_ref.order_by("timestamp")
                message_docs = query.stream()

            messages = []
            for doc in message_docs:
                msg_data = doc.to_dict()
                messages.append({
                    "message_id": getattr(doc, "id", None),
                    "role": msg_data.get("role"),
                    "content": msg_data.get("content"),
                    "timestamp": msg_data.get("timestamp"),
                    "reasoning_trace": msg_data.get("reasoning_trace"),
                    "metadata": msg_data.get("metadata"),
                })

            return {
                "session_id": session_id,
                "user_id": user_id,
                "messages": messages,
                "created_at": session_data.get("created_at"),
                "last_updated": session_data.get("last_updated", session_data.get("created_at")),
            }

        except Exception as e:
            logger.error(f"Error getting session history: {e}")
            return {"error": str(e)}


# Singleton instance
_firestore_service: FirestoreService | None = None


def get_firestore_service() -> FirestoreService:
    """Get the Firestore service singleton."""
    global _firestore_service
    if _firestore_service is None:
        _firestore_service = FirestoreService()
    return _firestore_service
