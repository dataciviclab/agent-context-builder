"""Cross-repo registry fetch helpers.

One fetcher per repo: fetches and parses the canonical ``registry.json``
(schema v1) that each Lab repo publishes under ``registry/``. Consumers
derive what they need from the parsed ``DIRegistry``: per-repo summary
(counts), signals (pipeline state), datasets (topic_index, explorer gap).
"""

from __future__ import annotations

from ..github import GitHubCollector
from ..signals import DIRegistry, parse_di_registry

_REGISTRY_PATH = "registry/registry.json"


class RegistryFetcher:
    """Fetch and parse registry.json for a list of repos (cached per repo).

    A repo without a ``registry.json`` is normal (not all Lab repos are
    migrated yet): returns ``None`` without polluting ``fetch_errors`` —
    only genuine failures (rate limit, timeouts, 5xx) are kept.
    """

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._cache: dict[str, DIRegistry | None] = {}

    def fetch(self, repos: list[str]) -> dict[str, DIRegistry | None]:
        """Fetch and parse registry.json for all given repos."""
        return {repo: self.fetch_repo(repo) for repo in repos}

    def fetch_repo(self, repo: str) -> DIRegistry | None:
        """Fetch and parse a single repo registry.json, or None if missing."""
        if repo in self._cache:
            return self._cache[repo]

        raw = self.collector.get_raw_file(repo, _REGISTRY_PATH)
        if raw is None:
            # A missing registry.json is expected for non-migrated repos:
            # drop the collector's recorded 404 so it doesn't surface as a
            # triage warning. Real errors (rate limit, timeouts) stay.
            err_key = f"{repo}:{_REGISTRY_PATH}"
            err = self.collector.fetch_errors.get(err_key, "")
            if "HTTP 404" in err:
                del self.collector.fetch_errors[err_key]
            self._cache[repo] = None
            return None

        try:
            registry = parse_di_registry(raw)
        except ValueError as exc:
            self.collector.fetch_errors[f"{repo}:registry"] = str(exc)
            registry = None
        self._cache[repo] = registry
        return registry
