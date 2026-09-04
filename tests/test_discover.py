"""Tests for discover_registries.py — org scan + config reconciliation."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.discover_registries import (
    list_org_repos_with_registry,
    load_config_repos,
    save_config_repos,
)

pytestmark = pytest.mark.pure_unit


@pytest.fixture
def sample_config(tmp_path: Path) -> Path:
    config = tmp_path / "dataciviclab.config.yml"
    config.write_text(
        textwrap.dedent("""\
            github_org: dataciviclab

            repos:
              - agent-context-builder
              - dataset-incubator
              - toolkit

            topics:
              pipeline:
                summary: Test
        """)
    )
    return config


class TestLoadConfigRepos:
    def test_loads_repos_list(self, sample_config: Path) -> None:
        repos = load_config_repos(sample_config)
        assert repos == ["agent-context-builder", "dataset-incubator", "toolkit"]

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config_repos(tmp_path / "nonexistent.yml")


class TestSaveConfigRepos:
    def test_preserves_yaml_structure(self, sample_config: Path) -> None:
        save_config_repos(sample_config, ["toolkit", "dataset-incubator", "new-repo"])
        repos = load_config_repos(sample_config)
        assert repos == ["toolkit", "dataset-incubator", "new-repo"]

    def test_topics_section_preserved(self, sample_config: Path) -> None:
        save_config_repos(sample_config, ["toolkit"])
        content = sample_config.read_text()
        assert "topics:" in content
        assert "pipeline:" in content

    def test_empty_repos(self, sample_config: Path) -> None:
        save_config_repos(sample_config, [])
        repos = load_config_repos(sample_config)
        assert repos == []


class TestListOrgReposWithRegistry:
    def test_discovery_logic(self) -> None:
        mock_repos = [
            {"name": "repo-a"},
            {"name": "repo-b"},
            {"name": "repo-c"},
        ]

        def _mock_get(url, **kwargs):
            resp = MagicMock()
            if "/repos" in url and "/contents/" not in url:
                resp.status_code = 200
                resp.json.return_value = mock_repos
                resp.raise_for_status = MagicMock()
            elif "repo-a/contents/registry" in url:
                resp.status_code = 200
            elif "repo-b/contents/registry" in url:
                resp.status_code = 404
            elif "repo-c/contents/registry" in url:
                resp.status_code = 200
            else:
                resp.status_code = 404
            return resp

        with patch("scripts.discover_registries.requests.get", side_effect=_mock_get):
            result = list_org_repos_with_registry("test-org", token="fake")

        assert result == ["repo-a", "repo-c"]

    def test_empty_org(self) -> None:
        def _mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = []
            resp.raise_for_status = MagicMock()
            return resp

        with patch("scripts.discover_registries.requests.get", side_effect=_mock_get):
            result = list_org_repos_with_registry("empty-org", token="fake")

        assert result == []


class TestReconciliationLogic:
    def test_finds_new_repos(self, sample_config: Path) -> None:
        current = load_config_repos(sample_config)
        discovered = ["agent-context-builder", "dataset-incubator", "toolkit", "new-repo"]
        to_add = sorted(set(discovered) - set(current))
        assert to_add == ["new-repo"]

    def test_no_changes_when_aligned(self, sample_config: Path) -> None:
        current = load_config_repos(sample_config)
        discovered = ["agent-context-builder", "dataset-incubator", "toolkit"]
        to_add = sorted(set(discovered) - set(current))
        assert to_add == []

    def test_does_not_remove_existing(self, sample_config: Path) -> None:
        current = load_config_repos(sample_config)
        discovered = ["toolkit"]  # subset — missing agent-context-builder, dataset-incubator
        to_add = sorted(set(discovered) - set(current))
        assert to_add == []  # nothing to add, nothing removed
