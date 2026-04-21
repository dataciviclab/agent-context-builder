"""Tests for signals module (parsing and data models)."""

import json
import pytest

from agent_context_builder.signals import (
    DICleanCatalog,
    RepoSignals,
    SourceObservatorySignals,
    SourceSignal,
    parse_di_clean_catalog,
    parse_repo_signals,
    parse_source_observatory_signals,
)


def _sample_json(signals: list[dict] | None = None) -> str:
    return json.dumps({
        "captured_at": "2026-04-12",
        "sources_checked": 3,
        "signals": signals or [
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
    })


def test_parse_returns_correct_counts():
    so = parse_source_observatory_signals(_sample_json())
    assert so.captured_at == "2026-04-12"
    assert so.sources_checked == 3
    assert len(so.signals) == 2


def test_regressions_filter():
    so = parse_source_observatory_signals(_sample_json())
    assert len(so.regressions) == 0


def test_drift_alerts_excludes_no_signal():
    """drift_alerts excludes stable sources and keeps catalog drift entries."""
    so = parse_source_observatory_signals(_sample_json())
    assert len(so.drift_alerts) == 1
    assert so.drift_alerts[0].source == "inps"
    assert len(so.alerts) == 1


def test_all_stable_empty_filters():
    raw = _sample_json([
        {
            "source": "istat_sdmx",
            "protocol": "sdmx",
            "signal_type": "no signal",
            "result": "stabile",
            "detail": "ok",
            "suggested_action": "nessuna",
        }
    ])
    so = parse_source_observatory_signals(raw)
    assert so.regressions == []
    assert so.alerts == []
    assert so.drift_alerts == []


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_source_observatory_signals("not json{")


def test_parse_missing_fields_uses_defaults():
    raw = json.dumps({"signals": [{"source": "test"}]})
    so = parse_source_observatory_signals(raw)
    assert so.captured_at == "unknown"
    assert so.signals[0].result == ""


def test_alerts_alias_matches_drift_alerts():
    """Legacy alerts alias now maps to the catalog drift alerts."""
    so = parse_source_observatory_signals(_sample_json())
    assert so.alerts == so.drift_alerts


# --- parse_repo_signals / RepoSignals ---

def _sample_repo_signals_json(signals: list[dict] | None = None) -> str:
    return json.dumps({
        "schema_version": "1",
        "generated_at": "2026-04-16T10:00:00",
        "repo": "dataciviclab/dataset-incubator",
        "topic": "pipeline_state",
        "signals": signals or [
            {
                "id": "irpef-comunale",
                "status": "ok",
                "label": "irpef-comunale (2022-2023)",
                "detail": "single-source, mart SQL presente",
                "action": "",
            },
            {
                "id": "ispra-ru-base",
                "status": "warn",
                "label": "ispra-ru-base (2020-2023)",
                "detail": "nessun mart SQL trovato",
                "action": "aggiungere mart SQL",
            },
            {
                "id": "broken-candidate",
                "status": "error",
                "label": "broken-candidate",
                "detail": "struttura non riconosciuta",
                "action": "verificare dataset.yml",
            },
        ],
        "summary": {"ok": 1, "warn": 1, "error": 1},
    })


def test_parse_repo_signals_basic():
    rs = parse_repo_signals(_sample_repo_signals_json())
    assert rs.repo == "dataciviclab/dataset-incubator"
    assert rs.topic == "pipeline_state"
    assert rs.generated_at == "2026-04-16T10:00:00"
    assert len(rs.signals) == 3


def test_parse_repo_signals_actionable():
    rs = parse_repo_signals(_sample_repo_signals_json())
    actionable = rs.actionable
    assert len(actionable) == 2
    statuses = {s.status for s in actionable}
    assert statuses == {"warn", "error"}


def test_parse_repo_signals_all_ok():
    raw = _sample_repo_signals_json([
        {"id": "a", "status": "ok", "label": "a", "detail": "", "action": ""},
    ])
    rs = parse_repo_signals(raw)
    assert rs.actionable == []


def test_parse_repo_signals_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_repo_signals("not json{")


def test_parse_repo_signals_missing_fields_use_defaults():
    raw = json.dumps({"signals": [{"id": "test"}]})
    rs = parse_repo_signals(raw)
    assert rs.generated_at == "unknown"
    assert rs.signals[0].status == "ok"
    assert rs.signals[0].label == "test"


def test_parse_radar_summary():
    from agent_context_builder.signals import parse_radar_summary

    raw = json.dumps({
        "generated_at": "2026-04-19T09:00:00+00:00",
        "probe_date": "2026-04-19",
        "sources_total": 3,
        "status_counts": {"GREEN": 2, "YELLOW": 1, "RED": 0},
        "sources": [
            {"id": "inps", "status": "GREEN", "protocol": "ckan",
             "observation_mode": "catalog-watch", "http_code": "200",
             "last_check": "2026-04-19", "datasets_in_use": ["ds1"]},
            {"id": "anac", "status": "YELLOW", "protocol": "ckan",
             "observation_mode": "radar-only", "http_code": "200",
             "last_check": "2026-04-19", "datasets_in_use": []},
            {"id": "istat", "status": "GREEN", "protocol": "sdmx",
             "observation_mode": "catalog-watch", "http_code": "200",
             "last_check": "2026-04-19", "datasets_in_use": []},
        ],
    })
    summary = parse_radar_summary(raw)
    assert summary.sources_total == 3
    assert summary.green == 2
    assert summary.yellow == 1
    assert summary.red == 0
    assert len(summary.unhealthy) == 1
    assert summary.unhealthy[0].id == "anac"


def test_parse_di_clean_catalog_basic():
    raw = json.dumps({
        "schema_version": 1,
        "name": "Lab Clean Registry",
        "updated_at": "2026-04-14",
        "datasets": [
            {
                "slug": "irpef_comunale",
                "name": "IRPEF Comunale",
                "status": "clean_ready",
                "visibility": "public",
                "period": {"start": 2022, "end": 2023},
                "location": {"type": "gcs", "path": "gs://bucket/irpef.parquet"},
                "columns": [
                    {"name": "anno", "role": "dimension"},
                    {"name": "comune", "role": "dimension"},
                    {"name": "imposta", "role": "metric"},
                ],
            }
        ],
    })

    catalog = parse_di_clean_catalog(raw)

    assert isinstance(catalog, DICleanCatalog)
    assert catalog.schema_version == "1"
    assert catalog.updated_at == "2026-04-14"
    assert len(catalog.clean_ready) == 1
    dataset = catalog.datasets[0]
    assert dataset.slug == "irpef_comunale"
    assert dataset.metric_columns == 1
    assert dataset.dimension_columns == 2
    assert dataset.column_count == 3


def test_parse_di_clean_catalog_missing_fields_use_defaults():
    raw = json.dumps({"datasets": [{"slug": "minimal"}]})

    catalog = parse_di_clean_catalog(raw)

    assert catalog.name == ""
    assert catalog.updated_at == "unknown"
    assert catalog.datasets[0].name == "minimal"
    assert catalog.datasets[0].status == ""
    assert catalog.datasets[0].location == {}
