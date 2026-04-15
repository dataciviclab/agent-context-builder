# Repo Signals — Standard di interoperabilità per ACB

Spec per i file JSON che i repo del Lab possono pubblicare affinché
`agent-context-builder` li consumi durante il build del contesto.

---

## Scopo

Ogni repo ha conoscenza locale che ACB non può derivare da GitHub:
- **source-observatory**: salute delle fonti dati (endpoint up/down, regressioni)
- **dataset-incubator**: stato dei candidati nel pipeline (stage, blocchi, pronti per promozione)
- (futuri repo): qualunque segnale operativo rilevante per un agente

Anziché costruire parser ad-hoc per ogni repo, ACB legge file JSON che seguono
questo standard e li aggrega in `workspace_triage.json` e `session_bootstrap.md`.

---

## Convenzione di posizionamento

Ogni repo pubblica il proprio file in una path nota e stabile, committata nel
repo stesso e aggiornata da CI (o manualmente). ACB la legge via
`raw.githubusercontent.com` — nessun clone locale necessario.

Paths per repo attivi:

| Repo | Path nel repo | Nota |
|------|--------------|------|
| `source-observatory` | `data/catalog/catalog_signals.json` | formato legacy (vedi §Legacy) |
| `dataset-incubator` | `registry/pipeline_signals.json` | adotta questo standard |

---

## Schema (v1)

```json
{
  "schema_version": "1",
  "generated_at": "2026-04-15",
  "repo": "dataset-incubator",
  "topic": "pipeline_state",
  "summary": {
    "total": 20,
    "by_status": { "ok": 16, "warn": 3, "error": 1 }
  },
  "signals": [
    {
      "id": "irpef-comunale",
      "status": "ok",
      "label": "irpef-comunale",
      "detail": "stage: incubating — anni 2019-2023, fonte: mef",
      "action": ""
    },
    {
      "id": "ispra-balneazione",
      "status": "warn",
      "label": "ispra-balneazione",
      "detail": "stage: incubating — nessun mart SQL, issue aperta da 60+ giorni",
      "action": "valutare se bloccare o archiviare"
    }
  ]
}
```

### Campi obbligatori

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `schema_version` | `"1"` | Versione dello schema (stringa, non numero) |
| `generated_at` | `YYYY-MM-DD` | Data di generazione |
| `repo` | string | Nome del repo GitHub (es. `"dataset-incubator"`) |
| `topic` | string | Dominio del segnale — vedi §Topic |
| `signals` | array | Lista di segnali — vedi §Segnale |

### Campi opzionali

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `summary` | object | Conteggi aggregati per status |
| `summary.total` | int | Totale elementi osservati |
| `summary.by_status` | object | Conteggi per valore di status |

---

## Valori di `topic`

| Valore | Repo | Significato |
|--------|------|-------------|
| `catalog_health` | source-observatory | Salute degli endpoint delle fonti |
| `pipeline_state` | dataset-incubator | Stato dei candidati nel pipeline |

Nuovi topic: aprire issue in `agent-context-builder` prima di adottarli,
per coordinare il parser ACB.

---

## Schema del segnale (`signals[]`)

| Campo | Tipo | Obbligatorio | Descrizione |
|-------|------|-------------|-------------|
| `id` | string | sì | Identificatore stabile (slug del dataset, nome fonte, ecc.) |
| `status` | `"ok"` \| `"warn"` \| `"error"` | sì | Stato sintetico |
| `label` | string | sì | Nome leggibile da mostrare in UI/bootstrap |
| `detail` | string | sì | Descrizione human-readable dello stato corrente |
| `action` | string | sì | Azione suggerita — stringa vuota `""` se nessuna |

### Semantica di `status`

| Valore | Significato |
|--------|-------------|
| `ok` | Nessun problema noto, nessuna azione richiesta |
| `warn` | Attenzione: qualcosa è anomalo ma non bloccante |
| `error` | Bloccante o regressione: richiede azione |

ACB mostra nel `session_bootstrap.md` solo i segnali `warn` e `error`.
I segnali `ok` appaiono solo nei conteggi di `summary`.

---

## Legacy: source-observatory

`source-observatory` usa un formato precedente allo standard (`catalog_signals.json`).
ACB mantiene un parser dedicato (`signals.py::parse_source_observatory_signals`)
che mappa il vecchio formato sul modello interno.

Migrazione pianificata: quando SO adotterà questo schema, il parser legacy
verrà rimosso. Non c'è urgenza — il formato SO è stabile e ben definito.

---

## Come aggiungere un nuovo repo

1. Definire il `topic` (aprire issue in ACB se non esiste)
2. Scrivere lo script che produce il JSON (es. `scripts/build_pipeline_signals.py`)
3. Aggiungere il file alla CI del repo (workflow che lo aggiorna e committa)
4. Registrare la path in ACB (`dataciviclab.config.yml` o nel codice di `GitHubCollector`)
5. Aggiungere il parser in `render.py` se il topic non è già supportato
