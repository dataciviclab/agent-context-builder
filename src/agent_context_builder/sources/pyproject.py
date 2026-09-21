"""Cross-repo pyproject.toml fetch helpers.

Fetches and parses ``pyproject.toml`` from each Lab repo via the GitHub API.
Used to enrich ``topic_index.json`` with project metadata (Python version,
build system, dependencies, etc.).
"""

from __future__ import annotations

import tomllib
from typing import Any

from ..github import GitHubCollector
from ..signals import RepoMetadata

_PYPROJECT_PATH = "pyproject.toml"


class PyprojectFetcher:
    """Fetch and parse pyproject.toml for a list of repos (cached per repo).

    A repo without a ``pyproject.toml`` returns ``None`` — the 404 is
    silently dropped from ``fetch_errors`` (same pattern as RegistryFetcher).
    """

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._cache: dict[str, RepoMetadata | None] = {}

    def fetch(self, repos: list[str]) -> dict[str, RepoMetadata | None]:
        """Fetch and parse pyproject.toml for all given repos."""
        return {repo: self.fetch_repo(repo) for repo in repos}

    def fetch_repo(self, repo: str) -> RepoMetadata | None:
        """Fetch and parse a single repo pyproject.toml, or None if missing."""
        if repo in self._cache:
            return self._cache[repo]

        raw = self.collector.get_raw_file(repo, _PYPROJECT_PATH)
        if raw is None:
            err_key = f"{repo}:{_PYPROJECT_PATH}"
            err = self.collector.fetch_errors.get(err_key, "")
            if "HTTP 404" in err:
                del self.collector.fetch_errors[err_key]
            self._cache[repo] = None
            return None

        try:
            data = tomllib.loads(raw)
        except Exception as exc:
            self.collector.fetch_errors[f"{repo}:pyproject"] = str(exc)
            self._cache[repo] = None
            return None

        meta = _parse_pyproject(repo, data)
        self._cache[repo] = meta
        return meta


def _parse_pyproject(repo: str, data: dict[str, Any]) -> RepoMetadata:
    """Extract structured metadata from parsed pyproject.toml dict."""
    project = data.get("project", {})
    build_system = data.get("build-system", {})
    setuptools = data.get("tool", {}).get("setuptools", {})

    # Dependencies
    deps = project.get("dependencies", [])
    optional_deps = project.get("optional-dependencies", {})

    # Packages — None means auto-discover, [] means no packages (data repo)
    packages: list[str] | None = None
    if "packages" in setuptools:
        pkgs = setuptools["packages"]
        packages = pkgs if pkgs else []

    # Source ID from toolkit extends
    source_id = data.get("tool", {}).get("toolkit", {}).get("extends", {}).get("source_id", "")

    # License — handle both string and dict forms
    lic = project.get("license", "")
    if isinstance(lic, dict):
        lic = lic.get("text", lic.get("file", ""))

    return RepoMetadata(
        repo=repo,
        name=project.get("name", ""),
        version=project.get("version", ""),
        description=project.get("description", ""),
        requires_python=project.get("requires-python", ""),
        build_backend=build_system.get("build-backend", ""),
        license=lic,
        dependencies=deps,
        optional_dependencies={k: list(v) for k, v in optional_deps.items()},
        packages=packages,
        source_id=source_id,
    )
