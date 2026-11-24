"""Cross-repo registry fetch helpers.

Uses ``lab_connectors.registry`` models and client for parsing.
One fetcher per repo: fetches and parses the canonical ``registry.json``
(schema v1 e v2) che ogni repo del Lab pubblica in ``registry/``.

Con un workspace locale configurato il registry del repo locale vince (build
con repo in corso d'opera); in CI non c'è workspace → GitHub-only.
"""

from __future__ import annotations

import json
from pathlib import Path

from lab_connectors.registry import Registry

from ..github import GitHubCollector
from ..workspace import resolve_repo_path

_REGISTRY_PATH = "registry/registry.json"


class RegistryFetcher:
    """Fetch and parse registry.json for a list of repos (cached per repo).

    A repo without a ``registry.json`` is normal (not all Lab repos are
    migrated yet): returns ``None`` without polluting ``fetch_errors`` —
    only genuine failures (rate limit, timeouts, 5xx) are kept.
    """

    def __init__(self, collector: GitHubCollector, local_root: Path | str | None = None):
        """Initialize the fetcher.

        Args:
            collector: GitHub collector (sorgente remota).
            local_root: Root del workspace locale: se un repo ha un
                ``registry/registry.json`` lì, quello vince (build locale con
                repo in corso d'opera). In CI è None → GitHub-only.
        """
        self.collector = collector
        self.local_root = Path(local_root) if local_root else None
        self._cache: dict[str, Registry | None] = {}

    def fetch(self, repos: list[str]) -> dict[str, Registry | None]:
        """Fetch and parse registry.json for all given repos."""
        return {repo: self.fetch_repo(repo) for repo in repos}

    def _local_registry_path(self, repo: str) -> Path | None:
        """Path del registry locale del repo, se c'è (workspace mode)."""
        repo_dir = resolve_repo_path(self.local_root, repo)
        if repo_dir is None:
            return None
        path = repo_dir / _REGISTRY_PATH
        return path if path.is_file() else None

    def fetch_repo(self, repo: str) -> Registry | None:
        """Fetch and parse a single repo registry.json, or None if missing."""
        if repo in self._cache:
            return self._cache[repo]

        local_path = self._local_registry_path(repo)
        if local_path is not None:
            try:
                registry = Registry.from_dict(json.loads(local_path.read_text(encoding="utf-8")))
            except (ValueError, OSError) as exc:
                self.collector.fetch_errors[f"{repo}:registry"] = str(exc)
                registry = None
            self._cache[repo] = registry
            return registry

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
            data = json.loads(raw)
            registry = Registry.from_dict(data)
        except (ValueError, json.JSONDecodeError) as exc:
            self.collector.fetch_errors[f"{repo}:registry"] = str(exc)
            registry = None
        self._cache[repo] = registry
        return registry
