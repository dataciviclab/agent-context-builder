"""Public MCP server — serves DataCivicLab context artifacts from the context branch.

Exposes three read-only tools built by the CI workflow:
  session_bootstrap — session_bootstrap.md
  workspace_triage  — workspace_triage.json
  topic_index       — topic_index.json

One optional tool:
  refresh_context — triggers a new CI build (requires GITHUB_TOKEN with workflow scope)

Configuration via environment variables:
  ACB_REPO       GitHub repo (default: dataciviclab/agent-context-builder)
  ACB_BRANCH     Branch where artifacts are published (default: context)
  GITHUB_TOKEN   Required only for the refresh_context tool
  ACB_LOG_LEVEL  Logging level, default INFO (options: DEBUG, INFO, WARNING, ERROR)
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from lab_connectors.http import HttpClient
from lab_connectors.mcp import create_mcp_server, get_mcp_logger, guard_timed

_REPO = os.environ.get("ACB_REPO", "dataciviclab/agent-context-builder")
_BRANCH = os.environ.get("ACB_BRANCH", "context")
_RAW_BASE = f"https://raw.githubusercontent.com/{_REPO}/{_BRANCH}"
_API_BASE = f"https://api.github.com/repos/{_REPO}"

# Rate-limit guard: GitHub allows ~2 workflow dispatches per hour per repo/ref
_REFRESH_MIN_INTERVAL = 60  # seconds — local guard before hitting GitHub limit
_last_refresh_attempt: float | None = None

_log = get_mcp_logger(
    "agent-context-builder",
    level=os.environ.get("ACB_LOG_LEVEL", "INFO"),
)

mcp = create_mcp_server(
    name="dataciviclab-context",
    instructions=(
        "DataCivicLab context artifacts, generated from GitHub every 6 hours. "
        "Start with session_bootstrap for a quick orientation, then use "
        "workspace_triage for machine-readable state and topic_index for "
        "targeted exploration by topic."
    ),
)


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
    """Return .env candidates, from explicit config to nearby parent directories."""
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
    """Load local .env files without overriding variables already set by the host.

    Lookup order:
    1. `ACB_ENV_FILE`, when set.
    2. `.env` from the current working directory upward.
    3. `.env` from this module directory upward.

    Partial `.env` files are allowed: the loader keeps checking later candidates
    until at least one missing or blank variable has been filled.
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return True

    loaded_any = False
    for env_path in _candidate_env_paths():
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(line)
            if not parsed:
                continue
            key, value = parsed
            if not os.environ.get(key):
                os.environ[key] = value
                loaded_any = True
    if loaded_any:
        _ENV_LOADED = True
    return loaded_any


def _get_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    _load_dotenv_if_present()
    return os.environ.get(name)


def _fetch(path: str, retries: int = 1, backoff: float = 1.0) -> str:
    """Fetch a file from the context branch with retry/backoff via HttpClient.

    Args:
        path: Path on the context branch (e.g. "session_bootstrap.md")
        retries: Number of retry attempts (default 1)
        backoff: Base backoff delay in seconds (default 1.0)
    """
    token = _get_env("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}
    url = f"{_RAW_BASE}/{path}"

    client = HttpClient(max_retries=retries, retry_backoff=backoff, timeout=10)
    result = client.get(url, headers=headers)

    if not result.is_ok or result.response is None:
        _log.error("fetch", "failed", path=path, error=str(result.err))
        raise result.err if result.err else RuntimeError(f"Failed to fetch {path}")

    response = result.response
    response.raise_for_status()
    _log.info("fetch", "success", path=path, status=response.status_code)
    return response.text


@mcp.tool(
    description="Orientamento rapido: repo attivi, PR aperte, discussion, stato locale, topic.",
    structured_output=True,
)
def session_bootstrap() -> dict[str, object]:
    def _exec() -> dict[str, object]:
        content = _fetch("session_bootstrap.md")
        return {"content": content, "format": "markdown", "ok": True}

    return guard_timed(_exec, "session_bootstrap")


@mcp.tool(
    description="Triage machine-readable: PR, issue, discussion, stato git per repo, warning.",
    structured_output=True,
)
def workspace_triage() -> dict[str, object]:
    def _exec() -> dict[str, object]:
        content = _fetch("workspace_triage.json")
        return {"content": json.loads(content), "ok": True}

    return guard_timed(_exec, "workspace_triage")


@mcp.tool(
    description=(
        "Topic index — repos, datasets_by_source, operational_topics, analyses. "
        "Quando ``resolve`` (dataset slug, analysis slug, o source name) è "
        "specificato, restituisce un sub-graph compatto con tutte le entità "
        "correlate. Senza ``resolve`` restituisce l'index completo (schema v3)."
    ),
    structured_output=True,
)
def topic_index(resolve: str | None = None) -> dict[str, object]:
    def _exec() -> dict[str, object]:
        raw = _fetch("topic_index.json")
        data: dict = json.loads(raw)

        if not resolve:
            return {"content": data, "ok": True}

        resolve_lower = resolve.lower()
        result: dict = {"resolve": resolve, "found": False}

        seen_sources: set[str] = set()
        seen_datasets: set[str] = set()
        seen_analyses: set[str] = set()
        seen_themes: set[str] = set()

        def _add_source(source: str) -> None:
            if source not in seen_sources:
                seen_sources.add(source)
                result.setdefault("sources", []).append(source)

        def _add_dataset(entry: dict) -> None:
            slug = entry["slug"]
            if slug not in seen_datasets:
                seen_datasets.add(slug)
                result.setdefault("datasets", []).append(entry)

        for section in ("datasets_by_source", "candidates_by_source"):
            entries = data.get(section, {})
            for source, datasets in entries.items():
                for ds in datasets:
                    if ds.get("slug", "").lower() == resolve_lower:
                        _add_dataset(
                            {
                                "slug": ds["slug"],
                                "name": ds.get("name", ""),
                                "source": source,
                                "period": ds.get("period"),
                                "stage": "published"
                                if section == "datasets_by_source"
                                else "incubating",
                            }
                        )
                        result["found"] = True
                        _add_source(source)

        for analysis in data.get("analyses", []):
            a_slug = analysis.get("slug", "")
            if a_slug.lower() == resolve_lower or resolve_lower in [
                d.lower() for d in analysis.get("datasets", [])
            ]:
                if a_slug not in seen_analyses:
                    seen_analyses.add(a_slug)
                    result.setdefault("analyses", []).append(analysis)
                    result["found"] = True

        abd = data.get("analyses_by_dataset", {})
        if resolve_lower in {k.lower() for k in abd}:
            for k, v in abd.items():
                if k.lower() == resolve_lower:
                    result.setdefault("analyses_for_dataset", []).extend(
                        s for s in v if s not in seen_analyses
                    )
                    result["found"] = True

        for theme in data.get("explorer_themes", []):
            ds_list = [d.lower() for d in theme.get("datasets", [])]
            if resolve_lower in ds_list:
                t_slug = theme.get("slug", "")
                if t_slug not in seen_themes:
                    seen_themes.add(t_slug)
                    result.setdefault("explorer_themes", []).append(
                        {"slug": t_slug, "name": theme.get("name")}
                    )
                    result["found"] = True

        for section in ("datasets_by_source", "candidates_by_source"):
            entries = data.get(section, {})
            for source in entries:
                if source.lower() == resolve_lower:
                    result["found"] = True
                    _add_source(source)
                    for ds in entries[source]:
                        _add_dataset(
                            {
                                "slug": ds["slug"],
                                "name": ds.get("name", ""),
                                "source": source,
                                "period": ds.get("period"),
                                "stage": "published"
                                if section == "datasets_by_source"
                                else "incubating",
                            }
                        )

        result["ts"] = datetime.now(timezone.utc).isoformat()
        return {"content": result, "ok": True}

    return guard_timed(_exec, "topic_index")


@mcp.tool(
    description=(
        "Triggera un nuovo build del contesto su CI. "
        "Richiede GITHUB_TOKEN con scope workflow. "
        "Gli artifact aggiornati saranno disponibili entro ~1 minuto. "
        "Rate-limit: GitHub allow ~2 dispatches per hour. "
        "Local guard: one dispatch per minute."
    ),
    structured_output=True,
)
def refresh_context() -> dict[str, object]:
    def _exec() -> dict:
        global _last_refresh_attempt

        token = _get_env("GITHUB_TOKEN")
        if not token:
            return {
                "ok": False,
                "error": "GITHUB_TOKEN non impostato. Serve un token con scope 'workflow'.",
            }

        now = time.monotonic()
        if _last_refresh_attempt is not None:
            elapsed = now - _last_refresh_attempt
            if elapsed < _REFRESH_MIN_INTERVAL:
                wait = _REFRESH_MIN_INTERVAL - elapsed
                return {
                    "ok": False,
                    "error": f"Troppo presto. Ultimo tentativo {int(elapsed)}s fa. "
                    f"Aspetta ~{int(wait)}s prima di riprovare.",
                    "retry_after": int(wait),
                }

        _last_refresh_attempt = now
        client = HttpClient(timeout=10)
        result = client.post(
            f"{_API_BASE}/actions/workflows/build-context.yml/dispatches",
            json={"ref": "main"},
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
            },
        )

        if not result.is_ok or result.response is None:
            _log.error("refresh_context", "network_error", error=str(result.err))
            return {"ok": False, "error": f"Errore di rete: {result.err}"}

        response = result.response
        if response.status_code == 204:
            _log.info("refresh_context", "triggered", ref="main")
            return {
                "ok": True,
                "message": "Build triggerato. Artifact aggiornati entro ~1 minuto.",
            }
        elif response.status_code == 422:
            _log.error(
                "refresh_context", "rejected", status=response.status_code, body=response.text
            )
            return {
                "ok": False,
                "error": "Build rifiutato (422). Verifica che il workflow sia su main.",
                "status_code": 422,
            }
        else:
            _log.error("refresh_context", "failed", status=response.status_code, body=response.text)
            return {
                "ok": False,
                "error": f"Errore {response.status_code}: {response.text}",
                "status_code": response.status_code,
            }

    return guard_timed(_exec, "refresh_context")


def _search_github_issues(
    query: str, token: str | None, limit: int = 10
) -> list[dict[str, object]]:
    """Search issues and PRs across dataciviclab org via GitHub Search API.

    Args:
        query: Search query (natural language, full-text on title + body)
        token: GitHub token (optional; affects rate limit)
        limit: Max results (default 10, max 50)

    Returns:
        List of matching issues/PRs with repo, number, title, state, url, type.
    """
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
    client = HttpClient(timeout=10)
    try:
        result = client.get(url, params=params, headers=headers)
    except Exception as exc:
        _log.warning("search_issues", "http_error", error=str(exc))
        return []

    if not result.is_ok or result.response is None:
        _log.warning("search_issues", "failed", error=str(result.err))
        return []

    try:
        response = result.response
        data = response.json()
        items = data.get("items", [])
    except Exception as exc:
        _log.warning("search_issues", "parse_error", error=str(exc))
        return []

    results = []
    for item in items:
        repo_full = item.get("repository_url", "").replace("https://api.github.com/repos/", "")
        results.append(
            {
                "repo": repo_full or "",
                "number": item.get("number"),
                "title": item.get("title", ""),
                "state": item.get("state", ""),
                "url": item.get("html_url", ""),
                "type": "pr" if "pull_request" in item else "issue",
                "updated_at": item.get("updated_at", ""),
            }
        )
    return results


def _search_topic_index(query: str, topic_data: dict) -> dict[str, list[dict[str, object]]]:
    """Search datasets and analyses in the topic_index data.

    Args:
        query: Search query (case-insensitive substring match)
        topic_data: Parsed topic_index.json content

    Returns:
        Dict with 'datasets' and 'analyses' lists.
    """
    q = query.lower()
    datasets_found: list[dict[str, object]] = []
    analyses_found: list[dict[str, object]] = []

    # Search datasets by slug, name, source
    seen_slugs: set[str] = set()
    for section in ("datasets_by_source", "candidates_by_source"):
        entries = topic_data.get(section, {})
        for source, datasets in entries.items():
            for ds in datasets:
                slug = ds.get("slug", "")
                name = ds.get("name", "")
                if slug not in seen_slugs and (
                    q in slug.lower() or q in name.lower() or q in source.lower()
                ):
                    seen_slugs.add(slug)
                    datasets_found.append(
                        {
                            "slug": slug,
                            "name": name,
                            "source": source,
                            "period": ds.get("period"),
                            "stage": "published"
                            if section == "datasets_by_source"
                            else "incubating",
                        }
                    )

    # Search analyses by slug, name, datasets
    for analysis in topic_data.get("analyses", []):
        a_slug = analysis.get("slug", "")
        a_name = analysis.get("name", "")
        a_datasets = " ".join(analysis.get("datasets", []))
        if q in a_slug.lower() or q in a_name.lower() or q in a_datasets.lower():
            analyses_found.append(
                {
                    "slug": a_slug,
                    "name": a_name,
                    "datasets": analysis.get("datasets", []),
                    "status": analysis.get("status", ""),
                }
            )

    return {"datasets": datasets_found, "analyses": analyses_found}


@mcp.tool(
    description=(
        "Cerca in issue, PR, dataset e analisi del DataCivicLab. "
        "Combina GitHub Search API (issue/PR full-text) con l'indice locale "
        "(dataset, analisi). I risultati sono raggruppati per tipo."
    ),
    structured_output=True,
)
def search(query: str, limit: int = 10) -> dict[str, object]:
    """Search across the DataCivicLab ecosystem.

    Args:
        query: Testo da cercare (es. \"disuguaglianza\", \"sanità\", \"appalti\")
        limit: Massimo risultati per sezione (default 10, max 50)

    Returns:
        Risultati raggruppati per tipo (issues, datasets, analyses).
    """

    def _exec() -> dict[str, object]:
        token = _get_env("GITHUB_TOKEN")

        # 1. Search GitHub Issues + PRs
        issues = _search_github_issues(query, token, limit)

        # 2. Fetch topic_index and search datasets + analyses
        try:
            topic_raw = _fetch("topic_index.json", retries=0)
            topic_data = json.loads(topic_raw)
        except Exception as exc:
            _log.warning("search", "topic_index_fetch_failed", error=str(exc))
            topic_data = {}

        local = (
            _search_topic_index(query, topic_data)
            if topic_data
            else {"datasets": [], "analyses": []}
        )

        total = len(issues) + len(local["datasets"]) + len(local["analyses"])
        return {
            "query": query,
            "total": total,
            "results": {
                "issues": issues,
                "datasets": local["datasets"],
                "analyses": local["analyses"],
            },
            "ok": True,
        }

    return guard_timed(_exec, "search")


def main() -> None:
    """Entry point per l'MCP server."""
    _log.info("main", "starting", repo=_REPO, branch=_BRANCH)
    mcp.run()


if __name__ == "__main__":
    main()
