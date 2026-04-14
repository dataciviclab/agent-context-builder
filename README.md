# agent-context-builder

Build compact operational context for [DataCivicLab](https://github.com/dataciviclab) agents from GitHub and optional local checkouts.

Replaces broad file reads at session start with three focused artifacts:

| Artifact | Target size | Used by |
|---|---|---|
| `session_bootstrap.md` | ~40 lines | agents, humans |
| `workspace_triage.json` | compact JSON | agents, MCP |
| `topic_index.json` | compact JSON | agents, MCP |

## How it works

The builder pulls from two sources:

- **GitHub** (always): open PRs, issues, and discussions per repo; no local checkout needed
- **Local git** (optional): current branch, dirty state, commits ahead per repo

GitHub-based artifacts are generated automatically every 6 hours by CI and published to the [`context` branch](../../tree/context). Anyone with repo access can consume them without running the builder locally.

## Artifacts

### `session_bootstrap.md`

Quick orientation for agents and humans:

```markdown
# Session Bootstrap

**Generated**: 2026-04-14T20:00:00

## Open PRs
- [dataset-incubator#137](...): feat: bdap-lea clean respect raw schema

## Open Discussions
- [dataciviclab#42](...) [Civic Questions]: IRPEF comunale — cosa ci dice?

## Local State
**dataset-incubator**: `feat/bdap-lea-clean-respect-raw`

## Topics
- datasets
- toolkit
```

### `workspace_triage.json`

Machine-readable summary consumed by agents and the `dataciviclab-state` MCP:

```json
{
  "open_prs": 2,
  "prs": [...],
  "open_issues": 14,
  "issues": [...],
  "open_discussions": 3,
  "discussions": [...],
  "git_state": {
    "dataset-incubator": { "available": true, "current_branch": "feat/...", "dirty": false }
  },
  "warnings": [...]
}
```

### `topic_index.json`

Semantic lookup by topic — repos, relevant paths, suggested next step:

```json
{
  "topics": {
    "datasets": {
      "summary": "Dataset incubation and published analyses",
      "repos": ["dataset-incubator", "dataciviclab"],
      "paths": ["dataset-incubator/", "dataciviclab/analisi/"],
      "next": "Review dataset-incubator/PROMOTION_CHECKLIST.md"
    }
  }
}
```

## Usage

### GitHub-only (no local checkout required)

```bash
pip install -e .
agent-context build --config dataciviclab.config.yml --out generated/
```

PR and issue data comes from the GitHub REST API (unauthenticated, public repos only).
Discussions require a token (GitHub GraphQL API always requires auth).

### With local checkout

```bash
export DATACIVICLAB_WORKSPACE=~/dev/dataciviclab-workspace
agent-context build --config dataciviclab.config.yml --out generated/
```

Or pass it directly:

```bash
agent-context build \
  --config dataciviclab.config.yml \
  --out generated/ \
  --workspace-root ~/dev/dataciviclab-workspace
```

### With discussions

```bash
export GITHUB_TOKEN=ghp_...
agent-context build --config dataciviclab.config.yml --out generated/
```

When `GITHUB_TOKEN` is set, discussions are collected automatically alongside PRs and issues.

## CI — automatic artifact publishing

The [`build-context` workflow](.github/workflows/build-context.yml) runs every 6 hours and on push to `main`. It generates GitHub-only artifacts and force-pushes them to the `context` branch.

Artifacts are available at:

```
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/session_bootstrap.md
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/workspace_triage.json
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/topic_index.json
```

The `dataciviclab-state` MCP reads from these URLs to serve context to agents without requiring local execution.

## Configuration

`dataciviclab.config.yml` at the root is the Lab's live config. It defines which repos and topics to monitor.

To use the builder for a different org, copy `examples/config.template.yml` and adapt it.

Key fields:

```yaml
github_org: dataciviclab

repos:
  - dataset-incubator
  - dataciviclab

topics:
  datasets:
    summary: Dataset incubation and published analyses
    repos: [dataset-incubator, dataciviclab]
    paths: [dataset-incubator/, dataciviclab/analisi/]
    next: Review PROMOTION_CHECKLIST.md
```

`workspace_root` is intentionally absent — set it via `--workspace-root` or `DATACIVICLAB_WORKSPACE` env var per machine.

## Graceful degradation

The builder never fails hard on missing data:

| Condition | Behavior |
|---|---|
| GitHub rate limit / 403 | `open_prs: null`, errors in `github_fetch_errors` |
| Private repo (404, no token) | repo skipped, error recorded |
| No token | discussions skipped with notice |
| Repo not cloned locally | `available: false, reason: path_not_found` |
| Local path not a git repo | `available: false, reason: not_git_repo` |
| `--workspace-root` not set | `available: false, reason: local_disabled` |

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Roadmap

- **P0** — MVP: bootstrap, triage, topic index, git collector, GitHub Actions ✓
- **P1** — JSON schemas for output stability; `dataciviclab-state` MCP integration
- **P2** — Local wrapper script; `AGENTS.md` fast path

## License

MIT
