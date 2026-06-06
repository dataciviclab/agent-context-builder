"""Tests for github module HTTP boundary — uses FakeHttpClient."""

from __future__ import annotations

import pytest
from lab_connectors.http import HttpResult
from lab_connectors.testing import fake_response

from agent_context_builder.github import GitHubCollector

pytestmark = pytest.mark.adapter

_GITHUB_RAW = "https://raw.githubusercontent.com/test-org/some-repo/main/data/file.json"
_GITHUB_API = "https://api.github.com/repos/test-org/some-repo"


def _register_get(fake_http, url: str, status: int = 200, body: str = "", json_data=None):
    """Register a GET response for *url* on *fake_http*."""
    fake_http.responses[url] = HttpResult(
        response=fake_response(status, text=body, json_data=json_data),
        err=None,
    )


def _make_collector(fake_http, token: str = "fake") -> GitHubCollector:
    return GitHubCollector("test-org", token=token, http_client=fake_http)


class TestGetRawFile:
    """get_raw_file deve gestire 4xx come errori, non restituire body di errore."""

    def test_404_returns_none(self, fake_http):
        """404 su get_raw_file → None + fetch_errors popolato."""
        _register_get(fake_http, _GITHUB_RAW, status=404)
        collector = _make_collector(fake_http)
        result = collector.get_raw_file("some-repo", "data/file.json")
        assert result is None
        assert "some-repo:data/file.json" in collector.fetch_errors
        assert "HTTP 404" in collector.fetch_errors["some-repo:data/file.json"]

    def test_200_returns_text(self, fake_http):
        """200 su get_raw_file → body restituito."""
        _register_get(fake_http, _GITHUB_RAW, status=200, body="ok")
        collector = _make_collector(fake_http)
        result = collector.get_raw_file("some-repo", "data/file.json")
        assert result == "ok"

    def test_403_records_error(self, fake_http):
        """403 su get_raw_file → None + errore tracciato."""
        _register_get(fake_http, _GITHUB_RAW, status=403)
        collector = _make_collector(fake_http)
        result = collector.get_raw_file("some-repo", "data/file.json")
        assert result is None
        assert "HTTP 403" in collector.fetch_errors["some-repo:data/file.json"]


class TestGetReposInfo:
    """get_repos_info deve segnalare 4xx come errori, non dati vuoti."""

    def test_403_skips_and_records_error(self, fake_http):
        """403 su get_repos_info → repo skippato + errore tracciato."""
        _register_get(fake_http, f"{_GITHUB_API}", status=403)
        collector = _make_collector(fake_http)
        result = collector.get_repos_info(["some-repo"])
        assert "some-repo" not in result
        assert "some-repo:info" in collector.fetch_errors
        assert "HTTP 403" in collector.fetch_errors["some-repo:info"]


class TestGetRepoPrs:
    """get_prs deve propagare 4xx come errori."""

    def test_403_records_error(self, fake_http):
        """403 su get_prs → lista vuota + errore tracciato."""
        _register_get(fake_http, f"{_GITHUB_API}/pulls", status=403)
        collector = _make_collector(fake_http)
        result = collector.get_prs(["some-repo"])
        assert result == []
        assert "some-repo:prs" in collector.fetch_errors
        assert "HTTP 403" in collector.fetch_errors["some-repo:prs"]


class TestGetIssues:
    """get_issues deve propagare 4xx come errori."""

    def test_403_records_error(self, fake_http):
        """403 su get_issues → lista vuota + errore tracciato."""
        _register_get(fake_http, f"{_GITHUB_API}/issues", status=403)
        collector = _make_collector(fake_http)
        result = collector.get_issues(["some-repo"])
        assert result == []
        assert "some-repo:issues" in collector.fetch_errors
        assert "HTTP 403" in collector.fetch_errors["some-repo:issues"]
