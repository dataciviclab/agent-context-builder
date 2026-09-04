"""Render output artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .config import Config
from .discussions import DiscussionCollector
from .git_local import GitLocalCollector
from .github import GitHubCollector
from .signals import (
    Analysis,
    DIRegistry,
    RadarSummary,
    SourceObservatorySignals,
)
from .sources.dcl import DataciviclabFetcher
from .sources.registry import RegistryFetcher
from .sources.so import SourceObservatoryFetcher
from .triage import build_workspace_triage


class Renderer:
    """Render context artifacts."""

    def __init__(
        self,
        config: Config,
        github_collector: GitHubCollector,
        git_collector: GitLocalCollector,
        discussion_collector: DiscussionCollector | None = None,
        fixed_timestamp: str | None = None,
    ):
        """Initialize renderer.

        Args:
            config: Configuration object
            github_collector: GitHub collector instance
            git_collector: Git local collector instance
            discussion_collector: Discussion collector instance (optional; requires token)
            fixed_timestamp: Fixed ISO timestamp for deterministic output (optional, for testing)
        """
        self.config = config
        self.github_collector = github_collector
        self.git_collector = git_collector
        self.discussion_collector = discussion_collector
        self.fixed_timestamp = fixed_timestamp or datetime.now().isoformat()
        self._so_fetcher = SourceObservatoryFetcher(self.github_collector)
        self._dcl_fetcher = DataciviclabFetcher(self.github_collector)
        self._registry_fetcher = RegistryFetcher(self.github_collector)

    def render_session_bootstrap(self) -> str:
        """Render session_bootstrap.md — compact signal-oriented overview.

        Target: ~30 lines. Only actionable signals + summary counts.
        Details live in workspace_triage.json and topic_index.json.
        """
        lines = []
        lines.append("# Session Bootstrap")
        lines.append("")
        lines.append(f"**Generated**: {self.fixed_timestamp}")
        if self.config.workspace_root:
            lines.append(f"**Workspace**: {self.config.workspace_root}")

        # Degradation warning first
        collector_warn = self.github_collector.collector_warning()
        if collector_warn:
            lines.append(f"> ⚠️ {collector_warn}")
        lines.append("")

        # ── STATUS LINE ───────────────────────────────────────────────────
        status_parts: list[str] = []

        # Radar
        radar = self._fetch_radar_summary()
        if radar is not None:
            status_parts.append(f"Radar: {radar.sources_total} fonti GREEN {radar.green}")
            if radar.red > 0:
                status_parts[-1] += f" · RED {radar.red}"

        # Pipeline (from registry signals)
        registry_summaries = self._registry_fetcher.fetch(self.config.repos)
        available_repos = [r for r, reg in registry_summaries.items() if reg is not None]
        total_datasets = sum(len(reg.datasets) for _, reg in registry_summaries.items() if reg)
        if available_repos:
            status_parts.append(f"Registry: {len(available_repos)} repo · {total_datasets} dataset")

        if status_parts:
            lines.append("## Stato")
            lines.append("")
            lines.append(" · ".join(status_parts))
            lines.append("")

        # ── ACTIONABLE ────────────────────────────────────────────────────
        actionable_items: list[str] = []

        # PRs (only actionable, max 5)
        prs = self.github_collector.get_prs(self.config.repos)
        feature_prs = [pr for pr in prs if pr.actionable]
        dep_count = len([pr for pr in prs if not pr.actionable])
        for pr in feature_prs[:5]:
            actionable_items.append(f"- [PR] {pr.repo}#{pr.number}: {pr.title}")
        if dep_count:
            actionable_items.append(f"- [PR] {dep_count} dependabot bump (skipped)")

        # Source drift (only if actionable)
        so = self._fetch_source_observatory_signals()
        if so is not None:
            for alert in so.drift_alerts[:3]:
                action = (
                    f" → {alert.suggested_action}"
                    if alert.suggested_action not in ("nessuna", "")
                    else ""
                )
                actionable_items.append(f"- [Fonte] {alert.source}: {alert.signal_type}{action}")

        # Open issues with problems (pipeline errors from registry signals)
        for repo, reg in registry_summaries.items():
            if reg is None:
                continue
            for sig in reg.signals:
                if sig.status in ("error", "warn"):
                    actionable_items.append(
                        f"- [Pipeline] {repo}/{sig.id}: {sig.status} — {sig.detail}"
                    )

        if actionable_items:
            lines.append("## Richiede attenzione")
            lines.append("")
            lines.extend(actionable_items)
            lines.append("")

        # ── ANALYSES ──────────────────────────────────────────────────────
        analyses = self._fetch_dcl_analyses()
        if analyses:
            active = [a for a in analyses if a.status == "active"]
            if active:
                # Show top-3 most recent (by discussion number, higher = more recent)
                with_disc = sorted(
                    [a for a in active if a.discussion is not None],
                    key=lambda a: a.discussion or 0,
                    reverse=True,
                )
                recent = with_disc[:3] if with_disc else active[:3]
                refs = ", ".join(
                    f"{a.slug} (#{a.discussion})" if a.discussion else a.slug for a in recent
                )
                lines.append(f"## Analisi attive ({len(active)})")
                lines.append("")
                lines.append(f"Ultimo update: {refs}")
                lines.append("")

        # ── INFRA (compact) ───────────────────────────────────────────────
        repos_state = self.git_collector.get_repos_state(self.config.repos)
        dirty_repos = [r for r, s in repos_state.items() if s.available and s.dirty]
        ahead_repos = [r for r, s in repos_state.items() if s.available and s.branches_ahead]
        if dirty_repos or ahead_repos:
            infra_parts: list[str] = []
            if dirty_repos:
                infra_parts.append(f"dirty: {', '.join(dirty_repos)}")
            if ahead_repos:
                infra_parts.append(f"ahead: {', '.join(ahead_repos)}")
            lines.append("## Infra")
            lines.append("")
            lines.append(f"Repos locali: {' · '.join(infra_parts)}")
            lines.append("")

        return "\n".join(lines)

    def _fetch_radar_summary(self) -> RadarSummary | None:
        return self._so_fetcher.fetch_radar_summary()

    def _fetch_source_observatory_signals(self) -> SourceObservatorySignals | None:
        return self._so_fetcher.fetch_catalog_signals()

    def render_workspace_triage(self) -> dict[str, Any]:
        """Render workspace_triage.json.

        Returns:
            Dictionary with triage data
        """
        return build_workspace_triage(
            self.config,
            self.github_collector,
            self.git_collector,
            self.discussion_collector,
            self.fixed_timestamp,
            so_fetcher=self._so_fetcher,
            registry_fetcher=self._registry_fetcher,
        )

    def _fetch_di_registry(
        self,
    ) -> tuple[DIRegistry, dict[str, str]] | None:
        """Fetch and merge registries from ALL repos.

        Returns (merged_registry, slug_to_repo) or None if no datasets.
        slug_to_repo maps dataset slug → repo name (for registry_source).
        """
        registries = self._registry_fetcher.fetch(self.config.repos)
        merged = DIRegistry(schema_version=1, repo="merged")
        slug_to_repo: dict[str, str] = {}
        for repo_name, reg in registries.items():
            if reg is None:
                continue
            for ds in reg.datasets:
                slug_to_repo[ds.slug] = repo_name
            merged.datasets.extend(reg.datasets)
            merged.marts.extend(reg.marts)
            merged.signals.extend(reg.signals)
            if isinstance(reg.entities, dict):
                merged.entities.update(reg.entities)
            if isinstance(reg.codelists, list):
                merged.codelists.extend(reg.codelists)
        return (merged, slug_to_repo) if merged.datasets else None

    def render_topic_index(self) -> dict[str, Any]:
        """Render topic_index.json (schema v6).

        Returns:
            - repos: GitHub description per repo (auto from API)
            - datasets: all datasets grouped by source, with full metadata
            - operational_topics: YAML-defined topics for agent navigation
            - analyses: list of analyses from dataciviclab/analisi/
            - analyses_by_dataset: reverse lookup dataset → analyses
        """
        # Repos with description from GitHub
        repos_info = self.github_collector.get_repos_info(self.config.repos)
        repos_section = {
            name: {"description": info.description, "url": info.url}
            for name, info in repos_info.items()
        }

        # Datasets grouped by source — full details for downstream consumers
        # (data-explorer, lab-dashboard, dataciviclab)
        result_catalog = self._fetch_di_registry()
        datasets_by_stage: dict[str, list[dict[str, Any]]] = {}
        if result_catalog:
            catalog, slug_to_repo = result_catalog
            # Build signal lookup for clean_rows
            signals_by_id: dict[str, Any] = {}
            for sig in catalog.signals:
                if sig.run is not None:
                    signals_by_id[sig.id] = sig.run

            for ds in catalog.datasets:
                source = ds.source or ds.source_id or "unknown"
                run = signals_by_id.get(ds.slug)
                clean_rows = None
                if run is not None:
                    clean_rows = (
                        run.output_rows.get("clean") if hasattr(run, "output_rows") else None
                    )

                entry: dict[str, Any] = {
                    "slug": ds.slug,
                    "url_slug": ds.slug.replace("_", "-"),
                    "name": ds.name or ds.slug,
                    "description": ds.description,
                    "source": ds.source,
                    "source_id": ds.source_id,
                    "period": ds.period,
                    "stage": ds.stage or "incubating",
                    "tags": ds.tags,
                    "category": ds.category,
                    "registry_source": slug_to_repo.get(ds.slug, ""),
                    "clean_rows": clean_rows,
                }
                # Location (GCS path + multi_file flag)
                if ds.location and ds.location.path:
                    entry["location"] = {
                        "type": ds.location.type,
                        "path": ds.location.path,
                        "multi_file": ds.location.multi_file,
                    }
                # Columns (schema)
                if ds.columns:
                    entry["columns"] = [
                        {
                            "name": c.name,
                            "type": c.type,
                            "role": c.role,
                            "semantic_type": c.semantic_type or "",
                            "description": c.description,
                        }
                        for c in ds.columns
                    ]
                # Mart references
                if ds.mart_refs:
                    entry["mart_refs"] = ds.mart_refs
                datasets_by_stage.setdefault(source, []).append(entry)

        # YAML-defined operational topics (agent navigation hints)
        operational_topics = {}
        for topic_name, topic in self.config.topics.items():
            operational_topics[topic_name] = {
                "summary": topic.summary,
                "repos": topic.repos,
                "next": topic.next,
            }

        # ── Analyses from dataciviclab ──────────────────────────────────
        analyses_list: list[dict[str, Any]] = []
        analyses_by_dataset: dict[str, list[str]] = {}
        analyses = self._fetch_dcl_analyses()
        if analyses:
            for a in analyses:
                ae: dict[str, Any] = {
                    "slug": a.slug,
                    "name": a.name,
                    "datasets": a.datasets,
                    "status": a.status,
                }
                if a.discussion is not None:
                    ae["discussion"] = a.discussion
                if a.issue is not None:
                    ae["issue"] = a.issue
                analyses_list.append(ae)

                # Build reverse lookup: dataset_slug → [analysis_slug, ...]
                for ds_slug in a.datasets:
                    analyses_by_dataset.setdefault(ds_slug, []).append(a.slug)

        result: dict[str, Any] = {
            "schema_version": 6,
            "generated_at": self.fixed_timestamp,
            "repos": repos_section,
            "datasets": datasets_by_stage,
            "operational_topics": operational_topics,
        }

        if analyses_list:
            result["analyses"] = analyses_list
            result["analyses_by_dataset"] = analyses_by_dataset

        return result

    def _fetch_dcl_analyses(self) -> list[Analysis]:
        """Fetch analyses from dataciviclab via DCL fetcher."""
        data = self._dcl_fetcher.fetch()
        return data.analyses
