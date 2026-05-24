# Contributing to agent-context-builder

Questa guida vale per la repo `agent-context-builder`.

Per le regole GitHub condivise dell'organizzazione, parti prima da
[`.github`](https://github.com/dataciviclab/.github).

## A cosa serve questa repo

`agent-context-builder` (ACB) genera contesto operativo compatto per gli
agenti AI del DataCivicLab a partire da GitHub e, opzionalmente, dai checkout
locali dei repo Lab.

Produce tre artifact:

| Artifact | Formato | Ruolo |
|---|---|---|
| `session_bootstrap.md` | Markdown | Orientamento rapido per agenti e umani (~40 righe) |
| `workspace_triage.json` | JSON v1 | PR, issue, discussion, warning, git state |
| `topic_index.json` | JSON v2 | Repos attivi, dataset per fonte, topic operativi |

La CI aggiorna gli artifact ogni 6 ore sul branch `context`.

Qui stanno:

- `src/` — sorgente del builder
- `scripts/` — script di supporto
- `schemas/` — schema degli artifact prodotti
- `dataciviclab.config.yml` — configurazione dei repo da monitorare
- workflow CI per build e deploy su branch `context`

Qui non stanno:

- tool MCP di dominio specifici — stanno nei rispettivi repo
- skill e playbook operativi — stanno in `lab-ops`
- il contesto usato dagli agenti durante le sessioni — è generato, non committato qui
- policy GitHub comuni — vanno in `.github`

## Artifact consumati

ACB legge artifact da altri repo del Lab per produrre il contesto:

| Repo | Path | Uso |
|---|---|---|
| `source-observatory` | `data/radar/radar_summary.json` | Health fonti |
| `source-observatory` | `data/catalog/catalog_signals.json` | Drift inventariale |
| `dataset-incubator` | `registry/pipeline_signals.json` | Stato candidate |
| `dataset-incubator` | `registry/clean_catalog.json` | Dataset disponibili |

Se modifichi la struttura di questi artifact upstream, ACB potrebbe rompersi.

## Setup locale

```bash
pip install -e ".[dev]"
```

Dipende da `lab-connectors` per MCP core:

```bash
pip install -e ../lab-connectors
```

### Eseguire i test

```bash
pytest tests/
ruff check src/
mypy src/
```

### Build manuale

```bash
# Remoto (solo GitHub)
agent-context build --config dataciviclab.config.yml --out generated/

# Locale (con stato git)
agent-context build \
  --config dataciviclab.config.yml \
  --out generated/ \
  --workspace-root ~/dev/dataciviclab-workspace
```

## Degradazione controllata

ACB è progettato per non crashare su contesto parziale:

| Condizione | Comportamento |
|---|---|
| Rate limit / 403 GitHub | Campi `null`, errore registrato in JSON |
| Token non presente | Discussion saltate |
| Repo locale assente | `available: false`, `reason: path_not_found` |
| Local mode non attivo | `available: false`, `reason: local_disabled` |

## Quando aprire una issue

Apri una issue in `agent-context-builder` se il lavoro riguarda:

- modifica della struttura degli artifact prodotti
- cambio del formato del contesto (es. nuovo campo in `topic_index.json`)
- bug nel builder o nei tool MCP
- aggiunta di una nuova fonte di dati per il contesto
- aggiornamento delle dipendenze o compatibilità

## Prima di aprire una PR

- verifica se esiste già una issue collegata
- se cambi la struttura di un artifact prodotto, aggiorna anche:
  - lo schema in `schemas/`
  - i test che validano l'output
  - i consumer negli agenti che usano quell'artifact
- se cambi un artifact consumato da upstream, coordina con `source-observatory`
  o `dataset-incubator`
- controlla che `ruff check .` e `mypy .` passino
- verifica la degradazione: cosa succede se la fonte upstream non è disponibile?

## Riferimenti

- [README.md](README.md) — documentazione completa
- [dataciviclab.config.yml](dataciviclab.config.yml) — configurazione repo monitorati
- [schemas/](schemas/) — schema degli artifact prodotti
- [`lab-connectors`](https://github.com/dataciviclab/lab-connectors) — dipendenza MCP
- [`source-observatory`](https://github.com/dataciviclab/source-observatory) — upstream artifact
- [`dataset-incubator`](https://github.com/dataciviclab/dataset-incubator) — upstream artifact
- [`.github`](https://github.com/dataciviclab/.github) — policy condivise
