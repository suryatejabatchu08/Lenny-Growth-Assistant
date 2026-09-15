"""
Supabase Database Service for Lenny Growth Assistant.
Provides high-reliability CRUD operations for users, sessions, messages,
citations, and artifacts using the Supabase REST Client over HTTPS (Port 443).
"""
import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

try:
    from .supabase_client import get_supabase_client
except ImportError:
    from supabase_client import get_supabase_client

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_db_connection() -> bool:
    """Check Supabase database connectivity via REST health probe."""
    try:
        client = get_supabase_client()
        # Query 1 row from sessions or transcript_chunks to verify connection
        client.table("sessions").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Supabase connection check failed: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Session Operations
# ──────────────────────────────────────────────────────────────────────────────

def create_session(title: Optional[str] = None, user_id: Optional[str] = None, active_provider: str = "ollama") -> Dict[str, Any]:
    """Create a new chat session in Supabase."""
    client = get_supabase_client()
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    data = {
        "id": session_id,
        "title": title or f"Chat {datetime.utcnow().strftime('%b %d, %H:%M')}",
        "active_provider": active_provider,
        "created_at": now,
        "updated_at": now,
    }
    if user_id:
        data["user_id"] = user_id

    res = client.table("sessions").insert(data).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    return data


def list_sessions() -> List[Dict[str, Any]]:
    """List all sessions ordered by updated_at descending."""
    client = get_supabase_client()
    res = client.table("sessions").select("*").order("updated_at", desc=True).execute()
    return res.data or []


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get a single session by its UUID."""
    client = get_supabase_client()
    res = client.table("sessions").select("*").eq("id", session_id).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    return None


def delete_session(session_id: str) -> bool:
    """Delete a session and all cascading records."""
    client = get_supabase_client()
    # Delete child records first to ensure clean deletion
    try:
        client.table("artifacts").delete().eq("session_id", session_id).execute()
        client.table("messages").delete().eq("session_id", session_id).execute()
    except Exception as e:
        logger.warning(f"Error cleaning child records for session {session_id}: {e}")

    res = client.table("sessions").delete().eq("id", session_id).execute()
    return bool(res.data)


def touch_session(session_id: str):
    """Update session updated_at timestamp."""
    try:
        client = get_supabase_client()
        client.table("sessions").update({"updated_at": datetime.utcnow().isoformat()}).eq("id", session_id).execute()
    except Exception as e:
        logger.warning(f"Failed to touch session {session_id}: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Message & Citation Operations
# ──────────────────────────────────────────────────────────────────────────────

def create_message(
    session_id: str,
    role: str,
    content: str,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    latency_ms: Optional[int] = None,
    retrieval_score: Optional[float] = None,
) -> Dict[str, Any]:
    """Store a message in the messages table."""
    client = get_supabase_client()
    message_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    data = {
        "id": message_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "created_at": now,
    }
    if provider:
        data["provider"] = provider
    if model_name:
        data["model_name"] = model_name
    if latency_ms is not None:
        data["latency_ms"] = latency_ms
    if retrieval_score is not None:
        data["retrieval_score"] = float(retrieval_score)

    res = client.table("messages").insert(data).execute()
    
    # If this is a user message, check if the session title is still default, and update it to the user's prompt
    if role == "user":
        try:
            sess = client.table("sessions").select("title").eq("id", session_id).execute()
            if sess.data and len(sess.data) > 0:
                current_title = sess.data[0].get("title", "")
                # If title starts with 'New Chat' or 'Chat ' or is empty, rename to first user query
                if not current_title or current_title.startswith("Chat ") or current_title.startswith("New Chat"):
                    clean_title = content.replace("Write a Ship 30 for 30 essay on:", "").strip()
                    # Truncate to reasonable length (e.g. 45 chars)
                    new_title = clean_title[:45] + ("..." if len(clean_title) > 45 else "")
                    if new_title:
                        client.table("sessions").update({
                            "title": new_title,
                            "updated_at": now
                        }).eq("id", session_id).execute()
        except Exception as e:
            logger.warning(f"Failed to auto-title session: {e}")

    touch_session(session_id)
    if res.data and len(res.data) > 0:
        return res.data[0]
    return data


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """Get all messages for a session with citations."""
    client = get_supabase_client()
    res = (
        client.table("messages")
        .select("*, message_citations(*, transcript_chunks(episode_title, guest_name, source_path, approx_timestamp))")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )

    messages = res.data or []
    formatted = []
    for msg in messages:
        citations = []
        raw_citations = msg.get("message_citations") or []
        for c in raw_citations:
            chunk = c.get("transcript_chunks") or {}
            citations.append({
                "episode_title": chunk.get("episode_title"),
                "guest_name": chunk.get("guest_name"),
                "source_path": chunk.get("source_path"),
                "relevance_score": c.get("relevance_score"),
                "approx_timestamp": chunk.get("approx_timestamp"),
            })

        formatted.append({
            "id": msg["id"],
            "session_id": msg["session_id"],
            "role": msg["role"],
            "content": msg["content"],
            "provider": msg.get("provider"),
            "model_name": msg.get("model_name"),
            "latency_ms": msg.get("latency_ms"),
            "retrieval_score": msg.get("retrieval_score"),
            "created_at": msg.get("created_at"),
            "citations": citations,
        })

    return formatted


def store_message_citations(message_id: str, citations: List[Dict[str, Any]]):
    """Store citation records linking a message to chunks."""
    if not citations:
        return

    client = get_supabase_client()
    rows = []
    for c in citations:
        chunk_id = c.get("chunk_id") or c.get("id")
        if chunk_id:
            rows.append({
                "id": str(uuid.uuid4()),
                "message_id": message_id,
                "chunk_id": chunk_id,
                "relevance_score": float(c.get("relevance_score", 0.0)),
            })

    if rows:
        try:
            client.table("message_citations").insert(rows).execute()
        except Exception as e:
            logger.warning(f"Failed to insert citations: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Artifact Operations
# ──────────────────────────────────────────────────────────────────────────────

def create_artifact(
    session_id: str,
    kind: str,
    content: str,
    word_count: int,
    structure_valid: bool,
    message_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Store a generated artifact in Supabase."""
    client = get_supabase_client()
    artifact_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    data = {
        "id": artifact_id,
        "session_id": session_id,
        "kind": kind,
        "content": content,
        "word_count": word_count,
        "structure_valid": structure_valid,
        "created_at": now,
    }
    if message_id:
        data["message_id"] = message_id

    res = client.table("artifacts").insert(data).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    return data


def get_session_artifacts(session_id: str) -> List[Dict[str, Any]]:
    """Retrieve all artifacts for a session."""
    client = get_supabase_client()
    res = (
        client.table("artifacts")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single artifact by its ID."""
    client = get_supabase_client()
    res = client.table("artifacts").select("*").eq("id", artifact_id).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    return None