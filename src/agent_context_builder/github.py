"""GitHub API interactions for context collection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from lab_connectors.http import HttpClient


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

    def __init__(self, org: str, token: Optional[str] = None,
                 http_client: Optional[HttpClient] = None):
        """Initialize GitHub collector.

        Args:
            org: GitHub organization
            token: GitHub API token (optional)
            http_client: Optional pre-configured HttpClient (for testing).
        """
        self.org = org
        self.token = token
        self.base_url = "https://api.github.com"
        self._http = http_client or HttpClient(timeout=10)
        # Populated by get_prs/get_issues — maps "<repo>:prs" or "<repo>:issues" to error message
        self.fetch_errors: dict[str, str] = {}

    def collector_warning(self) -> str | None:
        """Return a warning if fetch errors suggest rate-limit or auth degradation."""
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

    def _raise_on_bad_status(self, result, url_desc: str) -> None:
        """Raise RuntimeError if result is error or response status >= 400."""
        if not result.is_ok:
            raise RuntimeError(f"{url_desc}: {result.err}")
        status = result.response.status_code  # type: ignore[union-attr]
        if status >= 400:
            raise RuntimeError(f"{url_desc}: HTTP {status}")

    def _headers(self) -> dict[str, str]:
        """Build Authorization headers if token is set."""
        if self.token:
            return {"Authorization": f"token {self.token}"}
        return {}

    def _get_repo_prs(self, repo: str, state: str = "open") -> list[PR]:
        """Get PRs for a specific repo."""
        url = f"{self.base_url}/repos/{self.org}/{repo}/pulls"
        params = {"state": state, "per_page": 50}
        result = self._http.get(url, params=params, headers=self._headers())
        self._raise_on_bad_status(result, url)

        prs = []
        for item in result.response.json():  # type: ignore[union-attr]
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
        result = self._http.get(url, headers=self._headers())
        try:
            self._raise_on_bad_status(result, url)
            return result.response.text  # type: ignore[union-attr]
        except Exception as exc:
            self.fetch_errors[f"{repo}:{path}"] = str(exc)
            return None

    def get_repos_info(self, repos: list[str]) -> dict[str, RepoInfo]:
        """Get metadata (description, url) for each repo.

        Returns a dict keyed by repo name. Missing/failed repos are skipped silently.
        """
        result_map: dict[str, RepoInfo] = {}
        for repo in repos:
            try:
                url = f"{self.base_url}/repos/{self.org}/{repo}"
                result = self._http.get(url, headers=self._headers())
                self._raise_on_bad_status(result, url)
                data = result.response.json()  # type: ignore[union-attr]
                result_map[repo] = RepoInfo(
                    name=repo,
                    description=data.get("description") or "",
                    url=data.get("html_url", ""),
                )
            except Exception as exc:
                self.fetch_errors[f"{repo}:info"] = str(exc)
        return result_map

    def get_latest_workflow_run(
        self,
        repo: str,
        event: str = "push",
        status: str = "completed",
        workflow_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch the latest workflow run for a repo.

        If workflow_id is provided, uses the workflow-specific endpoint
        (e.g. ``deploy.yml``) to avoid ambiguity when multiple workflows
        trigger on the same event.

        Args:
            repo: Repository name (under self.org)
            event: Event type filter (e.g. push, workflow_dispatch)
            status: Status filter (e.g. completed, success)
            workflow_id: Workflow filename (e.g. ``deploy.yml``) for
                         precise targeting. Optional.

        Returns:
            Dict with run_id, name, status, conclusion, started_at, completed_at, html_url,
            or None if no runs found or on error.
        """
        if workflow_id:
            url = (
                f"{self.base_url}/repos/{self.org}/{repo}"
                f"/actions/workflows/{workflow_id}/runs"
            )
        else:
            url = f"{self.base_url}/repos/{self.org}/{repo}/actions/runs"
        params = {
            "event": event,
            "status": status,
            "per_page": 1,
        }
        try:
            result = self._http.get(url, params=params, headers=self._headers())
            self._raise_on_bad_status(result, url)
            data = result.response.json()  # type: ignore[union-attr]
            runs = data.get("workflow_runs", [])
            if not runs:
                return None
            run = runs[0]
            return {
                "run_id": run.get("id"),
                "name": run.get("name", ""),
                "status": run.get("status", ""),
                "conclusion": run.get("conclusion"),
                "started_at": run.get("run_started_at", ""),
                "completed_at": run.get("updated_at", ""),
                "html_url": run.get("html_url", ""),
            }
        except Exception as exc:
            self.fetch_errors[f"{repo}:workflow_runs"] = str(exc)
            return None

    def _get_repo_issues(self, repo: str, state: str = "open") -> list[Issue]:
        """Get issues for a specific repo (excluding pull requests).

        GitHub's /issues endpoint returns both issues and PRs.
        Filter out PRs by checking for pull_request field.
        """
        url = f"{self.base_url}/repos/{self.org}/{repo}/issues"
        params = {"state": state, "per_page": 50}
        result = self._http.get(url, params=params, headers=self._headers())
        self._raise_on_bad_status(result, url)

        issues = []
        for item in result.response.json():  # type: ignore[union-attr]
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
