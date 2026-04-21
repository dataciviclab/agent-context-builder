# topic_index.json — Schema v2

Artifact generato da ACB e pubblicato sul branch `context` di `agent-context-builder`.
Sostituisce la struttura v1 (campo `topics` flat).

---

## Struttura

```json
{
  "schema_version": 2,
  "generated_at": "2026-04-20T10:00:00",
  "repos": {
    "dataset-incubator": {
      "description": "Dataset candidati e pipeline di incubazione",
      "url": "https://github.com/dataciviclab/dataset-incubator"
    },
    "source-observatory": {
      "description": "Intelligence fonti: radar, inventory, catalog-watch",
      "url": "https://github.com/dataciviclab/source-observatory"
    }
  },
  "datasets_by_source": {
    "mef": [
      {
        "slug": "irpef-comunale",
        "name": "IRPEF Comunale 2019-2023",
        "period": {
          "start": 2019,
          "end": 2023
        },
        "visibility": "public",
      }
    ]
  },
  "operational_topics": {
    "datasets": {
      "name": "datasets",
      "summary": "Incubazione dataset",
      "repos": ["dataset-incubator", "dataciviclab"],
      "paths": ["dataset-incubator/", "dataciviclab/analisi/"],
      "next": "Vedere pipeline_signals.json per stato candidati"
    }
  }
}
```

---

## Campi radice

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `schema_version` | `2` | Versione dello schema (intero) |
| `generated_at` | ISO 8601 | Timestamp di generazione |
| `repos` | object | Mappa `repo_name → { description, url }` |
| `datasets_by_source` | object | Dataset clean raggruppati per fonte |
| `operational_topics` | object | Topic YAML-defined per navigazione agente |

## `repos`

Chiave: nome del repository GitHub configurato in ACB.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `description` | string \| null | Descrizione del repo da GitHub |
| `url` | string \| null | URL GitHub del repo |

## `datasets_by_source`

Chiave: nome della fonte (es. `"mef"`, `"istat"`). Valore: lista di dataset con `status == clean_ready` da `clean_catalog.json`.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `slug` | string | Identificatore stabile del dataset |
| `name` | string | Nome leggibile |
| `period` | object \| null | Periodo del dataset come oggetto `{start, end}` |
| `visibility` | string | `public` / `private` |

## `operational_topics`

Chiave: nome del topic (da `dataciviclab.config.yml`).

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `name` | string | Nome esplicito del topic |
| `summary` | string | Descrizione sintetica del topic |
| `repos` | array | Repo rilevanti |
| `paths` | array | Path suggeriti per esplorazione |
| `next` | string | Prima azione consigliata a un agente |
