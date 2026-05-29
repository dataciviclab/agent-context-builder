"""Tests for sources/dcl.py — DataciviclabFetcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_context_builder.sources.dcl import (
    DataciviclabFetcher,
    _extract_issue_number,
    _parse_active_md,
    _parse_frontmatter,
    _resolve_datasets,
    _slug_to_datasets,
)

# ── _parse_active_md ────────────────────────────────────────────────────────


def test_parse_active_md_basic():
    """Parse standard active.md table."""
    raw = """| filone | discussion | issue | stato |
|--------|------------|-------|-------|
| irpef-comunale | [#88](url) | --- | active |
| aifa-spesa-consumo | --- | --- | active |
"""
    entries = _parse_active_md(raw)
    assert len(entries) == 2

    slug, discussion, issue = entries[0]
    assert slug == "irpef-comunale"
    assert discussion == 88
    assert issue is None

    slug, discussion, issue = entries[1]
    assert slug == "aifa-spesa-consumo"
    assert discussion is None
    assert issue is None


def test_parse_active_md_empty():
    """Empty or no-table content returns empty list."""
    assert _parse_active_md("") == []
    assert _parse_active_md("No table here") == []


def test_parse_active_md_with_issue():
    """Parse table row that includes an issue number."""
    raw = """| filone | discussion | issue | stato |
|--------|------------|-------|-------|
| malasanita | [#99](url) | [#110](url) | active |
"""
    entries = _parse_active_md(raw)
    assert len(entries) == 1
    slug, discussion, issue = entries[0]
    assert slug == "malasanita"
    assert discussion == 99
    assert issue == 110


# ── _extract_issue_number ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cell,expected",
    [
        ("[#88](url)", 88),
        ("#88", 88),
        ("---", None),
        ("—", None),
        ("", None),
        ("text", None),
    ],
)
def test_extract_issue_number(cell, expected):
    assert _extract_issue_number(cell) == expected


# ── _parse_frontmatter ─────────────────────────────────────────────────────


def test_parse_frontmatter_basic():
    """Parse YAML-like frontmatter from analysis README."""
    raw = """---
title: IRPEF Comunale 2019-2023
description: Analisi IRPEF
date: 2026-05-24
topics: economia, finanza-pubblica
status: active
dataset_slug: irpef_comunale
---
# Content
"""
    fm = _parse_frontmatter(raw)
    assert fm["title"] == "IRPEF Comunale 2019-2023"
    assert fm["status"] == "active"
    assert fm["dataset_slug"] == "irpef_comunale"
    assert "Content" not in str(fm)  # not included


def test_parse_frontmatter_no_frontmatter():
    """File without frontmatter returns empty dict."""
    assert _parse_frontmatter("# Just content") == {}


def test_parse_frontmatter_empty():
    """Empty string returns empty dict."""
    assert _parse_frontmatter("") == {}


# ── _resolve_datasets ──────────────────────────────────────────────────────


def test_resolve_datasets_explicit():
    """Explicit dataset_slug in frontmatter takes precedence."""
    fm = {"dataset_slug": "bdap_entrate_stato"}
    assert _resolve_datasets(fm, "entrate-stato") == ["bdap_entrate_stato"]


def test_resolve_datasets_fallback():
    """Without explicit slug, analysis slug is converted (hyphens → underscores)."""
    assert _resolve_datasets({}, "irpef-comunale") == ["irpef_comunale"]


def test_slug_to_datasets_convention():
    """_slug_to_datasets converts hyphens to underscores."""
    assert _slug_to_datasets("aifa-spesa-consumo") == ["aifa_spesa_consumo"]
    assert _slug_to_datasets("entrate-stato") == ["entrate_stato"]
    assert _slug_to_datasets("dataset_slug") == ["dataset_slug"]


# ── DataciviclabFetcher ────────────────────────────────────────────────────


def _mock_collector(
    registry: str | None = None, readme_map: dict[str, str] | None = None
) -> MagicMock:
    """Build a mock GitHubCollector with configurable raw_file responses."""
    m = MagicMock()

    def _raw_file_side_effect(repo, path, ref="main"):
        if repo != "dataciviclab":
            return None
        if path == "analisi/registry/active.md":
            return registry
        if readme_map and path in readme_map:
            return readme_map[path]
        return None

    m.get_raw_file.side_effect = _raw_file_side_effect
    m.fetch_errors = {}
    return m


def test_fetch_analyses_basic():
    """Fetch analyses parses registry + README frontmatter."""
    registry = """| filone | discussion | issue | stato |
|--------|------------|-------|-------|
| irpef-comunale | [#88](url) | --- | active |
"""
    readme_map = {
        "analisi/irpef-comunale/README.md": """---
title: IRPEF Comunale
dataset_slug: irpef_comunale
status: active
---
# Content
""",
    }
    collector = _mock_collector(registry, readme_map)
    fetcher = DataciviclabFetcher(collector)
    analyses = fetcher.fetch_analyses()

    assert len(analyses) == 1
    a = analyses[0]
    assert a.slug == "irpef-comunale"
    assert a.name == "IRPEF Comunale"
    assert a.datasets == ["irpef_comunale"]
    assert a.discussion == 88
    assert a.issue is None
    assert a.status == "active"


def test_fetch_analyses_registry_unavailable():
    """When registry is not fetchable, returns empty list."""
    collector = _mock_collector(registry=None)
    fetcher = DataciviclabFetcher(collector)
    assert fetcher.fetch_analyses() == []


def test_fetch_analyses_readme_unavailable():
    """When an analysis README is not found, uses slug as name."""
    registry = """| filone | discussion | issue | stato |
|--------|------------|-------|-------|
| ghost-analysis | --- | --- | active |
"""
    collector = _mock_collector(registry, readme_map={})
    fetcher = DataciviclabFetcher(collector)
    analyses = fetcher.fetch_analyses()

    assert len(analyses) == 1
    a = analyses[0]
    assert a.slug == "ghost-analysis"
    assert a.name == "ghost-analysis"  # fallback
    assert a.datasets == ["ghost_analysis"]  # hyphens → underscores
