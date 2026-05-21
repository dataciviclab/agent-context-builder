"""Tests for discussions module — uses FakeHttpClient for HTTP boundary."""
from __future__ import annotations

from lab_connectors.http import HttpResult
from lab_connectors.testing import fake_response

from agent_context_builder.discussions import Discussion, DiscussionCollector

_GRAPHQL_URL = "https://api.github.com/graphql"


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
    collector = DiscussionCollector(org="dataciviclab", token=None,
                                    http_client=None)
    results = collector.get_discussions(["dataset-incubator"])

    assert results == []
    assert "dataset-incubator:discussions" in collector.fetch_errors
    assert "token" in collector.fetch_errors["dataset-incubator:discussions"].lower()


def test_get_discussions_api_error(fake_http):
    """HTTP errors are captured in fetch_errors, not raised."""
    fake_http.responses[_GRAPHQL_URL] = HttpResult(
        response=fake_response(403, text="Forbidden"),
        err=None,
    )
    collector = DiscussionCollector(org="dataciviclab", token="fake-token",
                                    http_client=fake_http)

    results = collector.get_discussions(["dataset-incubator"])

    assert results == []
    assert "dataset-incubator:discussions" in collector.fetch_errors


def test_get_discussions_success(fake_http):
    """Successful GraphQL response is parsed into Discussion objects."""
    fake_http.responses[_GRAPHQL_URL] = HttpResult(
        response=fake_response(200, json_data={
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
        }),
        err=None,
    )
    collector = DiscussionCollector(org="dataciviclab", token="fake-token",
                                    http_client=fake_http)

    results = collector.get_discussions(["dataset-incubator"])

    assert len(results) == 1
    assert results[0].number == 42
    assert results[0].category == "Civic Questions"
