"""Render output artifacts."""

from datetime import datetime
from typing import Any

from .config import Config
from .discussions import Discussion, DiscussionCollector
from .github import GitHubCollector, PR
from .git_local import GitLocalCollector, GitState
from .signals import (
    DICleanCatalog,
    RadarSummary,
    RepoSignals,
    SourceObservatorySignals,
    parse_di_clean_catalog,
    parse_radar_summary,
    parse_repo_signals,
    parse_source_observatory_signals,
)


class _UNSET:
    """Sentinel for uninitialized cache values."""


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
        # Cache for remote signal fetches — avoids double requests within one build
        self._so_signals_cache: SourceObservatorySignals | None | type[_UNSET] = _UNSET
        self._radar_cache: RadarSummary | None | type[_UNSET] = _UNSET
        self._di_signals_cache: RepoSignals | None | type[_UNSET] = _UNSET
        self._di_clean_catalog_cache: DICleanCatalog | None | type[_UNSET] = _UNSET

    def render_session_bootstrap(self) -> str:
        """Render session_bootstrap.md.

        Returns:
            Markdown content (target: 80-120 lines)
        """
        lines = []
        lines.append("# Session Bootstrap")
        lines.append("")
        lines.append(f"**Generated**: {self.fixed_timestamp}")
        if self.config.workspace_root:
            lines.append(f"**Workspace**: {self.config.workspace_root}")
        lines.append("")

        # Active repos
        lines.append("## Repos")
        lines.append("")
        for repo in self.config.repos:
            lines.append(f"- {repo}")
        lines.append("")

        # Open PRs
        lines.append("## Open PRs")
        lines.append("")
        prs = self.github_collector.get_prs(self.config.repos)
        github_errors = self.github_collector.fetch_errors
        collector_warn = self.github_collector.collector_warning()
        if collector_warn:
            lines.append(f"> **Warning**: {collector_warn}")
        if prs:
            _DEPENDABOT = {"dependabot[bot]", "dependabot"}
            feature_prs = [pr for pr in prs if pr.author not in _DEPENDABOT]
            dep_prs = [pr for pr in prs if pr.author in _DEPENDABOT]
            for pr in feature_prs[:10]:
                lines.append(f"- [{pr.repo}#{pr.number}]({pr.url}): {pr.title}")
            if dep_prs:
                lines.append(
                    f"- **Dependabot**: {len(dep_prs)} bump PR(s) - "
                    + ", ".join(f"[#{pr.number}]({pr.url})" for pr in dep_prs[:2])
                    + (" ..." if len(dep_prs) > 2 else "")
                )
        elif not github_errors:
            lines.append("*No open PRs*")
        lines.append("")

        # Open Discussions
        if self.discussion_collector is not None:
            lines.append("## Open Discussions")
            lines.append("")
            discussions = self.discussion_collector.get_discussions(self.config.repos)
            disc_errors = self.discussion_collector.fetch_errors
            if disc_errors:
                lines.append(f"> **Discussions unavailable** — {len(disc_errors)} fetch error(s)")
            if discussions:
                for d in discussions[:10]:
                    lines.append(f"- [{d.repo}#{d.number}]({d.url}) [{d.category}]: {d.title}")
            elif not disc_errors:
                lines.append("*No open discussions*")
            lines.append("")

        # Local git state per repo
        lines.append("## Local State")
        lines.append("")
        repos_state = self.git_collector.get_repos_state(self.config.repos)
        has_local_state = False
        for repo, state in repos_state.items():
            if state.available:
                has_local_state = True
                lines.append(f"**{repo}**: `{state.current_branch}`")
                if state.dirty:
                    lines.append(f"  - dirty ({state.untracked_files} untracked)")
                if state.branches_ahead:
                    lines.append(f"  - ahead: {', '.join(state.branches_ahead)}")
        if not has_local_state:
            lines.append("*No local git repos found*")
        lines.append("")

        # Topics
        if self.config.topics:
            lines.append("## Topics")
            lines.append("")
            for topic_name in self.config.topics:
                lines.append(f"- {topic_name}")
            lines.append("")

        # Radar health (GREEN/YELLOW/RED per fonte)
        radar = self._fetch_radar_summary()
        lines += self._render_radar_section(radar)

        # Source health (only issues — skip stable sources)
        so = self._fetch_source_observatory_signals()
        lines += self._render_source_health_section(so)

        # Pipeline state (only warn/error candidates)
        di = self._fetch_di_pipeline_signals()
        lines += self._render_pipeline_state_section(di)

        # Dataset catalog (clean/queryable datasets)
        catalog = self._fetch_di_clean_catalog()
        lines += self._render_dataset_catalog_section(catalog)

        return "\n".join(lines)

    def _fetch_radar_summary(self) -> RadarSummary | None:
        if self._radar_cache is not _UNSET:
            return self._radar_cache  # type: ignore[return-value]
        raw = self.github_collector.get_raw_file(
            "source-observatory", "data/radar/radar_summary.json"
        )
        if raw is None:
            self._radar_cache = None
            return None
        try:
            result = parse_radar_summary(raw)
        except ValueError as exc:
            self.github_collector.fetch_errors["source-observatory:radar_summary"] = str(exc)
            result = None
        self._radar_cache = result
        return result

    def _render_radar_section(self, radar: RadarSummary | None) -> list[str]:
        lines = ["## Radar Status", ""]
        if radar is None:
            lines.append("> *radar_summary unavailable*")
            lines.append("")
            return lines
        lines.append(
            f"Fonti: {radar.sources_total} — "
            f"GREEN {radar.green} · YELLOW {radar.yellow} · RED {radar.red} "
            f"(probe: {radar.probe_date})"
        )
        if radar.unhealthy:
            lines.append("")
            for s in radar.unhealthy:
                lines.append(f"- **{s.id}** ({s.protocol}): {s.status} [HTTP {s.http_code}]")
        lines.append("")
        return lines

    def _fetch_source_observatory_signals(self) -> SourceObservatorySignals | None:
        if self._so_signals_cache is not _UNSET:
            return self._so_signals_cache  # type: ignore[return-value]
        raw = self.github_collector.get_raw_file(
            "source-observatory", "data/catalog/catalog_signals.json"
        )
        if raw is None:
            self._so_signals_cache = None
            return None
        try:
            result = parse_source_observatory_signals(raw)
        except ValueError as exc:
            self.github_collector.fetch_errors["source-observatory:catalog_signals"] = str(exc)
            result = None
        self._so_signals_cache = result
        return result

    def _render_source_health_section(
        self, so: SourceObservatorySignals | None
    ) -> list[str]:
        lines = []
        lines.append("## Source Health")
        lines.append("")
        if so is None:
            err = self.github_collector.fetch_errors.get(
                "source-observatory:data/catalog/catalog_signals.json"
            ) or self.github_collector.fetch_errors.get(
                "source-observatory:catalog_signals"
            )
            if err:
                lines.append(f"> *catalog_signals unavailable — {err}*")
            else:
                lines.append("> *catalog_signals unavailable*")
            lines.append("")
            return lines

        # Show regressions first, then other alerts (mutually exclusive sets)
        issues = so.regressions + so.alerts
        if issues:
            for s in issues:
                lines.append(f"- **{s.source}** ({s.protocol}): {s.result} — {s.detail}")
                if s.suggested_action and s.suggested_action != "nessuna":
                    lines.append(f"  - azione: {s.suggested_action}")
        else:
            lines.append(f"*All {so.sources_checked} sources stable* (as of {so.captured_at})")
        lines.append(f"  *(captured {so.captured_at}, {so.sources_checked} sources checked)*")
        lines.append("")
        return lines

    def render_workspace_triage(self) -> dict[str, Any]:
        """Render workspace_triage.json.

        Returns:
            Dictionary with triage data
        """
        prs = self.github_collector.get_prs(self.config.repos)
        issues = self.github_collector.get_issues(self.config.repos)
        repos_state = self.git_collector.get_repos_state(self.config.repos)

        discussions: list[Discussion] = []
        disc_errors: dict[str, str] = {}
        if self.discussion_collector is not None:
            discussions = self.discussion_collector.get_discussions(self.config.repos)
            disc_errors = self.discussion_collector.fetch_errors

        github_errors = self.github_collector.fetch_errors
        triage = {
            "generated_at": self.fixed_timestamp,
            "workspace_root": (
                str(self.config.workspace_root) if self.config.workspace_root else None
            ),
            "repos": self.config.repos,
            "open_prs": len(prs) if not github_errors else None,
            "prs": [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "repo": pr.repo,
                    "url": pr.url,
                }
                for pr in prs
            ],
            "open_issues": len(issues) if not github_errors else None,
            "issues": [
                {
                    "number": issue.number,
                    "title": issue.title,
                    "repo": issue.repo,
                    "url": issue.url,
                }
                for issue in issues
            ],
            "open_discussions": (
                len(discussions)
                if self.discussion_collector is not None and not disc_errors
                else None
            ),
            "discussions": [
                {
                    "number": d.number,
                    "title": d.title,
                    "repo": d.repo,
                    "url": d.url,
                    "category": d.category,
                }
                for d in discussions
            ],
            "github_fetch_errors": {**github_errors, **disc_errors},
            "git_state": {
                repo: {
                    "available": state.available,
                    "reason": state.reason,
                    "dirty": state.dirty,
                    "current_branch": state.current_branch,
                    "branches_ahead": state.branches_ahead,
                    "untracked_files": state.untracked_files,
                }
                for repo, state in repos_state.items()
            },
            "warnings": self._collect_warnings(prs, repos_state),
            "radar": self._build_radar_dict(),
            "source_health": self._build_source_health_dict(),
            "pipeline_state": self._build_pipeline_state_dict(),
            "dataset_catalog": self._build_dataset_catalog_dict(),
        }
        return triage

    def _build_radar_dict(self) -> dict[str, Any]:
        radar = self._fetch_radar_summary()
        if radar is None:
            return {"available": False}
        return {
            "available": True,
            "probe_date": radar.probe_date,
            "sources_total": radar.sources_total,
            "green": radar.green,
            "yellow": radar.yellow,
            "red": radar.red,
            "unhealthy": [
                {"id": s.id, "status": s.status, "protocol": s.protocol, "http_code": s.http_code}
                for s in radar.unhealthy
            ],
        }

    def _build_source_health_dict(self) -> dict[str, Any]:
        so = self._fetch_source_observatory_signals()
        if so is None:
            return {
                "available": False,
                "errors": {
                    k: v for k, v in self.github_collector.fetch_errors.items()
                    if "source-observatory" in k
                },
            }
        return {
            "available": True,
            "captured_at": so.captured_at,
            "sources_checked": so.sources_checked,
            "regressions": [
                {
                    "source": s.source,
                    "protocol": s.protocol,
                    "detail": s.detail,
                    "suggested_action": s.suggested_action,
                }
                for s in so.regressions
            ],
            "alerts": [
                {
                    "source": s.source,
                    "protocol": s.protocol,
                    "signal_type": s.signal_type,
                    "result": s.result,
                    "detail": s.detail,
                    "suggested_action": s.suggested_action,
                }
                for s in so.alerts
            ],
        }

    def _fetch_di_pipeline_signals(self) -> RepoSignals | None:
        if self._di_signals_cache is not _UNSET:
            return self._di_signals_cache  # type: ignore[return-value]
        raw = self.github_collector.get_raw_file(
            "dataset-incubator", "registry/pipeline_signals.json"
        )
        if raw is None:
            self._di_signals_cache = None
            return None
        try:
            result = parse_repo_signals(raw)
        except ValueError as exc:
            self.github_collector.fetch_errors["dataset-incubator:pipeline_signals"] = str(exc)
            result = None
        self._di_signals_cache = result
        return result

    def _fetch_di_clean_catalog(self) -> DICleanCatalog | None:
        if self._di_clean_catalog_cache is not _UNSET:
            return self._di_clean_catalog_cache  # type: ignore[return-value]
        raw = self.github_collector.get_raw_file(
            "dataset-incubator", "registry/clean_catalog.json"
        )
        if raw is None:
            self._di_clean_catalog_cache = None
            return None
        try:
            result = parse_di_clean_catalog(raw)
        except ValueError as exc:
            self.github_collector.fetch_errors["dataset-incubator:clean_catalog"] = str(exc)
            result = None
        self._di_clean_catalog_cache = result
        return result

    def _render_pipeline_state_section(self, di: RepoSignals | None) -> list[str]:
        lines = []
        lines.append("## Pipeline State")
        lines.append("")
        if di is None:
            err = self.github_collector.fetch_errors.get(
                "dataset-incubator:registry/pipeline_signals.json"
            ) or self.github_collector.fetch_errors.get(
                "dataset-incubator:pipeline_signals"
            )
            if err:
                lines.append(f"> *pipeline_signals unavailable — {err}*")
            else:
                lines.append("> *pipeline_signals unavailable*")
            lines.append("")
            return lines

        summary = di.summary
        total = summary.get("total", len(di.signals))
        by_status = summary.get("by_status", {})
        actionable = di.actionable
        if actionable:
            for s in actionable:
                lines.append(f"- **{s.label}** [{s.status}]: {s.detail}")
                if s.action:
                    lines.append(f"  - azione: {s.action}")
        else:
            lines.append(f"*{total} candidates, tutti ok*")
        lines.append(
            f"  *(as of {di.generated_at} — "
            + ", ".join(f"{v} {k}" for k, v in sorted(by_status.items()) if v)
            + ")*"
        )
        lines.append("")
        return lines

    def _render_dataset_catalog_section(
        self, catalog: DICleanCatalog | None
    ) -> list[str]:
        lines = []
        lines.append("## Dataset Catalog")
        lines.append("")
        if catalog is None:
            err = self.github_collector.fetch_errors.get(
                "dataset-incubator:clean_catalog"
            ) or self.github_collector.fetch_errors.get(
                "dataset-incubator:registry/clean_catalog.json"
            )
            if err:
                lines.append(f"> *clean_catalog unavailable — {err}*")
            else:
                lines.append("> *clean_catalog unavailable*")
            lines.append("")
            return lines

        clean_ready = catalog.clean_ready
        public_count = sum(1 for d in clean_ready if d.visibility == "public")
        lines.append(
            f"*{len(clean_ready)} clean_ready dataset(s), "
            f"{public_count} public* (updated {catalog.updated_at})"
        )
        for dataset in clean_ready[:8]:
            period = self._format_period(dataset.period)
            location = dataset.location.get("path", "")
            line = f"- **{dataset.slug}** ({dataset.status}, {dataset.visibility}): "
            line += dataset.name
            if period:
                line += f" [{period}]"
            line += (
                f" - {dataset.metric_columns} metric, "
                f"{dataset.dimension_columns} dimension columns"
            )
            if location:
                line += f" - `{location}`"
            lines.append(line)
        if len(clean_ready) > 8:
            lines.append(f"- *...and {len(clean_ready) - 8} more clean_ready datasets*")
        lines.append("")
        return lines

    def _build_dataset_catalog_dict(self) -> dict[str, Any]:
        catalog = self._fetch_di_clean_catalog()
        if catalog is None:
            return {
                "available": False,
                "errors": {
                    k: v for k, v in self.github_collector.fetch_errors.items()
                    if "clean_catalog" in k
                },
            }
        return {
            "available": True,
            "schema_version": catalog.schema_version,
            "name": catalog.name,
            "updated_at": catalog.updated_at,
            "summary": {
                "total": len(catalog.datasets),
                "clean_ready": len(catalog.clean_ready),
                "public": sum(1 for d in catalog.clean_ready if d.visibility == "public"),
            },
            "datasets": [
                {
                    "slug": d.slug,
                    "name": d.name,
                    "status": d.status,
                    "visibility": d.visibility,
                    "period": d.period,
                    "location": d.location,
                    "metric_columns": d.metric_columns,
                    "dimension_columns": d.dimension_columns,
                    "column_count": d.column_count,
                }
                for d in catalog.datasets
            ],
        }

    @staticmethod
    def _format_period(period: dict[str, Any]) -> str:
        start = period.get("start")
        end = period.get("end")
        if start is None and end is None:
            return ""
        if start == end:
            return str(start)
        return f"{start or '?'}-{end or '?'}"

    def _build_pipeline_state_dict(self) -> dict[str, Any]:
        di = self._fetch_di_pipeline_signals()
        if di is None:
            return {
                "available": False,
                "errors": {
                    k: v for k, v in self.github_collector.fetch_errors.items()
                    if "dataset-incubator" in k
                },
            }
        return {
            "available": True,
            "generated_at": di.generated_at,
            "summary": di.summary,
            "actionable": [
                {"id": s.id, "status": s.status, "detail": s.detail, "action": s.action}
                for s in di.actionable
            ],
        }

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
            Dictionary with topic index
        """
        topics = {}
        for topic_name, topic in self.config.topics.items():
            topics[topic_name] = {
                "name": topic_name,
                "summary": topic.summary,
                "repos": topic.repos,
                "paths": topic.paths,
                "next": topic.next,
            }
        return {
            "generated_at": self.fixed_timestamp,
            "topics": topics,
        }
