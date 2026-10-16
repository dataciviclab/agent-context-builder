"""Tests for navigation.py — pure navigation graph builders and query helpers."""

from __future__ import annotations

from typing import Any

import pytest

from agent_context_builder.navigation import (
    build_domains,
    build_explorer_themes,
    build_repo_cards,
    build_reverse_indexes,
    category_to_domain,
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

FLAT: list[dict[str, Any]] = [
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
    {
        "slug": "anac_bandi_gara",
        "name": "Anac Bandi Gara",
        "stage": "published",
        "source_id": "anac",
        "registry_source": "appalti-pubblici",
        "category": "appalti",
        "tags": ["appalti", "anac", "bandi", "gara"],
        "description": (
            "Bandi di gara pubblici italiani (CIG): oggetto, importi, stazione appaltante"
        ),
        "columns": [
            {
                "name": "cig",
                "type": "VARCHAR",
                "role": "dimension",
                "semantic_type": "cig_code",
                "description": "Codice identificativo gara",
            },
            {
                "name": "importo",
                "type": "DOUBLE",
                "role": "metric",
                "semantic_type": "",
                "description": "Importo aggiudicazione",
            },
        ],
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
        "datasets": {"ispra": [FLAT[0]], "bdap": [FLAT[1]], "anac": [FLAT[2]]},
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
