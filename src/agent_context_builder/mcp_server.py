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


def _fetch(path: str) -> str:
    """Fetch a file from the context branch."""
    token = os.environ.get("GITHUB_TOKEN")
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
    """Lookup per topic: repo rilevanti, path, prossimo passo suggerito."""
    return _fetch("topic_index.json")


@mcp.tool()
def refresh_context() -> str:
    """Triggera un nuovo build del contesto su CI.

    Richiede GITHUB_TOKEN con scope workflow.
    Gli artifact aggiornati saranno disponibili entro ~1 minuto.
    """
    token = os.environ.get("GITHUB_TOKEN")
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
