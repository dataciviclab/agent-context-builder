"""Render output artifacts."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Config
from .github import GitHubCollector, Issue, PR
from .git_local import GitLocalCollector, GitState


class Renderer:
    """Render context artifacts."""

    def __init__(
        self,
        config: Config,
        github_collector: GitHubCollector,
        git_collector: GitLocalCollector,
        fixed_timestamp: str | None = None,
    ):
        """Initialize renderer.

        Args:
            config: Configuration object
            github_collector: GitHub collector instance
            git_collector: Git local collector instance
            fixed_timestamp: Fixed ISO timestamp for deterministic output (optional, for testing)
        """
        self.config = config
        self.github_collector = github_collector
        self.git_collector = git_collector
        self.fixed_timestamp = fixed_timestamp or datetime.now().isoformat()

    def render_session_bootstrap(self) -> str:
        """Render session_bootstrap.md.

        Returns:
            Markdown content (target: 80-120 lines)
        """
        lines = []
        lines.append("# Session Bootstrap")
        lines.append("")
        lines.append(f"**Generated**: {self.fixed_timestamp}")
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
        if prs:
            for pr in prs[:10]:  # Limit to first 10
                lines.append(f"- [{pr.repo}#{pr.number}]({pr.url}): {pr.title}")
        else:
            lines.append("*No open PRs*")
        lines.append("")

        # Local git state per repo
        lines.append("## Local State")
        lines.append("")
        repos_state = self.git_collector.get_repos_state(self.config.repos)
        has_local_state = False
        for repo, state in repos_state.items():
            if state:
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

        return "\n".join(lines)

    def render_workspace_triage(self) -> dict[str, Any]:
        """Render workspace_triage.json.

        Returns:
            Dictionary with triage data
        """
        prs = self.github_collector.get_prs(self.config.repos)
        issues = self.github_collector.get_issues(self.config.repos)
        repos_state = self.git_collector.get_repos_state(self.config.repos)

        triage = {
            "generated_at": self.fixed_timestamp,
            "workspace_root": str(self.config.workspace_root),
            "repos": self.config.repos,
            "open_prs": len(prs),
            "prs": [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "repo": pr.repo,
                    "url": pr.url,
                }
                for pr in prs
            ],
            "open_issues": len(issues),
            "issues": [
                {
                    "number": issue.number,
                    "title": issue.title,
                    "repo": issue.repo,
                    "url": issue.url,
                }
                for issue in issues
            ],
            "git_state": {
                repo: {
                    "dirty": state.dirty if state else None,
                    "current_branch": state.current_branch if state else None,
                    "branches_ahead": state.branches_ahead if state else [],
                    "untracked_files": state.untracked_files if state else 0,
                }
                for repo, state in repos_state.items()
            },
            "warnings": self._collect_warnings(prs, repos_state),
        }
        return triage

    def _collect_warnings(
        self, prs: list[PR], repos_state: dict[str, GitState | None]
    ) -> list[str]:
        """Collect warnings for triage.

        Args:
            prs: List of PRs
            repos_state: Dict mapping repo name to GitState or None

        Returns:
            List of warning messages
        """
        warnings = []
        if len(prs) > 5:
            warnings.append(f"Many open PRs: {len(prs)}")

        # Check for dirty or ahead repos
        for repo, state in repos_state.items():
            if state:
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
