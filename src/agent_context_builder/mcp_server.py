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
from lab_connectors.mcp import create_mcp_server, get_mcp_logger, guard_timed
from lab_connectors.mcp.errors import McpError, ErrorCode

_REPO = os.environ.get("ACB_REPO", "dataciviclab/agent-context-builder")
_BRANCH = os.environ.get("ACB_BRANCH", "context")
_RAW_BASE = f"https://raw.githubusercontent.com/{_REPO}/{_BRANCH}"
_API_BASE = f"https://api.github.com/repos/{_REPO}"

# Rate-limit guard: GitHub allows ~2 workflow dispatches per hour per repo/ref
_REFRESH_MIN_INTERVAL = 60  # seconds — local guard before hitting GitHub limit
_last_refresh_attempt: float | None = None

_log = get_mcp_logger("agent-context-builder")

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
    return json.dumps({
        "ok": False,
        "tool": tool,
        "path": path,
        "error": message,
        "status_code": status_code,
        "ts": datetime.now(timezone.utc).isoformat(),
    })


def _fetch(path: str, retries: int = 1, backoff: float = 1.0) -> str:
    """Fetch a file from the context branch with optional retry on transient errors.

    Args:
        path: Path on the context branch (e.g. "session_bootstrap.md")
        retries: Number of retries on 5xx or network errors (default 1, meaning one attempt + up to 1 retry)
        backoff: Initial backoff seconds, doubled on each retry (default 1.0)
    """
    token = _get_env("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}
    url = f"{_RAW_BASE}/{path}"
    attempt = 0
    last_err: Exception | None = None

    while attempt <= retries:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            _log.info("fetch", "success", path=path, status=response.status_code)
            return response.text
        except requests.HTTPError as e:
            # Don't retry on 4xx — they won't become valid by retrying
            if e.response is not None and 400 <= e.response.status_code < 500:
                _log.warning("fetch", "client_error", path=path, status=e.response.status_code)
                raise
            last_err = e
        except requests.RequestException as e:
            last_err = e

        attempt += 1
        if attempt <= retries:
            sleep = backoff * (2 ** (attempt - 1))
            _log.warning("fetch", "retry", path=path, attempt=attempt, sleep=round(sleep, 1), error=str(last_err))
            time.sleep(sleep)
        else:
            _log.error("fetch", "failed", path=path, error=str(last_err))
            raise last_err

    # Should never reach here, but mypy needs it
    raise RuntimeError("unreachable")


@mcp.tool()
def session_bootstrap() -> str:
    """Orientamento rapido: repo attivi, PR aperte, discussion, stato locale, topic."""
    try:
        return _fetch("session_bootstrap.md")
    except Exception as e:
        return _tool_error(
            "session_bootstrap", "session_bootstrap.md", str(e),
            e.response.status_code if isinstance(e, requests.HTTPError) and e.response else None
        )


@mcp.tool()
def workspace_triage() -> str:
    """Triage machine-readable: PR, issue, discussion, stato git per repo, warning."""
    try:
        return _fetch("workspace_triage.json")
    except Exception as e:
        return _tool_error(
            "workspace_triage", "workspace_triage.json", str(e),
            e.response.status_code if isinstance(e, requests.HTTPError) and e.response else None
        )


@mcp.tool()
def topic_index() -> str:
    """Topic index v2 — repos, datasets_by_source, operational_topics."""
    try:
        return _fetch("topic_index.json")
    except Exception as e:
        return _tool_error(
            "topic_index", "topic_index.json", str(e),
            e.response.status_code if isinstance(e, requests.HTTPError) and e.response else None
        )


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
        return json.dumps({
            "ok": False,
            "tool": "refresh_context",
            "error": "GITHUB_TOKEN non impostato. Serve un token con scope 'workflow'.",
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    now = time.monotonic()
    if _last_refresh_attempt is not None:
        elapsed = now - _last_refresh_attempt
        if elapsed < _REFRESH_MIN_INTERVAL:
            wait = _REFRESH_MIN_INTERVAL - elapsed
            return json.dumps({
                "ok": False,
                "tool": "refresh_context",
                "error": f"Troppo presto. Ultimo tentativo {int(elapsed)}s fa. "
                         f"Aspetta ~{int(wait)}s prima di riprovare.",
                "retry_after": int(wait),
                "ts": datetime.now(timezone.utc).isoformat(),
            })

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
            return json.dumps({
                "ok": True,
                "tool": "refresh_context",
                "message": "Build triggerato. Artifact aggiornati entro ~1 minuto.",
                "ts": datetime.now(timezone.utc).isoformat(),
            })
        elif response.status_code == 422:
            _log.error("refresh_context", "rejected", status=response.status_code, body=response.text)
            return json.dumps({
                "ok": False,
                "tool": "refresh_context",
                "error": "Build rifiutato (422). Verifica che il workflow sia abilitato su main.",
                "status_code": 422,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
        else:
            _log.error("refresh_context", "failed", status=response.status_code, body=response.text)
            return json.dumps({
                "ok": False,
                "tool": "refresh_context",
                "error": f"Errore {response.status_code}: {response.text}",
                "status_code": response.status_code,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
    except requests.RequestException as e:
        _log.error("refresh_context", "network_error", error=str(e))
        return json.dumps({
            "ok": False,
            "tool": "refresh_context",
            "error": f"Errore di rete: {e}",
            "ts": datetime.now(timezone.utc).isoformat(),
        })


def main() -> None:
    """Entry point per l'MCP server."""
    _log.info("main", "starting", repo=_REPO, branch=_BRANCH)
    mcp.run()


if __name__ == "__main__":
    main()
