"""
Retrieval service for Lenny Growth Assistant.
Uses Supabase RPC (match_chunks) for vector similarity search.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RetrievalService:
    """Embed queries and search transcript_chunks via Supabase RPC."""

    def __init__(self):
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.default_top_k = int(os.getenv("RETRIEVAL_TOP_K", "5"))
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))

        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
        logger.info(f"Embedding model loaded — dimension: {self.embedding_dimension}")

    def embed_query(self, text: str) -> List[float]:
        """Embed a query string and return a list of floats."""
        embedding = self.embedding_model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

    def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Call the Supabase `match_chunks` RPC function.
        Returns a list of chunks with metadata and similarity scores.
        """
        try:
            from .supabase_client import get_supabase_client
        except ImportError:
            try:
                from supabase_client import get_supabase_client
            except ImportError:
                from api.supabase_client import get_supabase_client

        if top_k is None:
            top_k = self.default_top_k
        if threshold is None:
            threshold = self.similarity_threshold

        client = get_supabase_client()

        response = client.rpc(
            "match_chunks",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": top_k,
            },
        ).execute()

        chunks = response.data or []
        logger.info(f"Vector search returned {len(chunks)} chunks (threshold={threshold})")
        return chunks

    def retrieve_context(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], float]:
        """
        Full retrieval pipeline:
          1. Embed the query.
          2. Search similar chunks via Supabase RPC.
          3. Assemble a source-attributed context block.

        Returns:
            (chunks, context_block_string, aggregate_retrieval_score)
        """
        query_embedding = self.embed_query(query)
        chunks = self.search_similar_chunks(query_embedding, top_k)

        if not chunks:
            logger.warning("No chunks found above similarity threshold")
            return [], None, 0.0

        # Aggregate score (mean of top-k similarities)
        retrieval_score = float(
            np.mean([chunk.get("similarity", 0.0) for chunk in chunks])
        )

        # Build a source-attributed context block for the prompt (trimmed for CPU speed)
        context_parts = []
        for chunk in chunks:
            source_line = f"[Source: {chunk['episode_title']} — {chunk['guest_name']}]"
            content_words = chunk['content'].split()
            # Trim chunk to first 180 words if longer to keep prompt small and fast
            trimmed_content = " ".join(content_words[:180])
            context_parts.append(f"{source_line}\n{trimmed_content}")

        context_block = "\n\n---\n\n".join(context_parts)

        logger.info(
            f"Retrieved {len(chunks)} chunks, aggregate score: {retrieval_score:.3f}"
        )
        return chunks, context_block, retrieval_score

    def retrieve_with_followup_context(
        self,
        query: str,
        conversation_history: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], float]:
        """
        Retrieve context considering conversation history.
        For follow-up questions, we augment the query with the last user turn
        so the embedding captures the conversational context.
        """
        augmented_query = query

        # If there is prior history, prepend the last user message for better recall
        if conversation_history:
            prior_user_msgs = [
                m["content"] for m in conversation_history
                if m.get("role") == "user"
            ]
            if prior_user_msgs:
                # Blend current query with the most recent prior question
                augmented_query = f"{prior_user_msgs[-1]} {query}"

        return self.retrieve_context(augmented_query, top_k)


# ──────────────────────────────────────────────────────────────────────────────
# Singleton + convenience helpers
# ──────────────────────────────────────────────────────────────────────────────

_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service


def retrieve_transcripts(
    query: str, top_k: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], Optional[str], float]:
    """Convenience wrapper."""
    return get_retrieval_service().retrieve_context(query, top_k)