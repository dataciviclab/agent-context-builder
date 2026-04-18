"""Render output artifacts."""

from datetime import datetime
from typing import Any

from .config import Config
from .discussions import Discussion, DiscussionCollector
from .github import GitHubCollector, PR
from .git_local import GitLocalCollector, GitState
from .signals import (
    RepoSignals,
    SourceCatalogSummary,
    SourceObservatorySignals,
    parse_repo_signals,
    parse_source_observatory_signals,
    parse_source_catalog_summary,
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
        self._source_catalog_cache: SourceCatalogSummary | None | type[_UNSET] = _UNSET
        self._di_signals_cache: RepoSignals | None | type[_UNSET] = _UNSET

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
        if github_errors:
            lines.append(
                f"> **GitHub unavailable** — {len(github_errors)} fetch error(s);"
                " PR/issue counts may be incomplete"
            )
        if prs:
            for pr in prs[:10]:  # Limit to first 10
                lines.append(f"- [{pr.repo}#{pr.number}]({pr.url}): {pr.title}")
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

        # Source inventory is opt-in until source-observatory publishes a stable artifact.
        if self.config.source_catalog_summary_path:
            source_catalog = self._fetch_source_catalog_summary()
            lines += self._render_source_inventory_section(source_catalog)

        # Source health (only issues — skip stable sources)
        so = self._fetch_source_observatory_signals()
        lines += self._render_source_health_section(so)

        # Pipeline state (only warn/error candidates)
        di = self._fetch_di_pipeline_signals()
        lines += self._render_pipeline_state_section(di)

        return "\n".join(lines)

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

    def _fetch_source_catalog_summary(self) -> SourceCatalogSummary | None:
        if self._source_catalog_cache is not _UNSET:
            return self._source_catalog_cache  # type: ignore[return-value]

        path = self.config.source_catalog_summary_path
        if not path:
            self._source_catalog_cache = None
            return None

        raw = self.github_collector.get_raw_file("source-observatory", path)
        if raw is None:
            self._source_catalog_cache = None
            return None
        try:
            result = parse_source_catalog_summary(raw)
        except ValueError as exc:
            self.github_collector.fetch_errors[
                "source-observatory:source_catalog_summary"
            ] = (
                f"{path}: {exc}"
            )
            result = None
        self._source_catalog_cache = result
        return result

    def _render_source_inventory_section(
        self, source_catalog: SourceCatalogSummary | None
    ) -> list[str]:
        lines = []
        lines.append("## Source Inventory")
        lines.append("")
        if source_catalog is None:
            err = self.github_collector.fetch_errors.get(
                "source-observatory:source_catalog_summary"
            )
            if err:
                lines.append(f"> *source catalog summary unavailable — {err}*")
            else:
                lines.append("> *source catalog summary unavailable*")
            lines.append("")
            return lines

        source_count = len(source_catalog.sources)
        candidate_count = len(source_catalog.intake_candidates)
        if source_count == 0 and candidate_count == 0:
            lines.append(f"*No source inventory entries* (as of {source_catalog.captured_at})")
            lines.append("")
            return lines

        for src in source_catalog.sources[:5]:
            parts = [f"- **{src.source_id}**"]
            if src.protocol:
                parts.append(f"[{src.protocol}]")
            if src.items is not None:
                item_text = f"{src.items} items"
                if src.titled is not None:
                    item_text += f", {src.titled} titled"
                parts.append(f": {item_text}")
            elif src.titled is not None:
                parts.append(f": {src.titled} titled")
            if src.inventory_method:
                parts.append(f"(`{src.inventory_method}`)")
            if src.status:
                parts.append(f"status: {src.status}")
            if src.api_base_url:
                parts.append(f"<{src.api_base_url}>")
            lines.append(" ".join(parts))

        if source_count > 5:
            lines.append(f"- *…and {source_count - 5} more sources*")

        if candidate_count:
            lines.append(f"  *{candidate_count} intake candidate(s); top entries:*")
            for candidate in source_catalog.intake_candidates[:3]:
                span = ""
                if candidate.year_min is not None or candidate.year_max is not None:
                    span = f" ({candidate.year_min or '?'}-{candidate.year_max or '?'})"
                score = candidate.intake_score if candidate.intake_score is not None else "n/d"
                lines.append(
                    f"  - **{candidate.source_id}**: {candidate.title}"
                    f" [{score}]{span}"
                )

        lines.append(f"  *(captured {source_catalog.captured_at})*")
        lines.append("")
        return lines

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
            "source_health": self._build_source_health_dict(),
            "pipeline_state": self._build_pipeline_state_dict(),
        }
        if self.config.source_catalog_summary_path:
            triage["source_inventory"] = self._build_source_inventory_dict()
        return triage

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

    def _build_source_inventory_dict(self) -> dict[str, Any]:
        source_catalog = self._fetch_source_catalog_summary()
        if source_catalog is None:
            return {
                "available": False,
                "errors": {
                    k: v for k, v in self.github_collector.fetch_errors.items()
                    if "source_catalog_summary" in k
                },
            }
        return {
            "available": True,
            "captured_at": source_catalog.captured_at,
            "sources": [
                {
                    "source_id": s.source_id,
                    "protocol": s.protocol,
                    "items": s.items,
                    "titled": s.titled,
                    "inventory_method": s.inventory_method,
                    "api_base_url": s.api_base_url,
                    "status": s.status,
                }
                for s in source_catalog.sources
            ],
            "intake_candidates": [
                {
                    "source_id": c.source_id,
                    "item_name": c.item_name,
                    "title": c.title,
                    "granularity": c.granularity,
                    "year_min": c.year_min,
                    "year_max": c.year_max,
                    "intake_score": c.intake_score,
                }
                for c in source_catalog.intake_candidates[:10]
            ],
            "summary": source_catalog.summary,
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
        result = {
            "generated_at": self.fixed_timestamp,
            "topics": topics,
        }
        if self.config.source_catalog_summary_path:
            result["source_inventory"] = self._build_source_inventory_dict()
        return result
