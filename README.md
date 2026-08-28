# agent-context-builder

Genera contesto operativo compatto per agenti [DataCivicLab](https://github.com/dataciviclab).
ACB è il **layer di contesto**: ogni 6 ore scansiona i repo del Lab e produce
artifact che dicono ad agenti e umani *"cosa è successo e cosa serve attenzione"*.

## Artifact

| Artifact | Schema | Ruolo |
|---|---|---|
| `session_bootstrap.md` | — | Orientamento rapido (markdown) |
| `workspace_triage.json` | v1 | Stato Lab: radar, PR, issues, discussions, registry, pipeline |
| `topic_index.json` | v5 | Catalogo: 211 dataset (con columns, location), 18 analisi, explorer themes |

Branch `context`:
```text
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/topic_index.json
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/workspace_triage.json
```

## Fonti consumate

| Repo | Artifact | Cosa |
|---|---|---|
| tutti i repo config | `registry/registry.json` | Dataset (slug, columns, location, stage), signals, marts |
| `source-observatory` | `data/radar/radar_summary.json` | Radar 36 fonti (GREEN/YELLOW/RED) |
| `source-observatory` | `data/catalog/catalog_signals.json` | Drift inventariale |
| `data-explorer` | `catalog/datasets.json` + `catalog/themes.json` | Temi editoriali |

## Tool MCP

Esposti via `agent-context-mcp` (server MCP `dataciviclab-context`).

| Tool | Quando usarlo |
|---|---|
| `session_bootstrap()` | Prima chiamata — orientamento rapido |
| `workspace_triage(section=)` | Stato precisi: radar, prs, issues, registry, pipeline |
| `topic_index(resolve=)` | Deep-dive su dataset/analisi per slug o fonte |
| `search(query)` | Ricerca cross-cutting: issues, PR, dataset, analisi |
| `refresh_context()` | Trigger rebuild CI |

### Esempi

```python
# Orientamento
session_bootstrap()
# → markdown con radar, PR, issues, discussions

# Stato radar
workspace_triage(section="radar")
# → {"green": 35, "yellow": 0, "red": 1, ...}

# Deep-dive dataset
topic_index(resolve="ispra_ru_base")
# → {slug, name, source, period, stage, gcs_path, analyses: [...]

# Ricerca
search("rifiuti")
# → {issues: [...], datasets: [{slug, name, stage}], analyses: [...]}
```

### Configurazione

```json
{
  "mcpServers": {
    "dataciviclab-context": {
      "command": "agent-context-mcp",
      "env": { "GITHUB_TOKEN": "<opzionale>" }
    }
  }
}
```

## Utilizzo locale

```bash
pip install -e ".[dev]"
agent-context build --config dataciviclab.config.yml --out generated/
```

## Sviluppo

```bash
pip install -e ".[dev]"
pytest          # 141 test
ruff check src/ tests/
mypy src/ tests/
```

## Licenza

MIT
