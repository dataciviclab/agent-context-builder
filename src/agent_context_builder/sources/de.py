"""Data-explorer fetch and parse helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..github import GitHubCollector
from ..signals import ExplorerTheme, parse_explorer_themes


@dataclass
class DataExplorerData:
    """Cached data-explorer artifact bundle."""

    themes: list[ExplorerTheme] | None


class DataExplorerFetcher:
    """Fetch data-explorer artifacts from GitHub raw URLs.

    Consumes:
      - catalog/themes.json (editorial theme assignments)
    """

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._themes_cache: list[ExplorerTheme] | None | object = _UNSET

    def fetch(self) -> DataExplorerData:
        """Fetch all data-explorer artifacts."""
        return DataExplorerData(themes=self.fetch_themes())

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


class _Unset:
    pass


_UNSET = _Unset()
