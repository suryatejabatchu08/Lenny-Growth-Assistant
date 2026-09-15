"""
Supabase client singleton for Lenny Growth Assistant.
Used by the retrieval service and ingestion pipeline for vector search via RPC.
"""
import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Get or create the Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment"
            )
        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized")
    return _supabase_client
