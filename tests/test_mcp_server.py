"""Tests for MCP server resources and tools."""

from unittest.mock import MagicMock, patch


def _mock_response(text: str, status: int = 200):
    m = MagicMock()
    m.text = text
    m.status_code = status
    m.raise_for_status.return_value = None
    return m


def test_session_bootstrap_resource():
    """session_bootstrap fetches session_bootstrap.md from context branch."""
    from agent_context_builder.mcp_server import session_bootstrap

    with patch("agent_context_builder.mcp_server.requests.get") as mock_get:
        mock_get.return_value = _mock_response("# Session Bootstrap\n")
        result = session_bootstrap()

    assert "Session Bootstrap" in result
    called_url = mock_get.call_args[0][0]
    assert "session_bootstrap.md" in called_url
    assert "context" in called_url


def test_workspace_triage_resource():
    """workspace_triage fetches workspace_triage.json from context branch."""
    from agent_context_builder.mcp_server import workspace_triage

    with patch("agent_context_builder.mcp_server.requests.get") as mock_get:
        mock_get.return_value = _mock_response('{"open_prs": 2}')
        result = workspace_triage()

    assert "open_prs" in result
    assert "workspace_triage.json" in mock_get.call_args[0][0]


def test_topic_index_resource():
    """topic_index fetches topic_index.json from context branch."""
    from agent_context_builder.mcp_server import topic_index

    with patch("agent_context_builder.mcp_server.requests.get") as mock_get:
        mock_get.return_value = _mock_response('{"topics": {}}')
        result = topic_index()

    assert "topics" in result
    assert "topic_index.json" in mock_get.call_args[0][0]


def test_refresh_context_no_token(monkeypatch):
    """refresh_context returns error message when GITHUB_TOKEN not set."""
    from agent_context_builder.mcp_server import refresh_context

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = refresh_context()

    assert "GITHUB_TOKEN" in result


def test_refresh_context_success(monkeypatch):
    """refresh_context triggers workflow dispatch and reports success."""
    from agent_context_builder.mcp_server import refresh_context

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_response("", status=204)
        result = refresh_context()

    assert "triggerato" in result.lower()


def test_refresh_context_api_error(monkeypatch):
    """refresh_context reports API errors without raising."""
    from agent_context_builder.mcp_server import refresh_context

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_response("Forbidden", status=403)
        result = refresh_context()

    assert "403" in result
