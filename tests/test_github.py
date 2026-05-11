"""Tests for github module HTTP boundary."""

from unittest.mock import MagicMock, patch

from agent_context_builder.github import GitHubCollector


def _make_http_result(status_code: int, body: str = ""):
    """Build a mock HttpResult with the given status code."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = body
    mock_resp.json.return_value = {}
    result = MagicMock()
    result.is_ok = status_code < 500  # come HttpClient reale
    result.response = mock_resp
    result.err = None
    return result


class TestGetRawFile:
    """get_raw_file deve gestire 4xx come errori, non restituire body di errore."""

    def test_404_returns_none(self):
        """404 su get_raw_file → None + fetch_errors popolato."""
        collector = GitHubCollector("test-org", token="fake")
        with patch.object(collector._http, "get", return_value=_make_http_result(404)):
            result = collector.get_raw_file("some-repo", "data/file.json")
        assert result is None
        assert "some-repo:data/file.json" in collector.fetch_errors
        assert "HTTP 404" in collector.fetch_errors["some-repo:data/file.json"]

    def test_200_returns_text(self):
        """200 su get_raw_file → body restituito."""
        collector = GitHubCollector("test-org", token="fake")
        with patch.object(collector._http, "get", return_value=_make_http_result(200, "ok")):
            result = collector.get_raw_file("some-repo", "data/file.json")
        assert result == "ok"

    def test_403_records_error(self):
        """403 su get_raw_file → None + errore tracciato."""
        collector = GitHubCollector("test-org", token="fake")
        with patch.object(collector._http, "get", return_value=_make_http_result(403)):
            result = collector.get_raw_file("some-repo", "data/file.json")
        assert result is None
        assert "HTTP 403" in collector.fetch_errors["some-repo:data/file.json"]


class TestGetReposInfo:
    """get_repos_info deve segnalare 4xx come errori, non dati vuoti."""

    def test_403_skips_and_records_error(self):
        """403 su get_repos_info → repo skippato + errore tracciato."""
        collector = GitHubCollector("test-org", token="fake")
        with patch.object(collector._http, "get", return_value=_make_http_result(403)):
            result = collector.get_repos_info(["some-repo"])
        assert "some-repo" not in result
        assert "some-repo:info" in collector.fetch_errors
        assert "HTTP 403" in collector.fetch_errors["some-repo:info"]


class TestGetRepoPrs:
    """get_prs deve propagare 4xx come errori."""

    def test_403_records_error(self):
        """403 su get_prs → lista vuota + errore tracciato."""
        collector = GitHubCollector("test-org", token="fake")
        with patch.object(collector._http, "get", return_value=_make_http_result(403)):
            result = collector.get_prs(["some-repo"])
        assert result == []
        assert "some-repo:prs" in collector.fetch_errors
        assert "HTTP 403" in collector.fetch_errors["some-repo:prs"]


class TestGetIssues:
    """get_issues deve propagare 4xx come errori."""

    def test_403_records_error(self):
        """403 su get_issues → lista vuota + errore tracciato."""
        collector = GitHubCollector("test-org", token="fake")
        with patch.object(collector._http, "get", return_value=_make_http_result(403)):
            result = collector.get_issues(["some-repo"])
        assert result == []
        assert "some-repo:issues" in collector.fetch_errors
        assert "HTTP 403" in collector.fetch_errors["some-repo:issues"]
