"""Tests for the CLI entry point (``cli.py``)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from agent_context_builder.cli import cli
from agent_context_builder.config import Config

pytestmark = pytest.mark.contract


def _minimal_config(tmp_path: Path) -> tuple[Path, Config]:
    """Write a minimal config YAML and return (path, Config object)."""
    config_path = tmp_path / "dataciviclab.config.yml"
    config_path.write_text(
        "github_org: test-org\nrepos:\n  - repo1\n",
        encoding="utf-8",
    )
    return config_path, Config(workspace_root=None, github_org="test-org", repos=["repo1"])


def _mock_renderer():
    """Build a MagicMock that mimics Renderer's output methods."""
    m = MagicMock()
    m.render_session_bootstrap.return_value = "# Session Bootstrap\n"
    m.render_workspace_triage.return_value = {
        "open_prs": 0,
        "open_issues": 0,
        "open_discussions": 0,
        "warnings": [],
        "github_fetch_errors": {},
        "git_state": {},
        "source_health": {"available": False},
        "dataset_catalog": {"available": False},
        "discussions": [],
    }
    m.render_topic_index.return_value = {
        "repos": {},
        "datasets_by_source": {},
        "operational_topics": {},
    }
    return m


def test_build_creates_three_artifacts(tmp_path: Path):
    """``build`` generates session_bootstrap.md, workspace_triage.json, topic_index.json."""
    config_path, cfg = _minimal_config(tmp_path)
    out = tmp_path / "out_artifacts"

    with (
        patch("agent_context_builder.cli.load_config", return_value=cfg),
        patch("agent_context_builder.cli.GitHubCollector"),
        patch("agent_context_builder.cli.GitLocalCollector"),
        patch("agent_context_builder.cli.Renderer") as rdr_cls,
    ):
        rdr_cls.return_value = _mock_renderer()
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "build",
                "--config",
                str(config_path),
                "--out",
                str(out),
            ],
        )

    assert result.exit_code == 0, result.output
    assert (out / "session_bootstrap.md").exists()
    assert (out / "workspace_triage.json").exists()
    assert (out / "topic_index.json").exists()
    assert (out / "session_bootstrap.md").read_text() == "# Session Bootstrap\n"
    triage = json.loads((out / "workspace_triage.json").read_text())
    assert triage["open_prs"] == 0


def test_build_without_token_skips_discussions(tmp_path: Path):
    """When --github-token is not set, discussions collector is None."""
    config_path, cfg = _minimal_config(tmp_path)
    out = tmp_path / "out"

    with (
        patch("agent_context_builder.cli.load_config", return_value=cfg),
        patch("agent_context_builder.cli.GitHubCollector"),
        patch("agent_context_builder.cli.GitLocalCollector"),
        patch("agent_context_builder.cli.Renderer") as rdr_cls,
    ):
        rdr_cls.return_value = _mock_renderer()
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "build",
                "--config",
                str(config_path),
                "--out",
                str(out),
            ],
        )

    assert result.exit_code == 0, result.output
    assert "discussions skipped" in result.output
    _, kwargs = rdr_cls.call_args
    assert kwargs.get("discussion_collector") is None


def test_build_with_token_passes_to_collectors(tmp_path: Path):
    """--github-token is passed to GitHubCollector and DiscussionCollector."""
    config_path, cfg = _minimal_config(tmp_path)
    out = tmp_path / "out"

    with (
        patch("agent_context_builder.cli.load_config", return_value=cfg),
        patch("agent_context_builder.cli.GitHubCollector") as gh_cls,
        patch("agent_context_builder.cli.GitLocalCollector"),
        patch("agent_context_builder.cli.DiscussionCollector") as disc_cls,
        patch("agent_context_builder.cli.Renderer") as rdr_cls,
    ):
        gh_cls.return_value = MagicMock()
        disc_cls.return_value = MagicMock()
        rdr_cls.return_value = _mock_renderer()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "build",
                "--config",
                str(config_path),
                "--out",
                str(out),
                "--github-token",
                "my-token",
            ],
        )

    assert result.exit_code == 0, result.output
    gh_cls.assert_called_once_with("test-org", token="my-token")
    disc_cls.assert_called_once_with("test-org", token="my-token")
    _, kwargs = rdr_cls.call_args
    assert kwargs["discussion_collector"] is not None


def test_build_with_generated_at_produces_deterministic_output(tmp_path: Path):
    """--generated-at overrides the timestamp for reproducible builds."""
    config_path, cfg = _minimal_config(tmp_path)
    out = tmp_path / "out"

    with (
        patch("agent_context_builder.cli.load_config", return_value=cfg),
        patch("agent_context_builder.cli.GitHubCollector"),
        patch("agent_context_builder.cli.GitLocalCollector"),
        patch("agent_context_builder.cli.Renderer") as rdr_cls,
    ):
        rdr_cls.return_value = _mock_renderer()
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "build",
                "--config",
                str(config_path),
                "--out",
                str(out),
                "--generated-at",
                "2026-01-15T00:00:00Z",
            ],
        )

    assert result.exit_code == 0, result.output
    _, kwargs = rdr_cls.call_args
    assert kwargs["fixed_timestamp"] == "2026-01-15T00:00:00Z"


def test_build_with_workspace_root_overrides_config(tmp_path: Path):
    """--workspace-root overrides the workspace_root from config."""
    config_path, cfg = _minimal_config(tmp_path)
    out = tmp_path / "out"
    ws_root = tmp_path / "my_workspace"

    with (
        patch("agent_context_builder.cli.load_config", return_value=cfg),
        patch("agent_context_builder.cli.GitHubCollector"),
        patch("agent_context_builder.cli.GitLocalCollector") as git_cls,
        patch("agent_context_builder.cli.Renderer") as rdr_cls,
    ):
        git_cls.return_value = MagicMock()
        rdr_cls.return_value = _mock_renderer()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "build",
                "--config",
                str(config_path),
                "--out",
                str(out),
                "--workspace-root",
                str(ws_root),
            ],
        )

    assert result.exit_code == 0, result.output
    assert "my_workspace" in result.output
    git_cls.assert_called_once_with(ws_root)
    cfg_after = rdr_cls.call_args[0][0]
    assert cfg_after.workspace_root == ws_root


def test_build_fails_on_missing_config(tmp_path: Path):
    """Non-existent --config path → Click error."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "build",
            "--config",
            str(tmp_path / "nonexistent.yml"),
            "--out",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code != 0
    assert "does not exist" in result.output
