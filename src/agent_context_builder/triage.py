"""Workspace triage rendering helpers."""

from __future__ import annotations

from typing import Any

from .config import Config
from .discussions import Discussion, DiscussionCollector
from .git_local import GitLocalCollector, GitState
from .github import PR, GitHubCollector
from .signals import DIRegistry
from .sources.registry import RegistryFetcher
from .sources.so import SourceObservatoryFetcher


def build_workspace_triage(
    config: Config,
    github_collector: GitHubCollector,
    git_collector: GitLocalCollector,
    discussion_collector: DiscussionCollector | None,
    fixed_timestamp: str,
    so_fetcher: SourceObservatoryFetcher | None = None,
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
        "generated_at": radar.generated_at,
        "probe_date": radar.probe_date,
        "sources_total": radar.sources_total,
        "green": radar.green,
        "yellow": radar.yellow,
        "red": radar.red,
        "persistent_red": radar.persistent_red,
        "sources": [
            {
                "id": s.id,
                "status": s.status,
                "protocol": s.protocol,
                "http_code": s.http_code,
                "note": s.note,
                "red_streak": s.red_streak,
            }
            for s in radar.sources
        ],
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
        by_status[s.status] = by_status.get(s.status, 0) + 1
    actionable = [
        {
            "id": s.id,
            "status": s.status,
            "detail": s.detail,
            "action": s.action,
        }
        for s in signals
        if s.status in ("warn", "error")
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
    # Compute GCS count from datasets with GCS location (non-empty path)
    gcs = sum(
        1
        for ds in registry.datasets
        if hasattr(ds, "location")
        and getattr(ds.location, "type", "") == "gcs"
        and getattr(ds.location, "path", "")
    )
    # codelists/entities may be dicts with nested structure — count inner items
    codelists = _count_section(registry.codelists, "codelists")
    entities = _count_section(registry.entities, "entities")

    # Signals with run details (for downstream dashboards)
    signals_detail = []
    for sig in registry.signals:
        sig_entry: dict[str, Any] = {
            "id": sig.id,
            "source_id": sig.source_id,
            "status": sig.status,
            "label": sig.label,
            "detail": sig.detail,
        }
        if sig.run is not None:
            sig_entry["run"] = {
                "run_id": sig.run.run_id,
                "year": sig.run.year,
                "status": sig.run.status,
                "started_at": sig.run.started_at,
                "finished_at": sig.run.finished_at,
            }
        signals_detail.append(sig_entry)

    result: dict[str, Any] = {
        "repo": repo,
        "available": True,
        "source_repo": registry.source_repo or registry.repo,
        "updated_at": registry.updated_at,
        "datasets": len(registry.datasets),
        "marts": len(registry.marts),
        "signals": len(registry.signals),
        "codelists": codelists,
        "entities": entities,
        "gcs": gcs,
        "reason": "",
    }
    if signals_detail:
        result["signals_detail"] = signals_detail
    return result


def _count_section(section: Any, inner_key: str) -> int:
    """Count entries in a registry section that may be a list or nested dict."""
    if isinstance(section, list):
        return len(section)
    if isinstance(section, dict):
        inner = section.get(inner_key)
        if isinstance(inner, (list, dict)):
            return len(inner)
    return 0


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
