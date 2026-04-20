# topic_index.json — Schema v2

Artifact generato da ACB e pubblicato sul branch `context`.
Sostituisce la struttura v1 (campo `topics` flat).

---

## Struttura

```json
{
  "schema_version": 2,
  "generated_at": "2026-04-20T10:00:00",
  "repos": {
    "dataset-incubator": "Dataset candidati e pipeline di incubazione",
    "source-observatory": "Intelligence fonti: radar, inventory, catalog-watch"
  },
  "datasets_by_source": {
    "mef": [
      {
        "slug": "irpef-comunale",
        "name": "IRPEF Comunale 2019-2023",
        "visibility": "public",
        "column_count": 12,
        "metric_columns": 4,
        "dimension_columns": 8
      }
    ]
  },
  "operational_topics": {
    "datasets": {
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
| `repos` | object | Mappa `repo_name → descrizione GitHub` |
| `datasets_by_source` | object | Dataset clean raggruppati per fonte |
| `operational_topics` | object | Topic YAML-defined per navigazione agente |

## `datasets_by_source`

Chiave: nome della fonte (es. `"mef"`, `"istat"`). Valore: lista di dataset con `status == clean_ready` da `clean_catalog.json`.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `slug` | string | Identificatore stabile del dataset |
| `name` | string | Nome leggibile |
| `visibility` | string | `public` / `private` |
| `column_count` | int | Totale colonne |
| `metric_columns` | int | Colonne con `role: metric` |
| `dimension_columns` | int | Colonne con `role: dimension` |

## `operational_topics`

Chiave: nome del topic (da `dataciviclab.config.yml`).

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `summary` | string | Descrizione sintetica del topic |
| `repos` | array | Repo rilevanti |
| `paths` | array | Path suggeriti per esplorazione |
| `next` | string | Prima azione consigliata a un agente |
