"""Signal data models and parsers for pre-computed Lab artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceSignal:
    """Single source health signal from source-observatory."""

    source: str
    protocol: str
    signal_type: str
    result: str
    detail: str
    suggested_action: str


@dataclass
class SourceObservatorySignals:
    """Aggregated signals from source-observatory catalog_signals.json."""

    captured_at: str
    sources_checked: int
    signals: list[SourceSignal] = field(default_factory=list)

    @property
    def regressions(self) -> list[SourceSignal]:
        return [s for s in self.signals if s.result == "regressione"]

    @property
    def alerts(self) -> list[SourceSignal]:
        return [s for s in self.signals if s.signal_type not in ("no signal", "")]


def parse_source_observatory_signals(raw: str) -> SourceObservatorySignals:
    """Parse raw JSON string into SourceObservatorySignals.

    Args:
        raw: Raw JSON content of catalog_signals.json

    Returns:
        Parsed SourceObservatorySignals instance

    Raises:
        ValueError: If the JSON is invalid or missing required fields
    """
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    signals = [
        SourceSignal(
            source=s.get("source", ""),
            protocol=s.get("protocol", ""),
            signal_type=s.get("signal_type", ""),
            result=s.get("result", ""),
            detail=s.get("detail", ""),
            suggested_action=s.get("suggested_action", ""),
        )
        for s in data.get("signals", [])
    ]

    return SourceObservatorySignals(
        captured_at=data.get("captured_at", "unknown"),
        sources_checked=data.get("sources_checked", len(signals)),
        signals=signals,
    )
