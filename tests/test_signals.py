"""Tests for signals module (parsing and data models)."""

import json
import pytest

from agent_context_builder.signals import (
    SourceObservatorySignals,
    SourceSignal,
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


def test_alerts_excludes_no_signal():
    so = parse_source_observatory_signals(_sample_json())
    assert len(so.alerts) == 1
    assert so.alerts[0].signal_type == "health"


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
