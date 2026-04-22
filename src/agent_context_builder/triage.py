"""Workspace triage rendering helpers."""

from __future__ import annotations

from typing import Any

from .config import Config
from .discussions import Discussion, DiscussionCollector
from .git_local import GitLocalCollector, GitState
from .github import GitHubCollector, PR
from .sources.di import DatasetIncubatorFetcher
from .sources.so import SourceObservatoryFetcher


def build_workspace_triage(
    config: Config,
    github_collector: GitHubCollector,
    git_collector: GitLocalCollector,
    discussion_collector: DiscussionCollector | None,
    fixed_timestamp: str,
    so_fetcher: SourceObservatoryFetcher | None = None,
    di_fetcher: DatasetIncubatorFetcher | None = None,
) -> dict[str, Any]:
    """Build the workspace_triage.json payload."""
    prs = github_collector.get_prs(config.repos)
    issues = github_collector.get_issues(config.repos)
    repos_state = git_collector.get_repos_state(config.repos)

    discussions: list[Discussion] = []
    disc_errors: dict[str, str] = {}
    if discussion_collector is not None:
        discussions = discussion_collector.get_discussions(config.repos)
        disc_errors = discussion_collector.fetch_errors

    so_fetcher = so_fetcher or SourceObservatoryFetcher(github_collector)
    di_fetcher = di_fetcher or DatasetIncubatorFetcher(github_collector)

    return {
        "generated_at": fixed_timestamp,
        "workspace_root": str(config.workspace_root) if config.workspace_root else None,
        "repos": config.repos,
        "open_prs": len(prs) if not github_collector.fetch_errors else None,
        "prs": [_serialize_pr(pr) for pr in prs],
        "open_issues": len(issues) if not github_collector.fetch_errors else None,
        "issues": [_serialize_issue(issue) for issue in issues],
        "open_discussions": (
            len(discussions) if discussion_collector is not None and not disc_errors else None
        ),
        "discussions": [_serialize_discussion(d) for d in discussions],
        "github_fetch_errors": {**github_collector.fetch_errors, **disc_errors},
        "git_state": _serialize_git_state(repos_state),
        "warnings": _collect_warnings(github_collector, prs, repos_state),
        "radar": _build_radar_dict(so_fetcher),
        "source_health": _build_source_health_dict(so_fetcher, github_collector),
        "pipeline_state": _build_pipeline_state_dict(di_fetcher, github_collector),
        "dataset_catalog": _build_dataset_catalog_dict(di_fetcher, github_collector),
        "portal_scout": _build_portal_scout_dict(so_fetcher),
    }


def _serialize_pr(pr: PR) -> dict[str, Any]:
    return {"number": pr.number, "title": pr.title, "repo": pr.repo, "url": pr.url}


def _serialize_issue(issue: Any) -> dict[str, Any]:
    return {"number": issue.number, "title": issue.title, "repo": issue.repo, "url": issue.url}


def _serialize_discussion(discussion: Discussion) -> dict[str, Any]:
    return {
        "number": discussion.number,
        "title": discussion.title,
        "repo": discussion.repo,
        "url": discussion.url,
        "category": discussion.category,
    }


def _serialize_git_state(repos_state: dict[str, GitState]) -> dict[str, Any]:
    return {
        repo: {
            "available": state.available,
            "reason": state.reason,
            "dirty": state.dirty,
            "current_branch": state.current_branch,
            "branches_ahead": state.branches_ahead,
            "untracked_files": state.untracked_files,
        }
        for repo, state in repos_state.items()
    }


def _build_radar_dict(fetcher: SourceObservatoryFetcher) -> dict[str, Any]:
    radar = fetcher.fetch_radar_summary()
    if radar is None:
        return {"available": False}
    return {
        "available": True,
        "probe_date": radar.probe_date,
        "sources_total": radar.sources_total,
        "green": radar.green,
        "yellow": radar.yellow,
        "red": radar.red,
        "unhealthy": [
            {"id": s.id, "status": s.status, "protocol": s.protocol, "http_code": s.http_code}
            for s in radar.unhealthy
        ],
    }


def _build_source_health_dict(
    fetcher: SourceObservatoryFetcher,
    github_collector: GitHubCollector,
) -> dict[str, Any]:
    so = fetcher.fetch_catalog_signals()
    if so is None:
        return {
            "available": False,
            "errors": {
                k: v for k, v in github_collector.fetch_errors.items() if "source-observatory" in k
            },
        }
    return {
        "available": True,
        "captured_at": so.captured_at,
        "sources_checked": so.sources_checked,
        "regressions": [
            {
                "source": s.source,
                "protocol": s.protocol,
                "detail": s.detail,
                "suggested_action": s.suggested_action,
            }
            for s in so.regressions
        ],
        "alerts": [
            {
                "source": s.source,
                "protocol": s.protocol,
                "signal_type": s.signal_type,
                "result": s.result,
                "detail": s.detail,
                "suggested_action": s.suggested_action,
            }
            for s in so.alerts
        ],
    }


def _build_pipeline_state_dict(
    fetcher: DatasetIncubatorFetcher,
    github_collector: GitHubCollector,
) -> dict[str, Any]:
    di = fetcher.fetch_pipeline_signals()
    if di is None:
        return {
            "available": False,
            "errors": {
                k: v for k, v in github_collector.fetch_errors.items() if "dataset-incubator" in k
            },
        }
    return {
        "available": True,
        "generated_at": di.generated_at,
        "summary": di.summary,
        "actionable": [
            {"id": s.id, "status": s.status, "detail": s.detail, "action": s.action}
            for s in di.actionable
        ],
    }


def _build_dataset_catalog_dict(
    fetcher: DatasetIncubatorFetcher,
    github_collector: GitHubCollector,
) -> dict[str, Any]:
    catalog = fetcher.fetch_clean_catalog()
    if catalog is None:
        return {
            "available": False,
            "errors": {
                k: v for k, v in github_collector.fetch_errors.items() if "clean_catalog" in k
            },
        }
    return {
        "available": True,
        "schema_version": catalog.schema_version,
        "name": catalog.name,
        "updated_at": catalog.updated_at,
        "summary": {
            "total": len(catalog.datasets),
            "clean_ready": len(catalog.clean_ready),
            "public": sum(1 for d in catalog.clean_ready if d.visibility == "public"),
        },
        "datasets": [
            {
                "slug": d.slug,
                "name": d.name,
                "status": d.status,
                "visibility": d.visibility,
                "period": d.period,
                "location": d.location,
                "metric_columns": d.metric_columns,
                "dimension_columns": d.dimension_columns,
                "column_count": d.column_count,
            }
            for d in catalog.datasets
        ],
    }


def _build_portal_scout_dict(fetcher: SourceObservatoryFetcher) -> dict[str, Any]:
    scout = fetcher.fetch_portal_scout()
    if scout is None:
        return {"available": False}
    return {
        "available": True,
        "generated_at": scout.generated_at,
        "total_portals": scout.total_portals,
        "new_candidates": scout.new_candidates,
        "new_confirmed_protocol": scout.new_confirmed_protocol,
        "by_protocol": scout.by_protocol,
        "new_structured": [
            {"domain": c.domain, "protocol": c.protocol} for c in scout.new_structured
        ],
    }


def _collect_warnings(
    github_collector: GitHubCollector,
    prs: list[PR],
    repos_state: dict[str, GitState],
) -> list[str]:
    warnings = [
        f"GitHub fetch failed — {key}: {err}"
        for key, err in github_collector.fetch_errors.items()
    ]
    if len(prs) > 5:
        warnings.append(f"Many open PRs: {len(prs)}")
    for repo, state in repos_state.items():
        if state.available:
            if state.dirty:
                warnings.append(f"{repo}: dirty ({state.untracked_files} untracked)")
            if state.branches_ahead:
                warnings.append(f"{repo}: ahead on {', '.join(state.branches_ahead)}")
    return warnings
