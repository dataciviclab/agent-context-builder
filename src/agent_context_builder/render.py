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
    ):
        """Initialize renderer.

        Args:
            config: Configuration object
            github_collector: GitHub collector instance
            git_collector: Git local collector instance
        """
        self.config = config
        self.github_collector = github_collector
        self.git_collector = git_collector

    def render_session_bootstrap(self) -> str:
        """Render session_bootstrap.md.

        Returns:
            Markdown content (target: 80-120 lines)
        """
        lines = []
        lines.append("# Session Bootstrap")
        lines.append("")
        lines.append(f"**Generated**: {datetime.now().isoformat()}")
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

        # Local git state
        lines.append("## Local State")
        lines.append("")
        git_state = self.git_collector.get_state()
        if git_state:
            lines.append(f"**Branch**: {git_state.current_branch}")
            lines.append(f"**Dirty**: {git_state.dirty}")
            if git_state.branches_ahead:
                lines.append(f"**Ahead**: {', '.join(git_state.branches_ahead)}")
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
        git_state = self.git_collector.get_state()

        triage = {
            "generated_at": datetime.now().isoformat(),
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
                "dirty": git_state.dirty if git_state else None,
                "current_branch": git_state.current_branch if git_state else None,
                "branches_ahead": git_state.branches_ahead if git_state else [],
                "untracked_files": git_state.untracked_files if git_state else 0,
            }
            if git_state
            else None,
            "warnings": self._collect_warnings(prs, git_state),
        }
        return triage

    def _collect_warnings(self, prs: list[PR], git_state: GitState | None) -> list[str]:
        """Collect warnings for triage.

        Args:
            prs: List of PRs
            git_state: Git state or None

        Returns:
            List of warning messages
        """
        warnings = []
        if len(prs) > 5:
            warnings.append(f"Many open PRs: {len(prs)}")
        if git_state and git_state.dirty:
            warnings.append("Workspace is dirty")
        if git_state and git_state.branches_ahead:
            warnings.append(
                f"Branches ahead of remote: {', '.join(git_state.branches_ahead)}"
            )
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
                "repos": topic.repos,
                "paths": topic.paths,
            }
        return {
            "generated_at": datetime.now().isoformat(),
            "topics": topics,
        }
