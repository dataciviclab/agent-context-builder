"""Tests for render module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent_context_builder.config import Config
from agent_context_builder.discussions import Discussion, DiscussionCollector
from agent_context_builder.github import PR, RepoInfo
from agent_context_builder.render import Renderer
from tests.conftest import (
    _UNAVAILABLE,
    make_git_mock,
    make_github_mock,
    sample_di_clean_catalog_json,
    sample_di_json,
    sample_so_json,
)

pytestmark = pytest.mark.contract


def _r(config, gh=None, git_state=None, disc=None):
    """Shortcut: Renderer(config, gh, git, disc) + optional git_state."""
    return Renderer(
        config,
        gh or make_github_mock(),
        make_git_mock(git_state or {}),
        discussion_collector=disc,
    )


def _cfg(root=None, repos=None):
    """Shortcut: Config with workspace_root, github_org, repos."""
    return Config(
        workspace_root=root,
        github_org="test-org",
        repos=repos or ["repo1"],
    )


# ── session_bootstrap ─────────────────────────────────────────────────────


def test_render_session_bootstrap():
    """Test session_bootstrap.md rendering."""
    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1", "repo2"],
    )
    repos_state = {"repo1": _UNAVAILABLE, "repo2": _UNAVAILABLE}
    bootstrap = _r(config, git_state=repos_state).render_session_bootstrap()

    assert "Session Bootstrap" in bootstrap
    assert "## 🛠 INFRA" in bootstrap
    assert "6 attivi" not in bootstrap
    assert len(bootstrap.split("\n")) > 10


def test_render_session_bootstrap_github_error():
    """Bootstrap shows warning when GitHub fetch fails."""
    gh = make_github_mock(fetch_errors={"repo1:prs": "403 rate limit exceeded"})
    bootstrap = _r(
        _cfg(root=Path("/tmp/test")), gh=gh, git_state={"repo1": _UNAVAILABLE}
    ).render_session_bootstrap()

    assert "## 📥 INTAKE" in bootstrap
    assert "Pipeline" in bootstrap
    assert "unavailable" in bootstrap


def test_render_session_bootstrap_groups_dependabot_prs():
    """Bootstrap keeps Dependabot PRs compact and leaves feature PRs visible."""
    prs = [
        PR(1, "feat: improve context", "repo1", "https://example.test/pr/1", author="gabry"),
        PR(
            2,
            "chore(deps): bump package",
            "repo1",
            "https://example.test/pr/2",
            author="dependabot[bot]",
        ),
        PR(
            3,
            "chore(deps): bump action",
            "repo1",
            "https://example.test/pr/3",
            author="dependabot[bot]",
        ),
    ]
    gh = make_github_mock(prs=prs)
    bootstrap = _r(
        _cfg(root=Path("/tmp/test")), gh=gh, git_state={"repo1": _UNAVAILABLE}
    ).render_session_bootstrap()

    assert "feat: improve context" in bootstrap
    assert "**Dependabot**: 2 bump PR(s)" in bootstrap
    assert "chore(deps): bump package" not in bootstrap


# ── workspace_triage ──────────────────────────────────────────────────────


def test_render_workspace_triage():
    """Test workspace_triage.json rendering with no errors."""
    triage = _r(
        _cfg(root=Path("/tmp/test")), git_state={"repo1": _UNAVAILABLE}
    ).render_workspace_triage()

    assert "generated_at" in triage
    assert triage["open_prs"] == 0
    assert triage["github_fetch_errors"] == {}
    assert triage["git_state"]["repo1"]["available"] is False
    assert triage["git_state"]["repo1"]["reason"] == "path_not_found"


def test_render_workspace_triage_github_error():
    """Triage shows null counts and errors when GitHub fetch fails."""
    errors = {"repo1:prs": "403 rate limit exceeded"}
    gh = make_github_mock(fetch_errors=errors)
    triage = _r(
        _cfg(root=Path("/tmp/test")), gh=gh, git_state={"repo1": _UNAVAILABLE}
    ).render_workspace_triage()

    assert triage["open_prs"] is None
    assert triage["open_issues"] is None
    assert triage["github_fetch_errors"] == errors
    assert any("GitHub fetch failed" in w for w in triage["warnings"])


def test_render_workspace_triage_git_state_reason():
    """Git state includes available and reason for unavailable repos."""
    from agent_context_builder.git_local import GitState

    repos_state = {
        "repo1": GitState(
            available=True,
            reason=None,
            dirty=True,
            current_branch="main",
            branches_ahead=["main"],
            untracked_files=2,
        ),
    }
    triage = _r(_cfg(root=Path("/tmp/test")), git_state=repos_state).render_workspace_triage()

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
        Discussion(
            42,
            "IRPEF: cosa ci dice?",
            "dataset-incubator",
            "https://github.com/dataciviclab/dataset-incubator/discussions/42",
            "Civic Questions",
            "gabry",
            "2026-04-14T20:00:00Z",
        ),
    ]
    bootstrap = _r(
        config, disc=disc, git_state={"dataset-incubator": _UNAVAILABLE}
    ).render_session_bootstrap()

    assert "## 🔗 OPEN" in bootstrap
    assert "IRPEF" in bootstrap
    assert "[Civic Questions]" in bootstrap


def test_render_triage_with_discussions():
    """Triage includes open_discussions count and discussions list."""
    config = Config(workspace_root=None, github_org="dataciviclab", repos=["dataset-incubator"])
    disc = MagicMock(spec=DiscussionCollector)
    disc.fetch_errors = {}
    disc.get_discussions.return_value = [
        Discussion(
            42,
            "IRPEF: cosa ci dice?",
            "dataset-incubator",
            "https://github.com/...",
            "Civic Questions",
            "gabry",
            "2026-04-14T20:00:00Z",
        ),
    ]
    triage = _r(
        config, disc=disc, git_state={"dataset-incubator": _UNAVAILABLE}
    ).render_workspace_triage()

    assert triage["open_discussions"] == 1
    assert triage["discussions"][0]["number"] == 42


def test_render_triage_without_discussion_collector():
    """Triage omits discussions when no collector provided."""
    triage = _r(_cfg(), git_state={"repo1": _UNAVAILABLE}).render_workspace_triage()

    assert triage["open_discussions"] is None
    assert triage["discussions"] == []


# ── Catalog drift ─────────────────────────────────────────────────────────


def test_render_bootstrap_with_catalog_drift():
    """Bootstrap includes the catalog drift section with inventory detail."""
    gh = make_github_mock(raw_file=sample_so_json(drift=True))
    bootstrap = _r(_cfg(), gh=gh).render_session_bootstrap()

    assert "## 🔍 SCOUTING" in bootstrap
    assert "inps" in bootstrap
    assert "inventory change" in bootstrap


def test_render_bootstrap_catalog_drift_all_stable():
    """Bootstrap shows SCOUTING section with no drift when all sources are stable."""
    gh = make_github_mock(raw_file=sample_so_json(drift=False))
    bootstrap = _r(_cfg(), gh=gh).render_session_bootstrap()

    assert "## 🔍 SCOUTING" in bootstrap
    assert "no drift signals" in bootstrap


def test_render_bootstrap_catalog_drift_unavailable():
    """Bootstrap shows unavailable when catalog signals fetch fails."""
    bootstrap = _r(_cfg(), gh=make_github_mock(raw_file=None)).render_session_bootstrap()

    assert "## 📥 INTAKE" in bootstrap
    assert "Pipeline" in bootstrap
    assert "unavailable" in bootstrap


# ── Source health ─────────────────────────────────────────────────────────


def test_render_triage_source_health_available():
    """Triage includes source_health with drift alerts when signals fetched."""
    gh = make_github_mock(raw_file=sample_so_json(drift=True))
    triage = _r(_cfg(), gh=gh).render_workspace_triage()

    sh = triage["source_health"]
    assert sh["available"] is True
    assert len(sh["alerts"]) == 1
    assert sh["alerts"][0]["source"] == "inps"


def test_render_triage_source_health_unavailable():
    """Triage source_health marks unavailable when fetch fails."""
    triage = _r(_cfg(), gh=make_github_mock(raw_file=None)).render_workspace_triage()

    assert triage["source_health"]["available"] is False


# ── Signals + caching ─────────────────────────────────────────────────────


def test_render_signals_cached_across_bootstrap_and_triage():
    """Each remote file is fetched exactly once across bootstrap + triage."""
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
    renderer = _r(_cfg(), gh=gh)

    renderer.render_session_bootstrap()
    renderer.render_workspace_triage()

    # 6 files fetched: radar_summary + catalog_signals + pipeline_signals
    # + clean_catalog + themes.json.py = 5 via get_raw_file
    # + 1 directory listing call via list_directory (analisi/)
    assert gh.get_raw_file.call_count == 5
    assert gh.list_directory.call_count == 1
    paths_fetched = [call.args[1] for call in gh.get_raw_file.call_args_list]
    assert "data/radar/radar_summary.json" in paths_fetched
    assert "data/catalog/catalog_signals.json" in paths_fetched
    assert "registry/pipeline_signals.json" in paths_fetched
    assert "registry/clean_catalog.json" in paths_fetched
    assert "src/data/themes.json.py" in paths_fetched


# ── Topic index ───────────────────────────────────────────────────────────


def test_render_topic_index():
    """Topic index includes repos, datasets_by_source, operational_topics."""
    from agent_context_builder.config import Topic

    config = Config(
        workspace_root=Path("/tmp/test"),
        github_org="test-org",
        repos=["repo1"],
        topics={
            "toolkit": Topic(
                name="toolkit",
                repos=["repo1"],
                paths=["src/"],
                summary="Pipeline engine",
                next="check docs",
            ),
        },
    )
    gh = make_github_mock(
        repos_info={
            "repo1": RepoInfo(
                name="repo1", description="Test repo", url="https://github.com/test-org/repo1"
            ),
        },
    )

    def _raw_file_side_effect(repo, path, ref="main"):
        if path == "registry/clean_catalog.json":
            return sample_di_clean_catalog_json()
        return None

    gh.get_raw_file.side_effect = _raw_file_side_effect
    result = _r(config, gh=gh).render_topic_index()

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
    gh = make_github_mock()

    def _raw_file_side_effect(repo, path, ref="main"):
        if path == "registry/clean_catalog.json":
            return sample_di_clean_catalog_json()
        return None

    gh.get_raw_file.side_effect = _raw_file_side_effect
    bootstrap = _r(_cfg(), gh=gh).render_session_bootstrap()

    assert "Dataset Catalog" in bootstrap
    assert "**Dataset Catalog**: 1 published · 1 public · updated" in bootstrap


def test_render_triage_dataset_catalog_available():
    """Triage includes machine-readable clean catalog entries."""
    gh = make_github_mock()

    def _raw_file_side_effect(repo, path, ref="main"):
        if path == "registry/clean_catalog.json":
            return sample_di_clean_catalog_json()
        return None

    gh.get_raw_file.side_effect = _raw_file_side_effect
    catalog = _r(_cfg(), gh=gh).render_workspace_triage()["dataset_catalog"]

    assert catalog["available"] is True
    assert catalog["updated_at"] == "2026-04-14"
    assert catalog["summary"] == {"total": 2, "published": 1}
    assert catalog["datasets"][0]["slug"] == "irpef_comunale"
    assert catalog["datasets"][0]["metric_columns"] == 1
    assert catalog["datasets"][0]["dimension_columns"] == 2


def test_render_triage_dataset_catalog_unavailable():
    """Triage marks dataset catalog unavailable when clean_catalog fetch fails."""
    catalog = _r(_cfg(), gh=make_github_mock(raw_file=None)).render_workspace_triage()[
        "dataset_catalog"
    ]

    assert catalog["available"] is False


# ── Topic index v3: analyses ───────────────────────────────────────────────


def _sample_analysis_readme(slug: str, discussion: int | None = None) -> str:
    """Simulate an analysis README.md with frontmatter."""
    if slug == "irpef-comunale":
        return f"""---
title: IRPEF Comunale 2019-2023
description: Analisi IRPEF
date: 2026-05-24
topics: economia, finanza-pubblica
status: active
dataset_slug: irpef_comunale
discussion: {discussion or 88}
---
# IRPEF Comunale
Content...
"""
    elif slug == "aifa-spesa-consumo":
        return """---
title: AIFA Spesa farmaceutica 2018-2024
description: Spesa farmaci
date: 2026-05-24
topics: sanita
status: active
dataset_slug: aifa_spesa_consumo
---
# AIFA Spesa
Content...
"""
    return ""


def test_render_topic_index_v3_with_analyses():
    """Topic index v3 includes analyses and analyses_by_dataset."""
    config = _cfg(repos=["repo1", "dataciviclab"])
    gh = make_github_mock()

    # Discovery via directory listing (no active.md needed)
    gh.list_directory.return_value = ["irpef-comunale", "aifa-spesa-consumo"]

    def _raw_file_side_effect(repo, path, ref="main"):
        if path == "registry/clean_catalog.json":
            return sample_di_clean_catalog_json()
        if repo == "dataciviclab" and path.startswith("analisi/") and path.endswith("/README.md"):
            slug = path.split("/")[1]
            disc = 88 if slug == "irpef-comunale" else None
            return _sample_analysis_readme(slug, discussion=disc)
        return None

    gh.get_raw_file.side_effect = _raw_file_side_effect
    result = _r(config, gh=gh).render_topic_index()

    assert result["schema_version"] == 3
    assert "analyses" in result
    assert "analyses_by_dataset" in result

    # Check analyses content
    analyses = result["analyses"]
    assert len(analyses) == 2

    irpef = next(a for a in analyses if a["slug"] == "irpef-comunale")
    assert irpef["name"] == "IRPEF Comunale 2019-2023"
    assert irpef["datasets"] == ["irpef_comunale"]
    assert irpef["discussion"] == 88
    assert irpef["status"] == "active"
    assert "issue" not in irpef  # None → omitted

    aifa = next(a for a in analyses if a["slug"] == "aifa-spesa-consumo")
    assert aifa["name"] == "AIFA Spesa farmaceutica 2018-2024"
    assert aifa["datasets"] == ["aifa_spesa_consumo"]
    assert "discussion" not in aifa  # None → omitted
    assert "issue" not in aifa

    # Check reverse lookup
    abd = result["analyses_by_dataset"]
    assert abd["irpef_comunale"] == ["irpef-comunale"]
    assert abd["aifa_spesa_consumo"] == ["aifa-spesa-consumo"]


def test_render_topic_index_v2_when_no_analyses():
    """Topic index stays v2 when dataciviclab data is unavailable."""
    config = _cfg(repos=["repo1"])
    gh = make_github_mock(raw_file=sample_di_clean_catalog_json())

    def _raw_file_side_effect(repo, path, ref="main"):
        if path == "registry/clean_catalog.json":
            return sample_di_clean_catalog_json()
        return None

    gh.get_raw_file.side_effect = _raw_file_side_effect
    result = _r(config, gh=gh).render_topic_index()

    assert result["schema_version"] == 2
    assert "analyses" not in result
    assert "analyses_by_dataset" not in result
