"""
Unit tests for agent skills and orchestrator.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.agents.qa_agent import QAAgent
from api.agents.ship30_agent import Ship30Agent
from api.agents.artifact_agent import ArtifactAgent
from api.agents.orchestrator import AgentOrchestrator


@pytest.mark.asyncio
async def test_qa_agent_initialization():
    """Test QA agent initialization."""
    with patch("api.agents.qa_agent.get_retrieval_service") as mock_get_service:
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        agent = QAAgent()
        assert agent.name == "qa_agent"
        assert agent.retrieval_service == mock_service


@pytest.mark.asyncio
async def test_qa_agent_low_grounding():
    """Test QA agent when retrieval score is below threshold."""
    with patch("api.agents.qa_agent.get_retrieval_service") as mock_get_service:
        mock_service = Mock()
        mock_service.retrieve_with_followup_context.return_value = ([], "", 0.1)
        mock_get_service.return_value = mock_service

        agent = QAAgent()
        result = await agent.execute("What is the meaning of life?")

        assert "couldn't find strong support" in result["answer"]
        assert result["citations"] == []
        assert result["is_grounded"] is False


@pytest.mark.asyncio
async def test_ship30_agent_initialization():
    """Test Ship 30 agent initialization."""
    with patch("api.agents.ship30_agent.get_retrieval_service") as mock_get_service:
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        agent = Ship30Agent()
        assert agent.name == "ship30_agent"


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test agent orchestrator initializes all skills."""
    with patch("api.agents.qa_agent.QAAgent"), \
         patch("api.agents.ship30_agent.Ship30Agent"), \
         patch("api.agents.artifact_agent.ArtifactAgent"):

        orchestrator = AgentOrchestrator()
        assert "qa" in orchestrator._agents
        assert "ship30" in orchestrator._agents
        assert "artifact" in orchestrator._agents


if __name__ == "__main__":
    pytest.main([__file__])