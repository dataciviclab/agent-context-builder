# agent-context-builder

Genera contesto operativo compatto per agenti [DataCivicLab](https://github.com/dataciviclab).
ACB è il **layer di navigazione e contesto**: ogni 6 ore scansiona i repo del Lab e produce
artifact che dicono ad agenti e umani *"dove cerco, cosa ho, cosa è successo"*.

## Artifact

| Artifact | Schema | Ruolo |
|---|---|---|
| `session_bootstrap.md` | — | Orientamento rapido (markdown) |
| `workspace_triage.json` | v1 | Stato Lab: radar, PR, issues, discussions, registry, pipeline |
| `topic_index.json` | v7 | Navigation index: domains → repos → sources → datasets + analisi pubbliche |

Branch `context`:
```text
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/topic_index.json
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/workspace_triage.json
```

## Gerarchia di navigazione

```
domain (tema editoriale)
  └── repo (ownership + pipeline)
        └── source (fonte esterna)
              └── dataset (artefatto)
                    └── analysis / signal
```

## Fonti consumate

| Repo | Artifact | Cosa |
|---|---|---|
| tutti i repo config | `registry/registry.json` | Dataset (slug, columns, location, stage), signals, marts |
| `source-observatory` | `data/radar/radar_summary.json` | Radar 36 fonti (GREEN/YELLOW/RED) |
| `source-observatory` | `data/catalog/catalog_signals.json` | Drift inventariale |
| `data-explorer` | `catalog/themes.json` | Temi editoriali (domain layer) |
| `data-explorer` | `src/dataset/*.md` | Pagine pubbliche / analisi (frontmatter YAML) |

### Auto-discovery repo

Lo script `scripts/discover_registries.py` scansiona l'organizzazione GitHub
alla ricerca di repo con `registry/registry.json` e propone (via PR automatica)
l'aggiornamento di `dataciviclab.config.yml`. Il workflow `.github/workflows/discover-registries.yml`
gira quotidianamente.

```bash
# Dry-run: mostra cosa cambierebbe
python scripts/discover_registries.py --org dataciviclab --config dataciviclab.config.yml

# Applica: aggiorna il YAML
python scripts/discover_registries.py --org dataciviclab --config dataciviclab.config.yml --apply
```

## Tool MCP

Esposti via `agent-context-mcp` (server MCP `dataciviclab-context`).

| Tool | Quando usarlo |
|---|---|
| `session_bootstrap()` | Prima chiamata — orientamento rapido |
| `lab_map(domain=)` | Struttura del Lab: domains → repos → sources |
| `find(query, type=, domain=)` | Ricerca ranked su dataset/repo/domain/source/analysis |
| `explore(ref)` | Deep-dive di qualsiasi entità (slug repo, dataset, domain, source) |
| `workspace_triage(section=)` | Stato precisi: radar, prs, issues, registry, pipeline |
| `topic_index(resolve=)` | Legacy deep-dive (delega a explore quando v7) |
| `search(query)` | Legacy search (wraps find + GitHub issues) |
| `refresh_context()` | Trigger rebuild CI |

### Esempi

```python
# Orientamento
session_bootstrap()
# → markdown con radar, PR, issues, discussions

# Struttura del Lab
lab_map()
# → {domains: [...], repos: [...], sources: {...}, totals: {...}}

# Trovare un dataset
find("rifiuti", type="dataset")
# → results[{type, slug, name, parent_repo, parent_domain, score}]

# Contesto di un repo
explore("open-ispra")
# → {type: repo, role, domain, datasets: [...], sources: [...]}

# Stato radar
workspace_triage(section="radar")
# → {"green": 35, "yellow": 0, "red": 1, ...}
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

Env opzionale:

| Variabile | Default | Effetto |
|---|---|---|
| `ACB_ARTIFACT_TTL_SECONDS` | `120` | TTL cache artifact (`topic_index.json`, …) nei tool MCP |
| `ACB_BRANCH` | `context` | Branch dove vivono gli artifact |
| `ACB_LOG_LEVEL` | `INFO` | Logging MCP |

La cache viene invalidata da `refresh_context()` dopo un build CI riuscito.

## Utilizzo locale

```bash
pip install -e ".[dev]"
agent-context build --config dataciviclab.config.yml --out generated/
```

## Sviluppo

```bash
pip install -e ".[dev]"
pytest          # test suite
ruff check src/ tests/
mypy src/ tests/
```

## Licenza

MIT
