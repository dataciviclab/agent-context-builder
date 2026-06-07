"""Tests for MCP server resources — uses FakeHttpClient for HTTP boundary."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from lab_connectors.http import HttpResult
from lab_connectors.testing import FakeHttpClient, fake_response

import agent_context_builder.mcp_server as mcp_server

# ---------------------------------------------------------------------------
# _fetch-based tools — inject FakeHttpClient via patching HttpClient class
# ---------------------------------------------------------------------------


def _patch_fetch(fake: FakeHttpClient, path: str, text: str = "", status: int = 200) -> None:
    """Register a response for one of the context-branch artifact URLs.

    For error status codes (>= 400), ``_FakeResponse.raise_for_status()``
    automatically raises ``_FakeHTTPError`` (a subclass of
    ``requests.HTTPError``), so no manual side_effect is needed.
    """
    url = f"https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/{path}"
    fake.responses[url] = HttpResult(
        response=fake_response(status, text=text),
        err=None,
    )


@pytest.mark.contract
def test_session_bootstrap_resource():
    """session_bootstrap fetches session_bootstrap.md from context branch."""
    fake = FakeHttpClient()
    _patch_fetch(fake, "session_bootstrap.md", text="# Session Bootstrap\n")

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value = fake
        result = mcp_server.session_bootstrap()

    assert result["format"] == "markdown"
    assert "Session Bootstrap" in result["content"]


@pytest.mark.contract
def test_workspace_triage_resource():
    """workspace_triage fetches workspace_triage.json from context branch."""
    fake = FakeHttpClient()
    _patch_fetch(fake, "workspace_triage.json", text='{"open_prs": 2}')

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value = fake
        result = mcp_server.workspace_triage()

    assert result["ok"] is True
    assert result["content"]["open_prs"] == 2


@pytest.mark.contract
def test_topic_index_resource():
    """topic_index fetches topic_index.json from context branch."""
    fake = FakeHttpClient()
    _patch_fetch(fake, "topic_index.json", text='{"topics": {}}')

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value = fake
        result = mcp_server.topic_index()

    assert result["ok"] is True
    assert "topics" in result["content"]


@pytest.mark.contract
def test_session_bootstrap_http_error():
    """session_bootstrap returns error dict on HTTP failure instead of raising."""
    fake = FakeHttpClient()
    _patch_fetch(fake, "session_bootstrap.md", status=403)

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value = fake
        result = mcp_server.session_bootstrap()

    assert result["ok"] is False
    assert "error" in result


@pytest.mark.contract
def test_workspace_triage_http_error():
    """workspace_triage returns error dict on HTTP failure instead of raising."""
    fake = FakeHttpClient()
    _patch_fetch(fake, "workspace_triage.json", status=404)

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value = fake
        result = mcp_server.workspace_triage()

    assert result["ok"] is False
    assert "error" in result


@pytest.mark.contract
def test_topic_index_http_error():
    """topic_index returns error dict on HTTP failure instead of raising."""
    fake = FakeHttpClient()
    _patch_fetch(fake, "topic_index.json", status=500)

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value = fake
        result = mcp_server.topic_index()

    assert result["ok"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# topic_index(resolve=...) — sub-graph traversal
# ---------------------------------------------------------------------------


_SAMPLE_V3_INDEX = json.dumps(
    {
        "schema_version": 3,
        "datasets_by_source": {
            "ISPRA": [
                {
                    "slug": "ispra_ru_base",
                    "name": "Rifiuti Urbani",
                    "period": {"start": 2020, "end": 2024},
                },
            ],
            "MEF": [
                {
                    "slug": "irpef_comunale",
                    "name": "IRPEF Comunale",
                    "period": {"start": 2019, "end": 2023},
                },
            ],
        },
        "candidates_by_source": {
            "ISPRA": [
                {
                    "slug": "ispra_consumo_suolo",
                    "name": "Consumo Suolo",
                    "period": {"start": 2024, "end": 2024},
                },
            ],
        },
        "analyses": [
            {
                "slug": "irpef-comunale",
                "name": "IRPEF Comunale 2019-2023",
                "datasets": ["irpef_comunale"],
                "path": "analisi/irpef-comunale/README.md",
                "status": "active",
                "discussion": 88,
            },
        ],
        "analyses_by_dataset": {
            "irpef_comunale": ["irpef-comunale"],
        },
        "explorer_themes": [
            {
                "slug": "finanza-pubblica",
                "name": "Finanza pubblica",
                "datasets": ["irpef-comunale", "entrate-stato"],
            },
        ],
    }
)


@pytest.mark.contract
def test_topic_index_resolve_by_dataset_slug():
    """resolve finds a published dataset and its related analyses."""
    fake = FakeHttpClient()
    _patch_fetch(fake, "topic_index.json", text=_SAMPLE_V3_INDEX)

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value = fake
        result = mcp_server.topic_index(resolve="irpef_comunale")

    data = result["content"]
    assert data["resolve"] == "irpef_comunale"
    assert data["found"] is True
    # Published dataset found
    assert len(data["datasets"]) == 1
    assert data["datasets"][0]["slug"] == "irpef_comunale"
    assert data["datasets"][0]["stage"] == "published"
    # Analysis found via datasets list match (irpef_comunale in analysis.datasets)
    assert len(data["analyses"]) == 1
    assert data["analyses"][0]["slug"] == "irpef-comunale"
    # No duplicates in analyses
    assert len(data["analyses"]) == 1


@pytest.mark.contract
def test_topic_index_resolve_by_source_dedup():
    """resolve by source name deduplicates datasets and sources across sections."""
    fake = FakeHttpClient()
    _patch_fetch(fake, "topic_index.json", text=_SAMPLE_V3_INDEX)

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value = fake
        result = mcp_server.topic_index(resolve="ISPRA")

    data = result["content"]
    assert data["resolve"] == "ISPRA"
    assert data["found"] is True

    # sources should appear exactly once
    assert len(data["sources"]) == 1
    assert data["sources"] == ["ISPRA"]

    # datasets should include both published and incubating, deduped
    slugs = [d["slug"] for d in data["datasets"]]
    assert len(slugs) == 2
    assert "ispra_ru_base" in slugs
    assert "ispra_consumo_suolo" in slugs
    stages = {d["slug"]: d["stage"] for d in data["datasets"]}
    assert stages["ispra_ru_base"] == "published"
    assert stages["ispra_consumo_suolo"] == "incubating"


@pytest.mark.contract
def test_topic_index_resolve_not_found():
    """resolve returns found=False when nothing matches."""
    fake = FakeHttpClient()
    _patch_fetch(fake, "topic_index.json", text=_SAMPLE_V3_INDEX)

    with patch("agent_context_builder.mcp_server.HttpClient") as mock_cls:
        mock_cls.return_value = fake
        result = mcp_server.topic_index(resolve="nonexistent")

    data = result["content"]
    assert data["resolve"] == "nonexistent"
    assert data["found"] is False


# ---------------------------------------------------------------------------
# refresh_context — via HttpClient.post
# ---------------------------------------------------------------------------


def _reset_refresh_state(monkeypatch) -> None:
    """Reset global state for refresh_context tests.

    Sets ``_ENV_LOADED = False`` so that ``_load_dotenv_if_present()``
    actually loads from .env files during the test.
    """
    monkeypatch.setattr(mcp_server, "_last_refresh_attempt", None)
    monkeypatch.setattr(mcp_server, "_ENV_LOADED", False)


def _mock_http_result(status: int = 204):
    """Build an HttpResult-like object for mocking HttpClient.post."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = "mock response"
    from lab_connectors.http import HttpResult

    return HttpResult(response=resp, err=None, ssl_fallback_used=None)


@pytest.mark.adapter
def test_refresh_context_no_token(monkeypatch):
    """refresh_context returns error message when GITHUB_TOKEN not set."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("ACB_ENV_FILE", raising=False)
    monkeypatch.setattr(mcp_server, "_ENV_LOADED", True)
    result = mcp_server.refresh_context()

    assert result["ok"] is False
    assert "GITHUB_TOKEN" in result["error"]


@pytest.mark.adapter
def test_refresh_context_loads_token_from_env_file(monkeypatch, tmp_path):
    """refresh_context can use a local .env when the host does not export env vars."""
    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("ACB_ENV_FILE", str(env_file))
    _reset_refresh_state(monkeypatch)

    with patch("agent_context_builder.mcp_server.HttpClient.post") as mock_post:
        mock_post.return_value = _mock_http_result(204)
        result = mcp_server.refresh_context()

    assert result["ok"] is True
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "token file-token"


@pytest.mark.adapter
def test_refresh_context_loads_token_when_env_is_empty(monkeypatch, tmp_path):
    """A blank inherited value should not block the local .env fallback."""
    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("ACB_ENV_FILE", str(env_file))
    _reset_refresh_state(monkeypatch)

    with patch("agent_context_builder.mcp_server.HttpClient.post") as mock_post:
        mock_post.return_value = _mock_http_result(204)
        result = mcp_server.refresh_context()

    assert result["ok"] is True
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "token file-token"


@pytest.mark.adapter
def test_refresh_context_continues_after_partial_env(monkeypatch, tmp_path):
    """A partial explicit .env should not prevent later candidates from filling tokens."""
    explicit_env = tmp_path / "partial.env"
    explicit_env.write_text("ACB_BRANCH=context\n", encoding="utf-8")
    workspace_env = tmp_path / ".env"
    workspace_env.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("ACB_ENV_FILE", str(explicit_env))
    _reset_refresh_state(monkeypatch)

    with patch("agent_context_builder.mcp_server.HttpClient.post") as mock_post:
        mock_post.return_value = _mock_http_result(204)
        result = mcp_server.refresh_context()

    assert result["ok"] is True
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "token file-token"


@pytest.mark.adapter
def test_refresh_context_success(monkeypatch):
    """refresh_context triggers workflow dispatch and reports success."""
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    _reset_refresh_state(monkeypatch)

    with patch("agent_context_builder.mcp_server.HttpClient.post") as mock_post:
        mock_post.return_value = _mock_http_result(204)
        result = mcp_server.refresh_context()

    assert result["ok"] is True


@pytest.mark.adapter
def test_refresh_context_api_error(monkeypatch):
    """refresh_context reports API errors without raising."""
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    _reset_refresh_state(monkeypatch)

    with patch("agent_context_builder.mcp_server.HttpClient.post") as mock_post:
        mock_post.return_value = _mock_http_result(403)
        result = mcp_server.refresh_context()

    assert result["ok"] is False
    assert result["status_code"] == 403
