"""GitHub API interactions for context collection."""

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
    author: str = ""


@dataclass
class Issue:
    """Issue summary."""

    number: int
    title: str
    repo: str
    url: str
    state: str = "open"


@dataclass
class RepoInfo:
    """Repository metadata."""

    name: str
    description: str
    url: str


class GitHubCollector:
    """Collect context from GitHub API."""

    def __init__(self, org: str, token: Optional[str] = None):
        """Initialize GitHub collector.

        Args:
            org: GitHub organization
            token: GitHub API token (optional)
        """
        self.org = org
        self.token = token
        self.base_url = "https://api.github.com"
        # Populated by get_prs/get_issues — maps "<repo>:prs" or "<repo>:issues" to error message
        self.fetch_errors: dict[str, str] = {}

    def collector_warning(self) -> str | None:
        """Return a human-readable warning if fetch errors suggest rate-limit or auth degradation."""
        if not self.fetch_errors:
            return None
        msgs = " ".join(self.fetch_errors.values()).lower()
        if "403" in msgs or "rate limit" in msgs or "secondary rate" in msgs:
            return (
                "GitHub rate-limit or auth error "
                f"({len(self.fetch_errors)} collector(s) affected) - data may be incomplete"
            )
        return (
            f"GitHub fetch error ({len(self.fetch_errors)} collector(s) affected) "
            "- data may be incomplete"
        )

    def get_prs(self, repos: list[str], state: str = "open") -> list[PR]:
        """Get open PRs across repos.

        Args:
            repos: List of repo names
            state: PR state (open, closed, all)

        Returns:
            List of PR objects. Repos that failed are recorded in self.fetch_errors.
        """
        prs = []
        for repo in repos:
            try:
                prs.extend(self._get_repo_prs(repo, state))
            except Exception as e:
                self.fetch_errors[f"{repo}:prs"] = str(e)
        return prs

    def get_issues(self, repos: list[str], state: str = "open") -> list[Issue]:
        """Get issues across repos.

        Args:
            repos: List of repo names
            state: Issue state (open, closed, all)

        Returns:
            List of Issue objects. Repos that failed are recorded in self.fetch_errors.
        """
        issues = []
        for repo in repos:
            try:
                issues.extend(self._get_repo_issues(repo, state))
            except Exception as e:
                self.fetch_errors[f"{repo}:issues"] = str(e)
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
                    author=item.get("user", {}).get("login", ""),
                )
            )
        return prs

    def get_raw_file(self, repo: str, path: str, ref: str = "main") -> str | None:
        """Fetch raw file content from GitHub.

        Uses raw.githubusercontent.com — works without token on public repos.
        On failure, records the error in self.fetch_errors and returns None.

        Args:
            repo: Repository name (under self.org)
            path: File path within the repo
            ref: Branch or tag (default: main)

        Returns:
            Raw file content as string, or None on failure.
        """
        url = f"https://raw.githubusercontent.com/{self.org}/{repo}/{ref}/{path}"
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            self.fetch_errors[f"{repo}:{path}"] = str(exc)
            return None

    def get_repos_info(self, repos: list[str]) -> dict[str, RepoInfo]:
        """Get metadata (description, url) for each repo.

        Returns a dict keyed by repo name. Missing/failed repos are skipped silently.
        """
        result: dict[str, RepoInfo] = {}
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        for repo in repos:
            try:
                url = f"{self.base_url}/repos/{self.org}/{repo}"
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                result[repo] = RepoInfo(
                    name=repo,
                    description=data.get("description") or "",
                    url=data.get("html_url", ""),
                )
            except Exception as exc:
                self.fetch_errors[f"{repo}:info"] = str(exc)
        return result

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
