# agent-context-builder

Autonomous context generation for agents: compact bootstrap, workspace triage, and topic index.

## Overview

Reduces token cost for agent sessions by generating compact context artifacts from authoritative sources (GitHub API, local git) instead of reading large raw files.

### Outputs

- **`session_bootstrap.md`** (80-120 lines) — Quick orientation: repos, open PRs, local state, topics
- **`workspace_triage.json`** — Machine-readable summary: PRs, issues, warnings, git state
- **`topic_index.json`** — Topic lookup for targeted agent exploration

## Installation

```bash
pip install -e .
```

## Usage

```bash
agent-context build \
  --config examples/dataciviclab.config.yml \
  --out generated/
```

Generates three JSON/Markdown artifacts in `generated/`.

## Configuration

Create a YAML config file:

```yaml
workspace_root: /path/to/workspace
github_org: myorg
repos:
  - repo1
  - repo2
topics:
  my-topic:
    repos: [repo1]
    paths: [path/to/files]
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
```

## Roadmap

- **P0**: MVP (session_bootstrap, workspace_triage, topic_index, git collector)
- **P1**: Telemetry summarizer, JSON schemas, topic expansion
- **P2**: Lab integration, MCP exposure, local wrapper scripts

## License

MIT