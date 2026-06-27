"""
Firestore service for JustiBot chat persistence.
Manages user sessions and message history in Cloud Firestore.

Data model:
  users/{user_uid}/sessions/{session_id}              — session metadata
  users/{user_uid}/sessions/{session_id}/messages/{}  — individual messages
"""

import logging
from datetime import datetime, timezone

import firebase_admin.firestore
from google.cloud import firestore

logger = logging.getLogger(__name__)


def _ts_to_iso(value) -> str:
    """Convert a Firestore timestamp or datetime to ISO 8601 string."""
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    # Firestore DatetimeWithNanoseconds has a timestamp() method
    if hasattr(value, "timestamp"):
        return datetime.fromtimestamp(value.timestamp(), tz=timezone.utc).isoformat()
    return str(value)


class FirestoreService:
    """
    Wrapper around Cloud Firestore for chat session and message persistence.
    Firebase Admin is already initialised by the auth middleware — do NOT
    call firebase_admin.initialize_app() here.
    """

    def __init__(self):
        self.db = firebase_admin.firestore.client()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _session_ref(self, user_uid: str, session_id: str):
        return self.db.collection("users").document(user_uid) \
                      .collection("sessions").document(session_id)

    def _messages_ref(self, user_uid: str, session_id: str):
        return self._session_ref(user_uid, session_id).collection("messages")

    @staticmethod
    def _doc_to_dict(doc) -> dict:
        """Convert a Firestore document snapshot to a plain dict."""
        data = doc.to_dict() or {}
        # Normalise all timestamp fields to ISO strings
        for field in ("created_at", "updated_at"):
            if field in data:
                data[field] = _ts_to_iso(data[field])
        return data

    # ── Session CRUD ─────────────────────────────────────────────────────────

    async def create_session(
        self,
        user_uid: str,
        session_id: str,
        first_message: str,
    ) -> dict:
        """Create a new session document and return its metadata."""
        title = first_message[:60] + ("..." if len(first_message) > 60 else "")
        now_iso = datetime.now(timezone.utc).isoformat()

        doc_data = {
            "session_id": session_id,
            "title": title,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "message_count": 0,
        }
        self._session_ref(user_uid, session_id).set(doc_data)

        # Return dict with readable timestamps instead of SERVER_TIMESTAMP sentinel
        return {
            "session_id": session_id,
            "title": title,
            "created_at": now_iso,
            "updated_at": now_iso,
            "message_count": 0,
        }

    async def get_sessions(self, user_uid: str) -> list[dict]:
        """Return up to 50 sessions for a user, newest first."""
        try:
            query = (
                self.db.collection("users").document(user_uid)
                    .collection("sessions")
                    .order_by("updated_at", direction=firestore.Query.DESCENDING)
                    .limit(50)
            )
            docs = query.stream()
            sessions = []
            for doc in docs:
                data = self._doc_to_dict(doc)
                if "session_id" not in data:
                    data["session_id"] = doc.id
                sessions.append(data)
            return sessions
        except Exception as exc:
            logger.error("[FIRESTORE] get_sessions failed for uid=%s: %s", user_uid, exc)
            return []

    async def get_session(
        self,
        user_uid: str,
        session_id: str,
    ) -> dict | None:
        """Return a single session document, or None if it doesn't exist."""
        try:
            doc = self._session_ref(user_uid, session_id).get()
            if not doc.exists:
                return None
            data = self._doc_to_dict(doc)
            if "session_id" not in data:
                data["session_id"] = doc.id
            return data
        except Exception as exc:
            logger.error("[FIRESTORE] get_session failed: %s", exc)
            return None

    async def delete_session(
        self,
        user_uid: str,
        session_id: str,
    ) -> bool:
        """
        Delete a session and all its messages.
        Returns True if the session existed, False otherwise.
        """
        session_ref = self._session_ref(user_uid, session_id)
        doc = session_ref.get()
        if not doc.exists:
            return False

        # Delete messages in batches of 500
        messages_ref = self._messages_ref(user_uid, session_id)
        while True:
            batch_docs = list(messages_ref.limit(500).stream())
            if not batch_docs:
                break
            batch = self.db.batch()
            for msg_doc in batch_docs:
                batch.delete(msg_doc.reference)
            batch.commit()

        session_ref.delete()
        return True

    # ── Message CRUD ─────────────────────────────────────────────────────────

    async def save_message(
        self,
        user_uid: str,
        session_id: str,
        role: str,
        content: str,
        sources: list = [],
        cached: bool = False,
    ) -> str:
        """
        Append a message to the session and update session metadata.
        Returns the auto-generated message_id.
        """
        msg_data = {
            "role": role,
            "content": content,
            "sources": sources,
            "cached": cached,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        _, doc_ref = self._messages_ref(user_uid, session_id).add(msg_data)

        # Update parent session
        self._session_ref(user_uid, session_id).update({
            "updated_at": firestore.SERVER_TIMESTAMP,
            "message_count": firestore.Increment(1),
        })

        return doc_ref.id

    async def get_messages(
        self,
        user_uid: str,
        session_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """Return messages for a session, oldest first, capped at `limit`."""
        try:
            query = (
                self._messages_ref(user_uid, session_id)
                    .order_by("created_at", direction=firestore.Query.ASCENDING)
                    .limit(limit)
            )
            docs = query.stream()
            messages = []
            for doc in docs:
                data = doc.to_dict() or {}
                data["message_id"] = doc.id
                data["created_at"] = _ts_to_iso(data.get("created_at"))
                messages.append(data)
            return messages
        except Exception as exc:
            logger.error("[FIRESTORE] get_messages failed: %s", exc)
            return []

    # ── Utilities ─────────────────────────────────────────────────────────────

    async def update_session_title(
        self,
        user_uid: str,
        session_id: str,
        title: str,
    ) -> None:
        """Update the title field of a session."""
        self._session_ref(user_uid, session_id).update({"title": title})
