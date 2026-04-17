# agent-context-builder

Genera contesto operativo compatto per agenti [DataCivicLab](https://github.com/dataciviclab)
da GitHub e, se disponibile, dai checkout locali dei repo Lab.

## Artifact

| Artifact | Target | Ruolo |
|---|---|---|
| `session_bootstrap.md` | ~40 righe | orientamento rapido per agenti e umani |
| `workspace_triage.json` | JSON | PR, issue, discussion, warning, git state |
| `topic_index.json` | JSON | lookup semantico per topic, repo e path |

La CI aggiorna gli artifact GitHub-only ogni 6 ore sul branch `context`.

URL raw:

```text
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/session_bootstrap.md
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/workspace_triage.json
https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context/topic_index.json
```

## Utilizzo

### Shared mode via MCP

Usa `agent-context-mcp` / `dataciviclab-context` per leggere gli artifact remoti.
Non richiede checkout locale.

```bash
pip install -e ".[mcp]"
agent-context-mcp
```

Risorse MCP:

| URI | Contenuto |
|---|---|
| `context://session_bootstrap` | markdown di avvio sessione |
| `context://workspace_triage` | triage machine-readable |
| `context://topic_index` | indice topic |

Tool:

| Tool | Uso |
|---|---|
| `refresh_context` | triggera build CI; richiede `GITHUB_TOKEN` con scope `workflow` |

Esempio `settings.json`:

```json
{
  "mcpServers": {
    "dataciviclab-context": {
      "command": "agent-context-mcp",
      "env": {
        "GITHUB_TOKEN": "<opzionale-per-refresh>"
      }
    }
  }
}
```

### Local mode

Esegue il builder localmente per includere lo stato git (branch, dirty).

```bash
pip install -e .
agent-context build \
  --config dataciviclab.config.yml \
  --out generated/ \
  --workspace-root ~/dev/dataciviclab-workspace
```

Windows:

```powershell
.\codex-context.ps1 -WorkspaceRoot "C:\path\to\dataciviclab-workspace"
```

Il wrapper imposta UTF-8, neutralizza `CURL_CA_BUNDLE` ereditato e usa `.venv314`
o `.venv` se presenti.

## Configurazione (`dataciviclab.config.yml`)

Definisce organizzazione, repo e topic da monitorare.

```yaml
github_org: dataciviclab
repos:
  - dataset-incubator
  - dataciviclab
topics:
  datasets:
    summary: Incubazione dataset
    repos: [dataset-incubator, dataciviclab]
    paths: [dataset-incubator/, dataciviclab/analisi/]
```

`workspace_root` resta fuori dalla config: usare `--workspace-root` o
`DATACIVICLAB_WORKSPACE`. `GITHUB_TOKEN` serve per GitHub Discussions e refresh CI.

Variabili MCP utili: `ACB_REPO`, `ACB_BRANCH`.

## Degradazione controllata

Il builder non deve crashare per contesto parziale:

| Condizione | Comportamento |
|---|---|
| rate limit / 403 GitHub | campi `null`, errore in JSON |
| repo privato senza token | repo saltato, warning registrato |
| nessun token | discussion saltate |
| repo locale assente | `available: false`, `reason: path_not_found` |
| path non git | `available: false`, `reason: not_git_repo` |
| local mode non attivo | `available: false`, `reason: local_disabled` |

## Sviluppo

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Roadmap & Licenza

- **P1**: schema JSON stabile per artifact consumabili da MCP e agenti.
- **P2**: session brief/local health più compatti.
- **Licenza**: MIT
