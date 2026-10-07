"""Public MCP server — serves DataCivicLab context artifacts from the context branch.

Tools:
  session_bootstrap  — quick orientation (markdown)
  workspace_triage   — machine-readable state (compact + sections)
  lab_map            — navigation tree: domains → repos → sources
  find               — ranked cross-entity search (dataset/repo/domain/source/analysis)
  explore            — deep-dive any Lab entity by ref
  topic_index        — dataset/analysis exploration (resolve for deep-dive)
  search             — legacy cross-cutting search (wraps find + GitHub issues)
  refresh_context    — trigger CI rebuild (action)

Configuration:
  ACB_REPO       GitHub repo (default: dataciviclab/agent-context-builder)
  ACB_BRANCH     Branch where artifacts are published (default: context)
  GITHUB_TOKEN   Required only for refresh_context
  ACB_LOG_LEVEL  Logging level (default: INFO)
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from lab_connectors.http import HttpClient
from lab_connectors.mcp import create_mcp_server, get_mcp_logger, guard_timed

from .navigation import explore_ref, lab_map_summary, search_index

_REPO = os.environ.get("ACB_REPO", "dataciviclab/agent-context-builder")
_BRANCH = os.environ.get("ACB_BRANCH", "context")
_RAW_BASE = f"https://raw.githubusercontent.com/{_REPO}/{_BRANCH}"
_API_BASE = f"https://api.github.com/repos/{_REPO}"

_REFRESH_MIN_INTERVAL = 60
_last_refresh_attempt: float | None = None

_log = get_mcp_logger("agent-context-builder", level=os.environ.get("ACB_LOG_LEVEL", "INFO"))

mcp = create_mcp_server(
    name="dataciviclab-context",
    instructions=(
        "DataCivicLab context artifacts, generated from GitHub every 6 hours. "
        "Start with session_bootstrap for orientation, then lab_map for structure, "
        "find for discovery, explore for deep-dive, workspace_triage for state."
    ),
)


# ── Env / HTTP helpers ─────────────────────────────────────────────────────────
_ENV_LOADED = False


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip().strip('"').strip("'")
    return key, value


def _candidate_env_paths() -> list[Path]:
    explicit = os.environ.get("ACB_ENV_FILE", "").strip()
    paths: list[Path] = []
    if explicit:
        paths.append(Path(explicit).expanduser())
    starts = [Path.cwd(), Path(__file__).resolve()]
    for start in starts:
        current = start if start.is_dir() else start.parent
        paths.extend(parent / ".env" for parent in [current] + list(current.parents))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def _load_dotenv_if_present() -> bool:
    global _ENV_LOADED
    if _ENV_LOADED:
        return True
    _ENV_LOADED = True
    loaded = False
    for path in _candidate_env_paths():
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                parsed = _parse_env_line(line)
                if parsed is None:
                    continue
                key, value = parsed
                if key not in os.environ or not os.environ[key]:
                    os.environ[key] = value
                    loaded = True
        except OSError:
            continue
    return loaded


def _get_env(name: str) -> str | None:
    _load_dotenv_if_present()
    return os.environ.get(name) or None


_http: HttpClient | None = None


def _get_http() -> HttpClient:
    global _http
    if _http is None:
        _http = HttpClient(timeout=15)
    return _http


def _fetch(path: str, retries: int = 1, backoff: float = 1.0) -> str:
    url = f"{_RAW_BASE}/{path}"
    client = _get_http()
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            result = client.get(url)
        except Exception as exc:
            last_err = exc
            _log.warning("fetch", "exception", path=path, attempt=attempt, error=str(exc))
            if attempt < retries:
                time.sleep(backoff * (2**attempt))
            continue
        if result.is_ok and result.response is not None:
            return result.response.text
        last_err = Exception(
            f"HTTP {result.response.status_code if result.response else 'N/A'}: {result.err}"
        )
        _log.warning("fetch", "http_error", path=path, error=result.err)
        if attempt < retries:
            time.sleep(backoff * (2**attempt))
    raise last_err or Exception(f"Failed to fetch {path}")


# ── Tools ──────────────────────────────────────────────────────────────────────


@mcp.tool(
    description="Quick orientation — compact markdown overview of Lab state.",
    structured_output=True,
)
def session_bootstrap() -> dict[str, object]:
    def _exec() -> dict[str, object]:
        content = _fetch("session_bootstrap.md")
        return {"content": content, "format": "markdown", "ok": True}

    return guard_timed(_exec, "session_bootstrap")


@mcp.tool(
    description=(
        "Machine-readable Lab state. Default: compact summary. "
        "Use section= to get a specific part: radar, prs, issues, "
        "discussions, registry, git, warnings."
    ),
    structured_output=True,
)
def workspace_triage(section: str | None = None) -> dict[str, object]:
    def _exec() -> dict[str, object]:
        raw = _fetch("workspace_triage.json")
        data: dict = json.loads(raw)

        # Default: compact summary
        if section is None:
            radar = data.get("radar", {})
            registry = data.get("registry_summary", [])
            total_ds = sum(r.get("datasets", 0) for r in registry if r.get("available"))
            total_signals = sum(r.get("signals", 0) for r in registry if r.get("available"))
            return {
                "radar": {
                    "green": radar.get("green", 0),
                    "yellow": radar.get("yellow", 0),
                    "red": radar.get("red", 0),
                    "persistent_red": radar.get("persistent_red", 0),
                },
                "datasets": total_ds,
                "signals": total_signals,
                "repos_active": sum(1 for r in registry if r.get("available")),
                "prs": data.get("open_prs") or len(data.get("prs", [])),
                "issues": data.get("open_issues") or len(data.get("issues", [])),
                "discussions": data.get("open_discussions") or len(data.get("discussions", [])),
                "warnings": data.get("warnings", []),
                "ok": True,
            }

        # Section filter
        sections = {
            "radar": lambda d: d.get("radar", {}),
            "prs": lambda d: {"prs": d.get("prs", []), "count": len(d.get("prs", []))},
            "issues": lambda d: {"issues": d.get("issues", []), "count": len(d.get("issues", []))},
            "discussions": lambda d: {
                "discussions": d.get("discussions", []),
                "count": len(d.get("discussions", [])),
            },
            "registry": lambda d: {"registry_summary": d.get("registry_summary", [])},
            "git": lambda d: {"git_state": d.get("git_state", {})},
            "warnings": lambda d: {"warnings": d.get("warnings", [])},
            "pipeline": lambda d: {"pipeline_state": d.get("pipeline_state", {})},
            "source_health": lambda d: {"source_health": d.get("source_health", {})},
        }

        extractor = sections.get(section)
        if extractor is None:
            return {
                "ok": False,
                "error": f"Sezione '{section}' non valida. Opzioni: {list(sections.keys())}",
            }

        return {"content": extractor(data), "ok": True}

    return guard_timed(_exec, "workspace_triage")


def _load_topic_index() -> dict[str, Any]:
    raw = _fetch("topic_index.json")
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


@mcp.tool(
    description=(
        "Lab navigation map — domains → repos → sources. "
        "Use domain= to focus on one editorial theme."
    ),
    structured_output=True,
)
def lab_map(domain: str | None = None) -> dict[str, object]:
    def _exec() -> dict[str, object]:
        data = _load_topic_index()
        summary = lab_map_summary(data, domain=domain)
        return {"content": summary, "ok": True}

    return guard_timed(_exec, "lab_map")


@mcp.tool(
    description=(
        "Ranked search across datasets, repos, domains, sources, and analyses. "
        "Filters: type= (dataset|repo|domain|source|analysis), domain=, limit=. "
        "Returns type + parent pointers. Use explore(ref) for details."
    ),
    structured_output=True,
)
def find(
    query: str,
    type: str | None = None,
    domain: str | None = None,
    limit: int = 10,
    include_github: bool = False,
) -> dict[str, object]:
    def _exec() -> dict[str, object]:
        data = _load_topic_index()
        results = search_index(data, query, entity_type=type, domain=domain, limit=limit)
        payload: dict[str, Any] = {
            "query": query,
            "total": len(results),
            "results": results,
            "ok": True,
        }
        if include_github:
            token = _get_env("GITHUB_TOKEN")
            payload["issues"] = _search_github_issues(query, token, limit)
            payload["total"] += len(payload["issues"])
        return {"content": payload, "ok": True}

    return guard_timed(_exec, "find")


@mcp.tool(
    description=(
        "Deep-dive any Lab entity by ref: dataset slug, repo name, domain slug, "
        "source id, or analysis slug. Returns card + children + routing hints."
    ),
    structured_output=True,
)
def explore(ref: str) -> dict[str, object]:
    def _exec() -> dict[str, object]:
        data = _load_topic_index()
        card = explore_ref(data, ref)
        if not card.get("found"):
            # Fallback: try legacy topic_index resolve semantics
            result = _legacy_resolve(data, ref)
            card = {**card, **result}
        return {"content": card, "ok": True}

    return guard_timed(_exec, "explore")


def _legacy_resolve(data: dict[str, Any], resolve: str) -> dict[str, Any]:
    """Best-effort resolve matching old topic_index(resolve=) behaviour."""
    resolve_lower = resolve.lower()
    extra: dict[str, Any] = {}
    seen: set[str] = set()
    datasets_found: list[dict[str, Any]] = []
    for source, ds_list in (data.get("datasets") or {}).items():
        for ds in ds_list or []:
            slug = ds.get("slug", "")
            if slug.lower() == resolve_lower and slug not in seen:
                seen.add(slug)
                datasets_found.append(
                    {
                        "slug": slug,
                        "name": ds.get("name", ""),
                        "source": source,
                        "stage": ds.get("stage", "published"),
                    }
                )
            elif resolve_lower in {s.lower() for s in (ds.get("tags") or [])}:
                if slug not in seen:
                    seen.add(slug)
                    datasets_found.append(
                        {
                            "slug": slug,
                            "name": ds.get("name", ""),
                            "source": source,
                            "stage": ds.get("stage", "published"),
                        }
                    )
    if datasets_found:
        extra["datasets"] = datasets_found
        extra["found"] = True
    return extra


@mcp.tool(
    description=(
        "Dataset/analysis exploration (legacy). "
        "Without resolve: returns compact summary (counts by source, stage). "
        "With resolve (slug, name, or source): returns sub-graph with related entities. "
        "Prefer explore() and find() for navigation."
    ),
    structured_output=True,
)
def topic_index(resolve: str | None = None) -> dict[str, object]:
    def _exec() -> dict[str, object]:
        raw = _fetch("topic_index.json")
        data: dict = json.loads(raw)

        # Default: compact summary
        if not resolve:
            by_source: dict[str, int] = {}
            by_stage: dict[str, int] = {}
            for source, ds_list in data.get("datasets", {}).items():
                for ds in ds_list:
                    by_source[source] = by_source.get(source, 0) + 1
                    stage = ds.get("stage", "unknown")
                    by_stage[stage] = by_stage.get(stage, 0) + 1
            top_sources = sorted(by_source.items(), key=lambda x: -x[1])[:10]
            return {
                "total": sum(by_stage.values()),
                "by_stage": by_stage,
                "top_sources": {s: n for s, n in top_sources},
                "n_sources": len(by_source),
                "analyses": len(data.get("analyses", [])),
                "domains": len(data.get("domains", [])),
                "ok": True,
            }

        # Prefer navigation explore when schema v7 indexes are present
        if data.get("by_slug") or data.get("domains"):
            card = explore_ref(data, resolve)
            if card.get("found"):
                return {"content": card, "ok": True}

        # Resolve: sub-graph (legacy path)
        resolve_lower = resolve.lower()
        result: dict[str, Any] = {"resolve": resolve, "found": False}
        seen_slugs: set[str] = set()

        for source, ds_list in data.get("datasets", {}).items():
            for ds in ds_list:
                slug = ds.get("slug", "")
                if slug.lower() == resolve_lower and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    result.setdefault("datasets", []).append(
                        {
                            "slug": slug,
                            "name": ds.get("name", ""),
                            "source": source,
                            "period": ds.get("period"),
                            "stage": ds.get("stage", "published"),
                            "gcs_path": ds.get("location", {}).get("path", ""),
                        }
                    )
                    result["found"] = True

        for a in data.get("analyses", []):
            a_slug = a.get("slug", "")
            if a_slug.lower() == resolve_lower or resolve_lower in [
                d.lower() for d in a.get("datasets", [])
            ]:
                result.setdefault("analyses", []).append(
                    {
                        "slug": a_slug,
                        "name": a.get("name", ""),
                        "datasets": a.get("datasets", []),
                        "status": a.get("status", ""),
                    }
                )
                result["found"] = True

        entries = data.get("datasets", {})
        if resolve_lower in {s.lower() for s in entries}:
            for source, ds_list in entries.items():
                if source.lower() == resolve_lower:
                    result["found"] = True
                    for ds in ds_list:
                        slug = ds.get("slug", "")
                        if slug not in seen_slugs:
                            seen_slugs.add(slug)
                            result.setdefault("datasets", []).append(
                                {
                                    "slug": slug,
                                    "name": ds.get("name", ""),
                                    "source": source,
                                    "period": ds.get("period"),
                                    "stage": ds.get("stage", "published"),
                                }
                            )

        result["count"] = len(result.get("datasets", []))
        return {"content": result, "ok": True}

    return guard_timed(_exec, "topic_index")


@mcp.tool(
    description=(
        "Legacy cross-cutting search across issues, PRs, datasets, and analyses. "
        "Prefer find() for ranked navigation. Returns compact results."
    ),
    structured_output=True,
)
def search(query: str, limit: int = 10) -> dict[str, object]:
    def _exec() -> dict[str, object]:
        token = _get_env("GITHUB_TOKEN")

        # GitHub Issues + PRs
        issues = _search_github_issues(query, token, limit)

        # Local search via navigation index (v7) or legacy topic_index fields
        try:
            topic_data = _load_topic_index()
        except Exception:
            topic_data = {}

        if topic_data.get("by_slug") or topic_data.get("datasets"):
            ranked = search_index(topic_data, query, limit=limit)
            datasets = [
                {
                    "slug": r["slug"],
                    "name": r.get("name", ""),
                    "stage": r.get("stage", "published"),
                }
                for r in ranked
                if r.get("type") == "dataset"
            ]
            analyses = [
                {
                    "slug": r["slug"],
                    "name": r.get("name", ""),
                    "datasets": r.get("datasets") or [],
                }
                for r in ranked
                if r.get("type") == "analysis"
            ]
        else:
            local = (
                _search_topic_index(query, topic_data)
                if topic_data
                else {
                    "datasets": [],
                    "analyses": [],
                }
            )
            datasets = local["datasets"]
            analyses = local["analyses"]

        return {
            "query": query,
            "total": len(issues) + len(datasets) + len(analyses),
            "issues": issues,
            "datasets": datasets,
            "analyses": analyses,
            "ok": True,
        }

    return guard_timed(_exec, "search")


@mcp.tool(
    description=(
        "Trigger a new context build on CI. "
        "Requires GITHUB_TOKEN with workflow scope. "
        "Artifacts updated within ~1 minute. Rate limit: 2 dispatches/hour."
    ),
    structured_output=True,
)
def refresh_context() -> dict[str, object]:
    def _exec() -> dict:
        global _last_refresh_attempt

        token = _get_env("GITHUB_TOKEN")
        if not token:
            return {"ok": False, "error": "GITHUB_TOKEN non impostato."}

        now = time.monotonic()
        if _last_refresh_attempt is not None:
            elapsed = now - _last_refresh_attempt
            if elapsed < _REFRESH_MIN_INTERVAL:
                wait = _REFRESH_MIN_INTERVAL - elapsed
                return {
                    "ok": False,
                    "error": f"Rate limit. Aspetta ~{int(wait)}s.",
                    "retry_after": int(wait),
                }

        _last_refresh_attempt = now
        client = _get_http()
        result = client.post(
            f"{_API_BASE}/actions/workflows/build-context.yml/dispatches",
            json={"ref": "main"},
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
        )

        if not result.is_ok or result.response is None:
            return {"ok": False, "error": f"Errore di rete: {result.err}"}

        if result.response.status_code == 204:
            return {"ok": True, "message": "Build triggerato. Aggiornamento entro ~1 minuto."}
        elif result.response.status_code == 422:
            return {"ok": False, "error": "Build rifiutato (422). Verifica workflow su main."}
        else:
            return {"ok": False, "error": f"Errore {result.response.status_code}"}

    return guard_timed(_exec, "refresh_context")


# ── Search helpers ─────────────────────────────────────────────────────────────


def _search_github_issues(
    query: str, token: str | None, limit: int = 10
) -> list[dict[str, object]]:
    url = "https://api.github.com/search/issues"
    headers = (
        {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
        if token
        else {}
    )
    params = {
        "q": f"{query} org:dataciviclab",
        "sort": "updated",
        "order": "desc",
        "per_page": min(limit, 50),
    }
    client = _get_http()
    try:
        result = client.get(url, params=params, headers=headers)
    except Exception:
        return []
    if not result.is_ok or result.response is None:
        return []
    try:
        items = result.response.json().get("items", [])
    except Exception:
        return []
    return [
        {
            "repo": item.get("repository_url", "").replace("https://api.github.com/repos/", ""),
            "number": item.get("number"),
            "title": item.get("title", ""),
            "state": item.get("state", ""),
            "url": item.get("html_url", ""),
            "type": "pr" if "pull_request" in item else "issue",
        }
        for item in items
    ]


def _word_match(query: str, text: str) -> bool:
    words = query.lower().split()
    text_lower = text.lower()
    for word in words:
        if not re.search(r"\b" + re.escape(word) + r"\b", text_lower):
            return False
    return True


def _search_topic_index(query: str, topic_data: dict) -> dict[str, list[dict[str, object]]]:
    datasets_found: list[dict[str, object]] = []
    analyses_found: list[dict[str, object]] = []
    seen_slugs: set[str] = set()

    for source, ds_list in topic_data.get("datasets", {}).items():
        for ds in ds_list:
            slug = ds.get("slug", "")
            name = ds.get("name", "")
            if slug not in seen_slugs and (
                query.lower() in slug.lower()
                or _word_match(query, name)
                or _word_match(query, source)
            ):
                seen_slugs.add(slug)
                datasets_found.append(
                    {"slug": slug, "name": name, "stage": ds.get("stage", "published")}
                )

    for a in topic_data.get("analyses", []):
        a_slug = a.get("slug", "")
        a_name = a.get("name", "")
        a_datasets = " ".join(a.get("datasets", []))
        if (
            query.lower() in a_slug.lower()
            or _word_match(query, a_name)
            or query.lower() in a_datasets.lower()
        ):
            analyses_found.append(
                {"slug": a_slug, "name": a_name, "datasets": a.get("datasets", [])}
            )

    return {"datasets": datasets_found, "analyses": analyses_found}


def main() -> None:
    _log.info("main", "starting", repo=_REPO, branch=_BRANCH)
    mcp.run()


if __name__ == "__main__":
    main()
