"""
Artifact Generation Agent Skill for Lenny Growth Assistant.
Converts conversation content into polished Markdown or self-contained HTML artifacts.
"""
import os
import re
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentExecutionError, AgentValidationError
from ..providers.ollama_provider import get_provider
from ..providers.base_provider import GenerationConfig, ProviderUnavailableError

logger = logging.getLogger(__name__)

MARKDOWN_SYSTEM_PROMPT = """You are a professional technical writer.

Convert the conversation content below into a well-structured Markdown document.
The document should be publication-ready: clear headings, concise paragraphs, bullet points where appropriate,
and any insights properly attributed.

OUTPUT FORMAT:
- Start with a # Title
- Use ## for major sections
- Use **bold** for key terms
- Use > blockquotes for notable quotes from transcript sources
- End with a "## Key Takeaways" section

Produce ONLY the Markdown document — no preamble, no explanation.

CONVERSATION CONTENT:
{content}
"""

HTML_SYSTEM_PROMPT = """You are a professional web designer and writer.

Convert the content below into a complete, self-contained HTML/CSS document.
The page should look clean and professional with inline styles.

REQUIREMENTS:
- Complete HTML5 document (<!DOCTYPE html> ... </html>)
- Inline <style> block with clean typography and layout
- No <script> tags (security requirement — the artifact is sandboxed)
- No external resources (fonts, CDN links) — use system fonts only
- Max width 800px, centered, comfortable padding
- Readable headings, good line spacing

Produce ONLY the HTML document — no explanation.

CONTENT:
{content}
"""


class ArtifactAgent(BaseAgent):
    """Agent for generating Markdown and HTML artifacts from conversation content."""

    def __init__(self):
        super().__init__("artifact_agent")

    async def execute(
        self,
        content: str,
        artifact_type: str = "markdown",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate an artifact from content.

        Returns dict with:
            artifact, artifact_type, word_count, validation, latency_ms
        """
        start = time.monotonic()
        self._log_execution("artifact_start", {"type": artifact_type, "content_len": len(content)})

        if artifact_type not in ("markdown", "html"):
            raise AgentValidationError(f"Unsupported artifact type: {artifact_type}")

        try:
            provider = get_provider()
            if not provider.is_available():
                raise ProviderUnavailableError(
                    f"Ollama isn't reachable at {provider.host}. "
                    "Make sure Ollama is running: `ollama serve`"
                )

            # Build prompt context from conversation if provided
            context = content
            if conversation_history:
                history_text = "\n\n".join(
                    f"{m['role'].upper()}: {m['content']}"
                    for m in (conversation_history or [])[-6:]  # last 3 turns
                    if m.get("role") and m.get("content")
                )
                context = f"CONVERSATION:\n{history_text}\n\nUSER REQUEST: {content}"

            if artifact_type == "markdown":
                system = MARKDOWN_SYSTEM_PROMPT.format(content=context)
            else:
                system = HTML_SYSTEM_PROMPT.format(content=context)

            config = GenerationConfig(
                max_tokens=int(os.getenv("MAX_TOKENS_ARTIFACT", "2048")),
                temperature=0.5,
                stream=True,
            )

            parts: List[str] = []
            async for token in provider.generate(
                [{"role": "user", "content": f"Generate a {artifact_type} artifact from the content above."}],
                system=system,
                config=config,
            ):
                parts.append(token)

            artifact_content = "".join(parts).strip()
            latency_ms = int((time.monotonic() - start) * 1000)

            word_count = len(artifact_content.split())
            validation = self._validate_artifact(artifact_content, artifact_type)

            self._log_execution("artifact_complete", {
                "type": artifact_type,
                "word_count": word_count,
                "passed": validation["passed"],
                "latency_ms": latency_ms,
            })

            return {
                "artifact": artifact_content,
                "artifact_type": artifact_type,
                "word_count": word_count,
                "validation": validation,
                "latency_ms": latency_ms,
            }

        except (ProviderUnavailableError, AgentValidationError):
            raise
        except Exception as e:
            logger.error(f"Artifact agent error: {e}", exc_info=True)
            raise AgentExecutionError(f"Artifact agent failed: {e}") from e

    def _validate_artifact(self, artifact: str, artifact_type: str) -> Dict[str, Any]:
        """Validate artifact content."""
        if not artifact:
            return {"passed": False, "errors": ["Artifact is empty"], "checks": {}}

        checks: Dict[str, Any] = {}
        passed = True
        errors = []

        if artifact_type == "markdown":
            has_heading = bool(re.search(r"^#+\s+\S", artifact, re.MULTILINE))
            word_count = len(artifact.split())
            length_ok = 50 <= word_count <= 10_000

            checks["has_heading"] = {
                "passed": has_heading,
                "message": "Has a top-level heading" if has_heading else "No heading found",
            }
            checks["reasonable_length"] = {
                "passed": length_ok,
                "message": f"{word_count} words",
            }
            if not has_heading:
                passed = False
                errors.append("Markdown artifact should have at least one heading")
            if not length_ok:
                passed = False
                errors.append(f"Word count ({word_count}) outside 50–10,000 range")

        elif artifact_type == "html":
            has_doctype = "<!doctype html>" in artifact.lower()
            has_body = bool(re.search(r"<body[\s>]", artifact, re.IGNORECASE))
            # Security: no script execution or event handlers (sandboxed iframe blocks these anyway)
            has_scripts = bool(re.search(r"<script[\s>]", artifact, re.IGNORECASE))
            has_handlers = bool(re.search(r"\bon\w+\s*=", artifact, re.IGNORECASE))

            checks["basic_structure"] = {
                "passed": has_doctype and has_body,
                "message": "Has DOCTYPE and <body>" if (has_doctype and has_body) else "Missing DOCTYPE or <body>",
            }
            checks["no_scripts"] = {
                "passed": not has_scripts,
                "message": "No <script> tags" if not has_scripts else "<script> tag found (removed by sandbox)",
            }
            checks["no_event_handlers"] = {
                "passed": not has_handlers,
                "message": "No inline event handlers" if not has_handlers else "Inline handlers found",
            }

            if not (has_doctype and has_body):
                passed = False
                errors.append("HTML artifact needs a full document structure")
            # Scripts are blocked by the sandbox — not a failure, just flagged

        return {"passed": passed, "errors": errors, "checks": checks}


# Alias for backward compat
ArtifactGenerationAgent = ArtifactAgent