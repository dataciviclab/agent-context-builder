"""Render output artifacts."""

from datetime import datetime
from typing import Any

from .config import Config
from .discussions import DiscussionCollector
from .git_local import GitLocalCollector
from .github import GitHubCollector
from .signals import (
    DICleanCatalog,
    PortalScoutSummary,
    RadarSummary,
    RepoSignals,
    SourceObservatorySignals,
)
from .sources.di import DatasetIncubatorFetcher
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
        """Initialize renderer."""
        self.config = config
        self.github_collector = github_collector
        self.git_collector = git_collector
        self.discussion_collector = discussion_collector
        self.fixed_timestamp = fixed_timestamp or datetime.now().isoformat()
        self._so_fetcher = SourceObservatoryFetcher(github_collector)
        self._di_fetcher = DatasetIncubatorFetcher(github_collector)

    def render_session_bootstrap(self) -> str:
        """Render session_bootstrap.md."""
        lines: list[str] = []
        lines.append("# Session Bootstrap")
        lines.append("")
        lines.append(f"**Generated**: {self.fixed_timestamp}")
        if self.config.workspace_root:
            lines.append(f"**Workspace**: {self.config.workspace_root}")
        lines.append("")

        lines.append("## Repos")
        lines.append("")
        repos_info = self.github_collector.get_repos_info(self.config.repos)
        for repo in self.config.repos:
            info = repos_info.get(repo)
            if info and info.description:
                lines.append(f"- **{repo}**: {info.description}")
            else:
                lines.append(f"- {repo}")
        lines.append("")

        lines.append("## Open PRs")
        lines.append("")
        prs = self.github_collector.get_prs(self.config.repos)
        github_errors = self.github_collector.fetch_errors
        collector_warn = self.github_collector.collector_warning()
        if collector_warn:
            lines.append(f"> **Warning**: {collector_warn}")
        if prs:
            dependabot = {"dependabot[bot]", "dependabot"}
            feature_prs = [pr for pr in prs if pr.author not in dependabot]
            dep_prs = [pr for pr in prs if pr.author in dependabot]
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

        if self.config.topics:
            lines.append("## Topics")
            lines.append("")
            for topic_name in self.config.topics:
                lines.append(f"- {topic_name}")
            lines.append("")

        radar = self._so_fetcher.fetch_radar_summary()
        lines += self._render_radar_section(radar)

        so = self._so_fetcher.fetch_catalog_signals()
        lines += self._render_source_health_section(so)

        di = self._di_fetcher.fetch_pipeline_signals()
        lines += self._render_pipeline_state_section(di)

        catalog = self._di_fetcher.fetch_clean_catalog()
        lines += self._render_dataset_catalog_section(catalog)

        scout = self._so_fetcher.fetch_portal_scout()
        lines += self._render_portal_scout_section(scout)

        return "\n".join(lines)

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

    def _render_portal_scout_section(self, scout: PortalScoutSummary | None) -> list[str]:
        lines = ["## Portal Scout", ""]
        if scout is None:
            lines.append("> *discovered_portals_summary unavailable*")
            lines.append("")
            return lines
        lines.append(
            f"Portali rilevati: {scout.total_portals} — "
            f"nuovi candidati: {scout.new_candidates} — "
            f"strutturati confermati: {scout.new_confirmed_protocol}"
        )
        if scout.new_structured:
            lines.append("")
            lines.append("**Nuovi candidati strutturati:**")
            for c in scout.new_structured:
                lines.append(f"- `{c.domain}` — {c.protocol.upper()}")
        lines.append("")
        return lines

    def _render_source_health_section(self, so: SourceObservatorySignals | None) -> list[str]:
        lines = ["## Source Health", ""]
        if so is None:
            err = self.github_collector.fetch_errors.get(
                "source-observatory:data/catalog/catalog_signals.json"
            ) or self.github_collector.fetch_errors.get("source-observatory:catalog_signals")
            if err:
                lines.append(f"> *catalog_signals unavailable — {err}*")
            else:
                lines.append("> *catalog_signals unavailable*")
            lines.append("")
            return lines

        issues = so.regressions + so.alerts
        if issues:
            for s in issues:
                lines.append(f"- **{s.source}** ({s.protocol}): {s.result}")
                if s.suggested_action and s.suggested_action != "nessuna":
                    lines.append(f"  - azione: {s.suggested_action}")
        else:
            lines.append(f"*All {so.sources_checked} sources stable* (as of {so.captured_at})")
        lines.append(f"  *(captured {so.captured_at}, {so.sources_checked} sources checked)*")
        lines.append("")
        return lines

    def render_workspace_triage(self) -> dict[str, Any]:
        """Render workspace_triage.json."""
        return build_workspace_triage(
            self.config,
            self.github_collector,
            self.git_collector,
            self.discussion_collector,
            self.fixed_timestamp,
            so_fetcher=self._so_fetcher,
            di_fetcher=self._di_fetcher,
        )

    def _render_pipeline_state_section(self, di: RepoSignals | None) -> list[str]:
        lines = ["## Pipeline State", ""]
        if di is None:
            err = self.github_collector.fetch_errors.get(
                "dataset-incubator:registry/pipeline_signals.json"
            ) or self.github_collector.fetch_errors.get("dataset-incubator:pipeline_signals")
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

    def _render_dataset_catalog_section(self, catalog: DICleanCatalog | None) -> list[str]:
        lines = ["## Dataset Catalog", ""]
        if catalog is None:
            err = self.github_collector.fetch_errors.get("dataset-incubator:clean_catalog")
            err = err or self.github_collector.fetch_errors.get(
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
            f"*{len(clean_ready)} clean_ready dataset(s), {public_count} public* "
            f"(updated {catalog.updated_at})"
        )
        for dataset in clean_ready[:8]:
            period = self._format_period(dataset.period)
            line = f"- **{dataset.slug}** ({dataset.visibility}): {dataset.name}"
            if period:
                line += f" [{period}]"
            lines.append(line)
        if len(clean_ready) > 8:
            lines.append(f"- *...and {len(clean_ready) - 8} more clean_ready datasets*")
        lines.append("")
        return lines

    @staticmethod
    def _format_period(period: dict[str, Any]) -> str:
        start = period.get("start")
        end = period.get("end")
        if start is None and end is None:
            return ""
        if start == end:
            return str(start)
        return f"{start or '?'}-{end or '?'}"

    def render_topic_index(self) -> dict[str, Any]:
        """Render topic_index.json."""
        repos_info = self.github_collector.get_repos_info(self.config.repos)
        repos_section = {
            name: {"description": info.description, "url": info.url}
            for name, info in repos_info.items()
        }

        catalog = self._di_fetcher.fetch_clean_catalog()
        datasets_by_source: dict[str, list[dict[str, Any]]] = {}
        if catalog:
            for ds in catalog.clean_ready:
                source = ds.source or "unknown"
                datasets_by_source.setdefault(source, []).append(
                    {
                        "slug": ds.slug,
                        "name": ds.name,
                        "period": ds.period,
                        "visibility": ds.visibility,
                    }
                )

        operational_topics = {}
        for topic_name, topic in self.config.topics.items():
            operational_topics[topic_name] = {
                "name": topic_name,
                "summary": topic.summary,
                "repos": topic.repos,
                "paths": topic.paths,
                "next": topic.next,
            }

        return {
            "schema_version": 2,
            "generated_at": self.fixed_timestamp,
            "repos": repos_section,
            "datasets_by_source": datasets_by_source,
            "operational_topics": operational_topics,
        }
