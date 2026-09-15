"""
Transcript Ingestion Pipeline for Lenny Growth Assistant.
Clones/updates the podcast transcripts repository, chunks the markdown files,
generates normalized embeddings with SentenceTransformer, and stores vectors into Supabase via REST/PostgREST.
"""
import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
import git
import markdown
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class TranscriptIngestionPipeline:
    """End-to-end ingestion from GitHub transcripts repo into Supabase pgvector."""

    def __init__(self):
        self.repo_url = os.getenv(
            "TRANSCRIPT_REPO_URL",
            "https://github.com/ChatPRD/lennys-podcast-transcripts.git",
        )
        self.local_repo_path = Path(
            os.getenv("TRANSCRIPT_REPO_PATH", "./data/transcripts")
        )
        self.embedding_model_name = os.getenv(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
        self.chunk_size_words = int(os.getenv("CHUNK_SIZE_TOKENS", "400"))
        self.chunk_overlap_words = int(os.getenv("CHUNK_OVERLAP", "50"))
        self.batch_size = int(os.getenv("INGESTION_BATCH_SIZE", "50"))

        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        logger.info("Embedding model loaded successfully.")

        # Initialize Supabase client
        try:
            from api.supabase_client import get_supabase_client
            self.supabase = get_supabase_client()
            logger.info("Connected to Supabase REST API.")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    def clone_or_update_repo(self) -> Path:
        """Clone the transcripts repository or pull the latest commits if already present."""
        self.local_repo_path.parent.mkdir(parents=True, exist_ok=True)

        if self.local_repo_path.exists() and (self.local_repo_path / ".git").exists():
            logger.info(f"Pulling latest updates in {self.local_repo_path}...")
            try:
                repo = git.Repo(self.local_repo_path)
                origin = repo.remotes.origin
                origin.pull()
                logger.info("Repository updated successfully.")
            except Exception as e:
                logger.warning(f"Failed to pull latest git changes: {e}. Proceeding with existing local files.")
        else:
            logger.info(f"Cloning {self.repo_url} into {self.local_repo_path}...")
            git.Repo.clone_from(self.repo_url, str(self.local_repo_path), depth=1)
            logger.info("Clone completed.")

        return self.local_repo_path

    def parse_transcript_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a transcript markdown file, extracting metadata and raw text."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        metadata = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                content = parts[2]
                for line in frontmatter.strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip().strip('"\'')

        html = markdown.markdown(content)
        soup = BeautifulSoup(html, "html.parser")
        text_content = soup.get_text()

        episode_slug = file_path.parent.name
        if episode_slug in (".", "episodes", ""):
            episode_slug = file_path.stem

        episode_title = metadata.get(
            "title", episode_slug.replace("-", " ").title()
        )
        guest_name = metadata.get(
            "guest",
            metadata.get(
                "guest_name",
                episode_title.split(" - ")[-1] if " - " in episode_title else "Lenny Rachitsky",
            ),
        )

        try:
            rel_path = str(file_path.relative_to(self.local_repo_path))
        except ValueError:
            rel_path = str(file_path)

        return {
            "episode_slug": episode_slug,
            "episode_title": episode_title,
            "guest_name": guest_name,
            "content": text_content,
            "source_path": rel_path,
            "approx_timestamp": metadata.get("timestamp", "00:00:00"),
        }

    def chunk_text(self, text: str) -> List[str]:
        """Split text into word-based chunks with overlap."""
        words = text.split()
        if not words:
            return []

        chunks = []
        step = max(1, self.chunk_size_words - self.chunk_overlap_words)
        for i in range(0, len(words), step):
            chunk_words = words[i : i + self.chunk_size_words]
            chunk_str = " ".join(chunk_words).strip()
            if len(chunk_str) > 50:  # Ignore tiny trailing fragments
                chunks.append(chunk_str)
            if i + self.chunk_size_words >= len(words):
                break

        return chunks

    def store_chunks_batch(self, chunks_batch: List[Dict[str, Any]], max_retries: int = 3):
        """Insert a batch of chunk records into Supabase transcript_chunks via REST API."""
        if not chunks_batch:
            return

        for attempt in range(1, max_retries + 1):
            try:
                self.supabase.table("transcript_chunks").insert(chunks_batch).execute()
                logger.info(f"Successfully stored {len(chunks_batch)} chunks into Supabase.")
                return
            except Exception as e:
                logger.warning(f"Batch insert attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to insert batch after {max_retries} attempts.")
                    raise

    def run(self):
        """Execute the complete ingestion workflow."""
        logger.info("Starting transcript ingestion pipeline...")
        repo_path = self.clone_or_update_repo()

        # Find markdown files
        markdown_files = list(repo_path.glob("episodes/**/*.md")) + list(
            repo_path.glob("**/*transcript*.md")
        )
        unique_files = sorted(list(set(markdown_files)))
        logger.info(f"Discovered {len(unique_files)} transcript files to ingest.")

        if not unique_files:
            unique_files = sorted(list(set(repo_path.glob("**/*.md"))))
            logger.info(f"Fallback discovered {len(unique_files)} markdown files.")

        total_chunks = 0
        current_batch = []

        for f_idx, file_path in enumerate(unique_files, 1):
            try:
                transcript_meta = self.parse_transcript_file(file_path)
                text_chunks = self.chunk_text(transcript_meta["content"])
                if not text_chunks:
                    continue

                # Generate normalized embeddings for cosine similarity
                embeddings = self.embedding_model.encode(
                    text_chunks, normalize_embeddings=True
                ).tolist()

                for chunk_idx, (chunk_text, embedding) in enumerate(
                    zip(text_chunks, embeddings)
                ):
                    chunk_item = {
                        "episode_slug": transcript_meta["episode_slug"],
                        "episode_title": transcript_meta["episode_title"],
                        "guest_name": transcript_meta["guest_name"],
                        "source_path": transcript_meta["source_path"],
                        "approx_timestamp": transcript_meta["approx_timestamp"],
                        "chunk_index": chunk_idx,
                        "content": chunk_text,
                        "embedding": embedding,
                    }
                    current_batch.append(chunk_item)
                    total_chunks += 1

                    if len(current_batch) >= self.batch_size:
                        self.store_chunks_batch(current_batch)
                        current_batch = []

                logger.info(
                    f"[{f_idx}/{len(unique_files)}] Processed '{transcript_meta['episode_title']}' ({len(text_chunks)} chunks)"
                )
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")

        # Flush remaining batch
        if current_batch:
            self.store_chunks_batch(current_batch)

        logger.info(f"Ingestion completed! Total chunks stored in Supabase: {total_chunks}")


if __name__ == "__main__":
    pipeline = TranscriptIngestionPipeline()
    pipeline.run()