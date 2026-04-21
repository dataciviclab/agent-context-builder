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
    """Aggregated drift/inventory signals from source-observatory catalog_signals.json."""

    captured_at: str
    sources_checked: int
    signals: list[SourceSignal] = field(default_factory=list)

    @property
    def regressions(self) -> list[SourceSignal]:
        """Signals where result == 'regressione' (status degraded from previous run)."""
        return [s for s in self.signals if s.result == "regressione"]

    @property
    def alerts(self) -> list[SourceSignal]:
        """Legacy alias for drift alerts.

        Kept for compatibility with older call sites. Use `drift_alerts` for
        the new catalog-only boundary.
        """
        return self.drift_alerts

    @property
    def drift_alerts(self) -> list[SourceSignal]:
        """Signals that should surface in the catalog drift section."""
        return [
            s for s in self.signals
            if s.signal_type
            in ("inventory change", "structural drift", "missing_data", "follow-up candidate")
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


@dataclass
class DICleanDataset:
    """Single clean dataset entry from dataset-incubator clean_catalog.json."""

    slug: str
    name: str
    status: str
    visibility: str
    source: str = ""
    period: dict[str, Any] = field(default_factory=dict)
    location: dict[str, Any] = field(default_factory=dict)
    metric_columns: int = 0
    dimension_columns: int = 0
    column_count: int = 0


@dataclass
class DICleanCatalog:
    """Clean dataset catalog from dataset-incubator registry."""

    schema_version: str
    name: str
    updated_at: str
    datasets: list[DICleanDataset] = field(default_factory=list)

    @property
    def clean_ready(self) -> list[DICleanDataset]:
        """Datasets with status clean_ready."""
        return [d for d in self.datasets if d.status == "clean_ready"]


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


def parse_di_clean_catalog(raw: str) -> DICleanCatalog:
    """Parse dataset-incubator registry/clean_catalog.json.

    ACB keeps the fields needed for agent orientation and triage. Descriptive
    metadata such as description, source, and registry_source remains in the
    upstream catalog and is intentionally omitted from this compact model.

    Args:
        raw: Raw JSON content of clean_catalog.json

    Returns:
        Parsed DICleanCatalog instance

    Raises:
        ValueError: If the JSON is invalid
    """
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    datasets = []
    for item in data.get("datasets", []):
        columns = item.get("columns", [])
        metric_columns = sum(1 for c in columns if c.get("role") == "metric")
        dimension_columns = sum(1 for c in columns if c.get("role") == "dimension")
        datasets.append(
            DICleanDataset(
                slug=item.get("slug", ""),
                name=item.get("name", item.get("slug", "")),
                status=item.get("status", ""),
                visibility=item.get("visibility", ""),
                source=item.get("source", ""),
                period=item.get("period", {}),
                location=item.get("location", {}),
                metric_columns=metric_columns,
                dimension_columns=dimension_columns,
                column_count=len(columns),
            )
        )

    return DICleanCatalog(
        schema_version=str(data.get("schema_version", "1")),
        name=data.get("name", ""),
        updated_at=data.get("updated_at", "unknown"),
        datasets=datasets,
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


@dataclass
class PortalCandidate:
    """Single portal candidate from discovered_portals_summary.json."""

    domain: str
    protocol: str
    probe_url: str


@dataclass
class PortalScoutSummary:
    """Portal discovery summary from source-observatory discovered_portals_summary.json."""

    generated_at: str
    total_portals: int
    new_candidates: int
    new_confirmed_protocol: int
    known_registry_seen: int
    by_protocol: dict[str, int]
    new_structured: list[PortalCandidate] = field(default_factory=list)
    known_registry_healthcheck: list[PortalCandidate] = field(default_factory=list)


def parse_portal_scout_summary(raw: str) -> PortalScoutSummary:
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    def _parse_candidates(items: list[dict[str, Any]]) -> list[PortalCandidate]:
        return [
            PortalCandidate(
                domain=c.get("domain", ""),
                protocol=c.get("protocol", ""),
                probe_url=c.get("probe_url", ""),
            )
            for c in items
        ]

    return PortalScoutSummary(
        generated_at=data.get("generated_at", "unknown"),
        total_portals=data.get("total_portals", 0),
        new_candidates=data.get("new_candidates", 0),
        new_confirmed_protocol=data.get("new_confirmed_protocol", 0),
        known_registry_seen=data.get("known_registry_seen", 0),
        by_protocol=data.get("by_protocol", {}),
        new_structured=_parse_candidates(data.get("new_structured", [])),
        known_registry_healthcheck=_parse_candidates(data.get("known_registry_healthcheck", [])),
    )
