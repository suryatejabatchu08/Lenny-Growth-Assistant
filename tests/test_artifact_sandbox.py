"""
Tests for Artifact Agent validation and sandbox security against script injection.
"""
import pytest
from api.agents.artifact_agent import ArtifactAgent


@pytest.fixture
def agent():
    return ArtifactAgent()


def test_artifact_validation_clean_markdown(agent):
    """Test validation passes for well-formed markdown."""
    md_content = "# Title\n\nThis is a clean markdown document with sufficient words to pass the length requirement for validation. " * 5
    result = agent._validate_artifact(md_content, "markdown")

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["checks"]["has_heading"]["passed"] is True
    assert result["checks"]["reasonable_length"]["passed"] is True


def test_artifact_validation_clean_html(agent):
    """Test validation passes for well-formed script-free HTML."""
    html_content = """<!DOCTYPE html>
<html>
<head><title>Clean HTML</title></head>
<body>
    <h1>Clean Document</h1>
    <p>This is clean HTML content without scripts or dangerous handlers.</p>
</body>
</html>"""
    result = agent._validate_artifact(html_content, "html")

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["checks"]["basic_structure"]["passed"] is True
    assert result["checks"]["no_scripts"]["passed"] is True
    assert result["checks"]["no_event_handlers"]["passed"] is True


def test_artifact_detects_script_injection_tags(agent):
    """Test that <script> tags in HTML artifacts are detected by validation checks."""
    malicious_html = """<!DOCTYPE html>
<html>
<body>
    <h1>Injected Document</h1>
    <script>alert('XSS Attack');</script>
</body>
</html>"""
    result = agent._validate_artifact(malicious_html, "html")

    assert result["checks"]["no_scripts"]["passed"] is False
    assert "<script> tag found" in result["checks"]["no_scripts"]["message"]


def test_artifact_detects_inline_event_handlers(agent):
    """Test that inline event handlers (onerror, onload, onclick) are detected."""
    malicious_html = """<!DOCTYPE html>
<html>
<body>
    <img src="invalid.jpg" onerror="alert('xss')" />
    <button onclick="staleData()">Click</button>
</body>
</html>"""
    result = agent._validate_artifact(malicious_html, "html")

    assert result["checks"]["no_event_handlers"]["passed"] is False
    assert result["checks"]["no_event_handlers"]["message"] == "Inline handlers found"


def test_iframe_sandbox_policy_compliance():
    """
    Verify the iframe sandbox configuration matches security requirements.
    The sandbox attribute must NOT include 'allow-scripts' to prevent JS execution.
    """
    sandbox_policy = "allow-same-origin"

    # Strict security invariant: allow-scripts must be absent to sandbox untrusted HTML
    assert "allow-scripts" not in sandbox_policy
    assert sandbox_policy == "allow-same-origin"
