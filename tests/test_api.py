"""
Unit tests for API endpoints.
"""
import os
import sys
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test the basic health/liveness probe."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_config_endpoint():
    """Test the /config endpoint."""
    with patch("api.main.get_provider") as mock_get_provider:
        mock_provider = Mock()
        mock_provider.get_model_info.return_value = {
            "provider": "ollama",
            "model_name": "llama3.1:8b",
            "display_name": "Ollama · llama3.1:8b",
            "available": True,
            "host": "http://localhost:11434",
        }
        mock_get_provider.return_value = mock_provider

        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "ollama"
        assert data["model_name"] == "llama3.1:8b"
        assert data["available"] is True


def test_health_ready_endpoint():
    """Test the /health/ready probe."""
    with patch("api.main.check_db_connection", return_value=True), \
         patch("api.main.get_provider") as mock_get_provider:
        mock_provider = Mock()
        mock_provider.is_available.return_value = True
        mock_provider.get_model_info.return_value = {"provider": "ollama"}
        mock_get_provider.return_value = mock_provider

        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


if __name__ == "__main__":
    pytest.main([__file__])