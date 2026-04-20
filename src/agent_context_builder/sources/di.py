"""Dataset-incubator fetch and parse helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..github import GitHubCollector
from ..signals import DICleanCatalog, RepoSignals, parse_di_clean_catalog, parse_repo_signals


@dataclass
class DatasetIncubatorData:
    """Cached dataset-incubator artifact bundle."""

    pipeline_signals: RepoSignals | None
    clean_catalog: DICleanCatalog | None


class DatasetIncubatorFetcher:
    """Fetch dataset-incubator artifacts from GitHub raw URLs."""

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._pipeline_signals_cache: RepoSignals | None | object = _UNSET
        self._clean_catalog_cache: DICleanCatalog | None | object = _UNSET

    def fetch(self) -> DatasetIncubatorData:
        """Fetch all dataset-incubator artifacts."""
        return DatasetIncubatorData(
            pipeline_signals=self.fetch_pipeline_signals(),
            clean_catalog=self.fetch_clean_catalog(),
        )

    def fetch_pipeline_signals(self) -> RepoSignals | None:
        if self._pipeline_signals_cache is not _UNSET:
            return self._pipeline_signals_cache  # type: ignore[return-value]
        raw = self.collector.get_raw_file("dataset-incubator", "registry/pipeline_signals.json")
        if raw is None:
            self._pipeline_signals_cache = None
            return None
        try:
            result = parse_repo_signals(raw)
        except ValueError as exc:
            self.collector.fetch_errors["dataset-incubator:pipeline_signals"] = str(exc)
            result = None
        self._pipeline_signals_cache = result
        return result

    def fetch_clean_catalog(self) -> DICleanCatalog | None:
        if self._clean_catalog_cache is not _UNSET:
            return self._clean_catalog_cache  # type: ignore[return-value]
        raw = self.collector.get_raw_file("dataset-incubator", "registry/clean_catalog.json")
        if raw is None:
            self._clean_catalog_cache = None
            return None
        try:
            result = parse_di_clean_catalog(raw)
        except ValueError as exc:
            self.collector.fetch_errors["dataset-incubator:clean_catalog"] = str(exc)
            result = None
        self._clean_catalog_cache = result
        return result


class _Unset:
    pass


_UNSET = _Unset()

