"""Tests for MCP server resources and tools."""

from unittest.mock import MagicMock, patch


def _mock_response(text: str, status: int = 200):
    m = MagicMock()
    m.text = text
    m.status_code = status
    m.raise_for_status.return_value = None
    return m


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


def test_refresh_context_api_error(monkeypatch):
    """refresh_context reports API errors without raising."""
    from agent_context_builder.mcp_server import refresh_context

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_response("Forbidden", status=403)
        result = refresh_context()

    assert "403" in result
