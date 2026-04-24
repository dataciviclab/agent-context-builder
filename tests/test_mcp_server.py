"""Tests for MCP server resources and tools."""

import requests
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
    import agent_context_builder.mcp_server as mcp_server

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("ACB_ENV_FILE", raising=False)
    monkeypatch.setattr(mcp_server, "_ENV_LOADED", True)
    result = mcp_server.refresh_context()

    assert "GITHUB_TOKEN" in result


def test_refresh_context_loads_token_from_env_file(monkeypatch, tmp_path):
    """refresh_context can use a local .env when the host does not export env vars."""
    import agent_context_builder.mcp_server as mcp_server

    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("ACB_ENV_FILE", str(env_file))
    monkeypatch.setattr(mcp_server, "_ENV_LOADED", False)

    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_response("", status=204)
        result = mcp_server.refresh_context()

    assert "triggerato" in result.lower()
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "token file-token"


def test_refresh_context_loads_token_when_env_is_empty(monkeypatch, tmp_path):
    """A blank inherited value should not block the local .env fallback."""
    import agent_context_builder.mcp_server as mcp_server

    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("ACB_ENV_FILE", str(env_file))
    monkeypatch.setattr(mcp_server, "_ENV_LOADED", False)

    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_response("", status=204)
        result = mcp_server.refresh_context()

    assert "triggerato" in result.lower()
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "token file-token"


def test_refresh_context_continues_after_partial_env(monkeypatch, tmp_path):
    """A partial explicit .env should not prevent later candidates from filling tokens."""
    import agent_context_builder.mcp_server as mcp_server

    explicit_env = tmp_path / "partial.env"
    explicit_env.write_text("ACB_BRANCH=context\n", encoding="utf-8")
    workspace_env = tmp_path / ".env"
    workspace_env.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("ACB_ENV_FILE", str(explicit_env))
    monkeypatch.setattr(mcp_server, "_ENV_LOADED", False)

    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_response("", status=204)
        result = mcp_server.refresh_context()

    assert "triggerato" in result.lower()
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "token file-token"


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


def _mock_http_error(status: int):
    """Return a mock raising HTTPError."""
    response = _mock_response("error", status=status)
    exc = requests.HTTPError(f"{status} Client Error", response=response)
    response.raise_for_status.side_effect = exc
    return response


def test_session_bootstrap_http_error(monkeypatch):
    """session_bootstrap returns error string on HTTP failure instead of raising."""
    from agent_context_builder.mcp_server import session_bootstrap

    with patch("agent_context_builder.mcp_server.requests.get") as mock_get:
        mock_get.return_value = _mock_http_error(403)
        result = session_bootstrap()

    assert "session_bootstrap" in result
    assert "403" in result


def test_workspace_triage_http_error(monkeypatch):
    """workspace_triage returns error string on HTTP failure instead of raising."""
    from agent_context_builder.mcp_server import workspace_triage

    with patch("agent_context_builder.mcp_server.requests.get") as mock_get:
        mock_get.return_value = _mock_http_error(404)
        result = workspace_triage()

    assert "workspace_triage" in result
    assert "404" in result


def test_topic_index_http_error(monkeypatch):
    """topic_index returns error string on HTTP failure instead of raising."""
    from agent_context_builder.mcp_server import topic_index

    with patch("agent_context_builder.mcp_server.requests.get") as mock_get:
        mock_get.return_value = _mock_http_error(500)
        result = topic_index()

    assert "topic_index" in result
    assert "500" in result
