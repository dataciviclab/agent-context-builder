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
        """Render session_bootstrap.md.

        Organized by Lab phase: SCOUTING → REGISTRY → ANALYSES → EXPLORER →
        OPEN → INFRA. Target: ~40 lines. Details live in workspace_triage.json.
        """
        lines = []
        lines.append("# Session Bootstrap")
        lines.append("")
        lines.append(f"**Generated**: {self.fixed_timestamp}")
        if self.config.workspace_root:
            lines.append(f"**Workspace**: {self.config.workspace_root}")

        # Degradation warning first — always visible, not buried in OPEN
        collector_warn = self.github_collector.collector_warning()
        if collector_warn:
            lines.append(f"> ⚠️ {collector_warn}")
        lines.append("")

        # ── SCOUTING ────────────────────────────────────────────────────
        radar = self._fetch_radar_summary()
        so = self._fetch_source_observatory_signals()
        has_scouting = radar is not None or so is not None

        if has_scouting:
            lines.append("## 🔍 SCOUTING")
            lines.append("")

            # Radar
            if radar is not None:
                lines.append(
                    f"**Radar**: {radar.sources_total} fonti — "
                    f"GREEN {radar.green} · YELLOW {radar.yellow} · RED {radar.red} "
                    f"(probe: {radar.probe_date})"
                )
                if radar.persistent_red:
                    lines.append(f"  ⚠ **{radar.persistent_red} persistent RED**")
                if radar.unhealthy:
                    for rs in radar.unhealthy:
                        _d = f" — ↳ {', '.join(rs.datasets_in_use)}" if rs.datasets_in_use else ""
                        streak = f" (streak {rs.red_streak})" if rs.red_streak else ""
                        note = f" — {rs.note}" if rs.note else ""
                        _row = f"  · **{rs.id}** {rs.status} [{rs.http_code}]{note}{streak}{_d}"
                        lines.append(_row)
            else:
                lines.append("**Radar**: unavailable")

            # Catalog drift
            if so is None:
                lines.append("**Catalog Drift**: unavailable")
            else:
                issues = so.drift_alerts
                if issues:
                    for alert in issues:
                        action = (
                            f" — azione: {alert.suggested_action}"
                            if alert.suggested_action not in ("nessuna", "")
                            else ""
                        )
                        _row = (
                            f"  · **{alert.source}** ({alert.protocol}):"
                            f" {alert.signal_type}{action}"
                        )
                        lines.append(_row)
                else:
                    lines.append(
                        f"**Catalog Drift**: no drift signals "
                        f"({so.sources_checked} sources checked)"
                    )

            lines.append("")

        # ── REGISTRY (cross-repo) ────────────────────────────────────────
        registry_summaries = self._registry_fetcher.fetch(self.config.repos)
        available_summaries = [
            (repo, reg) for repo, reg in registry_summaries.items() if reg is not None
        ]
        if available_summaries:
            lines.append("## 🗂 REGISTRY")
            lines.append("")
            for repo, reg in available_summaries:
                lines.append(
                    f"  · **{repo}**: {len(reg.datasets)} ds · {reg.marts} marts · "
                    f"{len(reg.signals)} signals · {reg.updated_at}"
                )
            lines.append("")

        # ── ANALYSES ──────────────────────────────────────────────────────
        analyses = self._fetch_dcl_analyses()
        if analyses:
            active = [a for a in analyses if a.status == "active"]
            archived = [a for a in analyses if a.status == "archived"]
            lines.append("## 📊 ANALYSES")
            lines.append("")
            if active:
                lines.append(f"**Attive**: {len(active)}")
                for a in active:
                    datasets_str = ", ".join(a.datasets) if a.datasets else ""
                    parts = [f"**{a.name}**"]
                    if datasets_str:
                        parts.append(f"→ {datasets_str}")
                    if a.discussion is not None:
                        parts.append(
                            f"[discussion #{a.discussion}]"
                            f"(https://github.com/orgs/dataciviclab/discussions/{a.discussion})"
                        )
                    lines.append(f"  · {' · '.join(parts)}")
            if archived:
                lines.append(f"**Archiviate**: {len(archived)}")
                for a in archived:
                    lines.append(f"  · **{a.name}**")
            lines.append("")

        # ── EXPLORER ──────────────────────────────────────────────────────
        explorer_catalog = self._fetch_explorer_catalog()
        if explorer_catalog is not None:
            lines.append("## 🗂 EXPLORER")
            lines.append("")

            # Count themed datasets
            themed_slugs: set[str] = set()
            for t in explorer_catalog.themes:
                themed_slugs.update(t.datasets)

            # Link all'explorer
            lines.append(
                f"**Pubblicati**: {len(themed_slugs)} dataset · "
                f"{len(explorer_catalog.themes)} temi · "
                f"[data-explorer](https://dataciviclab.github.io/data-explorer/)"
            )
            for t in explorer_catalog.themes:
                datasets_str = ", ".join(t.datasets)
                lines.append(f"  · **{t.name}**: {datasets_str}")

            # Gap analysis: published datasets without a theme (no page yet)
            gap = explorer_catalog.without_theme
            if gap:
                lines.append(f"  ⚠ {len(gap)} dataset published non ancora su explorer:")
                for slug in gap[:5]:
                    lines.append(f"    · {slug}")
                if len(gap) > 5:
                    lines.append(f"    · ... e altri {len(gap) - 5}")

            # Deploy status
            last_deploy = self._de_fetcher.fetch_deploy_status()
            if last_deploy is not None:
                conclusion = last_deploy.get("conclusion", "unknown")
                icon = "✅" if conclusion == "success" else "❌"
                completed = (
                    last_deploy.get("completed_at", "")[:10]
                    if last_deploy.get("completed_at")
                    else "?"
                )
                lines.append(f"  **Deploy**: {icon} {conclusion} ({completed})")
            else:
                lines.append("  **Deploy**: dati non disponibili")

            lines.append("")

        # ── OPEN ─────────────────────────────────────────────────────────
        prs = self.github_collector.get_prs(self.config.repos)
        github_errors = self.github_collector.fetch_errors
        if self.discussion_collector:
            discussions = self.discussion_collector.get_discussions(self.config.repos)
            disc_errors = self.discussion_collector.fetch_errors
        else:
            discussions = []
            disc_errors = {}

        has_open = bool(prs) or bool(discussions) or bool(self.config.topics)
        if has_open:
            lines.append("## 🔗 OPEN")
            lines.append("")

            # PRs
            if prs:
                _DEPENDABOT = {"dependabot[bot]", "dependabot"}
                feature_prs = [pr for pr in prs if pr.author not in _DEPENDABOT]
                dep_prs = [pr for pr in prs if pr.author in _DEPENDABOT]
                for pr in feature_prs[:5]:
                    lines.append(f"- [{pr.repo}#{pr.number}]({pr.url}): {pr.title}")
                if dep_prs:
                    lines.append(f"- **Dependabot**: {len(dep_prs)} bump PR(s)")
            elif not github_errors:
                lines.append("**PRs**: none open")

            # Discussions
            if disc_errors:
                lines.append(f"**Discussions**: {len(disc_errors)} fetch error(s)")
            elif discussions:
                lines.append(f"**Discussions**: {len(discussions)} open")
                for d in discussions[:3]:
                    lines.append(f"  · [{d.category}] {d.title}")

            # Topics
            if self.config.topics:
                topics = " · ".join(self.config.topics.keys())
                lines.append(f"**Topics**: {topics}")

            lines.append("")

        # ── INFRA ─────────────────────────────────────────────────────────
        repos_state = self.git_collector.get_repos_state(self.config.repos)
        local_available = any(s.available for s in repos_state.values())
        repos_count = len(self.config.repos)

        lines.append("## 🛠 INFRA")
        lines.append("")
        lines.append(f"**Repos**: {repos_count} attivi")

        if local_available:
            for repo, state in repos_state.items():
                if state.available:
                    flags = []
                    if state.dirty:
                        flags.append("dirty")
                    if state.branches_ahead:
                        flags.append(f"ahead: {', '.join(state.branches_ahead)}")
                    flag_str = f" ({', '.join(flags)})" if flags else ""
                    lines.append(f"  · **{repo}** `{state.current_branch}`{flag_str}")
        else:
            lines.append("**Local git**: no workspace")

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
        """Render topic_index.json (schema v3).

        Returns:
            - repos: GitHub description per repo (auto from API)
            - datasets_by_source: published datasets grouped by source (auto from registry)
            - candidates_by_source: incubating datasets grouped by source
            - operational_topics: YAML-defined topics for agent navigation
            - explorer_themes: editorial themes from data-explorer (v2)
            - analyses: list of analyses from dataciviclab/analisi/ (v3)
            - analyses_by_dataset: reverse lookup dataset → analyses (v3)
        """
        # Repos with description from GitHub
        repos_info = self.github_collector.get_repos_info(self.config.repos)
        repos_section = {
            name: {"description": info.description, "url": info.url}
            for name, info in repos_info.items()
        }

        # Datasets grouped by source from the dataset-incubator registry
        catalog = self._fetch_di_registry()
        datasets_by_source: dict[str, list[dict[str, Any]]] = {}
        candidates_by_source: dict[str, list[dict[str, Any]]] = {}
        all_dataset_slugs: set[str] = set()
        if catalog:
            for ds in catalog.published:
                source = ds.source or "unknown"
                datasets_by_source.setdefault(source, []).append(
                    {
                        "slug": ds.slug,
                        "name": ds.name,
                        "period": ds.period,
                    }
                )
                all_dataset_slugs.add(ds.slug)
            for ds in catalog.incubating:
                source = ds.source or "unknown"
                candidates_by_source.setdefault(source, []).append(
                    {
                        "slug": ds.slug,
                        "name": ds.name,
                        "period": ds.period,
                    }
                )

        # YAML-defined operational topics (agent navigation hints)
        operational_topics = {}
        for topic_name, topic in self.config.topics.items():
            operational_topics[topic_name] = {
                "name": topic_name,
                "summary": topic.summary,
                "repos": topic.repos,
                "paths": topic.paths,
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

        # ── v3: Analyses from dataciviclab ──────────────────────────────
        analyses_list: list[dict[str, Any]] = []
        analyses_by_dataset: dict[str, list[str]] = {}
        analyses = self._fetch_dcl_analyses()
        if analyses:
            for a in analyses:
                entry: dict[str, Any] = {
                    "slug": a.slug,
                    "name": a.name,
                    "datasets": a.datasets,
                    "path": a.path,
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

        # Determine schema version: 3 if we have analyses, 2 otherwise
        schema_version = 3 if analyses_list else 2

        result: dict[str, Any] = {
            "schema_version": schema_version,
            "generated_at": self.fixed_timestamp,
            "repos": repos_section,
            "datasets_by_source": datasets_by_source,
            "candidates_by_source": candidates_by_source,
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
