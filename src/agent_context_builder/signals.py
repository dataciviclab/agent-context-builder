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
class SourceCatalogSource:
    """Compact inventory summary for a single source from source-observatory."""

    source_id: str
    protocol: str
    items: int | None
    titled: int | None
    inventory_method: str
    api_base_url: str
    status: str


@dataclass
class IntakeCandidate:
    """Compact intake candidate summary from source-observatory."""

    source_id: str
    item_name: str
    title: str
    granularity: str
    year_min: int | None
    year_max: int | None
    intake_score: int | float | None


@dataclass
class SourceCatalogSummary:
    """Aggregated source inventory summary from source-observatory."""

    captured_at: str
    sources: list[SourceCatalogSource] = field(default_factory=list)
    intake_candidates: list[IntakeCandidate] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


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


def parse_source_catalog_summary(raw: str) -> SourceCatalogSummary:
    """Parse a lightweight source catalog summary JSON string.

    Args:
        raw: Raw JSON content of a source catalog summary file

    Returns:
        Parsed SourceCatalogSummary instance

    Raises:
        ValueError: If the JSON is invalid
    """
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    sources = [
        SourceCatalogSource(
            source_id=s.get("source_id", s.get("source", "")),
            protocol=s.get("protocol", ""),
            items=s.get("items", s.get("rows")),
            titled=s.get("titled", s.get("items_with_title")),
            inventory_method=s.get("inventory_method", s.get("method", "")),
            api_base_url=s.get("api_base_url", ""),
            status=s.get("status", ""),
        )
        for s in data.get("sources", [])
    ]

    intake_candidates = [
        IntakeCandidate(
            source_id=c.get("source_id", c.get("source", "")),
            item_name=c.get("item_name", c.get("item", "")),
            title=c.get("title", ""),
            granularity=c.get("granularity", ""),
            year_min=c.get("year_min"),
            year_max=c.get("year_max"),
            intake_score=c.get("intake_score"),
        )
        for c in data.get("intake_candidates", [])
    ]

    summary = data.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    return SourceCatalogSummary(
        captured_at=data.get("captured_at", "unknown"),
        sources=sources,
        intake_candidates=intake_candidates,
        summary=summary,
    )
