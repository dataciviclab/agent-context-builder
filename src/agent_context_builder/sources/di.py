"""Dataset-incubator fetch and parse helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..github import GitHubCollector
from ..signals import DIRegistry, RepoSignals, parse_di_registry, parse_repo_signals


@dataclass
class DatasetIncubatorData:
    """Cached dataset-incubator artifact bundle."""

    pipeline_signals: RepoSignals | None
    registry: DIRegistry | None


class DatasetIncubatorFetcher:
    """Fetch dataset-incubator artifacts from GitHub raw URLs."""

    def __init__(self, collector: GitHubCollector):
        self.collector = collector
        self._pipeline_signals_cache: RepoSignals | None | object = _UNSET
        self._registry_cache: DIRegistry | None | object = _UNSET

    def fetch(self) -> DatasetIncubatorData:
        """Fetch all dataset-incubator artifacts."""
        return DatasetIncubatorData(
            pipeline_signals=self.fetch_pipeline_signals(),
            registry=self.fetch_registry(),
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

    def fetch_registry(self) -> DIRegistry | None:
        """Fetch and parse dataset-incubator registry.json (schema v1).

        The canonical artifact replaced the legacy clean_catalog.json
        projection: registry.json is generated first by build_registry.py
        and clean_catalog.json is only derived from it for compatibility.
        """
        if self._registry_cache is not _UNSET:
            return self._registry_cache  # type: ignore[return-value]
        raw = self.collector.get_raw_file("dataset-incubator", "registry/registry.json")
        if raw is None:
            self._registry_cache = None
            return None
        try:
            result = parse_di_registry(raw)
        except ValueError as exc:
            self.collector.fetch_errors["dataset-incubator:registry"] = str(exc)
            result = None
        self._registry_cache = result
        return result


class _Unset:
    pass


_UNSET = _Unset()
