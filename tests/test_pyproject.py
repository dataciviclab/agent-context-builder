"""Tests for pyproject fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_context_builder.github import GitHubCollector
from agent_context_builder.sources.pyproject import PyprojectFetcher, _parse_pyproject

pytestmark = pytest.mark.contract

SAMPLE_PYPROJECT = """
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "dataciviclab-eurostat"
version = "0.1.0"
description = "Eurostat datasets for DataCivicLab"
requires-python = ">=3.12"
license = "MIT"

dependencies = [
    "duckdb>=1.5.3,<2",
]

[tool.setuptools]
packages = []

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.5"]
pipeline = ["dataciviclab-toolkit @ git+https://github.com/dataciviclab/toolkit.git"]

[tool.toolkit.extends]
source_id = "eurostat"
"""


def _make_collector(raw_file_return=None):
    m = MagicMock(spec=GitHubCollector)
    m.get_raw_file.return_value = raw_file_return
    m.fetch_errors = {}
    return m


def test_parse_pyproject_basic():
    """Parse a minimal pyproject.toml."""
    import tomllib

    data = tomllib.loads(SAMPLE_PYPROJECT)
    meta = _parse_pyproject("eurostat", data)

    assert meta.repo == "eurostat"
    assert meta.name == "dataciviclab-eurostat"
    assert meta.version == "0.1.0"
    assert meta.requires_python == ">=3.12"
    assert meta.build_backend == "setuptools.build_meta"
    assert meta.license == "MIT"
    assert meta.packages == []
    assert meta.source_id == "eurostat"
    assert len(meta.dependencies) == 1
    assert "duckdb" in meta.dependencies[0]
    assert "dev" in meta.optional_dependencies
    assert "pipeline" in meta.optional_dependencies


def test_parse_pyproject_license_dict():
    """License as dict with text field."""
    import tomllib

    raw = """
[project]
name = "test"
license = {text = "CC-BY-4.0"}
"""
    data = tomllib.loads(raw)
    meta = _parse_pyproject("test", data)
    assert meta.license == "CC-BY-4.0"


def test_parse_pyproject_no_build_system():
    """Repo without [build-system]."""
    import tomllib

    raw = """
[project]
name = "test"
version = "0.1.0"
"""
    data = tomllib.loads(raw)
    meta = _parse_pyproject("test", data)
    assert meta.build_backend == ""
    assert meta.name == "test"


def test_fetcher_returns_none_for_missing():
    """Missing pyproject.toml returns None, drops 404 from fetch_errors."""
    collector = _make_collector(raw_file_return=None)
    collector.fetch_errors = {"repo1:pyproject.toml": "HTTP 404 Not Found"}

    fetcher = PyprojectFetcher(collector)
    result = fetcher.fetch_repo("repo1")

    assert result is None
    assert "repo1:pyproject.toml" not in collector.fetch_errors


def test_fetcher_parses_valid_pyproject():
    """Valid pyproject.toml is parsed correctly."""
    collector = _make_collector(raw_file_return=SAMPLE_PYPROJECT)

    fetcher = PyprojectFetcher(collector)
    result = fetcher.fetch_repo("eurostat")

    assert result is not None
    assert result.repo == "eurostat"
    assert result.source_id == "eurostat"
    assert result.packages == []


def test_fetcher_caches():
    """Second call returns cached result (no extra API call)."""
    collector = _make_collector(raw_file_return=SAMPLE_PYPROJECT)

    fetcher = PyprojectFetcher(collector)
    fetcher.fetch_repo("eurostat")
    fetcher.fetch_repo("eurostat")

    assert collector.get_raw_file.call_count == 1


def test_fetcher_keeps_real_errors():
    """Non-404 errors are kept in fetch_errors."""
    collector = _make_collector(raw_file_return=None)
    collector.fetch_errors = {"repo1:pyproject.toml": "HTTP 403 rate limit"}

    fetcher = PyprojectFetcher(collector)
    fetcher.fetch_repo("repo1")

    assert "repo1:pyproject.toml" in collector.fetch_errors


def test_fetch_multiple():
    """Fetch multiple repos."""
    collector = _make_collector()
    collector.get_raw_file.side_effect = lambda repo, path, ref="main": (
        SAMPLE_PYPROJECT if repo == "eurostat" else None
    )

    fetcher = PyprojectFetcher(collector)
    results = fetcher.fetch(["eurostat", "open-siope"])

    assert results["eurostat"] is not None
    assert results["open-siope"] is None
