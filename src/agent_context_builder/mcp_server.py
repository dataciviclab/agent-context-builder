"""Public MCP server — serves DataCivicLab context artifacts from the context branch.

Exposes three read-only tools built by the CI workflow:
  session_bootstrap — session_bootstrap.md
  workspace_triage  — workspace_triage.json
  topic_index       — topic_index.json

One optional tool:
  refresh_context — triggers a new CI build (requires GITHUB_TOKEN with workflow scope)

Configuration via environment variables:
  ACB_REPO    GitHub repo (default: dataciviclab/agent-context-builder)
  ACB_BRANCH  Branch where artifacts are published (default: context)
  GITHUB_TOKEN  Required only for the refresh_context tool
"""

import os
from pathlib import Path

import requests
from mcp.server.fastmcp import FastMCP

_REPO = os.environ.get("ACB_REPO", "dataciviclab/agent-context-builder")
_BRANCH = os.environ.get("ACB_BRANCH", "context")
_RAW_BASE = f"https://raw.githubusercontent.com/{_REPO}/{_BRANCH}"
_API_BASE = f"https://api.github.com/repos/{_REPO}"

mcp = FastMCP(
    "dataciviclab-context",
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


def _fetch(path: str) -> str:
    """Fetch a file from the context branch."""
    token = _get_env("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}
    response = requests.get(f"{_RAW_BASE}/{path}", headers=headers, timeout=10)
    response.raise_for_status()
    return response.text


@mcp.tool()
def session_bootstrap() -> str:
    """Orientamento rapido: repo attivi, PR aperte, discussion, stato locale, topic."""
    return _fetch("session_bootstrap.md")


@mcp.tool()
def workspace_triage() -> str:
    """Triage machine-readable: PR, issue, discussion, stato git per repo, warning."""
    return _fetch("workspace_triage.json")


@mcp.tool()
def topic_index() -> str:
    """Topic index v2 — repos, datasets_by_source, operational_topics."""
    return _fetch("topic_index.json")


@mcp.tool()
def refresh_context() -> str:
    """Triggera un nuovo build del contesto su CI.

    Richiede GITHUB_TOKEN con scope workflow.
    Gli artifact aggiornati saranno disponibili entro ~1 minuto.
    """
    token = _get_env("GITHUB_TOKEN")
    if not token:
        return (
            "Errore: GITHUB_TOKEN non impostato. "
            "Serve un token con scope 'workflow' per triggerare il build."
        )

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
        return "Build triggerato. Gli artifact saranno aggiornati entro ~1 minuto."
    return f"Errore: {response.status_code} — {response.text}"


def main() -> None:
    """Entry point per l'MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
