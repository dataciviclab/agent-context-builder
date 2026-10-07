"""Navigation graph builders for topic_index.json (schema v7).

Pure functions: no I/O. Input is the flat dataset list + themes + repo info;
output are the navigation sections consumed by MCP tools and dashboards.

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
        }

    return {
        "by_repo": {k: sorted(v) for k, v in sorted(by_repo.items())},
        "by_domain": {k: sorted(v) for k, v in sorted(by_domain.items())},
        "by_slug": by_slug,
    }


def flatten_datasets(datasets_by_source: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Flatten topic_index ``datasets`` dict into a list of dataset entries."""
    flat: list[dict[str, Any]] = []
    for _source, items in (datasets_by_source or {}).items():
        for item in items or []:
            if isinstance(item, dict) and item.get("slug"):
                flat.append(item)
    return flat


# ── Query helpers (work on a built topic_index dict) ─────────────────────────


def _norm(text: str | None) -> str:
    return (text or "").strip().lower()


def _word_match(query: str, text: str | None) -> bool:
    import re

    words = _norm(query).split()
    text_lower = _norm(text)
    if not words:
        return False
    for word in words:
        if not re.search(r"\b" + re.escape(word) + r"\b", text_lower):
            return False
    return True


def _score_entity(query: str, fields: list[tuple[str | None, str]]) -> int:
    """Score an entity against a query. fields: (value, weight_name)."""
    q = _norm(query)
    if not q:
        return 0
    score = 0
    for value, kind in fields:
        v = _norm(value)
        if not v:
            continue
        if v == q:
            score = max(score, {"slug": 100, "name": 80, "text": 40, "tag": 30}.get(kind, 20))
        elif q in v:
            score = max(score, {"slug": 80, "name": 60, "text": 30, "tag": 25}.get(kind, 15))
        elif _word_match(query, value):
            score = max(score, {"slug": 50, "name": 55, "text": 35, "tag": 28}.get(kind, 18))
    return score


def search_index(
    topic_index: dict[str, Any],
    query: str,
    entity_type: str | None = None,
    domain: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Ranked cross-entity search over a topic_index dict.

    entity_type: dataset | repo | domain | source | analysis | None (all)
    Returns items: {type, slug, name, parent_repo, parent_domain, score, stage?}
    """
    results: list[dict[str, Any]] = []
    type_filter = entity_type.lower() if entity_type else None

    by_slug = topic_index.get("by_slug") or {}
    datasets_by_source = topic_index.get("datasets") or {}

    # Datasets — use by_slug if present, else scan datasets
    dataset_entries: list[dict[str, Any]] = []
    if by_slug:
        for slug, meta in by_slug.items():
            dataset_entries.append(
                {
                    "slug": slug,
                    "name": meta.get("name") or slug,
                    "stage": meta.get("stage"),
                    "source_id": meta.get("source_id"),
                    "registry_source": meta.get("registry_source") or "",
                    "domain": meta.get("domain"),
                    "category": meta.get("category"),
                }
            )
    else:
        dataset_entries = flatten_datasets(datasets_by_source)

    if type_filter in (None, "dataset", "datasets"):
        for ds in dataset_entries:
            score = _score_entity(
                query,
                [
                    (ds.get("slug"), "slug"),
                    (ds.get("name"), "name"),
                    (ds.get("source_id"), "tag"),
                    (ds.get("category"), "tag"),
                    (ds.get("registry_source"), "tag"),
                ],
            )
            if score <= 0:
                continue
            d_domain = ds.get("domain")
            if domain and d_domain != domain:
                continue
            results.append(
                {
                    "type": "dataset",
                    "slug": ds.get("slug"),
                    "name": ds.get("name"),
                    "parent_repo": ds.get("registry_source") or "",
                    "parent_domain": d_domain,
                    "stage": ds.get("stage"),
                    "score": score,
                }
            )

    if type_filter in (None, "repo", "repos"):
        for repo, card in (topic_index.get("repos") or {}).items():
            if not isinstance(card, dict):
                continue
            score = _score_entity(
                query,
                [
                    (repo, "slug"),
                    (card.get("description"), "text"),
                    (card.get("role"), "tag"),
                    (card.get("domain"), "tag"),
                ],
            )
            if score <= 0:
                continue
            if domain and card.get("domain") != domain:
                continue
            results.append(
                {
                    "type": "repo",
                    "slug": repo,
                    "name": repo,
                    "parent_repo": repo,
                    "parent_domain": card.get("domain"),
                    "role": card.get("role"),
                    "n_datasets": card.get("n_datasets"),
                    "score": score,
                }
            )

    if type_filter in (None, "domain", "domains", "theme", "themes"):
        domains = topic_index.get("domains") or topic_index.get("explorer_themes") or []
        for dom in domains:
            if not isinstance(dom, dict):
                continue
            score = _score_entity(
                query,
                [
                    (dom.get("slug"), "slug"),
                    (dom.get("name"), "name"),
                    (dom.get("description"), "text"),
                ],
            )
            if score <= 0:
                continue
            if domain and dom.get("slug") != domain:
                continue
            results.append(
                {
                    "type": "domain",
                    "slug": dom.get("slug"),
                    "name": dom.get("name"),
                    "parent_repo": "",
                    "parent_domain": dom.get("slug"),
                    "dataset_count": dom.get("dataset_count") or len(dom.get("datasets") or []),
                    "score": score,
                }
            )

    if type_filter in (None, "analysis", "analyses"):
        for a in topic_index.get("analyses") or []:
            score = _score_entity(
                query,
                [
                    (a.get("slug"), "slug"),
                    (a.get("name"), "name"),
                    (a.get("description"), "text"),
                    (a.get("source"), "tag"),
                ],
            )
            if score <= 0:
                continue
            results.append(
                {
                    "type": "analysis",
                    "slug": a.get("slug"),
                    "name": a.get("name"),
                    "parent_repo": "",
                    "parent_domain": None,
                    "datasets": a.get("datasets") or [],
                    "score": score,
                }
            )

    if type_filter in (None, "source", "sources"):
        source_counts: dict[str, int] = {}
        for ds in dataset_entries:
            sid = ds.get("source_id") or ""
            if sid:
                source_counts[sid] = source_counts.get(sid, 0) + 1
        for sid, count in source_counts.items():
            score = _score_entity(query, [(sid, "slug")])
            if score <= 0:
                continue
            results.append(
                {
                    "type": "source",
                    "slug": sid,
                    "name": sid,
                    "parent_repo": "",
                    "parent_domain": None,
                    "n_datasets": count,
                    "score": score,
                }
            )

    results.sort(key=lambda r: (-r.get("score", 0), r.get("slug") or ""))
    return results[: max(limit, 1)]


def lab_map_summary(topic_index: dict[str, Any], domain: str | None = None) -> dict[str, Any]:
    """Compact navigation tree: domains → repos → sources."""
    repos = topic_index.get("repos") or {}
    domains = topic_index.get("domains") or []
    by_domain = topic_index.get("by_domain") or {}
    by_repo = topic_index.get("by_repo") or {}
    by_slug = topic_index.get("by_slug") or {}

    total_datasets = (
        sum(len(v) for v in by_repo.values()) if by_repo else sum(len(v) for v in by_slug.values())
    )
    published = sum(1 for m in by_slug.values() if m.get("stage") == "published")

    domain_nodes: list[dict[str, Any]] = []
    selected = [d for d in domains if not domain or d.get("slug") == domain]
    for d in selected:
        domain_nodes.append(
            {
                "slug": d.get("slug"),
                "name": d.get("name"),
                "description": d.get("description", ""),
                "dataset_count": d.get("dataset_count") or len(d.get("datasets") or []),
                "repos": d.get("repos") or [],
            }
        )

    repo_nodes: list[dict[str, Any]] = []
    for name, card in sorted(repos.items()):
        if not isinstance(card, dict):
            continue
        if domain and card.get("domain") != domain:
            continue
        repo_nodes.append(
            {
                "repo": name,
                "role": card.get("role"),
                "domain": card.get("domain"),
                "n_datasets": card.get("n_datasets") or len(by_repo.get(name) or []),
                "n_published": card.get("n_published", 0),
                "sources": card.get("sources") or [],
            }
        )

    sources: dict[str, int] = {}
    if domain:
        ds_slugs = by_domain.get(domain) or []
        for slug in ds_slugs:
            sid = (by_slug.get(slug) or {}).get("source_id") or ""
            if sid:
                sources[sid] = sources.get(sid, 0) + 1
    else:
        for meta in by_slug.values():
            sid = meta.get("source_id") or ""
            if sid:
                sources[sid] = sources.get(sid, 0) + 1

    return {
        "domains": domain_nodes,
        "repos": repo_nodes,
        "sources": dict(sorted(sources.items(), key=lambda x: (-x[1], x[0]))),
        "totals": {
            "repos": len(repo_nodes),
            "domains": len(domain_nodes),
            "datasets": total_datasets,
            "published": published,
            "analyses": len(topic_index.get("analyses") or []),
        },
        "ok": True,
    }


def explore_ref(topic_index: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve any Lab entity (repo, dataset, domain, source, analysis)."""
    ref_l = (ref or "").strip().lower()
    result: dict[str, Any] = {"ref": ref, "found": False}

    by_slug = topic_index.get("by_slug") or {}
    datasets_by_source = topic_index.get("datasets") or {}
    repos = topic_index.get("repos") or {}
    domains = topic_index.get("domains") or topic_index.get("explorer_themes") or []
    analyses = topic_index.get("analyses") or []
    analyses_by_dataset = topic_index.get("analyses_by_dataset") or {}
    by_repo = topic_index.get("by_repo") or {}
    by_domain = topic_index.get("by_domain") or {}

    def _dataset_card(slug: str) -> dict[str, Any] | None:
        meta = by_slug.get(slug)
        if meta is None:
            # scan datasets grouped by source
            for items in datasets_by_source.values():
                for item in items or []:
                    if item.get("slug") == slug:
                        meta = {
                            "name": item.get("name") or slug,
                            "stage": item.get("stage"),
                            "source_id": item.get("source_id"),
                            "registry_source": item.get("registry_source") or "",
                            "domain": None,
                            "category": item.get("category"),
                        }
                        break
                if meta is not None:
                    break
        if meta is None:
            return None
        return {
            "type": "dataset",
            "slug": slug,
            "name": meta.get("name") or slug,
            "stage": meta.get("stage"),
            "source_id": meta.get("source_id"),
            "registry_source": meta.get("registry_source") or "",
            "domain": meta.get("domain"),
            "category": meta.get("category"),
            "analyses": analyses_by_dataset.get(slug) or [],
        }

    # Dataset
    ds_card = _dataset_card(ref)
    if ds_card is not None:
        result.update(ds_card)
        result["found"] = True
        repo = ds_card.get("registry_source") or ""
        if repo and repo in repos:
            card = repos[repo]
            result["repo"] = {
                "name": repo,
                "role": card.get("role") if isinstance(card, dict) else None,
                "domain": card.get("domain") if isinstance(card, dict) else None,
                "url": card.get("url") if isinstance(card, dict) else "",
            }
        return result

    # Repo
    repo_key = ref if ref in repos else None
    if repo_key is None:
        for name in repos:
            if name.lower() == ref_l:
                repo_key = name
                break
    if repo_key is not None:
        card = repos[repo_key] if isinstance(repos[repo_key], dict) else {}
        ds_slugs = by_repo.get(repo_key) or []
        result.update(
            {
                "type": "repo",
                "slug": repo_key,
                "name": repo_key,
                "role": card.get("role"),
                "domain": card.get("domain"),
                "description": card.get("description", ""),
                "url": card.get("url", ""),
                "n_datasets": card.get("n_datasets") or len(ds_slugs),
                "n_published": card.get("n_published", 0),
                "sources": card.get("sources") or [],
                "datasets": ds_slugs[:50],
                "found": True,
            }
        )
        return result

    # Domain
    domain_key = None
    for d in domains:
        slug = d.get("slug") if isinstance(d, dict) else None
        if slug and slug.lower() == ref_l:
            domain_key = d
            break
    if domain_key is not None:
        slug = domain_key.get("slug")
        ds_slugs = domain_key.get("datasets") or by_domain.get(slug) or []
        result.update(
            {
                "type": "domain",
                "slug": slug,
                "name": domain_key.get("name"),
                "description": domain_key.get("description", ""),
                "repos": domain_key.get("repos") or [],
                "datasets": ds_slugs[:50],
                "dataset_count": domain_key.get("dataset_count") or len(ds_slugs),
                "found": True,
            }
        )
        return result

    # Source (source_id)
    source_ds: list[str] = []
    for source_key, items in datasets_by_source.items():
        if source_key.lower() == ref_l:
            for item in items or []:
                if item.get("slug"):
                    source_ds.append(item["slug"])
            result.update(
                {
                    "type": "source",
                    "slug": source_key,
                    "name": source_key,
                    "n_datasets": len(source_ds),
                    "datasets": source_ds[:50],
                    "found": True,
                }
            )
            return result
    for slug, meta in by_slug.items():
        sid = meta.get("source_id") or ""
        if sid and sid.lower() == ref_l:
            source_ds.append(slug)
    if source_ds:
        result.update(
            {
                "type": "source",
                "slug": ref,
                "name": ref,
                "n_datasets": len(source_ds),
                "datasets": sorted(source_ds)[:50],
                "found": True,
            }
        )
        return result

    # Analysis
    for a in analyses:
        if (a.get("slug") or "").lower() == ref_l:
            result.update(
                {
                    "type": "analysis",
                    "slug": a.get("slug"),
                    "name": a.get("name"),
                    "status": a.get("status"),
                    "description": a.get("description", ""),
                    "source": a.get("source", ""),
                    "period": a.get("period"),
                    "datasets": a.get("datasets") or [],
                    "found": True,
                }
            )
            return result

    return result
