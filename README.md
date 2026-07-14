# agent-context-builder

Genera contesto operativo compatto per agenti [DataCivicLab](https://github.com/dataciviclab)
da GitHub e, se disponibile, dai checkout locali dei repo Lab.

ACB è il **layer di contesto** dell'ecosistema: ogni 6 ore scansiona 10 repo,
colleziona segnali da source-observatory, dataset-incubator e data-explorer,
e produce artifact che dicono ad agenti e umani *"cosa è successo e cosa serve attenzione"*.

## Artifact prodotti

| Artifact | Versione | Ruolo |
|---|---|---|
| `session_bootstrap.md` | — | orientamento rapido: segnali, PR, discussion, stato git |
| `workspace_triage.json` | v1 | dati strutturati: issue, PR, discussion, warning, radar, pipeline |
| `topic_index.json` | v3 | indice navigabile: repos, dataset per fonte, analisi, explorer themes |

URL su branch `context`:

```text
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/session_bootstrap.md
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/workspace_triage.json
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/topic_index.json
```

## Artifact consumati da upstream

| Repo | Path | Uso |
|---|---|---|
| `source-observatory` | `data/radar/radar_summary.json` | health 33 fonti (GREEN/YELLOW/RED) |
| `source-observatory` | `data/catalog/catalog_signals.json` | drift inventariale per fonte |
| `dataset-incubator` | `registry/pipeline_signals.json` | stato 83 candidate pipeline |
| `dataset-incubator` | `registry/clean_catalog.json` | 63 dataset pubblicati (slug, colonne, periodo) |
| `data-explorer` | `src/data/themes.json.py` | 6 temi editoriali + gap explorer |

## Tool MCP

Esposti via `agent-context-mcp` (server MCP `dataciviclab-context`).

| Tool | Output | Quando usarlo |
|---|---|---|
| `session_bootstrap()` | Markdown | Prima chiamata della sessione — orientamento: segnali, PR, discussion, radar |
| `workspace_triage()` | JSON | Dati precisi: conteggi, stato git, source health, pipeline state |
| `topic_index(resolve=)` | JSON | Esplorare dataset/analisi per tema o slug |
| `search(query, limit=10)` | JSON | Cercare in tutto il Lab: issue, PR, dataset, analisi |
| `refresh_context()` | OK/error | Forzare rebuild CI (richiede GITHUB_TOKEN con scope workflow) |

### `search()` nel dettaglio

Combina due fonti in una risposta:

```
search("disuguaglianza")
  ├── GitHub Issues Search API → issue/PR da tutti i repo dataciviclab
  └── topic_index.json locale → dataset e analisi per nome/slug/fonte
```

Senza `GITHUB_TOKEN` funziona solo su dataset e analisi (topic_index).

Esempio di risposta:

```json
{
  "query": "rifiuti",
  "total": 9,
  "results": {
    "issues": [
      {"repo": "dataciviclab/data-explorer", "number": 201, "title": "feat: add ISPRA GHG...", "type": "pr"}
    ],
    "datasets": [
      {"slug": "ispra_ru_base", "name": "Rifiuti Urbani", "source": "ISPRA"}
    ],
    "analyses": [
      {"slug": "rifiuti-km2", "name": "Rifiuti per km²..."}
    ]
  }
}
```

### Configurazione MCP

```json
{
  "mcpServers": {
    "dataciviclab-context": {
      "command": "agent-context-mcp",
      "env": {
        "GITHUB_TOKEN": "<opzionale: serve per refresh_context e search issues>"
      }
    }
  }
}
```

## Utilizzo locale

```bash
pip install -e ".[mcp]"

# Solo GitHub (stato CI)
agent-context build --config dataciviclab.config.yml --out generated/

# Con stato git locale
agent-context build --config dataciviclab.config.yml --out generated/ \
  --workspace-root ~/dev/dataciviclab-workspace
```

Variabili ambiente utili:
- `GITHUB_TOKEN` — per discussion, refresh, search issues
- `DATACIVICLAB_WORKSPACE` — path workspace locale
- `ACB_REPO`, `ACB_BRANCH` — override repo/branch MCP (default: `dataciviclab/agent-context-builder`, `context`)

## Degradazione controllata

Nessun crash per contesto parziale:

| Condizione | Comportamento |
|---|---|
| rate limit / 403 GitHub | campi `null`, errore in JSON |
| nessun token | discussion e search issues saltate; topic_index search funziona |
| repo upstream non disponibile | `available: false`, articolazioni interne populate |
| repo locale assente | `available: false`, `reason: path_not_found` |
| local mode non attivo | `available: false`, `reason: local_disabled` |

## Sviluppo

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
```

## Licenza

MIT
