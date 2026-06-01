"""Tests for sources/dcl.py — DataciviclabFetcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_context_builder.sources.dcl import (
    DataciviclabFetcher,
    _extract_issue_number,
    _parse_active_md,
    _parse_discussion_number,
    _parse_frontmatter,
    _parse_issue_number,
    _resolve_datasets,
    _slug_to_datasets,
)

pytestmark = pytest.mark.pure_unit

# ── _parse_active_md (legacy) ───────────────────────────────────────────────


def test_parse_active_md_basic():
    """Parse standard active.md table (legacy, kept for fallback compat)."""
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


@pytest.mark.parametrize(
    "raw,expected_title",
    [
        (
            """---
title: "Malasanità 2022: mortalità evitabile"
status: active
---
""",
            "Malasanità 2022: mortalità evitabile",
        ),
        (
            """---
title: 'Something with : colon'
status: active
---
""",
            "Something with : colon",
        ),
        (
            """---
title: IRPEF Comunale
status: active
---
""",
            "IRPEF Comunale",
        ),
    ],
)
def test_parse_frontmatter_yaml_quotes(raw, expected_title):
    """Parse frontmatter with YAML quoting (double and single)."""
    fm = _parse_frontmatter(raw)
    assert fm["title"] == expected_title
    assert fm["status"] == "active"


def test_parse_frontmatter_empty_quotes():
    """Empty quoted values are handled correctly."""
    raw = """---
title: ""
description: ""
---
"""
    fm = _parse_frontmatter(raw)
    assert fm["title"] == ""
    assert fm["description"] == ""


# ── _parse_discussion_number / _parse_issue_number ─────────────────────────


@pytest.mark.parametrize(
    "frontmatter,expected",
    [
        ({"discussion": 242}, 242),
        ({"discussion": "242"}, 242),
        ({"discussion": "  242  "}, 242),
        ({}, None),
        ({"discussion": None}, None),
        ({"discussion": "abc"}, None),
    ],
)
def test_parse_discussion_number(frontmatter, expected):
    assert _parse_discussion_number(frontmatter) == expected


@pytest.mark.parametrize(
    "frontmatter,expected",
    [
        ({"issue": 110}, 110),
        ({"issue": "110"}, 110),
        ({"issue": "  110  "}, 110),
        ({}, None),
        ({"issue": None}, None),
        ({"issue": "abc"}, None),
    ],
)
def test_parse_issue_number(frontmatter, expected):
    assert _parse_issue_number(frontmatter) == expected


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


def _mock_collector_with_listing(
    slugs: list[str] | None = None,
    readme_map: dict[str, str] | None = None,
    registry_md: str | None = None,
) -> MagicMock:
    """Build a mock GitHubCollector for the new directory-listing strategy.

    Args:
        slugs: Directories that ``list_directory`` returns (the discovered
               analysis slugs). If None, listing is "unavailable".
        readme_map: Mapping from path (e.g. ``analisi/x/README.md``) to
                    file content.
        registry_md: Optional content for ``analisi/registry/active.md``.
                     Only used as fallback when ``list_directory`` returns None.
    """
    m = MagicMock()

    def _list_directory_side_effect(repo, path, ref="main"):
        if repo != "dataciviclab":
            return None
        if path != "analisi":
            return None
        return slugs  # None if listing unavailable

    def _raw_file_side_effect(repo, path, ref="main"):
        if repo != "dataciviclab":
            return None
        if path == "analisi/registry/active.md":
            return registry_md
        if readme_map and path in readme_map:
            return readme_map[path]
        return None

    m.list_directory.side_effect = _list_directory_side_effect
    m.get_raw_file.side_effect = _raw_file_side_effect
    m.fetch_errors = {}
    return m


@pytest.mark.contract
def test_fetch_analyses_basic():
    """Fetch analyses via directory listing + README frontmatter.

    Discussion number comes from frontmatter ``discussion`` field.
    """
    readme_map = {
        "analisi/irpef-comunale/README.md": """---
title: IRPEF Comunale
dataset_slug: irpef_comunale
status: active
discussion: 88
---
# Content
""",
    }
    collector = _mock_collector_with_listing(
        slugs=["irpef-comunale"], readme_map=readme_map
    )
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


@pytest.mark.contract
def test_fetch_analyses_multiple():
    """Fetch multiple analyses via directory listing."""
    readme_map = {
        "analisi/aifa-spesa-consumo/README.md": """---
title: AIFA Spesa
dataset_slug: aifa_spesa_consumo
status: active
discussion: 242
---
""",
        "analisi/entrate-stato/README.md": """---
title: Entrate Stato
dataset_slug: bdap_entrate_stato
status: active
discussion: 218
---
""",
    }
    collector = _mock_collector_with_listing(
        slugs=["aifa-spesa-consumo", "entrate-stato"],
        readme_map=readme_map,
    )
    fetcher = DataciviclabFetcher(collector)
    analyses = fetcher.fetch_analyses()

    assert len(analyses) == 2
    slugs = [a.slug for a in analyses]
    assert "aifa-spesa-consumo" in slugs
    assert "entrate-stato" in slugs


@pytest.mark.contract
def test_fetch_analyses_listing_unavailable():
    """When directory listing is unavailable AND no registry fallback, returns empty."""
    collector = _mock_collector_with_listing(slugs=None, registry_md=None)
    fetcher = DataciviclabFetcher(collector)
    assert fetcher.fetch_analyses() == []


@pytest.mark.contract
def test_fetch_analyses_listing_unavailable_fallback():
    """When directory listing fails, falls back to active.md registry."""
    registry_md = """| filone | discussion | issue | stato |
|--------|------------|-------|-------|
| legacy-slug | --- | --- | active |
"""
    readme_map = {
        "analisi/legacy-slug/README.md": """---
title: Legacy Analysis
status: active
---
""",
    }
    collector = _mock_collector_with_listing(
        slugs=None, readme_map=readme_map, registry_md=registry_md
    )
    fetcher = DataciviclabFetcher(collector)
    analyses = fetcher.fetch_analyses()

    assert len(analyses) == 1
    a = analyses[0]
    assert a.slug == "legacy-slug"
    assert a.name == "Legacy Analysis"
    assert a.status == "active"


@pytest.mark.contract
def test_fetch_analyses_readme_unavailable():
    """When an analysis README is not found, uses slug as name."""
    collector = _mock_collector_with_listing(
        slugs=["ghost-analysis"], readme_map={}
    )
    fetcher = DataciviclabFetcher(collector)
    analyses = fetcher.fetch_analyses()

    assert len(analyses) == 1
    a = analyses[0]
    assert a.slug == "ghost-analysis"
    assert a.name == "ghost-analysis"  # fallback
    assert a.datasets == ["ghost_analysis"]  # hyphens → underscores


@pytest.mark.contract
def test_fetch_analyses_excludes_non_analysis_dirs():
    """Directories like _template/ and registry/ are excluded."""
    collector = _mock_collector_with_listing(
        slugs=["_template", "registry", "irpef-comunale"],
        readme_map={
            "analisi/irpef-comunale/README.md": """---
title: IRPEF Comunale
status: active
---
""",
        },
    )
    fetcher = DataciviclabFetcher(collector)
    analyses = fetcher.fetch_analyses()

    assert len(analyses) == 1
    assert analyses[0].slug == "irpef-comunale"


@pytest.mark.contract
def test_fetch_analyses_frontmatter_discussion_and_issue():
    """Discussion and issue numbers come from frontmatter."""
    readme_map = {
        "analisi/malasanita/README.md": """---
title: "Malasanità 2022: mortalità evitabile e dotazione sanitaria regionale"
dataset_slug: malasanita_struttura_mortalita
status: active
discussion: 99
issue: 110
---
# Content
""",
    }
    collector = _mock_collector_with_listing(
        slugs=["malasanita"], readme_map=readme_map
    )
    fetcher = DataciviclabFetcher(collector)
    analyses = fetcher.fetch_analyses()

    assert len(analyses) == 1
    a = analyses[0]
    assert a.slug == "malasanita"
    assert a.name == "Malasanità 2022: mortalità evitabile e dotazione sanitaria regionale"
    assert a.datasets == ["malasanita_struttura_mortalita"]
    assert a.discussion == 99
    assert a.issue == 110
    assert a.status == "active"


@pytest.mark.contract
def test_fetch_analyses_no_discussion_in_frontmatter():
    """Analysis without discussion/issue in frontmatter gets None."""
    readme_map = {
        "analisi/civile-flussi/README.md": """---
title: Flussi giustizia civile
dataset_slug: civile_flussi
status: active
---
""",
    }
    collector = _mock_collector_with_listing(
        slugs=["civile-flussi"], readme_map=readme_map
    )
    fetcher = DataciviclabFetcher(collector)
    analyses = fetcher.fetch_analyses()

    assert len(analyses) == 1
    a = analyses[0]
    assert a.discussion is None
    assert a.issue is None


@pytest.mark.contract
def test_fetch_analyses_caching():
    """Fetcher caches results after first call."""
    readme_map = {
        "analisi/test/README.md": """---
title: Test
status: active
---
""",
    }
    collector = _mock_collector_with_listing(
        slugs=["test"], readme_map=readme_map
    )
    fetcher = DataciviclabFetcher(collector)
    analyses1 = fetcher.fetch_analyses()
    analyses2 = fetcher.fetch_analyses()

    assert len(analyses1) == 1
    assert len(analyses2) == 1
    # list_directory called exactly once (cached on second call)
    assert collector.list_directory.call_count == 1
