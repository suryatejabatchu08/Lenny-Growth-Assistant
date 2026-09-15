"""
Agent Orchestrator for Lenny Growth Assistant.
Manages and coordinates all agent skills.
"""
import logging
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent, AgentError
from .qa_agent import QAAgent
from .ship30_agent import Ship30Agent
from .artifact_agent import ArtifactAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates all agent skills in the Lenny Growth Assistant."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all agent skills."""
        try:
            self._agents["qa"] = QAAgent()
            self._agents["ship30"] = Ship30Agent()
            self._agents["artifact"] = ArtifactAgent()
            logger.info("All agent skills initialized")
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise

    def get_agent(self, agent_type: str) -> BaseAgent:
        if agent_type not in self._agents:
            raise AgentError(f"Unknown agent type: {agent_type}")
        return self._agents[agent_type]

    async def execute_qa(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 5,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute the Q&A agent."""
        return await self._agents["qa"].execute(
            query=query,
            conversation_history=conversation_history,
            top_k=top_k,
            **kwargs,
        )

    async def execute_ship30(
        self,
        topic: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute the Ship 30 for 30 essay agent."""
        return await self._agents["ship30"].execute(
            topic=topic,
            conversation_history=conversation_history,
            **kwargs,
        )

    async def execute_artifact(
        self,
        content: str,
        artifact_type: str = "markdown",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute the artifact generation agent."""
        return await self._agents["artifact"].execute(
            content=content,
            artifact_type=artifact_type,
            conversation_history=conversation_history,
            **kwargs,
        )

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    def get_agent_info(self) -> Dict[str, Any]:
        return {
            agent_type: {
                "name": agent.name,
                "type": agent_type,
                "class": agent.__class__.__name__,
            }
            for agent_type, agent in self._agents.items()
        }


# ──────────────────────────────────────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────────────────────────────────────

_orchestrator: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


# Convenience functions
async def answer_question(
    query: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    top_k: int = 5,
    **kwargs,
) -> Dict[str, Any]:
    return await get_agent_orchestrator().execute_qa(
        query=query, conversation_history=conversation_history, top_k=top_k, **kwargs
    )


async def generate_ship30_essay(
    topic: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    return await get_agent_orchestrator().execute_ship30(
        topic=topic, conversation_history=conversation_history, **kwargs
    )


async def generate_artifact(
    content: str,
    artifact_type: str = "markdown",
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    return await get_agent_orchestrator().execute_artifact(
        content=content,
        artifact_type=artifact_type,
        conversation_history=conversation_history,
        **kwargs,
    )