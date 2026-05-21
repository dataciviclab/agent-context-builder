"""Tests for signals module (parsing and data models)."""

import json

import pytest

from agent_context_builder.signals import (
    DICleanCatalog,
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


@pytest.mark.pure_unit
def test_parse_repo_signals_basic():
    rs = parse_repo_signals(_sample_repo_signals_json())
    assert rs.repo == "dataciviclab/dataset-incubator"
    assert rs.topic == "pipeline_state"
    assert rs.generated_at == "2026-04-16T10:00:00"
    assert len(rs.signals) == 3


@pytest.mark.pure_unit
def test_parse_repo_signals_actionable():
    rs = parse_repo_signals(_sample_repo_signals_json())
    actionable = rs.actionable
    assert len(actionable) == 2
    statuses = {s.status for s in actionable}
    assert statuses == {"warn", "error"}


@pytest.mark.pure_unit
def test_parse_repo_signals_all_ok():
    raw = _sample_repo_signals_json([
        {"id": "a", "status": "ok", "label": "a", "detail": "", "action": ""},
    ])
    rs = parse_repo_signals(raw)
    assert rs.actionable == []


@pytest.mark.pure_unit
def test_parse_repo_signals_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_repo_signals("not json{")


@pytest.mark.policy
def test_parse_repo_signals_missing_fields_use_defaults():
    raw = json.dumps({"signals": [{"id": "test"}]})
    rs = parse_repo_signals(raw)
    assert rs.generated_at == "unknown"
    assert rs.signals[0].status == "ok"
    assert rs.signals[0].label == "test"


@pytest.mark.contract
def test_parse_repo_signals_sample_run_parsing():
    """sample_run fields are parsed and exposed on RepoSignal."""
    raw = json.dumps({
        "schema_version": "1",
        "generated_at": "2026-04-30",
        "repo": "di",
        "topic": "pipeline",
        "signals": [
            {
                "id": "test-candidate",
                "status": "ok",
                "label": "test-candidate",
                "detail": "ok",
                "action": "",
                "sample_run": {
                    "status": "failed",
                    "run_id": "12345",
                    "run_url": "https://github.com/.../actions/runs/12345",
                    "checked_at": "2026-04-30",
                    "year": 2020,
                    "config_path": "candidates/test-candidate/dataset.yml",
                },
            },
        ],
    })
    rs = parse_repo_signals(raw)
    assert len(rs.signals) == 1
    sr = rs.signals[0]
    assert sr.sample_run is not None
    assert sr.sample_run.status == "failed"
    assert sr.sample_run.run_id == "12345"
    assert sr.sample_run.year == 2020


@pytest.mark.pure_unit
def test_parse_repo_signals_no_sample_run():
    """Signal without sample_run has None."""
    raw = json.dumps({
        "schema_version": "1",
        "generated_at": "2026-04-30",
        "repo": "di",
        "topic": "pipeline",
        "signals": [{"id": "a", "status": "ok", "label": "a", "detail": "", "action": ""}],
    })
    rs = parse_repo_signals(raw)
    assert rs.signals[0].sample_run is None


@pytest.mark.pure_unit
def test_failed_runs_property():
    """failed_runs returns only signals with a failed sample_run."""
    raw = json.dumps({
        "schema_version": "1",
        "generated_at": "2026-04-30",
        "repo": "di",
        "topic": "pipeline",
        "signals": [
            {"id": "ok-signal", "status": "ok", "label": "ok", "detail": "", "action": ""},
            {
                "id": "failed-signal",
                "status": "ok",
                "label": "failed-signal",
                "detail": "",
                "action": "",
                "sample_run": {
                    "status": "failed", "run_id": "1", "run_url": "x",
                    "checked_at": "x", "year": 2020, "config_path": "x.yml",
                },
            },
            {"id": "ok-signal-2", "status": "ok", "label": "ok2", "detail": "", "action": ""},
        ],
    })
    rs = parse_repo_signals(raw)
    assert len(rs.failed_runs) == 1
    assert rs.failed_runs[0].id == "failed-signal"


@pytest.mark.pure_unit
def test_candidates_property():
    """candidates returns datasets with stage != published."""
    raw = json.dumps({
        "schema_version": "1",
        "name": "Test",
        "updated_at": "2026-04-30",
        "datasets": [
            {"slug": "ready", "name": "Ready", "stage": "published", "columns": []},
            {"slug": "cand", "name": "Candidate", "stage": "incubating", "columns": []},
            {"slug": "cand2", "name": "Candidate 2", "stage": "incubating", "columns": []},
        ],
    })
    catalog = parse_di_clean_catalog(raw)
    assert len(catalog.clean_ready) == 1
    assert len(catalog.candidates) == 2
    assert {d.slug for d in catalog.candidates} == {"cand", "cand2"}


@pytest.mark.contract
def test_di_clean_catalog_columns_parsed():
    """Column name and role are parsed; type and description are excluded."""
    raw = json.dumps({
        "schema_version": "1",
        "name": "Test",
        "updated_at": "2026-04-30",
        "datasets": [
            {
                "slug": "test",
                "name": "Test",
                "stage": "published",
                "columns": [
                    {"name": "anno", "type": "INTEGER", "role": "dimension", "description": "Year"},
                    {"name": "valore", "type": "FLOAT", "role": "metric", "description": "Value"},
                ],
            }
        ],
    })
    catalog = parse_di_clean_catalog(raw)
    ds = catalog.datasets[0]
    assert len(ds.columns) == 2
    assert ds.columns[0].name == "anno"
    assert ds.columns[0].role == "dimension"
    assert ds.columns[1].name == "valore"
    assert ds.columns[1].role == "metric"


@pytest.mark.contract
def test_parse_radar_summary():
    from agent_context_builder.signals import parse_radar_summary

    raw = json.dumps({
        "generated_at": "2026-04-19T09:00:00+00:00",
        "probe_date": "2026-04-19",
        "sources_total": 3,
        "status_counts": {"GREEN": 2, "YELLOW": 1, "RED": 0},
        "persistent_red": 1,
        "sources": [
            {"id": "inps", "status": "GREEN", "protocol": "ckan",
             "observation_mode": "catalog-watch", "http_code": "200",
             "last_check": "2026-04-19", "datasets_in_use": ["ds1"]},
            {"id": "anac", "status": "YELLOW", "protocol": "ckan",
             "observation_mode": "radar-only", "http_code": "200",
             "last_check": "2026-04-19", "datasets_in_use": []},
            {"id": "dati_salute", "status": "RED", "protocol": "html",
             "observation_mode": "radar-only", "http_code": "-",
             "last_check": "2026-04-19", "datasets_in_use": [],
             "note": "SSL verify failed", "red_streak": 2},
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
    assert summary.persistent_red == 1
    assert len(summary.unhealthy) == 2
    assert summary.unhealthy[0].id == "anac"
    assert summary.unhealthy[1].id == "dati_salute"
    assert summary.unhealthy[1].note == "SSL verify failed"
    assert summary.unhealthy[1].red_streak == 2


@pytest.mark.contract
def test_parse_di_clean_catalog_basic():
    raw = json.dumps({
        "schema_version": 1,
        "name": "Lab Clean Registry",
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
    # Columns are parsed: name + role only (no type, no description)
    assert len(dataset.columns) == 3
    assert dataset.columns[0].name == "anno"
    assert dataset.columns[0].role == "dimension"
    assert dataset.columns[2].name == "imposta"
    assert dataset.columns[2].role == "metric"


@pytest.mark.policy
def test_parse_di_clean_catalog_missing_fields_use_defaults():
    raw = json.dumps({"datasets": [{"slug": "minimal"}]})

    catalog = parse_di_clean_catalog(raw)

    assert catalog.name == ""
    assert catalog.updated_at == "unknown"
    assert catalog.datasets[0].name == "minimal"
    assert catalog.datasets[0].stage == "incubating"
    assert catalog.datasets[0].location == {}
    assert catalog.datasets[0].columns == []
