"""
Main FastAPI application for Lenny Growth Assistant.
Provides endpoints for sessions, chat with grounded Q&A, Ship30 essay generation,
artifact generation, health checks, and config using Supabase REST backend.
"""
import os
import sys
import uuid
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure api and root directory are on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .database import (
        check_db_connection,
        create_session as create_session_db,
        list_sessions as list_sessions_db,
        get_session as get_session_db,
        delete_session as delete_session_db,
        create_message as create_message_db,
        get_session_messages as get_session_messages_db,
        store_message_citations,
        create_artifact as create_artifact_db,
        get_session_artifacts as get_session_artifacts_db,
        get_artifact as get_artifact_db,
    )
    from .retrieval import get_retrieval_service
    from .agents.orchestrator import get_agent_orchestrator
    from .providers.ollama_provider import get_provider
except ImportError:
    from database import (
        check_db_connection,
        create_session as create_session_db,
        list_sessions as list_sessions_db,
        get_session as get_session_db,
        delete_session as delete_session_db,
        create_message as create_message_db,
        get_session_messages as get_session_messages_db,
        store_message_citations,
        create_artifact as create_artifact_db,
        get_session_artifacts as get_session_artifacts_db,
        get_artifact as get_artifact_db,
    )
    from retrieval import get_retrieval_service
    from agents.orchestrator import get_agent_orchestrator
    from providers.ollama_provider import get_provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Lenny Growth Assistant API",
    description="Conversational RAG assistant for product management and growth strategy grounded in Lenny's Podcast transcripts.",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────────────────────────────────────

class CitationItem(BaseModel):
    episode_title: Optional[str] = None
    guest_name: Optional[str] = None
    source_path: Optional[str] = None
    relevance_score: Optional[float] = None
    approx_timestamp: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    provider: Optional[str] = None
    model_name: Optional[str] = None
    latency_ms: Optional[int] = None
    retrieval_score: Optional[float] = None
    created_at: Any
    citations: List[CitationItem] = []


class SessionCreate(BaseModel):
    title: Optional[str] = Field(None, description="Session title")
    user_id: Optional[str] = Field(None, description="User ID")


class SessionResponse(BaseModel):
    id: str
    title: Optional[str]
    user_id: Optional[str] = None
    active_provider: Optional[str] = "ollama"
    created_at: Any
    updated_at: Any


class ChatRequest(BaseModel):
    message: str = Field(..., description="User query or message")
    stream: bool = Field(False, description="Whether to stream response via SSE")
    top_k: int = Field(5, description="Number of transcript chunks to retrieve")


class ChatResponse(BaseModel):
    message_id: str
    session_id: str
    content: str
    provider: str
    model_name: str
    latency_ms: Optional[int] = None
    retrieval_score: Optional[float] = None
    citations: List[Dict[str, Any]] = []


class Ship30Request(BaseModel):
    topic: str = Field(..., description="Topic for the Ship 30 for 30 essay")
    stream: bool = Field(False, description="Whether to stream response via SSE")


class ArtifactRequest(BaseModel):
    content: str = Field(..., description="Content to transform into artifact")
    artifact_type: str = Field("markdown", description="Type: markdown or html")


class ArtifactResponse(BaseModel):
    id: str
    session_id: str
    message_id: Optional[str] = None
    artifact_type: str
    content: str
    word_count: int
    structure_valid: bool
    created_at: Any


class ProviderInfoResponse(BaseModel):
    provider: str
    model_name: str
    display_name: str
    available: bool
    host: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Health & Config Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Basic liveness probe."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready")
async def readiness_check():
    """Readiness check: verifies Supabase DB and LLM provider connectivity."""
    db_ok = check_db_connection()
    provider = get_provider()
    provider_ok = provider.is_available()

    if db_ok and provider_ok:
        return {
            "status": "ready",
            "database_ok": True,
            "provider_ok": True,
            "provider": provider.get_model_info(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE if not (db_ok and provider_ok) else status.HTTP_200_OK
    raise HTTPException(
        status_code=status_code,
        detail={
            "status": "not_ready",
            "database_ok": db_ok,
            "provider_ok": provider_ok,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.get("/config", response_model=ProviderInfoResponse)
async def get_config():
    """Return model provider configuration and availability."""
    provider = get_provider()
    info = provider.get_model_info()
    return ProviderInfoResponse(
        provider=info.get("provider", "ollama"),
        model_name=info.get("model_name", "llama3.1:8b"),
        display_name=info.get("display_name", "Ollama · llama3.1:8b"),
        available=info.get("available", False),
        host=info.get("host"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Session Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(session_data: SessionCreate):
    """Create a new chat session."""
    session = create_session_db(
        title=session_data.title,
        user_id=session_data.user_id,
        active_provider=os.getenv("LLM_PROVIDER", "ollama"),
    )
    return SessionResponse(
        id=session["id"],
        title=session.get("title"),
        user_id=session.get("user_id"),
        active_provider=session.get("active_provider", "ollama"),
        created_at=session.get("created_at"),
        updated_at=session.get("updated_at"),
    )


@app.get("/sessions", response_model=List[SessionResponse])
async def list_sessions():
    """List all sessions ordered by last updated."""
    sessions = list_sessions_db()
    return [
        SessionResponse(
            id=s["id"],
            title=s.get("title"),
            user_id=s.get("user_id"),
            active_provider=s.get("active_provider", "ollama"),
            created_at=s.get("created_at"),
            updated_at=s.get("updated_at"),
        )
        for s in sessions
    ]


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get single session by ID."""
    session = get_session_db(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        id=session["id"],
        title=session.get("title"),
        user_id=session.get("user_id"),
        active_provider=session.get("active_provider", "ollama"),
        created_at=session.get("created_at"),
        updated_at=session.get("updated_at"),
    )


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all related messages, citations, and artifacts."""
    success = delete_session_db(session_id)
    return {"message": "Session deleted successfully", "id": session_id, "success": success}


# ──────────────────────────────────────────────────────────────────────────────
# Message & Chat Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(session_id: str):
    """Retrieve all messages in a session with citations."""
    messages = get_session_messages_db(session_id)
    return [
        MessageResponse(
            id=m["id"],
            session_id=m["session_id"],
            role=m["role"],
            content=m["content"],
            provider=m.get("provider"),
            model_name=m.get("model_name"),
            latency_ms=m.get("latency_ms"),
            retrieval_score=m.get("retrieval_score"),
            created_at=m.get("created_at"),
            citations=[CitationItem(**c) for c in m.get("citations", [])],
        )
        for m in messages
    ]


@app.post("/sessions/{session_id}/messages")
async def chat(
    session_id: str,
    chat_req: ChatRequest,
):
    """
    Main conversational QA endpoint.
    Retrieves grounded context from Lenny transcripts and generates an answer.
    Supports standard JSON and Server-Sent Events streaming.
    """
    session = get_session_db(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Save user message
    user_msg = create_message_db(
        session_id=session_id,
        role="user",
        content=chat_req.message,
    )

    # 2. Get history
    history_records = get_session_messages_db(session_id)
    conversation_history = [
        {"role": m["role"], "content": m["content"]} for m in history_records
    ]

    orchestrator = get_agent_orchestrator()

    if chat_req.stream:
        async def stream_generator():
            try:
                result = await orchestrator.execute_qa(
                    query=chat_req.message,
                    conversation_history=conversation_history,
                    top_k=chat_req.top_k,
                )
                answer = result.get("answer", "")
                latency_ms = result.get("latency_ms", 0)
                retrieval_score = result.get("retrieval_score")
                citations = result.get("citations", [])

                # Save assistant message
                asst_msg = create_message_db(
                    session_id=session_id,
                    role="assistant",
                    content=answer,
                    provider="ollama",
                    model_name=os.getenv("LLM_MODEL", "llama3.1:8b"),
                    latency_ms=latency_ms,
                    retrieval_score=retrieval_score,
                )

                if citations:
                    store_message_citations(asst_msg["id"], citations)

                # Stream out tokens
                words = answer.split(" ")
                for i, word in enumerate(words):
                    chunk_text = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk_text})}\n\n"
                    await asyncio.sleep(0.01)

                final_payload = {
                    "type": "done",
                    "message_id": asst_msg["id"],
                    "session_id": session_id,
                    "content": answer,
                    "provider": asst_msg.get("provider", "ollama"),
                    "model_name": asst_msg.get("model_name", "llama3.1:8b"),
                    "latency_ms": latency_ms,
                    "retrieval_score": retrieval_score,
                    "citations": citations,
                }
                yield f"data: {json.dumps(final_payload)}\n\n"
            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Non-streaming response
    try:
        result = await orchestrator.execute_qa(
            query=chat_req.message,
            conversation_history=conversation_history,
            top_k=chat_req.top_k,
        )

        answer = result.get("answer", "")
        latency_ms = result.get("latency_ms", 0)
        retrieval_score = result.get("retrieval_score")
        citations = result.get("citations", [])

        asst_msg = create_message_db(
            session_id=session_id,
            role="assistant",
            content=answer,
            provider="ollama",
            model_name=os.getenv("LLM_MODEL", "llama3.1:8b"),
            latency_ms=latency_ms,
            retrieval_score=retrieval_score,
        )

        if citations:
            store_message_citations(asst_msg["id"], citations)

        return ChatResponse(
            message_id=asst_msg["id"],
            session_id=session_id,
            content=answer,
            provider=asst_msg.get("provider", "ollama"),
            model_name=asst_msg.get("model_name", "llama3.1:8b"),
            latency_ms=latency_ms,
            retrieval_score=retrieval_score,
            citations=citations,
        )
    except Exception as e:
        logger.error(f"Chat execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")


# ──────────────────────────────────────────────────────────────────────────────
# Ship 30 for 30 Essay Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/sessions/{session_id}/ship30")
async def generate_ship30(
    session_id: str,
    req: Ship30Request,
):
    """
    Generate a Ship 30 for 30 essay grounded in podcast transcripts.
    Saves an assistant message and an Artifact record.
    """
    session = get_session_db(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    create_message_db(
        session_id=session_id,
        role="user",
        content=f"Write a Ship 30 for 30 essay on: {req.topic}",
    )

    orchestrator = get_agent_orchestrator()

    try:
        result = await orchestrator.execute_ship30(topic=req.topic)
        essay_content = result.get("essay", "")
        word_count = result.get("word_count", 0)
        validation = result.get("validation", {})
        latency_ms = result.get("latency_ms", 0)

        asst_msg = create_message_db(
            session_id=session_id,
            role="assistant",
            content=essay_content,
            provider="ollama",
            model_name=os.getenv("LLM_MODEL", "llama3.1:8b"),
            latency_ms=latency_ms,
        )

        artifact = create_artifact_db(
            session_id=session_id,
            message_id=asst_msg["id"],
            kind="ship30",
            content=essay_content,
            word_count=word_count,
            structure_valid=validation.get("passed", False),
        )

        return {
            "message_id": asst_msg["id"],
            "artifact_id": artifact["id"],
            "session_id": session_id,
            "essay": essay_content,
            "word_count": word_count,
            "validation": validation,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        logger.error(f"Ship30 generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate essay: {str(e)}")


# ──────────────────────────────────────────────────────────────────────────────
# Artifact Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/sessions/{session_id}/artifacts", response_model=ArtifactResponse)
async def create_artifact(
    session_id: str,
    req: ArtifactRequest,
):
    """Generate a Markdown or HTML artifact from text or conversation content."""
    session = get_session_db(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    orchestrator = get_agent_orchestrator()

    try:
        result = await orchestrator.execute_artifact(
            content=req.content,
            artifact_type=req.artifact_type,
        )

        artifact = create_artifact_db(
            session_id=session_id,
            kind=req.artifact_type,
            content=result.get("artifact", ""),
            word_count=result.get("word_count", 0),
            structure_valid=result.get("validation", {}).get("passed", False),
        )

        return ArtifactResponse(
            id=artifact["id"],
            session_id=artifact["session_id"],
            message_id=artifact.get("message_id"),
            artifact_type=artifact.get("kind", req.artifact_type),
            content=artifact["content"],
            word_count=artifact["word_count"],
            structure_valid=artifact["structure_valid"],
            created_at=artifact["created_at"],
        )
    except Exception as e:
        logger.error(f"Artifact generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create artifact: {str(e)}")


@app.get("/sessions/{session_id}/artifacts", response_model=List[ArtifactResponse])
async def get_session_artifacts(session_id: str):
    """List all artifacts generated in a session."""
    artifacts = get_session_artifacts_db(session_id)
    return [
        ArtifactResponse(
            id=a["id"],
            session_id=a["session_id"],
            message_id=a.get("message_id"),
            artifact_type=a.get("kind", "markdown"),
            content=a["content"],
            word_count=a.get("word_count", 0),
            structure_valid=a.get("structure_valid", False),
            created_at=a["created_at"],
        )
        for a in artifacts
    ]


@app.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str):
    """Retrieve an artifact by its ID."""
    artifact = get_artifact_db(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return ArtifactResponse(
        id=artifact["id"],
        session_id=artifact["session_id"],
        message_id=artifact.get("message_id"),
        artifact_type=artifact.get("kind", "markdown"),
        content=artifact["content"],
        word_count=artifact.get("word_count", 0),
        structure_valid=artifact.get("structure_valid", False),
        created_at=artifact["created_at"],
    )


# ──────────────────────────────────────────────────────────────────────────────
# Ingestion Trigger
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/ingest/run")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """Trigger the transcript ingestion pipeline as a background task."""
    try:
        from ingestion.pipeline import TranscriptIngestionPipeline

        def _run():
            pipeline = TranscriptIngestionPipeline()
            pipeline.run()

        background_tasks.add_task(_run)
        return {"message": "Ingestion pipeline triggered in background"}
    except Exception as e:
        logger.error(f"Failed to trigger ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger ingestion: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)