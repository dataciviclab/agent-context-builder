"""Tests for navigation.py — pure navigation graph builders and query helpers."""

from __future__ import annotations

import pytest

from agent_context_builder.navigation import (
    build_domains,
    build_explorer_themes,
    build_repo_cards,
    build_reverse_indexes,
    category_to_domain,
    explore_ref,
    lab_map_summary,
    search_index,
)
from agent_context_builder.sources.explorer import ExplorerTheme

pytestmark = pytest.mark.pure_unit


class _Info:
    def __init__(self, description="", url=""):
        self.description = description
        self.url = url


THEMES = [
    ExplorerTheme(
        slug="territorio-ambiente",
        name="Territorio e ambiente",
        description="Ambiente ed energia",
        categories=["ambiente", "energia"],
    ),
    ExplorerTheme(
        slug="finanza-pubblica",
        name="Finanza pubblica",
        description="Conti pubblici",
        categories=["finanza-pubblica"],
    ),
]

FLAT = [
    {
        "slug": "ispra_ru_base",
        "name": "Rifiuti Urbani",
        "stage": "published",
        "source_id": "ispra",
        "registry_source": "rifiuti-urbani",
        "category": "ambiente",
    },
    {
        "slug": "bdap_entrate_stato",
        "name": "Entrate Stato",
        "stage": "incubating",
        "source_id": "bdap",
        "registry_source": "open-conto-annuale",
        "category": "finanza-pubblica",
    },
]


def _index() -> dict:
    cat_map = category_to_domain(THEMES)
    repos = build_repo_cards(
        {
            "rifiuti-urbani": _Info("Rifiuti", "https://example.test/r"),
            "open-conto-annuale": _Info("Conto annuale", "https://example.test/c"),
            "toolkit": _Info("Pipeline", "https://example.test/t"),
        },
        FLAT,
        cat_map,
        config_repos=["rifiuti-urbani", "open-conto-annuale", "toolkit"],
    )
    return {
        "schema_version": 7,
        "repos": repos,
        "datasets": {"ispra": [FLAT[0]], "bdap": [FLAT[1]]},
        "domains": build_domains(THEMES, FLAT, cat_map),
        "explorer_themes": build_explorer_themes(THEMES, FLAT, cat_map),
        "analyses": [
            {
                "slug": "rifiuti-urbani",
                "name": "Rifiuti urbani",
                "datasets": ["ispra_ru_base"],
                "status": "published",
            }
        ],
        "analyses_by_dataset": {"ispra_ru_base": ["rifiuti-urbani"]},
        **build_reverse_indexes(FLAT, cat_map),
    }


def test_category_to_domain_mapping():
    mapping = category_to_domain(THEMES)
    assert mapping["ambiente"] == "territorio-ambiente"
    assert mapping["finanza-pubblica"] == "finanza-pubblica"
    assert "pa" not in mapping


def test_build_repo_cards_enrichment():
    idx = _index()
    card = idx["repos"]["rifiuti-urbani"]
    assert card["role"] == "dati"
    assert card["domain"] == "territorio-ambiente"
    assert card["n_datasets"] == 1
    assert card["n_published"] == 1
    assert card["sources"] == ["ispra"]
    assert idx["repos"]["toolkit"]["role"] == "infra"


def test_build_domains_and_explorer_themes():
    idx = _index()
    assert idx["domains"][0]["slug"] == "territorio-ambiente"
    assert idx["domains"][0]["dataset_count"] == 1
    assert idx["explorer_themes"][0]["datasets"] == ["ispra_ru_base"]


def test_reverse_indexes():
    idx = _index()
    assert idx["by_repo"]["rifiuti-urbani"] == ["ispra_ru_base"]
    assert idx["by_domain"]["finanza-pubblica"] == ["bdap_entrate_stato"]
    assert idx["by_slug"]["ispra_ru_base"]["registry_source"] == "rifiuti-urbani"
    assert idx["by_slug"]["ispra_ru_base"]["domain"] == "territorio-ambiente"


def test_search_index_finds_dataset_by_slug():
    results = search_index(_index(), "ispra_ru_base")
    assert results
    top = results[0]
    assert top["type"] == "dataset"
    assert top["slug"] == "ispra_ru_base"
    assert top["parent_repo"] == "rifiuti-urbani"
    assert top["parent_domain"] == "territorio-ambiente"


def test_search_index_type_filter_repo():
    results = search_index(_index(), "toolkit", entity_type="repo")
    assert results
    assert results[0]["type"] == "repo"
    assert results[0]["slug"] == "toolkit"
    assert results[0]["role"] == "infra"


def test_search_index_domain_filter():
    results = search_index(_index(), "rifiuti", domain="territorio-ambiente")
    assert any(r["slug"] == "ispra_ru_base" for r in results)
    results2 = search_index(_index(), "entrate", domain="territorio-ambiente")
    assert not any(r["slug"] == "bdap_entrate_stato" for r in results2)


def test_search_index_source_and_analysis():
    src = search_index(_index(), "ispra", entity_type="source")
    assert src and src[0]["type"] == "source"
    ana = search_index(_index(), "rifiuti", entity_type="analysis")
    assert ana and ana[0]["type"] == "analysis"


def test_lab_map_summary_tree():
    summary = lab_map_summary(_index())
    assert summary["totals"]["datasets"] == 2
    assert summary["totals"]["published"] == 1
    assert any(d["slug"] == "territorio-ambiente" for d in summary["domains"])
    assert any(r["repo"] == "rifiuti-urbani" for r in summary["repos"])
    assert summary["sources"]["ispra"] == 1


def test_lab_map_summary_domain_filter():
    summary = lab_map_summary(_index(), domain="finanza-pubblica")
    assert summary["totals"]["datasets"] == 2  # totals remain global
    assert len(summary["domains"]) == 1
    assert summary["repos"] == [] or all(
        r["domain"] == "finanza-pubblica" for r in summary["repos"]
    )


def test_explore_ref_dataset_repo_domain():
    idx = _index()
    ds = explore_ref(idx, "ispra_ru_base")
    assert ds["found"] is True
    assert ds["type"] == "dataset"
    assert ds["registry_source"] == "rifiuti-urbani"
    assert ds["analyses"] == ["rifiuti-urbani"]

    repo = explore_ref(idx, "open-conto-annuale")
    assert repo["found"] is True
    assert repo["type"] == "repo"
    assert repo["datasets"] == ["bdap_entrate_stato"]

    dom = explore_ref(idx, "territorio-ambiente")
    assert dom["found"] is True
    assert dom["type"] == "domain"
    assert "ispra_ru_base" in dom["datasets"]


def test_explore_ref_analysis_and_source():
    idx = _index()
    ana = explore_ref(idx, "rifiuti-urbani")
    # slug collides with repo name — repo wins if listed after dataset miss;
    # analysis slug is also rifiuti-urbani. Dataset miss → repo hit.
    assert ana["found"] is True

    src = explore_ref(idx, "ispra")
    assert src["found"] is True
    assert src["type"] == "source"
    assert src["datasets"] == ["ispra_ru_base"]


def test_explore_ref_not_found():
    assert explore_ref(_index(), "nope")["found"] is False
