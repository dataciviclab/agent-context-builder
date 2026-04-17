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


def test_alerts_excludes_no_signal_and_regressions():
    """alerts excludes both 'no signal' sources and sources already in regressions."""
    so = parse_source_observatory_signals(_sample_json())
    # ANAC is a regression (result == "regressione"), so it must NOT appear in alerts
    assert len(so.alerts) == 0
    # ANAC must appear in regressions instead
    assert len(so.regressions) == 1
    assert so.regressions[0].source == "anac"


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


def test_parse_repo_signals_missing_fields_use_defaults():
    raw = json.dumps({"signals": [{"id": "test"}]})
    rs = parse_repo_signals(raw)
    assert rs.generated_at == "unknown"
    assert rs.signals[0].status == "ok"
    assert rs.signals[0].label == "test"
