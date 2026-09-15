"""
Base model provider interface for Lenny Growth Assistant.
"""
import os
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = True
    stop_sequences: List[str] = field(default_factory=list)


class ProviderError(Exception):
    """Base provider exception."""


class ProviderUnavailableError(ProviderError):
    """Provider is not reachable or not configured."""


class ProviderExecutionError(ProviderError):
    """Error during generation."""


class ModelProvider(ABC):
    """Abstract base class for all model providers."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> AsyncIterator[str]:
        """
        Generate a response for the given messages.

        Args:
            messages: List of {"role": "user"|"assistant", "content": str}
            system:   Optional system prompt
            config:   Generation hyperparameters

        Yields:
            Text chunks as they are generated.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is reachable right now."""

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Return a dict with provider, model_name, display_name, available."""