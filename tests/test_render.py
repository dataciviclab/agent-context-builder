"""Tests for render module."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from agent_context_builder.config import Config
from agent_context_builder.discussions import Discussion, DiscussionCollector
from agent_context_builder.github import PR, RepoInfo
from agent_context_builder.render import Renderer
from tests.conftest import (
    _UNAVAILABLE,
    make_github_mock,
    make_git_mock,
    sample_di_clean_catalog_json,
    sample_di_json,
    sample_so_json,
)


def _renderer(config, gh=None, git_state=None, disc=None):
    """Costruisce un Renderer con mock di default."""
    return Renderer(
        config,
        gh or make_github_mock(),
        make_git_mock(git_state or {}),
        discussion_collector=disc,
    )


# ── session_bootstrap ─────────────────────────────────────────────────────


def test_render_session_bootstrap():
    """Test session_bootstrap.md rendering."""
    config = Config(workspace_root=Path("/tmp/test"), github_org="test-org", repos=["repo1", "repo2"])
    repos_state = {"repo1": _UNAVAILABLE, "repo2": _UNAVAILABLE}
    bootstrap = _renderer(config, git_state=repos_state).render_session_bootstrap()

    assert "Session Bootstrap" in bootstrap
    assert "## 🛠 INFRA" in bootstrap
    assert "6 attivi" not in bootstrap
    assert len(bootstrap.split("\n")) > 10


def test_render_session_bootstrap_github_error():
    """Bootstrap shows warning when GitHub fetch fails."""
    config = Config(workspace_root=Path("/tmp/test"), github_org="test-org", repos=["repo1"])
    gh = make_github_mock(fetch_errors={"repo1:prs": "403 rate limit exceeded"})
    bootstrap = _renderer(config, gh=gh, git_state={"repo1": _UNAVAILABLE}).render_session_bootstrap()

    assert "## 📥 INTAKE" in bootstrap
    assert "Pipeline" in bootstrap
    assert "unavailable" in bootstrap


def test_render_session_bootstrap_groups_dependabot_prs():
    """Bootstrap keeps Dependabot PRs compact and leaves feature PRs visible."""
    config = Config(workspace_root=Path("/tmp/test"), github_org="test-org", repos=["repo1"])
    prs = [
        PR(1, "feat: improve context", "repo1", "https://example.test/pr/1", author="gabry"),
        PR(2, "chore(deps): bump package", "repo1", "https://example.test/pr/2", author="dependabot[bot]"),
        PR(3, "chore(deps): bump action", "repo1", "https://example.test/pr/3", author="dependabot[bot]"),
    ]
    gh = make_github_mock(prs=prs)
    bootstrap = _renderer(config, gh=gh, git_state={"repo1": _UNAVAILABLE}).render_session_bootstrap()

    assert "feat: improve context" in bootstrap
    assert "**Dependabot**: 2 bump PR(s)" in bootstrap
    assert "chore(deps): bump package" not in bootstrap


# ── workspace_triage ──────────────────────────────────────────────────────


def test_render_workspace_triage():
    """Test workspace_triage.json rendering with no errors."""
    config = Config(workspace_root=Path("/tmp/test"), github_org="test-org", repos=["repo1"])
    triage = _renderer(config, git_state={"repo1": _UNAVAILABLE}).render_workspace_triage()

    assert "generated_at" in triage
    assert triage["open_prs"] == 0
    assert triage["github_fetch_errors"] == {}
    assert triage["git_state"]["repo1"]["available"] is False
    assert triage["git_state"]["repo1"]["reason"] == "path_not_found"


def test_render_workspace_triage_github_error():
    """Triage shows null counts and errors when GitHub fetch fails."""
    config = Config(workspace_root=Path("/tmp/test"), github_org="test-org", repos=["repo1"])
    errors = {"repo1:prs": "403 rate limit exceeded"}
    gh = make_github_mock(fetch_errors=errors)
    triage = _renderer(config, gh=gh, git_state={"repo1": _UNAVAILABLE}).render_workspace_triage()

    assert triage["open_prs"] is None
    assert triage["open_issues"] is None
    assert triage["github_fetch_errors"] == errors
    assert any("GitHub fetch failed" in w for w in triage["warnings"])


def test_render_workspace_triage_git_state_reason():
    """Git state includes available and reason for unavailable repos."""
    from agent_context_builder.git_local import GitState
    config = Config(workspace_root=Path("/tmp/test"), github_org="test-org", repos=["repo1"])
    repos_state = {
        "repo1": GitState(available=True, reason=None, dirty=True, current_branch="main",
                          branches_ahead=["main"], untracked_files=2),
    }
    triage = _renderer(config, git_state=repos_state).render_workspace_triage()

    r1 = triage["git_state"]["repo1"]
    assert r1["available"] is True
    assert r1["reason"] is None
    assert r1["dirty"] is True
    assert r1["current_branch"] == "main"


# ── Discussions ───────────────────────────────────────────────────────────


def test_render_bootstrap_with_discussions():
    """Bootstrap includes discussions section when collector is present."""
    config = Config(workspace_root=None, github_org="dataciviclab", repos=["dataset-incubator"])
    disc = MagicMock(spec=DiscussionCollector)
    disc.fetch_errors = {}
    disc.get_discussions.return_value = [
        Discussion(42, "IRPEF: cosa ci dice?", "dataset-incubator",
                   "https://github.com/dataciviclab/dataset-incubator/discussions/42",
                   "Civic Questions", "gabry", "2026-04-14T20:00:00Z"),
    ]
    bootstrap = _renderer(config, disc=disc, git_state={"dataset-incubator": _UNAVAILABLE}).render_session_bootstrap()

    assert "## 🔗 OPEN" in bootstrap
    assert "IRPEF" in bootstrap
    assert "[Civic Questions]" in bootstrap


def test_render_triage_with_discussions():
    """Triage includes open_discussions count and discussions list."""
    config = Config(workspace_root=None, github_org="dataciviclab", repos=["dataset-incubator"])
    disc = MagicMock(spec=DiscussionCollector)
    disc.fetch_errors = {}
    disc.get_discussions.return_value = [
        Discussion(42, "IRPEF: cosa ci dice?", "dataset-incubator",
                   "https://github.com/...", "Civic Questions", "gabry", "2026-04-14T20:00:00Z"),
    ]
    triage = _renderer(config, disc=disc, git_state={"dataset-incubator": _UNAVAILABLE}).render_workspace_triage()

    assert triage["open_discussions"] == 1
    assert triage["discussions"][0]["number"] == 42


def test_render_triage_without_discussion_collector():
    """Triage omits discussions when no collector provided."""
    config = Config(workspace_root=None, github_org="dataciviclab", repos=["repo1"])
    triage = _renderer(config, git_state={"repo1": _UNAVAILABLE}).render_workspace_triage()

    assert triage["open_discussions"] is None
    assert triage["discussions"] == []


# ── Catalog drift ─────────────────────────────────────────────────────────


def test_render_bootstrap_with_catalog_drift():
    """Bootstrap includes the catalog drift section with inventory detail."""
    config = Config(workspace_root=None, github_org="test-org", repos=["repo1"])
    gh = make_github_mock(raw_file=sample_so_json(drift=True))
    bootstrap = _renderer(config, gh=gh).render_session_bootstrap()

    assert "## 🔍 SCOUTING" in bootstrap
    assert "inps" in bootstrap
    assert "inventory change" in bootstrap


def test_render_bootstrap_catalog_drift_all_stable():
    """Bootstrap shows SCOUTING section with no drift when all sources are stable."""
    config = Config(workspace_root=None, github_org="test-org", repos=["repo1"])
    gh = make_github_mock(raw_file=sample_so_json(drift=False))
    bootstrap = _renderer(config, gh=gh).render_session_bootstrap()

    assert "## 🔍 SCOUTING" in bootstrap
    assert "no drift signals" in bootstrap


def test_render_bootstrap_catalog_drift_unavailable():
    """Bootstrap shows unavailable when catalog signals fetch fails."""
    config = Config(workspace_root=None, github_org="test-org", repos=["repo1"])
    bootstrap = _renderer(config, gh=make_github_mock(raw_file=None)).render_session_bootstrap()

    assert "## 📥 INTAKE" in bootstrap
    assert "Pipeline" in bootstrap
    assert "unavailable" in bootstrap


# ── Source health ─────────────────────────────────────────────────────────


def test_render_triage_source_health_available():
    """Triage includes source_health with drift alerts when signals fetched."""
    config = Config(workspace_root=None, github_org="test-org", repos=["repo1"])
    gh = make_github_mock(raw_file=sample_so_json(drift=True))
    triage = _renderer(config, gh=gh).render_workspace_triage()

    sh = triage["source_health"]
    assert sh["available"] is True
    assert len(sh["alerts"]) == 1
    assert sh["alerts"][0]["source"] == "inps"


def test_render_triage_source_health_unavailable():
    """Triage source_health marks unavailable when fetch fails."""
    config = Config(workspace_root=None, github_org="test-org", repos=["repo1"])
    triage = _renderer(config, gh=make_github_mock(raw_file=None)).render_workspace_triage()

    assert triage["source_health"]["available"] is False


# ── Signals + caching ─────────────────────────────────────────────────────


def test_render_signals_cached_across_bootstrap_and_triage():
    """Each remote file is fetched exactly once across bootstrap + triage."""
    config = Config(workspace_root=None, github_org="test-org", repos=["repo1"])
    gh = make_github_mock()

    def _raw_file_side_effect(repo, path, ref="main"):
        if path == "data/catalog/catalog_signals.json":
            return sample_so_json(drift=False)
        if path == "registry/pipeline_signals.json":
            return sample_di_json()
        if path == "registry/clean_catalog.json":
            return sample_di_clean_catalog_json()
        return None

    gh.get_raw_file.side_effect = _raw_file_side_effect
    renderer = _renderer(config, gh=gh)

    renderer.render_session_bootstrap()
    renderer.render_workspace_triage()

    assert gh.get_raw_file.call_count == 5
    paths_fetched = [call.args[1] for call in gh.get_raw_file.call_args_list]
    assert "data/radar/radar_summary.json" in paths_fetched
    assert "data/catalog/catalog_signals.json" in paths_fetched
    assert "registry/pipeline_signals.json" in paths_fetched
    assert "registry/clean_catalog.json" in paths_fetched
    assert "catalog/themes.json" in paths_fetched


# ── Topic index ───────────────────────────────────────────────────────────


def test_render_topic_index():
    """Topic index includes repos, datasets_by_source, operational_topics."""
    from agent_context_builder.config import Topic

    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1"],
        topics={
            "toolkit": Topic(name="toolkit", repos=["repo1"], paths=["src/"],
                             summary="Pipeline engine", next="check docs"),
        },
    )
    gh = make_github_mock(
        repos_info={"repo1": RepoInfo(name="repo1", description="Test repo",
                                      url="https://github.com/test-org/repo1")},
    )

    def _raw_file_side_effect(repo, path, ref="main"):
        if path == "registry/clean_catalog.json":
            return sample_di_clean_catalog_json()
        return None

    gh.get_raw_file.side_effect = _raw_file_side_effect
    result = _renderer(config, gh=gh).render_topic_index()

    assert "repos" in result
    assert result["repos"]["repo1"]["description"] == "Test repo"
    assert "datasets_by_source" in result
    assert any(
        any(d["slug"] == "irpef_comunale" for d in slugs)
        for slugs in result["datasets_by_source"].values()
    )
    assert "operational_topics" in result
    assert result["operational_topics"]["toolkit"]["summary"] == "Pipeline engine"


# ── Clean catalog ─────────────────────────────────────────────────────────


def test_render_bootstrap_dataset_catalog_section():
    """Bootstrap includes clean dataset catalog summary when available."""
    config = Config(workspace_root=None, github_org="test-org", repos=["repo1"])
    gh = make_github_mock()

    def _raw_file_side_effect(repo, path, ref="main"):
        if path == "registry/clean_catalog.json":
            return sample_di_clean_catalog_json()
        return None

    gh.get_raw_file.side_effect = _raw_file_side_effect
    bootstrap = _renderer(config, gh=gh).render_session_bootstrap()

    assert "Dataset Catalog" in bootstrap
    assert "**Dataset Catalog**: 1 published · 1 public · updated" in bootstrap


def test_render_triage_dataset_catalog_available():
    """Triage includes machine-readable clean catalog entries."""
    config = Config(workspace_root=None, github_org="test-org", repos=["repo1"])
    gh = make_github_mock()

    def _raw_file_side_effect(repo, path, ref="main"):
        if path == "registry/clean_catalog.json":
            return sample_di_clean_catalog_json()
        return None

    gh.get_raw_file.side_effect = _raw_file_side_effect
    catalog = _renderer(config, gh=gh).render_workspace_triage()["dataset_catalog"]

    assert catalog["available"] is True
    assert catalog["updated_at"] == "2026-04-14"
    assert catalog["summary"] == {"total": 2, "published": 1}
    assert catalog["datasets"][0]["slug"] == "irpef_comunale"
    assert catalog["datasets"][0]["metric_columns"] == 1
    assert catalog["datasets"][0]["dimension_columns"] == 2


def test_render_triage_dataset_catalog_unavailable():
    """Triage marks dataset catalog unavailable when clean_catalog fetch fails."""
    config = Config(workspace_root=None, github_org="test-org", repos=["repo1"])
    catalog = _renderer(config, gh=make_github_mock(raw_file=None)).render_workspace_triage()["dataset_catalog"]

    assert catalog["available"] is False
