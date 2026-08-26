"""Render output artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .config import Config
from .discussions import DiscussionCollector
from .git_local import GitLocalCollector, GitState
from .github import PR, GitHubCollector
from .signals import (
    Analysis,
    DIRegistry,
    ExplorerCatalog,
    RadarSummary,
    SourceObservatorySignals,
)
from .sources.dcl import DataciviclabFetcher
from .sources.de import DataExplorerFetcher
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
        self._de_fetcher = DataExplorerFetcher(self.github_collector)
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

        # Explorer
        explorer_catalog = self._fetch_explorer_catalog()
        if explorer_catalog is not None:
            themed: set[str] = set()
            for t in explorer_catalog.themes:
                themed.update(t.datasets)
            gap = len(explorer_catalog.without_theme)
            status_parts.append(
                f"Explorer: {len(themed)} pubblicati" + (f" · {gap} senza tema" if gap else "")
            )

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
            de_fetcher=self._de_fetcher,
            registry_fetcher=self._registry_fetcher,
        )

    def _fetch_explorer_catalog(self) -> ExplorerCatalog | None:
        return self._de_fetcher.fetch_explorer_catalog()

    def _fetch_di_registry(self) -> DIRegistry | None:
        return self._registry_fetcher.fetch_repo("dataset-incubator")

    @staticmethod
    def _format_period(period: dict[str, Any]) -> str:
        start = period.get("start")
        end = period.get("end")
        if start is None and end is None:
            return ""
        if start == end:
            return str(start)
        return f"{start or '?'}-{end or '?'}"

    def _collect_warnings(self, prs: list[PR], repos_state: dict[str, GitState]) -> list[str]:
        """Collect warnings for triage.

        Args:
            prs: List of PRs
            repos_state: Dict mapping repo name to GitState

        Returns:
            List of warning messages
        """
        warnings = []

        # GitHub fetch failures
        for key, err in self.github_collector.fetch_errors.items():
            warnings.append(f"GitHub fetch failed — {key}: {err}")

        if len(prs) > 5:
            warnings.append(f"Many open PRs: {len(prs)}")

        # Check for dirty or ahead repos
        for repo, state in repos_state.items():
            if state.available:
                if state.dirty:
                    warnings.append(f"{repo}: dirty ({state.untracked_files} untracked)")
                if state.branches_ahead:
                    warnings.append(f"{repo}: ahead on {', '.join(state.branches_ahead)}")

        return warnings

    def render_topic_index(self) -> dict[str, Any]:
        """Render topic_index.json (schema v4).

        Returns:
            - repos: GitHub description per repo (auto from API)
            - datasets: all datasets (published + incubating) grouped by source, with stage
            - operational_topics: YAML-defined topics for agent navigation
            - explorer_themes: editorial themes from data-explorer
            - analyses: list of analyses from dataciviclab/analisi/
            - analyses_by_dataset: reverse lookup dataset → analyses
        """
        # Repos with description from GitHub
        repos_info = self.github_collector.get_repos_info(self.config.repos)
        repos_section = {
            name: {"description": info.description, "url": info.url}
            for name, info in repos_info.items()
        }

        # Datasets grouped by source — unified section with stage field
        catalog = self._fetch_di_registry()
        datasets_by_stage: dict[str, list[dict[str, Any]]] = {}
        if catalog:
            for ds in catalog.datasets:
                source = ds.source or "unknown"
                datasets_by_stage.setdefault(source, []).append(
                    {
                        "slug": ds.slug,
                        "name": ds.name or ds.slug,
                        "period": ds.period,
                        "stage": ds.stage or "incubating",
                    }
                )

        # YAML-defined operational topics (agent navigation hints)
        operational_topics = {}
        for topic_name, topic in self.config.topics.items():
            operational_topics[topic_name] = {
                "summary": topic.summary,
                "repos": topic.repos,
                "next": topic.next,
            }

        # Explorer themes from data-explorer
        explorer_themes_list: list[dict[str, Any]] = []
        explorer_catalog = self._fetch_explorer_catalog()
        if explorer_catalog is not None:
            explorer_themes_list = [
                {
                    "slug": t.slug,
                    "name": t.name,
                    "datasets": t.datasets,
                }
                for t in explorer_catalog.themes
            ]

        # ── Analyses from dataciviclab ──────────────────────────────────
        analyses_list: list[dict[str, Any]] = []
        analyses_by_dataset: dict[str, list[str]] = {}
        analyses = self._fetch_dcl_analyses()
        if analyses:
            for a in analyses:
                entry: dict[str, Any] = {
                    "slug": a.slug,
                    "name": a.name,
                    "datasets": a.datasets,
                    "status": a.status,
                }
                if a.discussion is not None:
                    entry["discussion"] = a.discussion
                if a.issue is not None:
                    entry["issue"] = a.issue
                analyses_list.append(entry)

                # Build reverse lookup: dataset_slug → [analysis_slug, ...]
                for ds_slug in a.datasets:
                    analyses_by_dataset.setdefault(ds_slug, []).append(a.slug)

        result: dict[str, Any] = {
            "schema_version": 4,
            "generated_at": self.fixed_timestamp,
            "repos": repos_section,
            "datasets": datasets_by_stage,
            "operational_topics": operational_topics,
            "explorer_themes": explorer_themes_list,
        }

        if analyses_list:
            result["analyses"] = analyses_list
            result["analyses_by_dataset"] = analyses_by_dataset

        return result

    def _fetch_dcl_analyses(self) -> list[Analysis]:
        """Fetch analyses from dataciviclab via DCL fetcher."""
        data = self._dcl_fetcher.fetch()
        return data.analyses
