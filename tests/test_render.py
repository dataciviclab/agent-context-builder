"""Tests for render module."""

from pathlib import Path
from unittest.mock import MagicMock

from agent_context_builder.config import Config
from agent_context_builder.github import GitHubCollector
from agent_context_builder.git_local import GitLocalCollector
from agent_context_builder.render import Renderer


def test_render_session_bootstrap():
    """Test session_bootstrap.md rendering."""
    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1", "repo2"],
    )

    github_collector = MagicMock(spec=GitHubCollector)
    github_collector.get_prs.return_value = []
    github_collector.get_issues.return_value = []

    git_collector = MagicMock(spec=GitLocalCollector)
    git_collector.get_state.return_value = None

    renderer = Renderer(config, github_collector, git_collector)
    bootstrap = renderer.render_session_bootstrap()

    assert "Session Bootstrap" in bootstrap
    assert "repo1" in bootstrap
    assert "repo2" in bootstrap
    assert len(bootstrap.split("\n")) > 10


def test_render_workspace_triage():
    """Test workspace_triage.json rendering."""
    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1"],
    )

    github_collector = MagicMock(spec=GitHubCollector)
    github_collector.get_prs.return_value = []
    github_collector.get_issues.return_value = []

    git_collector = MagicMock(spec=GitLocalCollector)
    git_collector.get_state.return_value = None

    renderer = Renderer(config, github_collector, git_collector)
    triage = renderer.render_workspace_triage()

    assert "generated_at" in triage
    assert "open_prs" in triage
    assert triage["open_prs"] == 0


def test_render_topic_index():
    """Test topic_index.json rendering."""
    from agent_context_builder.config import Topic

    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1"],
        topics={
            "topic1": Topic(name="topic1", repos=["repo1"], paths=["path1"]),
        },
    )

    github_collector = MagicMock(spec=GitHubCollector)
    git_collector = MagicMock(spec=GitLocalCollector)

    renderer = Renderer(config, github_collector, git_collector)
    topics = renderer.render_topic_index()

    assert "topics" in topics
    assert "topic1" in topics["topics"]
