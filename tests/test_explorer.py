"""Tests for sources/explorer.py — ExplorerFetcher (data-explorer pages + themes)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_context_builder.github import GitHubCollector
from agent_context_builder.sources.explorer import (
    ExplorerFetcher,
    _parse_frontmatter,
    _parse_themes,
    _resolve_datasets,
    _resolve_status,
)

pytestmark = pytest.mark.pure_unit


def _mock_collector(
    files: list[str] | None = None,
    raw_map: dict[str, str] | None = None,
) -> MagicMock:
    m = MagicMock(spec=GitHubCollector)
    m.list_files.return_value = files
    raw_map = raw_map or {}

    def _raw(repo, path, ref="main"):
        return raw_map.get(path)

    m.get_raw_file.side_effect = _raw
    m.fetch_errors = {}
    return m


# ── frontmatter helpers ─────────────────────────────────────────────────────


def test_parse_frontmatter_basic():
    raw = """---
title: Rifiuti urbani
description: Dati ISPRA
dataset_slug: ispra_ru_base
source: ISPRA
period: "2020-2024"
data_driven: true
---
# Page
"""
    fm = _parse_frontmatter(raw)
    assert fm["title"] == "Rifiuti urbani"
    assert fm["dataset_slug"] == "ispra_ru_base"
    assert fm["data_driven"] == "true"


def test_resolve_datasets_explicit_and_fallback():
    assert _resolve_datasets({"dataset_slug": "x_y"}, "page") == ["x_y"]
    assert _resolve_datasets({}, "my-page") == ["my_page"]


def test_resolve_status_from_frontmatter_and_data_driven():
    assert _resolve_status({"status": "active"}) == "active"
    assert _resolve_status({"data_driven": "true"}) == "published"
    assert _resolve_status({}) == "active"


def test_parse_themes_from_explorer_catalog():
    raw = """{
  "schema_version": 1,
  "temi": [
    {"slug": "ambiente-x", "name": "Ambiente", "categories": ["ambiente"], "icon": "x"}
  ]
}
"""
    themes = _parse_themes(raw)
    assert len(themes) == 1
    assert themes[0].slug == "ambiente-x"
    assert themes[0].categories == ["ambiente"]


def test_parse_themes_invalid_json_returns_empty():
    assert _parse_themes("not-json") == []


# ── fetch_analyses ──────────────────────────────────────────────────────────


@pytest.mark.contract
def test_fetch_analyses_from_dataset_pages():
    raw_map = {
        "src/dataset/rifiuti-urbani.md": """---
title: Rifiuti urbani
dataset_slug: ispra_ru_base
data_driven: true
source: ISPRA
---
""",
        "src/dataset/cinque-per-mille.md": """---
title: 5x1000
dataset_slug: ade_cinque_per_mille
data_driven: true
---
""",
    }
    collector = _mock_collector(files=["rifiuti-urbani.md", "cinque-per-mille.md"], raw_map=raw_map)
    analyses = ExplorerFetcher(collector).fetch_analyses()

    assert len(analyses) == 2
    by_slug = {a.slug: a for a in analyses}
    assert by_slug["rifiuti-urbani"].datasets == ["ispra_ru_base"]
    assert by_slug["rifiuti-urbani"].status == "published"
    assert by_slug["rifiuti-urbani"].source == "ISPRA"
    assert by_slug["cinque-per-mille"].datasets == ["ade_cinque_per_mille"]


@pytest.mark.contract
def test_fetch_analyses_listing_unavailable():
    collector = _mock_collector(files=None)
    assert ExplorerFetcher(collector).fetch_analyses() == []


@pytest.mark.contract
def test_fetch_analyses_page_unavailable_keeps_stub():
    collector = _mock_collector(files=["ghost.md"], raw_map={})
    analyses = ExplorerFetcher(collector).fetch_analyses()
    assert len(analyses) == 1
    assert analyses[0].slug == "ghost"
    assert analyses[0].datasets == ["ghost"]


@pytest.mark.contract
def test_fetch_analyses_caching():
    collector = _mock_collector(
        files=["a.md"],
        raw_map={"src/dataset/a.md": "---\ntitle: A\ndataset_slug: a\n---\n"},
    )
    fetcher = ExplorerFetcher(collector)
    first = fetcher.fetch_analyses()
    second = fetcher.fetch_analyses()
    assert len(first) == 1
    assert first is second
    assert collector.list_files.call_count == 1


# ── fetch_themes ────────────────────────────────────────────────────────────


@pytest.mark.contract
def test_fetch_themes_reads_catalog():
    raw = '{"temi": [{"slug": "finanza", "name": "Finanza", "categories": ["finanza-pubblica"]}]}'
    collector = _mock_collector(raw_map={"catalog/themes.json": raw})
    themes = ExplorerFetcher(collector).fetch_themes()
    assert len(themes) == 1
    assert themes[0].slug == "finanza"


@pytest.mark.contract
def test_fetch_themes_missing_returns_empty():
    collector = _mock_collector(raw_map={})
    assert ExplorerFetcher(collector).fetch_themes() == []


@pytest.mark.contract
def test_fetch_analyses_and_themes_independent_caches():
    collector = _mock_collector(
        files=["x.md"],
        raw_map={
            "src/dataset/x.md": "---\ntitle: X\ndataset_slug: x\n---\n",
            "catalog/themes.json": """{"temi": [{"slug": "t", "name": "T", "categories": []}]}""",
        },
    )
    fetcher = ExplorerFetcher(collector)
    assert len(fetcher.fetch_themes()) == 1
    assert len(fetcher.fetch_analyses()) == 1
    assert len(fetcher.fetch_themes()) == 1
