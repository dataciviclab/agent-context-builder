"""GitHub API interactions for context collection."""

import subprocess
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class PR:
    """Pull request summary."""

    number: int
    title: str
    repo: str
    url: str
    state: str = "open"


@dataclass
class Issue:
    """Issue summary."""

    number: int
    title: str
    repo: str
    url: str
    state: str = "open"


class GitHubCollector:
    """Collect context from GitHub API."""

    def __init__(self, org: str, token: Optional[str] = None):
        """Initialize GitHub collector.

        Args:
            org: GitHub organization
            token: GitHub API token (optional, uses gh CLI fallback)
        """
        self.org = org
        self.token = token
        self.base_url = "https://api.github.com"

    def get_prs(self, repos: list[str], state: str = "open") -> list[PR]:
        """Get open PRs across repos.

        Args:
            repos: List of repo names
            state: PR state (open, closed, all)

        Returns:
            List of PR objects
        """
        prs = []
        for repo in repos:
            try:
                prs.extend(self._get_repo_prs(repo, state))
            except Exception as e:
                # Gracefully degrade on API errors
                print(f"Warning: Failed to fetch PRs for {repo}: {e}")
                continue
        return prs

    def get_issues(self, repos: list[str], state: str = "open") -> list[Issue]:
        """Get issues across repos.

        Args:
            repos: List of repo names
            state: Issue state (open, closed, all)

        Returns:
            List of Issue objects
        """
        issues = []
        for repo in repos:
            try:
                issues.extend(self._get_repo_issues(repo, state))
            except Exception as e:
                print(f"Warning: Failed to fetch issues for {repo}: {e}")
                continue
        return issues

    def _get_repo_prs(self, repo: str, state: str = "open") -> list[PR]:
        """Get PRs for a specific repo."""
        url = f"{self.base_url}/repos/{self.org}/{repo}/pulls"
        params = {"state": state, "per_page": 50}
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        prs = []
        for item in response.json():
            prs.append(
                PR(
                    number=item["number"],
                    title=item["title"],
                    repo=repo,
                    url=item["html_url"],
                    state=item["state"],
                )
            )
        return prs

    def _get_repo_issues(self, repo: str, state: str = "open") -> list[Issue]:
        """Get issues for a specific repo (excluding pull requests).

        GitHub's /issues endpoint returns both issues and PRs.
        Filter out PRs by checking for pull_request field.
        """
        url = f"{self.base_url}/repos/{self.org}/{repo}/issues"
        params = {"state": state, "per_page": 50}
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        issues = []
        for item in response.json():
            # Skip pull requests: they have a pull_request field
            if "pull_request" in item:
                continue
            issues.append(
                Issue(
                    number=item["number"],
                    title=item["title"],
                    repo=repo,
                    url=item["html_url"],
                    state=item["state"],
                )
            )
        return issues
