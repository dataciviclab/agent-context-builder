"""Tests for MCP server resources — mocks HttpClient, not raw requests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from lab_connectors.http import HttpResult


def _http_ok(text: str = "") -> HttpResult:
    """Build success HttpResult."""
    resp = MagicMock()
    resp.status_code = 200
    resp.text = text
    resp.raise_for_status.return_value = None
    return HttpResult(response=resp, err=None)


def _http_error(status: int = 500) -> HttpResult:
    """Build HTTP error HttpResult (non-2xx response, not network error)."""
    import requests
    resp = MagicMock()
    resp.status_code = status
    resp.text = "error"
    resp.raise_for_status.side_effect = requests.HTTPError(
        f"HTTP {status}", response=resp,
    )
    return HttpResult(response=resp, err=None)


# ---------------------------------------------------------------------------
# _fetch-based tools — mock HttpClient.get
# ---------------------------------------------------------------------------


def test_session_bootstrap_resource():
    """session_bootstrap fetches session_bootstrap.md from context branch."""
    from agent_context_builder.mcp_server import session_bootstrap

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value.get.return_value = _http_ok("# Session Bootstrap\n")
        result = session_bootstrap()

    assert "Session Bootstrap" in result


def test_workspace_triage_resource():
    """workspace_triage fetches workspace_triage.json from context branch."""
    from agent_context_builder.mcp_server import workspace_triage

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value.get.return_value = _http_ok('{"open_prs": 2}')
        result = workspace_triage()

    assert "open_prs" in result


def test_topic_index_resource():
    """topic_index fetches topic_index.json from context branch."""
    from agent_context_builder.mcp_server import topic_index

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value.get.return_value = _http_ok('{"topics": {}}')
        result = topic_index()

    assert "topics" in result


def test_session_bootstrap_http_error():
    """session_bootstrap returns JSON error on HTTP failure instead of raising."""
    import agent_context_builder.mcp_server as mcp_server

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value.get.return_value = _http_error(403)
        result = mcp_server.session_bootstrap()

    import json
    data = json.loads(result)
    assert data["ok"] is False
    assert data["tool"] == "session_bootstrap"
    assert data["status_code"] == 403


def test_workspace_triage_http_error():
    """workspace_triage returns JSON error on HTTP failure instead of raising."""
    import agent_context_builder.mcp_server as mcp_server

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value.get.return_value = _http_error(404)
        result = mcp_server.workspace_triage()

    import json
    data = json.loads(result)
    assert data["ok"] is False
    assert data["tool"] == "workspace_triage"
    assert data["status_code"] == 404


def test_topic_index_http_error():
    """topic_index returns JSON error on HTTP failure instead of raising."""
    import agent_context_builder.mcp_server as mcp_server

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value.get.return_value = _http_error(500)
        result = mcp_server.topic_index()

    import json
    data = json.loads(result)
    assert data["ok"] is False
    assert data["tool"] == "topic_index"
    assert data["status_code"] == 500


# ---------------------------------------------------------------------------
# refresh_context — still uses raw requests.post (separate concern)
# ---------------------------------------------------------------------------


def test_refresh_context_no_token(monkeypatch):
    """refresh_context returns error message when GITHUB_TOKEN not set."""
    import agent_context_builder.mcp_server as mcp_server

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("ACB_ENV_FILE", raising=False)
    monkeypatch.setattr(mcp_server, "_ENV_LOADED", True)
    result = mcp_server.refresh_context()

    assert "GITHUB_TOKEN" in result


def _mock_post_response(status: int = 204):
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status.return_value = None
    return resp


def test_refresh_context_loads_token_from_env_file(monkeypatch, tmp_path):
    """refresh_context can use a local .env when the host does not export env vars."""
    import agent_context_builder.mcp_server as mcp_server

    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("ACB_ENV_FILE", str(env_file))
    monkeypatch.setattr(mcp_server, "_ENV_LOADED", False)
    monkeypatch.setattr(mcp_server, "_last_refresh_attempt", None)

    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_post_response(204)
        result = mcp_server.refresh_context()

    import json
    data = json.loads(result)
    assert data["ok"] is True
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "token file-token"


def test_refresh_context_loads_token_when_env_is_empty(monkeypatch, tmp_path):
    """A blank inherited value should not block the local .env fallback."""
    import agent_context_builder.mcp_server as mcp_server

    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("ACB_ENV_FILE", str(env_file))
    monkeypatch.setattr(mcp_server, "_ENV_LOADED", False)
    monkeypatch.setattr(mcp_server, "_last_refresh_attempt", None)

    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_post_response(204)
        result = mcp_server.refresh_context()

    import json
    data = json.loads(result)
    assert data["ok"] is True
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
    monkeypatch.setattr(mcp_server, "_last_refresh_attempt", None)

    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_post_response(204)
        result = mcp_server.refresh_context()

    import json
    data = json.loads(result)
    assert data["ok"] is True
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "token file-token"


def test_refresh_context_success(monkeypatch):
    """refresh_context triggers workflow dispatch and reports success."""
    import agent_context_builder.mcp_server as mcp_server

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(mcp_server, "_last_refresh_attempt", None)
    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_post_response(204)
        result = mcp_server.refresh_context()

    import json
    data = json.loads(result)
    assert data["ok"] is True


def test_refresh_context_api_error(monkeypatch):
    """refresh_context reports API errors without raising."""
    import agent_context_builder.mcp_server as mcp_server

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(mcp_server, "_last_refresh_attempt", None)
    with patch("agent_context_builder.mcp_server.requests.post") as mock_post:
        mock_post.return_value = _mock_post_response(403)
        result = mcp_server.refresh_context()

    import json
    data = json.loads(result)
    assert data["ok"] is False
    assert data["status_code"] == 403
