"""Data-explorer fetch and parse helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..github import GitHubCollector
from ..signals import ExplorerTheme, parse_explorer_themes


@dataclass
class DataExplorerData:
    """Cached data-explorer artifact bundle."""

    themes: list[ExplorerTheme] | None
    last_deploy: dict[str, Any] | None


class DataExplorerFetcher:
    """Fetch data-explorer artifacts from GitHub raw URLs + API.

    Consumes:
      - catalog/themes.json (editorial theme assignments)
      - GitHub Actions API (deploy status, operativo)
    """

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._themes_cache: list[ExplorerTheme] | None | object = _UNSET
        self._deploy_cache: dict[str, Any] | None | object = _UNSET

    def fetch(self) -> DataExplorerData:
        """Fetch all data-explorer artifacts."""
        return DataExplorerData(
            themes=self.fetch_themes(),
            last_deploy=self.fetch_deploy_status(),
        )

    def fetch_themes(self) -> list[ExplorerTheme] | None:
        """Fetch and parse catalog/themes.json from data-explorer.

        Returns None if the artifact is unavailable or malformed.
        """
        if self._themes_cache is not _UNSET:
            return self._themes_cache  # type: ignore[return-value]
        raw = self.collector.get_raw_file("data-explorer", "catalog/themes.json")
        if raw is None:
            self._themes_cache = None
            return None
        try:
            result = parse_explorer_themes(raw)
        except ValueError as exc:
            self.collector.fetch_errors["data-explorer:themes"] = str(exc)
            result = None
        self._themes_cache = result
        return result

    def fetch_deploy_status(self) -> dict[str, Any] | None:
        """Fetch latest deploy workflow run for data-explorer.

        Returns a dict with run_id, name, status, conclusion, started_at,
        completed_at, html_url — or None if unavailable.
        """
        if self._deploy_cache is not _UNSET:
            return self._deploy_cache  # type: ignore[return-value]
        result = self.collector.get_latest_workflow_run("data-explorer")
        self._deploy_cache = result
        return result


class _Unset:
    pass


_UNSET = _Unset()
