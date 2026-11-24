"""Tests per la modalità workspace locale (repo per nome, registry locali).

Il workspace è ``{dominio}/{repo}``: i collector locali devono risolvere per
nome e i registry locali devono vincere su GitHub quando si fa un build con
``--workspace-root`` (in CI ``workspace_root`` è None → GitHub-only).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent_context_builder.git_local import GitLocalCollector, GitState
from agent_context_builder.sources.registry import RegistryFetcher
from agent_context_builder.workspace import resolve_repo_path

pytestmark = pytest.mark.pure_unit


def _write_registry(path: Path, datasets: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": 2, "datasets": datasets, "marts": []}), encoding="utf-8"
    )


class TestResolveRepoPath:
    def test_direct(self, tmp_path: Path) -> None:
        (tmp_path / "toolkit").mkdir()
        assert resolve_repo_path(tmp_path, "toolkit") == tmp_path / "toolkit"

    def test_nested_by_domain(self, tmp_path: Path) -> None:
        nested = tmp_path / "diritto-legge" / "open-politica"
        nested.mkdir(parents=True)
        assert resolve_repo_path(tmp_path, "open-politica") == nested

    def test_missing(self, tmp_path: Path) -> None:
        assert resolve_repo_path(tmp_path, "nope") is None

    def test_none_root(self) -> None:
        assert resolve_repo_path(None, "toolkit") is None


class TestLocalRegistryWins:
    def test_prefers_local_registry(self, tmp_path: Path) -> None:
        """Un registry locale vince; il collector GitHub non viene chiamato."""
        _write_registry(
            tmp_path / "diritto-legge" / "open-politica" / "registry" / "registry.json",
            [{"slug": "atti", "partitions": {"2026": 10}}],
        )
        collector = MagicMock()
        fetcher = RegistryFetcher(collector, local_root=tmp_path)

        reg = fetcher.fetch_repo("open-politica")

        assert reg is not None
        assert reg.datasets[0].partitions == {2026: 10}
        collector.get_raw_file.assert_not_called()

    def test_falls_back_to_github_without_local(self, tmp_path: Path) -> None:
        """Senza registry locale si usa GitHub (una chiamata per repo)."""
        collector = MagicMock()
        collector.get_raw_file.return_value = json.dumps({"datasets": [{"slug": "x"}]})
        fetcher = RegistryFetcher(collector, local_root=tmp_path)

        reg = fetcher.fetch_repo("open-politica")

        assert reg is not None and reg.datasets[0].slug == "x"
        collector.get_raw_file.assert_called_once_with("open-politica", "registry/registry.json")

    def test_missing_registry_is_none_not_error(self, tmp_path: Path) -> None:
        collector = MagicMock()
        collector.get_raw_file.return_value = None
        collector.fetch_errors = {}
        fetcher = RegistryFetcher(collector, local_root=tmp_path)
        assert fetcher.fetch_repo("senza-registry") is None
        assert collector.fetch_errors == {}

    def test_invalid_local_registry_records_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "repo1" / "registry" / "registry.json"
        bad.parent.mkdir(parents=True)
        bad.write_text("{ non json", encoding="utf-8")
        collector = MagicMock()
        collector.fetch_errors = {}
        fetcher = RegistryFetcher(collector, local_root=tmp_path)
        assert fetcher.fetch_repo("repo1") is None
        assert "repo1:registry" in collector.fetch_errors


class TestGitCollectorNested:
    def test_nested_repo_is_found(self, tmp_path: Path, monkeypatch) -> None:
        """Il git state locale usa la risoluzione per nome (layout a domini)."""
        nested = tmp_path / "diritto-legge" / "open-politica"
        nested.mkdir(parents=True)
        collector = GitLocalCollector(tmp_path)
        seen: list[Path] = []

        def fake_state(path: Path) -> GitState:
            seen.append(path)
            return GitState(available=True, reason=None, dirty=False, current_branch="main")

        monkeypatch.setattr(collector, "_get_repo_state", fake_state)
        states = collector.get_repos_state(["open-politica", "assente"])

        assert seen == [nested]
        assert states["open-politica"].available is True
        assert states["assente"].reason == "path_not_found"
