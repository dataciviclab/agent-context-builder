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
        """Signals where result == 'regressione' (status degraded from previous run)."""
        return [s for s in self.signals if s.result == "regressione"]

    @property
    def alerts(self) -> list[SourceSignal]:
        """Non-stable signals that are NOT regressions (e.g. warnings, anomalies).

        Mutually exclusive with regressions: each signal appears in at most one list.
        """
        regression_sources = {s.source for s in self.regressions}
        return [
            s for s in self.signals
            if s.signal_type not in ("no signal", "")
            and s.source not in regression_sources
        ]


@dataclass
class RepoSignal:
    """Single signal entry following the repo-signals standard v1."""

    id: str
    status: str  # ok | warn | error
    label: str
    detail: str
    action: str


@dataclass
class RepoSignals:
    """Aggregated signals from a repo following the repo-signals standard v1."""

    schema_version: str
    generated_at: str
    repo: str
    topic: str
    signals: list[RepoSignal] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def actionable(self) -> list[RepoSignal]:
        """Signals that are warn or error (shown in bootstrap)."""
        return [s for s in self.signals if s.status in ("warn", "error")]


def parse_repo_signals(raw: str) -> RepoSignals:
    """Parse a repo-signals standard v1 JSON string.

    Args:
        raw: Raw JSON content of a pipeline_signals.json (or compatible)

    Returns:
        Parsed RepoSignals instance

    Raises:
        ValueError: If the JSON is invalid
    """
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    signals = [
        RepoSignal(
            id=s.get("id", ""),
            status=s.get("status", "ok"),
            label=s.get("label", s.get("id", "")),
            detail=s.get("detail", ""),
            action=s.get("action", ""),
        )
        for s in data.get("signals", [])
    ]

    return RepoSignals(
        schema_version=str(data.get("schema_version", "1")),
        generated_at=data.get("generated_at", "unknown"),
        repo=data.get("repo", ""),
        topic=data.get("topic", ""),
        signals=signals,
        summary=data.get("summary", {}),
    )


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


@dataclass
class RadarSource:
    """Single source entry from radar_summary.json."""

    id: str
    status: str
    protocol: str
    observation_mode: str
    http_code: str
    last_check: str
    datasets_in_use: list[str] = field(default_factory=list)


@dataclass
class RadarSummary:
    """Radar health summary from source-observatory radar_summary.json."""

    generated_at: str
    probe_date: str
    sources_total: int
    green: int
    yellow: int
    red: int
    sources: list[RadarSource] = field(default_factory=list)

    @property
    def unhealthy(self) -> list[RadarSource]:
        return [s for s in self.sources if s.status in ("YELLOW", "RED")]


def parse_radar_summary(raw: str) -> RadarSummary:
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    counts = data.get("status_counts", {})
    sources = [
        RadarSource(
            id=s.get("id", ""),
            status=s.get("status", ""),
            protocol=s.get("protocol", ""),
            observation_mode=s.get("observation_mode", ""),
            http_code=s.get("http_code", "-"),
            last_check=s.get("last_check", ""),
            datasets_in_use=s.get("datasets_in_use") or [],
        )
        for s in data.get("sources", [])
    ]

    return RadarSummary(
        generated_at=data.get("generated_at", "unknown"),
        probe_date=data.get("probe_date", "unknown"),
        sources_total=data.get("sources_total", len(sources)),
        green=counts.get("GREEN", 0),
        yellow=counts.get("YELLOW", 0),
        red=counts.get("RED", 0),
        sources=sources,
    )
