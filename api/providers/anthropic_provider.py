"""
Anthropic provider stub — kept for future use.
Disabled: ANTHROPIC_API_KEY is not configured for this deployment.
"""
from typing import AsyncIterator, List, Optional, Dict, Any
from .base_provider import ModelProvider, GenerationConfig, ProviderUnavailableError


class AnthropicProvider(ModelProvider):
    """Stub — Anthropic is not the active provider in this deployment."""

    def __init__(self, **kwargs):
        super().__init__("anthropic")

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> AsyncIterator[str]:
        raise ProviderUnavailableError(
            "Anthropic provider is not configured. Set LLM_PROVIDER=ollama and "
            "ensure Ollama is running."
        )
        # make this a valid async generator
        return
        yield  # noqa: unreachable — needed to satisfy the type checker

    def is_available(self) -> bool:
        return False

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "anthropic",
            "model_name": "not configured",
            "display_name": "Anthropic (disabled)",
            "available": False,
        }