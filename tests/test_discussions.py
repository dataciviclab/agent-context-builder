"""Tests for discussions module — mocks HttpClient, not raw requests."""

from unittest.mock import MagicMock, patch

from lab_connectors.http import HttpResult

from agent_context_builder.discussions import Discussion, DiscussionCollector


def _http_ok(json_data: dict) -> HttpResult:
    """Build success HttpResult."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_data
    return HttpResult(response=resp, err=None)


def _http_error() -> HttpResult:
    """Build network error HttpResult."""
    return HttpResult(response=None, err=Exception("network error"))


def test_discussion_creation():
    """Discussion dataclass holds expected fields."""
    d = Discussion(
        number=1, title="Analisi IRPEF", repo="dataset-incubator",
        url="https://github.com/dataciviclab/dataset-incubator/discussions/1",
        category="Civic Questions", author="gabry", updated_at="2026-04-14T20:00:00Z",
    )
    assert d.number == 1
    assert d.category == "Civic Questions"


def test_get_discussions_no_token():
    """Without token, all repos fail with ValueError recorded in fetch_errors."""
    collector = DiscussionCollector(org="dataciviclab", token=None)
    results = collector.get_discussions(["dataset-incubator"])

    assert results == []
    assert "dataset-incubator:discussions" in collector.fetch_errors
    assert "token" in collector.fetch_errors["dataset-incubator:discussions"].lower()


def test_get_discussions_api_error():
    """HTTP errors are captured in fetch_errors, not raised."""
    collector = DiscussionCollector(org="dataciviclab", token="fake-token")

    with patch("agent_context_builder.discussions.HttpClient") as mock_cls:
        mock_instance = mock_cls.return_value
        # Simulate HTTP 403 — response with error status, not network error
        resp = MagicMock()
        resp.status_code = 403
        resp.json.side_effect = Exception("403 Forbidden")
        mock_instance.post.return_value = HttpResult(response=resp, err=None)

        results = collector.get_discussions(["dataset-incubator"])

    assert results == []
    assert "dataset-incubator:discussions" in collector.fetch_errors


def test_get_discussions_success():
    """Successful GraphQL response is parsed into Discussion objects."""
    collector = DiscussionCollector(org="dataciviclab", token="fake-token")

    mock_payload = {
        "data": {
            "repository": {
                "discussions": {
                    "nodes": [
                        {
                            "number": 42,
                            "title": "IRPEF comunale: cosa ci dice?",
                            "url": "https://github.com/dataciviclab/dataset-incubator/discussions/42",
                            "category": {"name": "Civic Questions"},
                            "author": {"login": "gabry"},
                            "updatedAt": "2026-04-14T20:00:00Z",
                        }
                    ]
                }
            }
        }
    }

    with patch("agent_context_builder.discussions.HttpClient") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.post.return_value = _http_ok(mock_payload)
        results = collector.get_discussions(["dataset-incubator"])

    assert len(results) == 1
    assert results[0].number == 42
    assert results[0].category == "Civic Questions"
