"""Tests for render module."""

from pathlib import Path
from unittest.mock import MagicMock

from agent_context_builder.config import Config
from agent_context_builder.discussions import Discussion, DiscussionCollector
from agent_context_builder.git_local import GitLocalCollector, GitState
from agent_context_builder.github import GitHubCollector
from agent_context_builder.render import Renderer

_UNAVAILABLE = GitState(available=False, reason="path_not_found", dirty=None, current_branch=None)


def _make_github_mock(prs=None, issues=None, fetch_errors=None):
    m = MagicMock(spec=GitHubCollector)
    m.get_prs.return_value = prs or []
    m.get_issues.return_value = issues or []
    m.fetch_errors = fetch_errors or {}
    return m


def _make_git_mock(repos_state=None):
    m = MagicMock(spec=GitLocalCollector)
    m.get_repos_state.return_value = repos_state or {}
    return m


def test_render_session_bootstrap():
    """Test session_bootstrap.md rendering."""
    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1", "repo2"],
    )
    repos_state = {"repo1": _UNAVAILABLE, "repo2": _UNAVAILABLE}
    renderer = Renderer(config, _make_github_mock(), _make_git_mock(repos_state))
    bootstrap = renderer.render_session_bootstrap()

    assert "Session Bootstrap" in bootstrap
    assert "repo1" in bootstrap
    assert "repo2" in bootstrap
    assert len(bootstrap.split("\n")) > 10


def test_render_session_bootstrap_github_error():
    """Bootstrap shows warning when GitHub fetch fails."""
    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1"],
    )
    repos_state = {"repo1": _UNAVAILABLE}
    renderer = Renderer(
        config,
        _make_github_mock(fetch_errors={"repo1:prs": "403 rate limit exceeded"}),
        _make_git_mock(repos_state),
    )
    bootstrap = renderer.render_session_bootstrap()

    assert "GitHub unavailable" in bootstrap
    assert "No open PRs" not in bootstrap


def test_render_workspace_triage():
    """Test workspace_triage.json rendering with no errors."""
    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1"],
    )
    repos_state = {"repo1": _UNAVAILABLE}
    renderer = Renderer(config, _make_github_mock(), _make_git_mock(repos_state))
    triage = renderer.render_workspace_triage()

    assert "generated_at" in triage
    assert triage["open_prs"] == 0
    assert triage["github_fetch_errors"] == {}
    assert triage["git_state"]["repo1"]["available"] is False
    assert triage["git_state"]["repo1"]["reason"] == "path_not_found"


def test_render_workspace_triage_github_error():
    """Triage shows null counts and errors when GitHub fetch fails."""
    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1"],
    )
    repos_state = {"repo1": _UNAVAILABLE}
    errors = {"repo1:prs": "403 rate limit exceeded"}
    renderer = Renderer(config, _make_github_mock(fetch_errors=errors), _make_git_mock(repos_state))
    triage = renderer.render_workspace_triage()

    assert triage["open_prs"] is None
    assert triage["open_issues"] is None
    assert triage["github_fetch_errors"] == errors
    assert any("GitHub fetch failed" in w for w in triage["warnings"])


def test_render_workspace_triage_git_state_reason():
    """Git state includes available and reason for unavailable repos."""
    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1"],
    )
    repos_state = {
        "repo1": GitState(available=True, reason=None, dirty=True, current_branch="main", branches_ahead=["main"], untracked_files=2)
    }
    renderer = Renderer(config, _make_github_mock(), _make_git_mock(repos_state))
    triage = renderer.render_workspace_triage()

    r1 = triage["git_state"]["repo1"]
    assert r1["available"] is True
    assert r1["reason"] is None
    assert r1["dirty"] is True
    assert r1["current_branch"] == "main"


def test_render_bootstrap_with_discussions():
    """Bootstrap includes discussions section when collector is present."""
    config = Config(workspace_root=None, github_org="dataciviclab", repos=["dataset-incubator"])
    repos_state = {"dataset-incubator": _UNAVAILABLE}

    disc_collector = MagicMock(spec=DiscussionCollector)
    disc_collector.fetch_errors = {}
    disc_collector.get_discussions.return_value = [
        Discussion(
            number=42, title="IRPEF: cosa ci dice?",
            repo="dataset-incubator",
            url="https://github.com/dataciviclab/dataset-incubator/discussions/42",
            category="Civic Questions", author="gabry", updated_at="2026-04-14T20:00:00Z",
        )
    ]

    renderer = Renderer(config, _make_github_mock(), _make_git_mock(repos_state), discussion_collector=disc_collector)
    bootstrap = renderer.render_session_bootstrap()

    assert "Open Discussions" in bootstrap
    assert "IRPEF" in bootstrap
    assert "Civic Questions" in bootstrap


def test_render_triage_with_discussions():
    """Triage includes open_discussions count and discussions list."""
    config = Config(workspace_root=None, github_org="dataciviclab", repos=["dataset-incubator"])
    repos_state = {"dataset-incubator": _UNAVAILABLE}

    disc_collector = MagicMock(spec=DiscussionCollector)
    disc_collector.fetch_errors = {}
    disc_collector.get_discussions.return_value = [
        Discussion(
            number=42, title="IRPEF: cosa ci dice?",
            repo="dataset-incubator",
            url="https://github.com/dataciviclab/dataset-incubator/discussions/42",
            category="Civic Questions", author="gabry", updated_at="2026-04-14T20:00:00Z",
        )
    ]

    renderer = Renderer(config, _make_github_mock(), _make_git_mock(repos_state), discussion_collector=disc_collector)
    triage = renderer.render_workspace_triage()

    assert triage["open_discussions"] == 1
    assert triage["discussions"][0]["number"] == 42
    assert triage["discussions"][0]["category"] == "Civic Questions"


def test_render_triage_without_discussion_collector():
    """Triage omits discussions when no collector provided."""
    config = Config(workspace_root=None, github_org="dataciviclab", repos=["repo1"])
    repos_state = {"repo1": _UNAVAILABLE}

    renderer = Renderer(config, _make_github_mock(), _make_git_mock(repos_state))
    triage = renderer.render_workspace_triage()

    assert triage["open_discussions"] is None
    assert triage["discussions"] == []


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

    renderer = Renderer(config, _make_github_mock(), _make_git_mock())
    topics = renderer.render_topic_index()

    assert "topics" in topics
    assert "topic1" in topics["topics"]
