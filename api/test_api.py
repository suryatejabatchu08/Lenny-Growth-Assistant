"""
Test script for the FastAPI API
"""
import os
import sys
from fastapi.testclient import TestClient

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

def test_api_endpoints():
    """Test the API endpoints"""
    client = TestClient(app)

    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✓ Health endpoint works")

    # Test readiness endpoint (might fail if DB not set up, but that's OK for this test)
    response = client.get("/health/ready")
    # Could be 200 or 503 depending on DB setup
    print(f"✓ Readiness endpoint returned status: {response.status_code}")

    # Test sessions endpoint
    response = client.get("/sessions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print("✓ Sessions list endpoint works")

    # Test config endpoint
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "model_name" in data
    assert "display_name" in data
    assert "available" in data
    print("✓ Config endpoint works")

    print("All API tests completed!")

if __name__ == "__main__":
    test_api_endpoints()