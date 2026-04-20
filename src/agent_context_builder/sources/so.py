"""Source-observatory fetch and parse helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..github import GitHubCollector
from ..signals import (
    PortalScoutSummary,
    RadarSummary,
    SourceObservatorySignals,
    parse_portal_scout_summary,
    parse_radar_summary,
    parse_source_observatory_signals,
)


@dataclass
class SourceObservatoryData:
    """Cached source-observatory artifact bundle."""

    radar: RadarSummary | None
    catalog_signals: SourceObservatorySignals | None
    portal_scout: PortalScoutSummary | None


class SourceObservatoryFetcher:
    """Fetch source-observatory artifacts from GitHub raw URLs."""

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._radar_cache: RadarSummary | None | object = _UNSET
        self._catalog_signals_cache: SourceObservatorySignals | None | object = _UNSET
        self._portal_scout_cache: PortalScoutSummary | None | object = _UNSET

    def fetch(self) -> SourceObservatoryData:
        """Fetch all source-observatory artifacts."""
        return SourceObservatoryData(
            radar=self.fetch_radar_summary(),
            catalog_signals=self.fetch_catalog_signals(),
            portal_scout=self.fetch_portal_scout(),
        )

    def fetch_radar_summary(self) -> RadarSummary | None:
        if self._radar_cache is not _UNSET:
            return self._radar_cache  # type: ignore[return-value]
        raw = self.collector.get_raw_file("source-observatory", "data/radar/radar_summary.json")
        if raw is None:
            self._radar_cache = None
            return None
        try:
            result = parse_radar_summary(raw)
        except ValueError as exc:
            self.collector.fetch_errors["source-observatory:radar_summary"] = str(exc)
            result = None
        self._radar_cache = result
        return result

    def fetch_catalog_signals(self) -> SourceObservatorySignals | None:
        if self._catalog_signals_cache is not _UNSET:
            return self._catalog_signals_cache  # type: ignore[return-value]
        raw = self.collector.get_raw_file("source-observatory", "data/catalog/catalog_signals.json")
        if raw is None:
            self._catalog_signals_cache = None
            return None
        try:
            result = parse_source_observatory_signals(raw)
        except ValueError as exc:
            self.collector.fetch_errors["source-observatory:catalog_signals"] = str(exc)
            result = None
        self._catalog_signals_cache = result
        return result

    def fetch_portal_scout(self) -> PortalScoutSummary | None:
        if self._portal_scout_cache is not _UNSET:
            return self._portal_scout_cache  # type: ignore[return-value]
        raw = self.collector.get_raw_file(
            "source-observatory", "data/portal_scout/discovered_portals_summary.json"
        )
        if raw is None:
            self._portal_scout_cache = None
            return None
        try:
            result = parse_portal_scout_summary(raw)
        except ValueError as exc:
            self.collector.fetch_errors["source-observatory:portal_scout"] = str(exc)
            result = None
        self._portal_scout_cache = result
        return result


class _Unset:
    pass


_UNSET = _Unset()

