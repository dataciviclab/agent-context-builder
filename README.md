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

## Tool MCP — migrato a dcl-mcp

Il server MCP (`session_bootstrap`, `lab_map`, `find`, `explore`,
`workspace_triage`) non vive più qui: è migrato in
[`dataciviclab/dcl-mcp`](https://github.com/dataciviclab/dcl-mcp) insieme
ai tool Discussions e al nuovo `gcs_query`. ACB resta il **builder**:
CLI + CI che producono gli artifact sul branch `context`, che dcl-mcp
consuma da remoto.

Per l'uso degli artefatti via MCP, vedi il README di dcl-mcp. Le env
`ACB_REPO` / `ACB_BRANCH` / `ACB_ARTIFACT_TTL_SECONDS` continuano a
valere lì (puntano a questa repo come sorgente).

### Configurazione (dcl-mcp)

```json
{
  "mcpServers": {
    "dataciviclab": {
      "command": "dcl-mcp",
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

Il rebuild degli artifact è un'azione CLI/CI: non è esposto come tool MCP
(dcl-mcp punta agli esterni). I consumer rileggono dopo il TTL.

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
