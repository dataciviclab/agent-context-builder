"""Signal data models and parsers for pre-computed Lab artifacts."""

from __future__ import annotations

import ast
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
            s
            for s in self.signals
            if s.signal_type
            in ("inventory change", "structural drift", "missing_data", "follow-up candidate")
        ]


@dataclass
class RepoSignalSampleRun:
    """Sample run metadata for a pipeline signal."""

    status: str  # passed | failed
    run_id: str
    run_url: str
    checked_at: str
    year: int
    config_path: str


@dataclass
class RepoSignal:
    """Single signal entry following the repo-signals standard v1."""

    id: str
    status: str  # ok | warn | error
    label: str
    detail: str
    action: str
    source_id: str = ""
    sample_run: RepoSignalSampleRun | None = None


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

    @property
    def failed_runs(self) -> list[RepoSignal]:
        """Signals with a failed sample_run (shown in bootstrap)."""
        return [
            s for s in self.signals if s.sample_run is not None and s.sample_run.status == "failed"
        ]


@dataclass
class DIRegistryDatasetColumn:
    """Simplified column descriptor for triage."""

    name: str
    role: str  # metric | dimension


@dataclass
class DIRegistryDataset:
    """Single dataset entry from a Lab registry.json (schema v1)."""

    slug: str
    name: str
    stage: str
    source_id: str = ""
    source: str = ""
    period: dict[str, Any] = field(default_factory=dict)
    location: dict[str, Any] = field(default_factory=dict)
    metric_columns: int = 0
    dimension_columns: int = 0
    column_count: int = 0
    columns: list[DIRegistryDatasetColumn] = field(default_factory=list)


@dataclass
class DIRegistry:
    """Dataset registry from a Lab repo registry.json (schema v1)."""

    schema_version: str
    name: str
    updated_at: str
    datasets: list[DIRegistryDataset] = field(default_factory=list)

    @property
    def published(self) -> list[DIRegistryDataset]:
        """Datasets with stage published."""
        return [d for d in self.datasets if d.stage == "published"]

    @property
    def incubating(self) -> list[DIRegistryDataset]:
        """Datasets with stage incubating."""
        return [d for d in self.datasets if d.stage == "incubating"]


def _parse_sample_run(raw: dict[str, Any] | None) -> RepoSignalSampleRun | None:
    """Parse a sample_run dict into a RepoSignalSampleRun instance."""
    if raw is None:
        return None
    return RepoSignalSampleRun(
        status=raw.get("status", ""),
        run_id=raw.get("run_id", ""),
        run_url=raw.get("run_url", ""),
        checked_at=raw.get("checked_at", ""),
        year=raw.get("year", 0),
        config_path=raw.get("config_path", ""),
    )


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
            source_id=s.get("source_id", ""),
            status=s.get("status", "ok"),
            label=s.get("label", s.get("id", "")),
            detail=s.get("detail", ""),
            action=s.get("action", ""),
            sample_run=_parse_sample_run(s.get("sample_run")),
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


def parse_di_registry(raw: str) -> DIRegistry:
    """Parse a Lab registry.json (schema v1) — canonical cross-repo artifact.

    Reads the ``datasets`` section, which is the same list that the legacy
    ``clean_catalog.json`` projection exposed. ACB keeps the fields needed
    for agent orientation and triage; descriptive metadata (description,
    registry_source, mart_refs, run) remains in the upstream registry.

    Args:
        raw: Raw JSON content of a registry.json

    Returns:
        Parsed DIRegistry instance

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
            DIRegistryDataset(
                slug=item.get("slug", ""),
                name=item.get("name", item.get("slug", "")),
                stage=item.get("stage", "incubating"),
                source_id=item.get("source_id", ""),
                source=item.get("source", ""),
                period=item.get("period", {}),
                location=item.get("location", {}),
                metric_columns=metric_columns,
                dimension_columns=dimension_columns,
                column_count=len(columns),
                columns=[
                    DIRegistryDatasetColumn(name=c.get("name", ""), role=c.get("role", ""))
                    for c in columns
                ],
            )
        )

    return DIRegistry(
        schema_version=str(data.get("schema_version", "1")),
        name=data.get("name") or data.get("source_repo") or data.get("repo", ""),
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
    note: str | None = None
    red_streak: int = 0


@dataclass
class RadarSummary:
    """Radar health summary from source-observatory radar_summary.json."""

    generated_at: str
    probe_date: str
    sources_total: int
    green: int
    yellow: int
    red: int
    persistent_red: int = 0
    sources: list[RadarSource] = field(default_factory=list)

    @property
    def unhealthy(self) -> list[RadarSource]:
        return [s for s in self.sources if s.status in ("YELLOW", "RED")]


@dataclass
class Analysis:
    """Analysis entry from dataciviclab/analisi/.

    Parsed from the analysis README.md frontmatter and registry/active.md.
    """

    slug: str
    name: str
    datasets: list[str] = field(default_factory=list)
    discussion: int | None = None
    issue: int | None = None
    path: str = ""
    status: str = "active"


@dataclass
class ExplorerTheme:
    """Single theme entry from data-explorer editorial themes."""

    slug: str
    name: str
    datasets: list[str]


def parse_explorer_themes_from_py(raw_py: str) -> list[ExplorerTheme]:
    """Parse themes list from ``src/data/themes.json.py`` source file.

    Instead of fetching a static JSON (which no longer exists after the
    Observable Framework migration), this function reads the Python data
    loader file and extracts the ``themes`` variable via ``ast.parse`` +
    ``ast.literal_eval``.

    The file ``themes.json.py`` in data-explorer has a stable structure:
    a top-level ``themes`` variable assigned to a list of dicts with
    ``slug``, ``name``, ``datasets`` (and optional ``description``,
    ``questions``) keys.

    Uses full AST parsing rather than naive bracket matching so that
    brackets in docstrings, imports, or other code before ``themes =``
    do not cause false positives.

    Args:
        raw_py: Raw content of ``src/data/themes.json.py``

    Returns:
        List of ExplorerTheme instances

    Raises:
        ValueError: If the ``themes`` variable cannot be found or evaluated
    """
    try:
        tree = ast.parse(raw_py)
    except SyntaxError as exc:
        raise ValueError(f"Failed to parse themes.json.py as Python: {exc}") from exc

    themes_value = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "themes":
                    themes_value = node.value
                    break
        if themes_value is not None:
            break

    if themes_value is None:
        raise ValueError("No top-level 'themes' variable found in themes.json.py")

    try:
        data: list[dict[str, Any]] = ast.literal_eval(themes_value)
    except (ValueError, SyntaxError) as exc:
        raise ValueError(f"Failed to evaluate themes literal: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(f"Expected list literal for themes, got {type(data).__name__}")

    return [
        ExplorerTheme(
            slug=item.get("slug", ""),
            name=item.get("name", ""),
            datasets=item.get("datasets", []),
        )
        for item in data
    ]


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
            note=s.get("note"),
            red_streak=s.get("red_streak", 0),
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
        persistent_red=data.get("persistent_red", 0),
        sources=sources,
    )


@dataclass
class RepoRegistrySummary:
    """Compact per-repo summary of a registry.json (schema v1).

    Orientation data only: section counts + GCS availability + freshness.
    The detailed dataset/mart entries stay in the upstream registry,
    consumed via the toolkit MCP (registry_show/find/overview).

    ``stage`` is intentionally NOT exposed: it is a builder default
    (``incubating``) that only dataset-incubator ever promotes, so it does
    not reflect actual publication. Being in the registry with a GCS
    location is the real "published" signal.
    """

    repo: str
    available: bool
    source_repo: str = ""
    updated_at: str = ""
    datasets: int = 0
    marts: int = 0
    signals: int = 0
    codelists: int = 0
    entities: int = 0
    gcs: int = 0
    reason: str = ""


def _section_count(section: Any) -> int:
    """Count entries in a registry section.

    Sections are either lists (datasets/marts/signals) or dicts wrapping a
    dict keyed by name (codelists/codelists, entities/entities). For dicts
    the count is the number of keys.
    """
    if isinstance(section, list):
        return len(section)
    if isinstance(section, dict):
        for key in ("codelists", "entities", "signals"):
            value = section.get(key)
            if isinstance(value, list):
                return len(value)
            if isinstance(value, dict):
                return len(value)
    return 0


def parse_registry_summary(repo: str, raw: str | None) -> RepoRegistrySummary:
    """Build a compact registry summary from raw registry.json content.

    A ``None`` raw payload means the repo has no registry.json (or the fetch
    failed): reported as ``available=False`` with a reason, never raising.

    Args:
        repo: Repository name (under the org)
        raw: Raw JSON content of the repo's registry.json, or None

    Returns:
        RepoRegistrySummary instance
    """
    if raw is None:
        return RepoRegistrySummary(repo=repo, available=False, reason="registry_not_found")

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        return RepoRegistrySummary(repo=repo, available=False, reason=f"invalid_json: {exc}")
    datasets = data.get("datasets", [])
    if not isinstance(datasets, list):
        datasets = []
    gcs_count = sum(
        1 for d in datasets if isinstance(d, dict) and d.get("location", {}).get("type") == "gcs"
    )

    return RepoRegistrySummary(
        repo=repo,
        available=True,
        source_repo=data.get("source_repo", ""),
        updated_at=data.get("updated_at", ""),
        datasets=len(datasets),
        marts=_section_count(data.get("marts", [])),
        signals=_section_count(data.get("signals", [])),
        codelists=_section_count(data.get("codelists", [])),
        entities=_section_count(data.get("entities", [])),
        gcs=gcs_count,
    )


def _count_stages(datasets: list[dict[str, Any]]) -> dict[str, int]:
    """Count datasets by stage from a registry datasets list (legacy, unused).

    Kept only as a documented reference: ``stage`` is a builder default that
    only dataset-incubator promotes; it must not surface in ACB output.
    """
    counts: dict[str, int] = {}
    for ds in datasets:
        if isinstance(ds, dict):
            stage = ds.get("stage", "")
            if stage:
                counts[stage] = counts.get(stage, 0) + 1
    return counts
