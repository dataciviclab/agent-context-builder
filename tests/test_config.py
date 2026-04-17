"""Tests for config module."""

from pathlib import Path

import pytest

from agent_context_builder.config import Config, Topic, load_config





def test_config_without_workspace_root():
    """workspace_root is optional — GitHub-only mode."""
    config = Config(github_org="test-org", repos=["repo1"])
    assert config.workspace_root is None


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





def test_load_config_unsupported_format(tmp_path):
    """Test loading unsupported config format."""
    config_file = tmp_path / "test.txt"
    config_file.write_text("invalid")

    with pytest.raises(ValueError, match="Unsupported config format"):
        load_config(config_file)
