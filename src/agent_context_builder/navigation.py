"""Navigation graph builders for topic_index.json (schema v7).

Pure functions: no I/O. Input is the flat dataset list + themes + repo info;
output are the navigation sections consumed by dashboards and by the
dcl-mcp server (query-side: search/lab_map/explore — migrated to
dataciviclab/dcl-mcp with the MCP server).

Hierarchy:

    domain (editorial theme)
      └── repo (ownership unit)
            └── source (external origin)
                  └── dataset (artifact)
                        └── analysis / signal
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .sources.explorer import ExplorerTheme

# Repo roles (AGENTS.md §2 map). Everything else defaults to "dati".
REPO_ROLES: dict[str, str] = {
    "toolkit": "infra",
    "lab-connectors": "infra",
    "dataset-incubator": "infra",
    "agent-context-builder": "infra",
    "lab-ops": "infra",
    "lab-dashboard": "infra",
    "source-observatory": "osservatorio",
    "data-explorer": "editoriale",
    "dataciviclab": "editoriale",
}

_DEFAULT_ROLE = "dati"


def category_to_domain(themes: list[ExplorerTheme]) -> dict[str, str]:
    """Map dataset ``category`` → domain slug from editorial themes."""
    mapping: dict[str, str] = {}
    for theme in themes:
        for cat in theme.categories:
            mapping[cat] = theme.slug
    return mapping


def dataset_domain(category: str | None, cat_map: dict[str, str]) -> str | None:
    if not category:
        return None
    return cat_map.get(category)


def build_domains(
    themes: list[ExplorerTheme],
    flat_datasets: list[dict[str, Any]],
    cat_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Build domains[] with linked repos and dataset counts."""
    ds_by_domain: dict[str, list[str]] = defaultdict(list)
    repos_by_domain: dict[str, set[str]] = defaultdict(set)
    seen_by_domain: dict[str, set[str]] = defaultdict(set)
    for ds in flat_datasets:
        domain = dataset_domain(ds.get("category"), cat_map)
        if not domain:
            continue
        slug = ds["slug"]
        if slug not in seen_by_domain[domain]:
            seen_by_domain[domain].add(slug)
            ds_by_domain[domain].append(slug)
        repo = ds.get("registry_source") or ""
        if repo:
            repos_by_domain[domain].add(repo)

    domains: list[dict[str, Any]] = []
    for theme in themes:
        domains.append(
            {
                "slug": theme.slug,
                "name": theme.name,
                "description": theme.description,
                "icon": theme.icon,
                "categories": theme.categories,
                "repos": sorted(repos_by_domain.get(theme.slug, [])),
                "datasets": sorted(ds_by_domain.get(theme.slug, [])),
                "dataset_count": len(ds_by_domain.get(theme.slug, [])),
            }
        )
    return domains


def build_explorer_themes(
    themes: list[ExplorerTheme],
    flat_datasets: list[dict[str, Any]],
    cat_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Compact themes for lab-dashboard Grafo (slug, name, datasets)."""
    ds_by_domain: dict[str, list[str]] = defaultdict(list)
    seen_by_domain: dict[str, set[str]] = defaultdict(set)
    for ds in flat_datasets:
        domain = dataset_domain(ds.get("category"), cat_map)
        if not domain:
            continue
        slug = ds["slug"]
        if slug not in seen_by_domain[domain]:
            seen_by_domain[domain].add(slug)
            ds_by_domain[domain].append(slug)
    result: list[dict[str, Any]] = []
    for theme in themes:
        result.append(
            {
                "slug": theme.slug,
                "name": theme.name,
                "datasets": sorted(ds_by_domain.get(theme.slug, [])),
            }
        )
    return result


def build_repo_cards(
    repos_info: dict[str, Any],
    flat_datasets: list[dict[str, Any]],
    cat_map: dict[str, str],
    config_repos: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Enrich repos section: role, domain, counts, sources."""
    by_repo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ds in flat_datasets:
        repo = ds.get("registry_source") or ""
        if repo:
            by_repo[repo].append(ds)

    names: list[str] = []
    seen: set[str] = set()
    for name in list(config_repos or []) + list(repos_info.keys()) + list(by_repo.keys()):
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    cards: dict[str, dict[str, Any]] = {}
    for name in names:
        info = repos_info.get(name)
        description = ""
        url = ""
        if info is not None:
            description = getattr(info, "description", "") or ""
            url = getattr(info, "url", "") or ""

        datasets = by_repo.get(name, [])
        n_published = sum(1 for d in datasets if d.get("stage") == "published")
        sources = sorted({d.get("source_id") or d.get("source") or "" for d in datasets} - {""})

        domain_counts: Counter[str] = Counter()
        for d in datasets:
            domain = dataset_domain(d.get("category"), cat_map)
            if domain:
                domain_counts[domain] += 1
        primary_domain = domain_counts.most_common(1)[0][0] if domain_counts else None

        cards[name] = {
            "description": description,
            "url": url,
            "role": REPO_ROLES.get(name, _DEFAULT_ROLE),
            "domain": primary_domain,
            "n_datasets": len(datasets),
            "n_published": n_published,
            "sources": sources,
        }
    return cards


def build_reverse_indexes(
    flat_datasets: list[dict[str, Any]],
    cat_map: dict[str, str],
) -> dict[str, Any]:
    """Precomputed lookups: by_repo, by_domain, by_slug."""
    by_repo: dict[str, list[str]] = defaultdict(list)
    by_domain: dict[str, list[str]] = defaultdict(list)
    seen_repo: dict[str, set[str]] = defaultdict(set)
    seen_domain: dict[str, set[str]] = defaultdict(set)
    by_slug: dict[str, dict[str, Any]] = {}

    for ds in flat_datasets:
        slug = ds["slug"]
        repo = ds.get("registry_source") or ""
        if repo and slug not in seen_repo[repo]:
            seen_repo[repo].add(slug)
            by_repo[repo].append(slug)
        domain = dataset_domain(ds.get("category"), cat_map)
        if domain and slug not in seen_domain[domain]:
            seen_domain[domain].add(slug)
            by_domain[domain].append(slug)
        by_slug[slug] = {
            "name": ds.get("name") or slug,
            "stage": ds.get("stage") or "incubating",
            "source_id": ds.get("source_id") or ds.get("source"),
            "registry_source": repo,
            "domain": domain,
            "category": ds.get("category"),
            # Discovery fields — kept in the projection so search works even
            # when only by_slug is present (backward-compatible additive).
            "tags": ds.get("tags"),
            "description": ds.get("description"),
        }

    return {
        "by_repo": {k: sorted(v) for k, v in sorted(by_repo.items())},
        "by_domain": {k: sorted(v) for k, v in sorted(by_domain.items())},
        "by_slug": by_slug,
    }
