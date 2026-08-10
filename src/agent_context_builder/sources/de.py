"""Data-explorer fetch and parse helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..github import GitHubCollector
from ..signals import ExplorerCatalog, parse_explorer_catalog


@dataclass
class DataExplorerData:
    """Cached data-explorer artifact bundle."""

    catalog: ExplorerCatalog | None
    last_deploy: dict[str, Any] | None


class DataExplorerFetcher:
    """Fetch data-explorer artifacts from GitHub raw URLs + API.

    Consumes:
      - catalog/datasets.json + catalog/themes.json (committed editorial
        catalog: per-dataset theme resolution; replaces the old static
        themes.json.py loader)
      - GitHub Actions API (deploy status, operativo)
    """

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._catalog_cache: ExplorerCatalog | None | object = _UNSET
        self._deploy_cache: dict[str, Any] | None | object = _UNSET

    def fetch(self) -> DataExplorerData:
        """Fetch all data-explorer artifacts."""
        return DataExplorerData(
            catalog=self.fetch_explorer_catalog(),
            last_deploy=self.fetch_deploy_status(),
        )

    def fetch_explorer_catalog(self) -> ExplorerCatalog | None:
        """Fetch and parse the committed editorial catalog.

        ``catalog/datasets.json`` resolves each dataset to its theme (URL
        slug); ``catalog/themes.json`` carries theme names/order. Both are
        committed JSON artifacts — no source parsing.
        """
        if self._catalog_cache is not _UNSET:
            return self._catalog_cache  # type: ignore[return-value]
        raw_catalog = self.collector.get_raw_file("data-explorer", "catalog/datasets.json")
        raw_themes = self.collector.get_raw_file("data-explorer", "catalog/themes.json")
        if raw_catalog is None or raw_themes is None:
            self._catalog_cache = None
            return None
        try:
            result = parse_explorer_catalog(raw_catalog, raw_themes)
        except ValueError as exc:
            self.collector.fetch_errors["data-explorer:themes"] = str(exc)
            result = None
        self._catalog_cache = result
        return result

    def fetch_deploy_status(self) -> dict[str, Any] | None:
        """Fetch latest deploy workflow run for data-explorer.

        Returns a dict with run_id, name, status, conclusion, started_at,
        completed_at, html_url — or None if unavailable.
        """
        if self._deploy_cache is not _UNSET:
            return self._deploy_cache  # type: ignore[return-value]
        result = self.collector.get_latest_workflow_run("data-explorer", workflow_id="deploy.yml")
        self._deploy_cache = result
        return result


class _Unset:
    pass


_UNSET = _Unset()
