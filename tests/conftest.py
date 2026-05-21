"""Shared fixtures for agent-context-builder tests.

Provides ``fake_http`` for injecting ``FakeHttpClient`` into
``DiscussionCollector`` and ``GitHubCollector``, plus convenience
fixtures for config, git state, and mock collectors.

Factory functions and sample data for render tests are also defined here —
they are importable from conftest (``from tests.conftest import ...``).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent_context_builder.config import Config
from agent_context_builder.github import GitHubCollector, RepoInfo
from agent_context_builder.git_local import GitLocalCollector, GitState
from agent_context_builder.render import Renderer
from agent_context_builder.discussions import DiscussionCollector


# ------------------------------------------------------------------
# Fake HTTP client
# ------------------------------------------------------------------


@pytest.fixture
def fake_http():
    """A clean ``FakeHttpClient`` instance.

    Usage::

        def test_discussions(fake_http):
            from lab_connectors.http import HttpResult
            from lab_connectors.testing import fake_response

            fake_http.responses["https://api.github.com/graphql"] = HttpResult(
                response=fake_response(200, json_data={...}), err=None,
            )
            collector = DiscussionCollector("org", "token", http_client=fake_http)
            collector.get_discussions(["repo"])
            assert fake_http.requests  # request log available
    """
    from lab_connectors.testing import FakeHttpClient

    return FakeHttpClient()


# ------------------------------------------------------------------
# Config fixtures
# ------------------------------------------------------------------


@pytest.fixture
def minimal_config() -> Config:
    """A ``Config`` with minimal required fields."""
    return Config(github_org="test-org", repos=["repo1"])


@pytest.fixture
def local_config(tmp_path) -> Config:
    """A ``Config`` with a workspace root (local git state enabled)."""
    return Config(
        workspace_root=tmp_path,
        github_org="test-org",
        repos=["repo1", "repo2"],
        topics={},
    )


# ------------------------------------------------------------------
# Git state fixtures
# ------------------------------------------------------------------


_UNAVAILABLE = GitState(
    available=False,
    reason="path_not_found",
    dirty=None,
    current_branch=None,
    branches_ahead=[],
    untracked_files=0,
)


@pytest.fixture
def git_unavailable() -> dict[str, GitState]:
    """All repos in unavailable state."""
    return {"repo1": _UNAVAILABLE, "repo2": _UNAVAILABLE}


# ------------------------------------------------------------------
# Mock collector helpers (for render tests)
# ------------------------------------------------------------------


@pytest.fixture
def mock_github_collector():
    """``MagicMock(spec=GitHubCollector)`` — for unit tests that don't need real HTTP."""
    return MagicMock(spec=GitHubCollector)


@pytest.fixture
def mock_git_collector():
    """``MagicMock`` mimicking ``GitLocalCollector`` for unit tests."""
    m = MagicMock()
    m.collector_warning.return_value = None
    return m


# ------------------------------------------------------------------
# Factory functions for render tests
# ------------------------------------------------------------------


def make_github_mock(
    prs=None, issues=None, fetch_errors=None, raw_file=None, repos_info=None,
):
    """Build a ``MagicMock(spec=GitHubCollector)`` with configured returns.

    Handles ``collector_warning`` derivation from *fetch_errors*.
    """
    m = MagicMock(spec=GitHubCollector)
    m.get_prs.return_value = prs or []
    m.get_issues.return_value = issues or []
    m.fetch_errors = fetch_errors or {}
    m.get_raw_file.return_value = raw_file
    m.get_repos_info.return_value = repos_info or {}
    errors = fetch_errors or {}
    if errors:
        msgs = " ".join(errors.values()).lower()
        if "403" in msgs or "rate limit" in msgs:
            m.collector_warning.return_value = (
                "GitHub rate-limit or auth error "
                f"({len(errors)} collector(s) affected) - data may be incomplete"
            )
        else:
            m.collector_warning.return_value = (
                f"GitHub fetch error ({len(errors)} collector(s) affected) "
                "- data may be incomplete"
            )
    else:
        m.collector_warning.return_value = None
    return m


def make_git_mock(repos_state=None):
    """Build a ``MagicMock(spec=GitLocalCollector)``."""
    m = MagicMock(spec=GitLocalCollector)
    m.get_repos_state.return_value = repos_state or {}
    return m


# ------------------------------------------------------------------
# Sample data for render / signals tests
# ------------------------------------------------------------------


def sample_so_json(drift: bool = False) -> str:
    """Simulate ``catalog_signals.json`` from source-observatory."""
    signals = []
    if drift:
        signals.append({
            "source": "inps", "protocol": "ckan",
            "signal_type": "inventory change", "result": "inventory change",
            "detail": "Delta inventario +8 rispetto alla baseline.",
            "suggested_action": "verificare se variazione attesa",
        })
    signals.append({
        "source": "istat_sdmx", "protocol": "sdmx",
        "signal_type": "no signal", "result": "stabile",
        "detail": "ok", "suggested_action": "nessuna",
    })
    return json.dumps({
        "captured_at": "2026-04-12", "sources_checked": len(signals), "signals": signals,
    })


def sample_di_json() -> str:
    """Simulate ``pipeline_signals.json`` from dataset-incubator."""
    return json.dumps({
        "schema_version": "1",
        "generated_at": "2026-04-16T10:00:00",
        "repo": "dataciviclab/dataset-incubator",
        "topic": "pipeline_state",
        "signals": [
            {"id": "irpef-comunale", "status": "ok", "label": "irpef-comunale", "detail": "", "action": ""},
        ],
        "summary": {"ok": 1, "warn": 0, "error": 0},
    })


def sample_di_clean_catalog_json() -> str:
    """Simulate ``clean_catalog.json`` from dataset-incubator."""
    return json.dumps({
        "schema_version": 1,
        "name": "Lab Clean Registry",
        "updated_at": "2026-04-14",
        "datasets": [
            {
                "slug": "irpef_comunale",
                "name": "IRPEF Comunale",
                "stage": "published",
                "period": {"start": 2022, "end": 2023},
                "location": {"type": "gcs", "path": "gs://dataciviclab-clean/irpef/irpef.parquet"},
                "columns": [
                    {"name": "anno", "role": "dimension"},
                    {"name": "comune", "role": "dimension"},
                    {"name": "imposta", "role": "metric"},
                ],
            },
            {
                "slug": "draft_dataset",
                "name": "Draft Dataset",
                "stage": "incubating",
                "columns": [],
            },
        ],
    })
