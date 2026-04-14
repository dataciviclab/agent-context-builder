# agent-context-builder

Genera contesto operativo compatto per gli agenti di [DataCivicLab](https://github.com/dataciviclab) a partire da GitHub e, opzionalmente, da checkout locali dei repo Lab.

Sostituisce le letture larghe a inizio sessione con tre artifact mirati:

| Artifact | Dimensione target | Consumato da |
|---|---|---|
| `session_bootstrap.md` | ~40 righe | agenti, umani |
| `workspace_triage.json` | JSON compatto | agenti, MCP |
| `topic_index.json` | JSON compatto | agenti, MCP |

## Come funziona

Il builder raccoglie da due fonti:

- **GitHub** (sempre): PR, issue e discussion aperte per repo; non richiede checkout locale
- **Git locale** (opzionale): branch corrente, stato dirty, commit non pushati per repo

Gli artifact basati su GitHub vengono generati automaticamente ogni 6 ore dalla CI e pubblicati sul [branch `context`](../../tree/context). Chiunque abbia accesso al repo può consumarli senza eseguire il builder localmente.

## Artifact

### `session_bootstrap.md`

Orientamento rapido per agenti e umani:

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

Riepilogo machine-readable consumato da agenti e dall'MCP `dataciviclab-state`:

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

Lookup semantico per topic — repo rilevanti, path, prossimo passo suggerito:

```json
{
  "topics": {
    "datasets": {
      "summary": "Incubazione dataset e analisi pubblicate",
      "repos": ["dataset-incubator", "dataciviclab"],
      "paths": ["dataset-incubator/", "dataciviclab/analisi/"],
      "next": "Consulta dataset-incubator/PROMOTION_CHECKLIST.md"
    }
  }
}
```

## Utilizzo

### Solo GitHub (senza checkout locale)

```bash
pip install -e .
agent-context build --config dataciviclab.config.yml --out generated/
```

PR e issue vengono dalla REST API di GitHub (accesso non autenticato, solo repo pubblici).
Le discussion richiedono un token (la GraphQL API di GitHub richiede sempre autenticazione).

### Con checkout locale

```bash
export DATACIVICLAB_WORKSPACE=~/dev/dataciviclab-workspace
agent-context build --config dataciviclab.config.yml --out generated/
```

Oppure passato direttamente:

```bash
agent-context build \
  --config dataciviclab.config.yml \
  --out generated/ \
  --workspace-root ~/dev/dataciviclab-workspace
```

### Con discussion

```bash
export GITHUB_TOKEN=ghp_...
agent-context build --config dataciviclab.config.yml --out generated/
```

Quando `GITHUB_TOKEN` è impostato, le discussion vengono raccolte automaticamente insieme a PR e issue.

## CI — pubblicazione automatica degli artifact

Il workflow [`build-context`](.github/workflows/build-context.yml) gira ogni 6 ore e a ogni push su `main`. Genera gli artifact in modalità GitHub-only e li pubblica con un force-push sul branch `context`.

Gli artifact sono disponibili a:

```
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/session_bootstrap.md
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/workspace_triage.json
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/topic_index.json
```

L'MCP `dataciviclab-state` legge da questi URL per servire il contesto agli agenti senza richiedere esecuzione locale.

## Configurazione

`dataciviclab.config.yml` alla root è la config attiva del Lab. Definisce quali repo e topic monitorare.

Per usare il builder con un'altra organizzazione, copia `examples/config.template.yml` e adattalo.

Campi principali:

```yaml
github_org: dataciviclab

repos:
  - dataset-incubator
  - dataciviclab

topics:
  datasets:
    summary: Incubazione dataset e analisi pubblicate
    repos: [dataset-incubator, dataciviclab]
    paths: [dataset-incubator/, dataciviclab/analisi/]
    next: Consulta PROMOTION_CHECKLIST.md
```

`workspace_root` è volutamente assente dalla config — si imposta via `--workspace-root` o env var `DATACIVICLAB_WORKSPACE`, per macchina.

## Degradazione controllata

Il builder non crasha mai per dati mancanti:

| Condizione | Comportamento |
|---|---|
| Rate limit GitHub / 403 | `open_prs: null`, errori in `github_fetch_errors` |
| Repo privato (404, senza token) | repo saltato, errore registrato |
| Nessun token | discussion saltate con avviso |
| Repo non clonato localmente | `available: false, reason: path_not_found` |
| Path locale non è un repo git | `available: false, reason: not_git_repo` |
| `--workspace-root` non impostato | `available: false, reason: local_disabled` |

## Sviluppo

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Roadmap

- **P0** — MVP: bootstrap, triage, topic index, git collector, GitHub Actions ✓
- **P1** — Schema JSON per stabilità output; integrazione MCP `dataciviclab-state`
- **P2** — Script wrapper locale; fast path in `AGENTS.md`

## Licenza

MIT
