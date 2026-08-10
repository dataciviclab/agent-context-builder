"""Cross-repo registry fetch helpers.

Consumes the canonical ``registry.json`` artifact (schema v1) that each Lab
repo publishes under ``registry/``. ACB reduces each registry to a compact
per-repo summary (section counts + stage counts + freshness) for orientation;
the detailed entries stay in the upstream registry, served by the toolkit MCP
(``registry_show``/``find``/``overview``).
"""

from __future__ import annotations

from ..github import GitHubCollector
from ..signals import RepoRegistrySummary, parse_registry_summary

_REGISTRY_PATH = "registry/registry.json"


class RegistryFetcher:
    """Fetch registry.json summaries for a list of repos.

    A repo without a ``registry.json`` is normal (not all Lab repos are
    migrated yet): reported as ``available=False, reason=registry_not_found``
    without polluting ``fetch_errors`` — only genuine failures (rate limit,
    timeouts, 5xx) are kept.
    """

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._cache: dict[str, RepoRegistrySummary | object] = {}

    def fetch(self, repos: list[str]) -> dict[str, RepoRegistrySummary]:
        """Fetch registry summaries for all given repos (cached per repo)."""
        return {repo: self.fetch_repo(repo) for repo in repos}

    def fetch_repo(self, repo: str) -> RepoRegistrySummary:
        """Fetch and summarize a single repo registry.json."""
        if repo in self._cache:
            cached = self._cache[repo]
            return cached if isinstance(cached, RepoRegistrySummary) else _unset_summary(repo)

        raw = self.collector.get_raw_file(repo, _REGISTRY_PATH)
        if raw is None:
            # A missing registry.json is expected for non-migrated repos:
            # drop the collector's recorded 404 so it doesn't surface as a
            # triage warning. Real errors (rate limit, timeouts) stay.
            err_key = f"{repo}:{_REGISTRY_PATH}"
            err = self.collector.fetch_errors.get(err_key, "")
            if "HTTP 404" in err:
                del self.collector.fetch_errors[err_key]
            summary = parse_registry_summary(repo, None)
            self._cache[repo] = summary
            return summary

        summary = parse_registry_summary(repo, raw)
        self._cache[repo] = summary
        return summary


def _unset_summary(repo: str) -> RepoRegistrySummary:
    """Fallback summary for a previously failed cache entry (never hit)."""
    return RepoRegistrySummary(repo=repo, available=False, reason="fetch_failed")
