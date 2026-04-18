"""Tests for config module."""

from pathlib import Path

import pytest

from agent_context_builder.config import Config, Topic, load_config


def test_topic_creation():
    """Test Topic creation."""
    topic = Topic(name="test", repos=["repo1"], paths=["path1"])
    assert topic.name == "test"
    assert topic.repos == ["repo1"]
    assert topic.paths == ["path1"]


def test_config_creation():
    """Test Config creation."""
    config = Config(
        workspace_root=Path("/tmp"),
        github_org="test-org",
        repos=["repo1", "repo2"],
        topics={},
    )
    assert config.github_org == "test-org"
    assert config.repos == ["repo1", "repo2"]


def test_config_without_workspace_root():
    """workspace_root is optional — GitHub-only mode."""
    config = Config(github_org="test-org", repos=["repo1"])
    assert config.workspace_root is None
    assert config.source_catalog_summary_path is None


def test_load_config_yaml_without_workspace_root(tmp_path):
    """Config YAML without workspace_root is valid."""
    config_file = tmp_path / "test.yml"
    config_file.write_text(
        """
github_org: dataciviclab
repos:
  - dataset-incubator
"""
    )
    config = load_config(config_file)
    assert config.workspace_root is None
    assert config.github_org == "dataciviclab"


def test_load_config_yaml(tmp_path):
    """Test loading YAML config."""
    config_file = tmp_path / "test.yml"
    config_file.write_text(
        """
workspace_root: /tmp/test
github_org: test-org
repos:
  - repo1
  - repo2
topics:
  test-topic:
    repos:
      - repo1
    paths:
      - path1
"""
    )

    config = load_config(config_file)
    assert config.github_org == "test-org"
    assert config.repos == ["repo1", "repo2"]
    assert "test-topic" in config.topics
    assert config.topics["test-topic"].repos == ["repo1"]


def test_load_config_yaml_source_catalog_summary_path(tmp_path):
    """YAML config can opt in to a source-observatory inventory artifact."""
    config_file = tmp_path / "test.yml"
    config_file.write_text(
        """
github_org: test-org
repos:
  - repo1
source_catalog_summary_path: data/catalog_inventory/generated/source_catalog_summary.json
"""
    )

    config = load_config(config_file)
    assert (
        config.source_catalog_summary_path
        == "data/catalog_inventory/generated/source_catalog_summary.json"
    )


def test_load_config_missing_file():
    """Test loading missing config file."""
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yml"))


def test_load_config_unsupported_format(tmp_path):
    """Test loading unsupported config format."""
    config_file = tmp_path / "test.txt"
    config_file.write_text("invalid")

    with pytest.raises(ValueError, match="Unsupported config format"):
        load_config(config_file)
