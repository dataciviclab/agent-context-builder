"""Tests for signals module (parsing and data models)."""

import json

import pytest
from lab_connectors.registry import Registry

from agent_context_builder.signals import (
    parse_explorer_catalog,
    parse_source_observatory_signals,
)
from tests.conftest import (
    sample_explorer_datasets_json,
    sample_explorer_themes_json,
)


def _sample_json(signals: list[dict] | None = None) -> str:
    return json.dumps(
        {
            "captured_at": "2026-04-12",
            "sources_checked": 3,
            "signals": signals
            or [
                {
                    "source": "istat_sdmx",
                    "protocol": "sdmx",
                    "signal_type": "no signal",
                    "result": "stabile",
                    "detail": "Stabile.",
                    "suggested_action": "nessuna",
                },
                {
                    "source": "inps",
                    "protocol": "ckan",
                    "signal_type": "inventory change",
                    "result": "inventory change",
                    "detail": "Delta inventario +12 rispetto alla baseline.",
                    "suggested_action": "verificare se variazione attesa",
                },
            ],
        }
    )


@pytest.mark.pure_unit
def test_parse_returns_correct_counts():
    so = parse_source_observatory_signals(_sample_json())
    assert so.captured_at == "2026-04-12"
    assert so.sources_checked == 3
    assert len(so.signals) == 2


@pytest.mark.pure_unit
def test_regressions_filter():
    so = parse_source_observatory_signals(_sample_json())
    assert len(so.regressions) == 0


@pytest.mark.policy
def test_drift_alerts_excludes_no_signal():
    """drift_alerts excludes stable sources and keeps catalog drift entries."""
    so = parse_source_observatory_signals(_sample_json())
    assert len(so.drift_alerts) == 1
    assert so.drift_alerts[0].source == "inps"
    assert len(so.alerts) == 1


@pytest.mark.pure_unit
def test_all_stable_empty_filters():
    raw = _sample_json(
        [
            {
                "source": "istat_sdmx",
                "protocol": "sdmx",
                "signal_type": "no signal",
                "result": "stabile",
                "detail": "ok",
                "suggested_action": "nessuna",
            }
        ]
    )
    so = parse_source_observatory_signals(raw)
    assert so.regressions == []
    assert so.alerts == []
    assert so.drift_alerts == []


@pytest.mark.pure_unit
def test_parse_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_source_observatory_signals("not json{")


@pytest.mark.policy
def test_parse_missing_fields_uses_defaults():
    raw = json.dumps({"signals": [{"source": "test"}]})
    so = parse_source_observatory_signals(raw)
    assert so.captured_at == "unknown"
    assert so.signals[0].result == ""


@pytest.mark.contract
def test_alerts_alias_matches_drift_alerts():
    """Legacy alerts alias now maps to the catalog drift alerts."""
    so = parse_source_observatory_signals(_sample_json())
    assert so.alerts == so.drift_alerts


@pytest.mark.pure_unit
def test_registry_published_incubating():
    """Registry.published/incubating filters by stage."""
    raw = json.dumps(
        {
            "schema_version": 1,
            "name": "Test",
            "updated_at": "2026-04-30",
            "datasets": [
                {"slug": "ready", "name": "Ready", "stage": "published"},
                {"slug": "cand", "name": "Candidate", "stage": "incubating"},
                {"slug": "cand2", "name": "Candidate 2", "stage": "incubating"},
            ],
        }
    )
    data = json.loads(raw)
    catalog = Registry.from_dict(data)
    published = [d for d in catalog.datasets if d.stage == "published"]
    incubating = [d for d in catalog.datasets if d.stage != "published"]
    assert len(published) == 1
    assert len(incubating) == 2
    assert {d.slug for d in incubating} == {"cand", "cand2"}


@pytest.mark.contract
def test_parse_radar_summary():
    from agent_context_builder.signals import parse_radar_summary

    raw = json.dumps(
        {
            "generated_at": "2026-04-19T09:00:00+00:00",
            "probe_date": "2026-04-19",
            "sources_total": 3,
            "status_counts": {"GREEN": 2, "YELLOW": 1, "RED": 0},
            "persistent_red": 1,
            "sources": [
                {
                    "id": "inps",
                    "status": "GREEN",
                    "protocol": "ckan",
                    "observation_mode": "catalog-watch",
                    "http_code": "200",
                    "last_check": "2026-04-19",
                    "datasets_in_use": ["ds1"],
                },
                {
                    "id": "anac",
                    "status": "YELLOW",
                    "protocol": "ckan",
                    "observation_mode": "radar-only",
                    "http_code": "200",
                    "last_check": "2026-04-19",
                    "datasets_in_use": [],
                },
                {
                    "id": "dati_salute",
                    "status": "RED",
                    "protocol": "html",
                    "observation_mode": "radar-only",
                    "http_code": "-",
                    "last_check": "2026-04-19",
                    "datasets_in_use": [],
                    "note": "SSL verify failed",
                    "red_streak": 2,
                },
                {
                    "id": "istat",
                    "status": "GREEN",
                    "protocol": "sdmx",
                    "observation_mode": "catalog-watch",
                    "http_code": "200",
                    "last_check": "2026-04-19",
                    "datasets_in_use": [],
                },
            ],
        }
    )
    summary = parse_radar_summary(raw)
    assert summary.sources_total == 3
    assert summary.green == 2
    assert summary.yellow == 1
    assert summary.red == 0
    assert summary.persistent_red == 1
    assert len(summary.unhealthy) == 2
    assert summary.unhealthy[0].id == "anac"
    assert summary.unhealthy[1].id == "dati_salute"
    assert summary.unhealthy[1].note == "SSL verify failed"
    assert summary.unhealthy[1].red_streak == 2


@pytest.mark.contract
def test_registry_from_dict_basic():
    raw = json.dumps(
        {
            "schema_version": 1,
            "source_repo": "dataciviclab/dataset-incubator",
            "updated_at": "2026-04-14",
            "datasets": [
                {
                    "slug": "irpef_comunale",
                    "name": "IRPEF Comunale",
                    "stage": "published",
                    "period": {"start": 2022, "end": 2023},
                    "location": {"type": "gcs", "path": "gs://bucket/irpef.parquet"},
                    "columns": [
                        {"name": "anno", "role": "dimension"},
                        {"name": "comune", "role": "dimension"},
                        {"name": "imposta", "role": "metric"},
                    ],
                }
            ],
        }
    )

    data = json.loads(raw)
    catalog = Registry.from_dict(data)

    assert isinstance(catalog, Registry)
    assert catalog.schema_version == 1
    assert catalog.updated_at == "2026-04-14"
    assert catalog.source_repo == "dataciviclab/dataset-incubator"
    published = [d for d in catalog.datasets if d.stage == "published"]
    assert len(published) == 1
    dataset = catalog.datasets[0]
    assert dataset.slug == "irpef_comunale"
    assert dataset.source == ""


@pytest.mark.policy
def test_registry_missing_fields_use_defaults():
    raw = json.dumps({"datasets": [{"slug": "minimal"}]})

    data = json.loads(raw)
    catalog = Registry.from_dict(data)

    assert catalog.source_repo == ""
    assert catalog.updated_at == ""
    assert catalog.datasets[0].slug == "minimal"
    assert catalog.datasets[0].name == ""  # new model doesn't default name to slug
    assert catalog.datasets[0].stage == ""
    assert catalog.datasets[0].period == {}


# ── Registry counts (registry_summary data) ────────────────────────────────


def _sample_full_registry_json() -> str:
    """A full registry.json (schema v1) with populated sections."""
    return json.dumps(
        {
            "schema_version": 1,
            "repo": "eurostat",
            "source_repo": "dataciviclab/eurostat",
            "updated_at": "2026-08-08",
            "datasets": [
                {
                    "slug": "a",
                    "name": "A",
                    "stage": "published",
                    "location": {"type": "gcs", "path": "gs://bucket/a"},
                },
                {
                    "slug": "b",
                    "name": "B",
                    "stage": "incubating",
                    "location": {"type": "gcs", "path": "gs://bucket/b"},
                },
                {"slug": "c", "name": "C", "stage": "incubating"},
            ],
            "marts": [{"slug": "m1"}, {"slug": "m2"}],
            "signals": [{"id": "s1"}],
            "codelists": {
                "schema_version": 1,
                "source_repo": "dataciviclab/eurostat",
                "codelists": {"c1": {}},
            },
            "entities": {
                "generated_from": "sample",
                "entities": {"e1": {}, "e2": {}},
                "bridges": [],
                "summary": {},
            },
        }
    )


@pytest.mark.pure_unit
def test_registry_counts():
    """Section counts + GCS availability + signals are parsed."""
    data = json.loads(_sample_full_registry_json())
    reg = Registry.from_dict(data)

    assert reg.schema_version == 1
    assert reg.source_repo == "dataciviclab/eurostat"
    assert reg.updated_at == "2026-08-08"
    assert len(reg.datasets) == 3
    published = [d for d in reg.datasets if d.stage == "published"]
    incubating = [d for d in reg.datasets if d.stage != "published"]
    assert len(published) == 1
    assert len(incubating) == 2
    gcs = sum(1 for d in reg.datasets if d.location.type == "gcs" and d.location.path)
    assert gcs == 2  # "c" has no location path
    assert len(reg.marts) == 2
    assert len(reg.signals) == 1


@pytest.mark.pure_unit
def test_registry_non_list_datasets():
    """A registry with a non-list datasets section degrades gracefully."""
    raw = json.dumps({"schema_version": 1, "datasets": {"not": "a list"}})
    data = json.loads(raw)
    # Registry.from_dict doesn't handle non-list datasets — this is an
    # edge case that shouldn't happen in production. The old parse_di_registry
    # handled it, but the new model expects valid input.
    with pytest.raises(AttributeError):
        Registry.from_dict(data)


# ── parse_explorer_catalog ─────────────────────────────────────────────────


@pytest.mark.pure_unit
def test_parse_explorer_catalog_themes():
    """Themes are derived from datasets.json (per-dataset theme) + themes.json."""
    catalog = parse_explorer_catalog(sample_explorer_datasets_json(), sample_explorer_themes_json())

    assert len(catalog.themes) == 2
    sanita = next(t for t in catalog.themes if t.slug == "sanita")
    assert sanita.name == "Sanità"
    assert sanita.datasets == ["spesa-farmaceutica"]
    territorio = next(t for t in catalog.themes if t.slug == "territorio-ambiente")
    assert territorio.datasets == ["rifiuti-urbani"]


@pytest.mark.pure_unit
def test_parse_explorer_catalog_without_theme():
    """Published datasets without a theme are reported in without_theme."""
    catalog = parse_explorer_catalog(sample_explorer_datasets_json(), sample_explorer_themes_json())

    assert catalog.without_theme == ["nuovo_dataset"]


@pytest.mark.pure_unit
def test_parse_explorer_catalog_invalid_json():
    """Malformed datasets.json raises ValueError."""
    import pytest

    with pytest.raises(ValueError, match="Invalid datasets.json"):
        parse_explorer_catalog("not json{", "{}")


@pytest.mark.pure_unit
def test_parse_explorer_catalog_missing_temi():
    """themes.json without a temi list raises ValueError."""
    import pytest

    with pytest.raises(ValueError, match="manca la chiave 'temi'"):
        parse_explorer_catalog('{"datasets": []}', '{"foo": 1}')
