"""Workspace triage rendering helpers."""

from __future__ import annotations

from typing import Any

from .config import Config
from .discussions import Discussion, DiscussionCollector
from .git_local import GitLocalCollector, GitState
from .github import PR, GitHubCollector
from .signals import DIRegistry
from .sources.de import DataExplorerFetcher
from .sources.registry import RegistryFetcher
from .sources.so import SourceObservatoryFetcher


def build_workspace_triage(
    config: Config,
    github_collector: GitHubCollector,
    git_collector: GitLocalCollector,
    discussion_collector: DiscussionCollector | None,
    fixed_timestamp: str,
    so_fetcher: SourceObservatoryFetcher | None = None,
    de_fetcher: DataExplorerFetcher | None = None,
    registry_fetcher: RegistryFetcher | None = None,
) -> dict[str, Any]:
    """Build the workspace_triage.json payload — actionable items only.

    Issues and discussions are filtered to exclude automated/non-actionable
    items (e.g. "analisi: XXX — nuovo dataset pubblicato", old presentazioni).
    """
    prs = github_collector.get_prs(config.repos)
    issues = github_collector.get_issues(config.repos)
    repos_state = git_collector.get_repos_state(config.repos)

    discussions: list[Discussion] = []
    disc_errors: dict[str, str] = {}
    if discussion_collector is not None:
        discussions = discussion_collector.get_discussions(config.repos)
        disc_errors = discussion_collector.fetch_errors

    so_fetcher = so_fetcher or SourceObservatoryFetcher(github_collector)
    de_fetcher = de_fetcher or DataExplorerFetcher(github_collector)
    registry_fetcher = registry_fetcher or RegistryFetcher(github_collector)

    # Filter to actionable only
    actionable_prs = [pr for pr in prs if pr.actionable]
    actionable_issues = [issue for issue in issues if issue.actionable]
    actionable_discussions = [d for d in discussions if d.actionable]

    return {
        "generated_at": fixed_timestamp,
        "workspace_root": str(config.workspace_root) if config.workspace_root else None,
        "repos": config.repos,
        "open_prs": len(actionable_prs) if not github_collector.fetch_errors else None,
        "prs": [_serialize_pr(pr) for pr in actionable_prs],
        "open_issues": len(actionable_issues) if not github_collector.fetch_errors else None,
        "issues": [_serialize_issue(issue) for issue in actionable_issues],
        "open_discussions": (
            len(actionable_discussions)
            if discussion_collector is not None and not disc_errors
            else None
        ),
        "discussions": [_serialize_discussion(d) for d in actionable_discussions],
        "github_fetch_errors": {**github_collector.fetch_errors, **disc_errors},
        "git_state": _serialize_git_state(repos_state),
        "warnings": _collect_warnings(github_collector, prs, repos_state),
        "radar": _build_radar_dict(so_fetcher),
        "source_health": _build_source_health_dict(so_fetcher, github_collector),
        "pipeline_state": _build_pipeline_state_dict(registry_fetcher, github_collector),
        "registry_summary": _build_registry_summary_dict(registry_fetcher, config.repos),
        "explorer": _build_explorer_dict(de_fetcher),
    }


def _serialize_pr(pr: PR) -> dict[str, Any]:
    return {
        "number": pr.number,
        "title": pr.title,
        "repo": pr.repo,
        "url": pr.url,
        "category": pr.category,
    }


def _serialize_issue(issue: Any) -> dict[str, Any]:
    return {
        "number": issue.number,
        "title": issue.title,
        "repo": issue.repo,
        "url": issue.url,
        "category": issue.category,
    }


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
        "persistent_red": radar.persistent_red,
        "unhealthy": [
            {
                "id": s.id,
                "status": s.status,
                "protocol": s.protocol,
                "http_code": s.http_code,
                "note": s.note,
                "red_streak": s.red_streak,
            }
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
    fetcher: RegistryFetcher,
    github_collector: GitHubCollector,
) -> dict[str, Any]:
    """Build pipeline_state from the dataset-incubator registry signals.

    The registry.json embeds the same signals that the legacy
    pipeline_signals.json projection exposed (id/status/detail/action).
    """
    registry = fetcher.fetch_repo("dataset-incubator")
    if registry is None:
        return {
            "available": False,
            "errors": {k: v for k, v in github_collector.fetch_errors.items() if "registry" in k},
        }
    signals = registry.signals
    by_status: dict[str, int] = {}
    for s in signals:
        status = s.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    actionable = [
        {
            "id": s.get("id", ""),
            "status": s.get("status", ""),
            "detail": s.get("detail", ""),
            "action": s.get("action", ""),
        }
        for s in signals
        if s.get("status") in ("warn", "error")
    ]
    return {
        "available": True,
        "generated_at": registry.updated_at,
        "summary": {"total": len(signals), "by_status": by_status},
        "actionable": actionable,
    }


def _build_registry_summary_dict(
    fetcher: RegistryFetcher,
    repos: list[str],
) -> list[dict[str, Any]]:
    """Build the registry_summary block — per-repo registry orientation.

    Cross-repo view over every configured repo's registry.json: section
    counts, GCS availability and freshness. Repos without a registry (not
    yet migrated) are reported as available=False.
    """
    registries = fetcher.fetch(repos)
    return [_registry_summary_item(repo, reg) for repo, reg in registries.items()]


def _registry_summary_item(repo: str, registry: DIRegistry | None) -> dict[str, Any]:
    """Serialize a single repo registry into the compact summary entry."""
    if registry is None:
        return {
            "repo": repo,
            "available": False,
            "source_repo": "",
            "updated_at": "",
            "datasets": 0,
            "marts": 0,
            "signals": 0,
            "codelists": 0,
            "entities": 0,
            "gcs": 0,
            "reason": "registry_not_found",
        }
    return {
        "repo": repo,
        "available": True,
        "source_repo": registry.name,
        "updated_at": registry.updated_at,
        "datasets": len(registry.datasets),
        "marts": registry.marts,
        "signals": len(registry.signals),
        "codelists": registry.codelists,
        "entities": registry.entities,
        "gcs": registry.gcs,
        "reason": "",
    }


def _build_explorer_dict(
    de_fetcher: DataExplorerFetcher,
) -> dict[str, Any]:
    """Build explorer state block for workspace_triage.json.

    Uses the committed data-explorer editorial catalog (datasets.json +
    themes.json): themes with dataset counts, themed dataset count, and the
    gap — published datasets with no theme (not exposed on explorer yet).
    Includes last deploy status from GitHub Actions API.
    """
    catalog = de_fetcher.fetch_explorer_catalog()
    if catalog is None:
        return {"available": False}

    themed_slugs: set[str] = set()
    for theme in catalog.themes:
        themed_slugs.update(theme.datasets)

    # Deploy status (operativo — GitHub Actions API)
    deploy: dict[str, Any] | None = None
    raw_deploy = de_fetcher.fetch_deploy_status()
    if raw_deploy is not None:
        deploy = {
            "run_id": raw_deploy.get("run_id"),
            "name": raw_deploy.get("name", ""),
            "status": raw_deploy.get("status", ""),
            "conclusion": raw_deploy.get("conclusion"),
            "completed_at": raw_deploy.get("completed_at", ""),
            "html_url": raw_deploy.get("html_url", ""),
        }

    return {
        "available": True,
        "themes": [
            {"slug": t.slug, "name": t.name, "dataset_count": len(t.datasets)}
            for t in catalog.themes
        ],
        "published_count": len(themed_slugs),
        "clean_ready_not_published": catalog.without_theme,
        "last_deploy": deploy,
    }


def _collect_warnings(
    github_collector: GitHubCollector,
    prs: list[PR],
    repos_state: dict[str, GitState],
) -> list[str]:
    warnings = [
        f"GitHub fetch failed — {key}: {err}" for key, err in github_collector.fetch_errors.items()
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
