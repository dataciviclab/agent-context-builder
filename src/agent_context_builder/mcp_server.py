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

import requests
from lab_connectors.http import HttpClient
from lab_connectors.mcp import create_mcp_server, get_mcp_logger

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


def _tool_error(tool: str, path: str, message: str, status_code: int | None = None) -> str:
    """Return a structured JSON error string for tool failures."""
    return json.dumps(
        {
            "ok": False,
            "tool": tool,
            "path": path,
            "error": message,
            "status_code": status_code,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )


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

    if result.is_error:
        _log.error("fetch", "failed", path=path, error=str(result.err))
        raise result.err

    result.response.raise_for_status()
    _log.info("fetch", "success", path=path, status=result.response.status_code)
    return result.response.text


@mcp.tool()
def session_bootstrap() -> str:
    """Orientamento rapido: repo attivi, PR aperte, discussion, stato locale, topic."""
    try:
        return _fetch("session_bootstrap.md")
    except Exception as e:
        return _tool_error(
            "session_bootstrap",
            "session_bootstrap.md",
            str(e),
            e.response.status_code if isinstance(e, requests.HTTPError) and e.response else None,
        )


@mcp.tool()
def workspace_triage() -> str:
    """Triage machine-readable: PR, issue, discussion, stato git per repo, warning."""
    try:
        return _fetch("workspace_triage.json")
    except Exception as e:
        return _tool_error(
            "workspace_triage",
            "workspace_triage.json",
            str(e),
            e.response.status_code if isinstance(e, requests.HTTPError) and e.response else None,
        )


@mcp.tool()
def topic_index(resolve: str | None = None) -> str:
    """Topic index — repos, datasets_by_source, operational_topics, analyses.

    Quando ``resolve`` (dataset slug, analysis slug, o source name) è
    specificato, restituisce un sub-graph compatto con tutte le entità
    correlate (dataset, analyses, source, explorer themes). Senza ``resolve``
    restituisce l'index completo (schema v3).
    """
    try:
        raw = _fetch("topic_index.json")
    except Exception as e:
        return _tool_error(
            "topic_index",
            "topic_index.json",
            str(e),
            e.response.status_code if isinstance(e, requests.HTTPError) and e.response else None,
        )

    if not resolve:
        return raw

    # Resolve: extract sub-graph for a single entity
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    resolve_lower = resolve.lower()
    result: dict = {"resolve": resolve, "found": False}

    # Dedup helpers: track seen slugs to avoid duplicates across sections
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

    # Search in datasets (both clean_ready and candidates)
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

    # Search in analyses
    for analysis in data.get("analyses", []):
        a_slug = analysis.get("slug", "")
        if a_slug.lower() == resolve_lower or resolve_lower in [
            d.lower() for d in analysis.get("datasets", [])
        ]:
            if a_slug not in seen_analyses:
                seen_analyses.add(a_slug)
                result.setdefault("analyses", []).append(analysis)
                result["found"] = True

    # Add analyses_by_dataset reverse lookup for this entity
    abd = data.get("analyses_by_dataset", {})
    if resolve_lower in {k.lower() for k in abd}:
        for k, v in abd.items():
            if k.lower() == resolve_lower:
                result.setdefault("analyses_for_dataset", []).extend(
                    s for s in v if s not in seen_analyses
                )
                result["found"] = True

    # Search in explorer themes
    for theme in data.get("explorer_themes", []):
        ds_list = [d.lower() for d in theme.get("datasets", [])]
        if resolve_lower in ds_list:
            t_slug = theme.get("slug", "")
            if t_slug not in seen_themes:
                seen_themes.add(t_slug)
                result.setdefault("explorer_themes", []).append(
                    {
                        "slug": t_slug,
                        "name": theme.get("name"),
                    }
                )
                result["found"] = True

    # Search in sources (by source name)
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
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def refresh_context() -> str:
    """Triggera un nuovo build del contesto su CI.

    Richiede GITHUB_TOKEN con scope workflow.
    Gli artifact aggiornati saranno disponibili entro ~1 minuto.

    Rate-limit: GitHub allows ~2 dispatches per hour per repo/ref.
    This tool enforces a local guard of one dispatch per minute.
    """
    global _last_refresh_attempt

    token = _get_env("GITHUB_TOKEN")
    if not token:
        return json.dumps(
            {
                "ok": False,
                "tool": "refresh_context",
                "error": "GITHUB_TOKEN non impostato. Serve un token con scope 'workflow'.",
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )

    now = time.monotonic()
    if _last_refresh_attempt is not None:
        elapsed = now - _last_refresh_attempt
        if elapsed < _REFRESH_MIN_INTERVAL:
            wait = _REFRESH_MIN_INTERVAL - elapsed
            return json.dumps(
                {
                    "ok": False,
                    "tool": "refresh_context",
                    "error": f"Troppo presto. Ultimo tentativo {int(elapsed)}s fa. "
                    f"Aspetta ~{int(wait)}s prima di riprovare.",
                    "retry_after": int(wait),
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )

    _last_refresh_attempt = now
    try:
        response = requests.post(
            f"{_API_BASE}/actions/workflows/build-context.yml/dispatches",
            json={"ref": "main"},
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )
        if response.status_code == 204:
            _log.info("refresh_context", "triggered", ref="main")
            return json.dumps(
                {
                    "ok": True,
                    "tool": "refresh_context",
                    "message": "Build triggerato. Artifact aggiornati entro ~1 minuto.",
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
        elif response.status_code == 422:
            _log.error(
                "refresh_context",
                "rejected",
                status=response.status_code,
                body=response.text,
            )
            return json.dumps(
                {
                    "ok": False,
                    "tool": "refresh_context",
                    "error": "Build rifiutato (422). Verifica che il workflow sia su main.",
                    "status_code": 422,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
        else:
            _log.error("refresh_context", "failed", status=response.status_code, body=response.text)
            return json.dumps(
                {
                    "ok": False,
                    "tool": "refresh_context",
                    "error": f"Errore {response.status_code}: {response.text}",
                    "status_code": response.status_code,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
    except requests.RequestException as e:
        _log.error("refresh_context", "network_error", error=str(e))
        return json.dumps(
            {
                "ok": False,
                "tool": "refresh_context",
                "error": f"Errore di rete: {e}",
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )


def main() -> None:
    """Entry point per l'MCP server."""
    _log.info("main", "starting", repo=_REPO, branch=_BRANCH)
    mcp.run()


if __name__ == "__main__":
    main()
