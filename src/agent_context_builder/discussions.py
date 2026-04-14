"""GitHub Discussions collector via GraphQL API."""

from dataclasses import dataclass
from typing import Optional

import requests

_GRAPHQL_URL = "https://api.github.com/graphql"

_QUERY = """
query($owner: String!, $repo: String!, $first: Int!) {
  repository(owner: $owner, name: $repo) {
    discussions(first: $first, states: [OPEN], orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        number
        title
        url
        category { name }
        author { login }
        updatedAt
      }
    }
  }
}
"""


@dataclass
class Discussion:
    """Open discussion summary."""

    number: int
    title: str
    repo: str
    url: str
    category: str
    author: str
    updated_at: str


class DiscussionCollector:
    """Collect open discussions from GitHub via GraphQL."""

    def __init__(self, org: str, token: Optional[str] = None):
        """Initialize discussion collector.

        Args:
            org: GitHub organization
            token: GitHub API token. GraphQL requires authentication.
        """
        self.org = org
        self.token = token
        # Maps "<repo>:discussions" to error message — populated during collection
        self.fetch_errors: dict[str, str] = {}

    def get_discussions(self, repos: list[str], first: int = 20) -> list[Discussion]:
        """Get open discussions across repos.

        Args:
            repos: List of repo names
            first: Max discussions per repo (default 20)

        Returns:
            List of Discussion objects. Repos that failed are in self.fetch_errors.
        """
        results = []
        for repo in repos:
            try:
                results.extend(self._get_repo_discussions(repo, first))
            except Exception as e:
                self.fetch_errors[f"{repo}:discussions"] = str(e)
        return results

    def _get_repo_discussions(self, repo: str, first: int) -> list[Discussion]:
        """Fetch open discussions for a single repo."""
        if not self.token:
            raise ValueError("GitHub token required for GraphQL Discussions API")

        response = requests.post(
            _GRAPHQL_URL,
            json={"query": _QUERY, "variables": {"owner": self.org, "repo": repo, "first": first}},
            headers={"Authorization": f"bearer {self.token}"},
            timeout=10,
        )
        response.raise_for_status()

        payload = response.json()
        if "errors" in payload:
            raise ValueError(f"GraphQL errors: {payload['errors']}")

        nodes = (
            payload.get("data", {})
            .get("repository", {})
            .get("discussions", {})
            .get("nodes", [])
        )
        return [
            Discussion(
                number=node["number"],
                title=node["title"],
                repo=repo,
                url=node["url"],
                category=node["category"]["name"] if node.get("category") else "",
                author=node["author"]["login"] if node.get("author") else "",
                updated_at=node.get("updatedAt", ""),
            )
            for node in nodes
        ]
