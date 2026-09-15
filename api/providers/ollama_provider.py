"""
Ollama local model provider for Lenny Growth Assistant.
Uses the Ollama /api/chat endpoint (chat format with message history).
"""
import os
import json
import logging
from typing import AsyncIterator, List, Optional, Dict, Any

import aiohttp
from .base_provider import (
    ModelProvider,
    GenerationConfig,
    ProviderUnavailableError,
    ProviderExecutionError,
)

logger = logging.getLogger(__name__)


class OllamaProvider(ModelProvider):
    """Ollama local model provider using /api/chat."""

    def __init__(self, host: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__("ollama")
        self.model_name = model_name or os.getenv("LLM_MODEL", "llama3.1:8b")
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        logger.info(f"OllamaProvider initialized: {self.model_name} @ {self.host}")

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> AsyncIterator[str]:
        """
        Stream tokens from Ollama /api/chat.

        messages must be in [{"role": "user"|"assistant", "content": str}] format.
        system is prepended as a system message if provided.
        """
        if config is None:
            config = GenerationConfig()

        # Build the messages list in Ollama chat format
        chat_messages = []
        if system:
            chat_messages.append({"role": "system", "content": system})
        chat_messages.extend(messages)

        payload = {
            "model": self.model_name,
            "messages": chat_messages,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "num_predict": min(config.max_tokens, 400),
                "num_ctx": 2048,
            },
        }
        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        try:
            logger.info(f"Calling Ollama ({self.model_name}) at {self.host}/api/chat...")
            timeout = aiohttp.ClientTimeout(total=300, connect=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.host}/api/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ProviderExecutionError(
                            f"Ollama returned HTTP {response.status}: {error_text}"
                        )

                    token_count = 0
                    async for line in response.content:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            if "message" in chunk:
                                token = chunk["message"].get("content", "")
                                if token:
                                    token_count += 1
                                    yield token
                            if chunk.get("done", False):
                                logger.info(f"Ollama generation finished ({token_count} tokens).")
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode Ollama chunk: {line!r}")
                            continue

        except ProviderExecutionError:
            raise
        except aiohttp.ClientConnectorError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Ollama at {self.host}. "
                f"Is Ollama running? Error: {e}"
            )
        except Exception as e:
            raise ProviderExecutionError(f"Ollama generation failed: {e}") from e

    def is_available(self) -> bool:
        """Check if Ollama is reachable (synchronous probe)."""
        import urllib.request
        import urllib.error

        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=5) as r:
                return r.status == 200
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "ollama",
            "model_name": self.model_name,
            "display_name": f"Ollama · {self.model_name}",
            "available": self.is_available(),
            "host": self.host,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Singleton / factory used by main.py and agents
# ──────────────────────────────────────────────────────────────────────────────

_provider_instance: Optional[OllamaProvider] = None


def get_provider() -> OllamaProvider:
    """Return the configured OllamaProvider singleton."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = OllamaProvider()
        logger.info(
            f"Initialized Ollama provider: {_provider_instance.model_name}"
        )
    return _provider_instance