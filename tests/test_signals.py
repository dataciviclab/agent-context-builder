"""Tests for signals module (parsing and data models)."""

import json
import pytest

from agent_context_builder.signals import (
    RepoSignals,
    SourceObservatorySignals,
    SourceSignal,
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
                "source": "anac",
                "protocol": "ckan",
                "signal_type": "health",
                "result": "regressione",
                "detail": "WAF attivo.",
                "suggested_action": "monitorare",
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
    assert len(so.regressions) == 1
    assert so.regressions[0].source == "anac"


def test_alerts_excludes_no_signal_and_regressions():
    """alerts excludes both 'no signal' sources and sources already in regressions."""
    so = parse_source_observatory_signals(_sample_json())
    # ANAC is a regression (result == "regressione"), so it must NOT appear in alerts
    assert len(so.alerts) == 0
    # ANAC must appear in regressions instead
    assert len(so.regressions) == 1
    assert so.regressions[0].source == "anac"


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


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_source_observatory_signals("not json{")


def test_parse_missing_fields_uses_defaults():
    raw = json.dumps({"signals": [{"source": "test"}]})
    so = parse_source_observatory_signals(raw)
    assert so.captured_at == "unknown"
    assert so.signals[0].result == ""


def test_alerts_excludes_regressions():
    """A signal that is a regression must not also appear in alerts."""
    so = parse_source_observatory_signals(_sample_json())
    regression_sources = {s.source for s in so.regressions}
    alert_sources = {s.source for s in so.alerts}
    assert regression_sources.isdisjoint(alert_sources), (
        f"Overlap between regressions and alerts: {regression_sources & alert_sources}"
    )


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
