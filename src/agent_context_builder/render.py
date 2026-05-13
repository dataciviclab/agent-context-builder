"""Render output artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .config import Config
from .discussions import DiscussionCollector
from .github import GitHubCollector, PR
from .git_local import GitLocalCollector, GitState
from .sources.de import DataExplorerFetcher
from .sources.di import DatasetIncubatorFetcher
from .sources.so import SourceObservatoryFetcher
from .signals import (
    ExplorerTheme,
    RadarSummary,
    SourceObservatorySignals,
)
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
        self._di_fetcher = DatasetIncubatorFetcher(self.github_collector)
        self._de_fetcher = DataExplorerFetcher(self.github_collector)

    def render_session_bootstrap(self) -> str:
        """Render session_bootstrap.md.

        Organized by Lab phase: SCOUTING → INTAKE → OPEN → INFRA.
        Target: ~40 lines. Details live in workspace_triage.json.
        """
        lines = []
        lines.append("# Session Bootstrap")
        lines.append("")
        lines.append(f"**Generated**: {self.fixed_timestamp}")
        if self.config.workspace_root:
            lines.append(f"**Workspace**: {self.config.workspace_root}")
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
                    for s in radar.unhealthy:
                        di = f" — ↳ {', '.join(s.datasets_in_use)}" if s.datasets_in_use else ""
                        streak = f" (streak {s.red_streak})" if s.red_streak else ""
                        note = f" — {s.note}" if s.note else ""
                        lines.append(
                            f"  · **{s.id}** {s.status} [{s.http_code}]{note}{streak}{di}"
                        )
            else:
                lines.append("**Radar**: unavailable")

            # Catalog drift
            if so is None:
                lines.append("**Catalog Drift**: unavailable")
            else:
                issues = so.drift_alerts
                if issues:
                    for s in issues:
                        action = f" — azione: {s.suggested_action}" if s.suggested_action not in ("nessuna", "") else ""
                        lines.append(f"  · **{s.source}** ({s.protocol}): {s.signal_type}{action}")
                else:
                    lines.append(
                        f"**Catalog Drift**: no drift signals "
                        f"({so.sources_checked} sources checked)"
                    )

            lines.append("")

        # ── INTAKE ────────────────────────────────────────────────────────
        di = self._fetch_di_pipeline_signals()
        catalog = self._fetch_di_clean_catalog()

        lines.append("## 📥 INTAKE")
        lines.append("")

        if di is not None:
            summary = di.summary
            total = summary.get("total", len(di.signals))
            by_status = summary.get("by_status", {})
            status_str = " · ".join(f"{v} {k}" for k, v in sorted(by_status.items()) if v)
            lines.append(f"**Pipeline**: {total} candidates — {status_str}")
            for s in di.failed_runs:
                run = s.sample_run
                lines.append(
                    f"  ⚠️ **{s.label}** — run fallito [{run.year}]({run.run_url})"
                )
        else:
            lines.append("**Pipeline**: unavailable")

        if catalog is not None:
            clean_ready = catalog.clean_ready
            public_count = len(clean_ready)  # tutti pubblici (visibility rimosso)
            lines.append(
                f"**Dataset Catalog**: {len(clean_ready)} published · "
                f"{public_count} public · updated {catalog.updated_at}"
            )
        else:
            lines.append("**Dataset Catalog**: unavailable")
        lines.append("")

        # ── EXPLORER ──────────────────────────────────────────────────────
        explorer_themes = self._fetch_explorer_themes()
        if explorer_themes is not None:
            lines.append("## 🗂 EXPLORER")
            lines.append("")

            # Count themed datasets
            themed_slugs: set[str] = set()
            for t in explorer_themes:
                themed_slugs.update(t.datasets)

            # Gap analysis
            catalog = self._fetch_di_clean_catalog()
            clean_ready_slugs: set[str] = set()
            if catalog is not None:
                for ds in catalog.clean_ready:
                    clean_ready_slugs.add(ds.slug)
            gap = sorted(clean_ready_slugs - themed_slugs)
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
                completed = (last_deploy.get("completed_at", "")[:10]
                             if last_deploy.get("completed_at") else "?")
                lines.append(f"  **Deploy**: {icon} {conclusion} ({completed})")
            else:
                lines.append(f"  **Deploy**: dati non disponibili")

            lines.append("")

        # ── OPEN ─────────────────────────────────────────────────────────
        prs = self.github_collector.get_prs(self.config.repos)
        github_errors = self.github_collector.fetch_errors
        collector_warn = self.github_collector.collector_warning()
        discussions = self.discussion_collector.get_discussions(self.config.repos) if self.discussion_collector else []
        disc_errors = self.discussion_collector.fetch_errors if self.discussion_collector else {}

        has_open = bool(prs) or bool(discussions) or bool(self.config.topics)
        if has_open:
            lines.append("## 🔗 OPEN")
            lines.append("")

            # PRs
            if collector_warn:
                lines.append(f"> Warning: GitHub fetch error — dati incompleti")
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
            di_fetcher=self._di_fetcher,
            de_fetcher=self._de_fetcher,
        )



    def _fetch_explorer_themes(self) -> list[ExplorerTheme] | None:
        return self._de_fetcher.fetch_themes()

    def _fetch_di_pipeline_signals(self) -> RepoSignals | None:
        return self._di_fetcher.fetch_pipeline_signals()

    def _fetch_di_clean_catalog(self) -> DICleanCatalog | None:
        return self._di_fetcher.fetch_clean_catalog()




    @staticmethod
    def _format_period(period: dict[str, Any]) -> str:
        start = period.get("start")
        end = period.get("end")
        if start is None and end is None:
            return ""
        if start == end:
            return str(start)
        return f"{start or '?'}-{end or '?'}"



    def _collect_warnings(
        self, prs: list[PR], repos_state: dict[str, GitState]
    ) -> list[str]:
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
        """Render topic_index.json.

        Returns:
            - repos: GitHub description per repo (auto from API)
            - datasets_by_source: clean_ready datasets grouped by source (auto from catalog)
            - operational_topics: YAML-defined topics for agent navigation
        """
        # Repos with description from GitHub
        repos_info = self.github_collector.get_repos_info(self.config.repos)
        repos_section = {
            name: {"description": info.description, "url": info.url}
            for name, info in repos_info.items()
        }

        # Datasets grouped by source from clean_catalog
        catalog = self._fetch_di_clean_catalog()
        datasets_by_source: dict[str, list[dict[str, Any]]] = {}
        candidates_by_source: dict[str, list[dict[str, Any]]] = {}
        if catalog:
            for ds in catalog.clean_ready:
                source = ds.source or "unknown"
                datasets_by_source.setdefault(source, []).append({
                    "slug": ds.slug,
                    "name": ds.name,
                    "period": ds.period,
                })
            for ds in catalog.candidates:
                source = ds.source or "unknown"
                candidates_by_source.setdefault(source, []).append({
                    "slug": ds.slug,
                    "name": ds.name,
                    "period": ds.period,
                })

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
        explorer_themes = self._fetch_explorer_themes()
        if explorer_themes is not None:
            explorer_themes_list = [
                {
                    "slug": t.slug,
                    "name": t.name,
                    "datasets": t.datasets,
                }
                for t in explorer_themes
            ]

        return {
            "schema_version": 2,
            "generated_at": self.fixed_timestamp,
            "repos": repos_section,
            "datasets_by_source": datasets_by_source,
            "candidates_by_source": candidates_by_source,
            "operational_topics": operational_topics,
            "explorer_themes": explorer_themes_list,
        }
