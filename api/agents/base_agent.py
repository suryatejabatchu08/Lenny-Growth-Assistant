"""
Base agent class for Lenny Growth Assistant
Defines the interface for all agent skills
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agent skills"""

    def __init__(self, name: str):
        self.name = name
        logger.info(f"Initialized agent: {self.name}")

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the agent skill"""
        pass

    def _log_execution(self, action: str, details: Optional[Dict[str, Any]] = None):
        """Log agent execution"""
        log_data = {
            "agent": self.name,
            "action": action,
        }
        if details:
            log_data.update(details)
        logger.info(f"Agent execution: {log_data}")

class AgentError(Exception):
    """Base exception for agent errors"""
    pass

class AgentExecutionError(AgentError):
    """Raised when agent execution fails"""
    pass

class AgentValidationError(AgentError):
    """Raised when agent input validation fails"""
    pass