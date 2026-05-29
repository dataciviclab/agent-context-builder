# topic_index.json — Schema v3

Artifact generato da ACB e pubblicato sul branch `context` di `agent-context-builder`.
Sostituisce la struttura v1 (campo `topics` flat) e v2.

**Schema version**: `3` quando `analyses` è presente, `2` altrimenti (backward compat).

---

## Struttura

```json
{
  "schema_version": 3,
  "generated_at": "2026-05-29T10:00:00",
  "repos": {
    "dataset-incubator": {
      "description": "Dataset candidati e pipeline di incubazione",
      "url": "https://github.com/dataciviclab/dataset-incubator"
    },
    "dataciviclab": {
      "description": "Hub pubblico del Lab",
      "url": "https://github.com/dataciviclab/dataciviclab"
    }
  },
  "datasets_by_source": {
    "ISPRA": [
      {
        "slug": "ispra_ru_base",
        "name": "ISPRA - Rifiuti Urbani (dati base)",
        "period": { "start": 2020, "end": 2024 }
      }
    ]
  },
  "candidates_by_source": {
    "INPS - OpenData": [
      {
        "slug": "pensioni_pa_dag",
        "name": "Pensioni Pa Dag",
        "period": { "start": 2024, "end": 2024 }
      }
    ]
  },
  "operational_topics": {
    "analyses": {
      "name": "analyses",
      "summary": "Analisi pubbliche su dati civici",
      "repos": ["dataciviclab"],
      "paths": ["dataciviclab/analisi/"],
      "next": "Vedi analisi/registry/active.md"
    }
  },
  "explorer_themes": [
    { "slug": "finanza-pubblica", "name": "Finanza pubblica", "datasets": ["irpef-comunale", "entrate-stato"] }
  ],
  "analyses": [
    {
      "slug": "aifa-spesa-consumo",
      "name": "AIFA Spesa farmaceutica convenzionata 2018-2024",
      "datasets": ["aifa_spesa_consumo"],
      "path": "analisi/aifa-spesa-consumo/README.md",
      "status": "active"
    }
  ],
  "analyses_by_dataset": {
    "aifa_spesa_consumo": ["aifa-spesa-consumo"]
  }
}
```

---

## Campi radice

| Campo | Tipo | Schema | Descrizione |
|-------|------|--------|-------------|
| `schema_version` | `int` | v2+ | `2` o `3` (3 se analyses presenti) |
| `generated_at` | ISO 8601 | v2+ | Timestamp di generazione |
| `repos` | object | v2+ | Mappa `repo_name → { description, url }` |
| `datasets_by_source` | object | v2+ | Dataset `published` raggruppati per fonte |
| `candidates_by_source` | object | v2+ | Dataset `incubating` raggruppati per fonte |
| `operational_topics` | object | v2+ | Topic YAML-defined per navigazione agente |
| `explorer_themes` | array | v2+ | Temi editoriali da data-explorer |
| `analyses` | array | **v3** | Lista analisi da `dataciviclab/analisi/` |
| `analyses_by_dataset` | object | **v3** | Reverse lookup: dataset_slug → analysis slugs |

## `repos`

Chiave: nome del repository GitHub configurato in ACB.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `description` | string \| null | Descrizione del repo da GitHub |
| `url` | string \| null | URL GitHub del repo |

## `datasets_by_source` / `candidates_by_source`

Chiave: nome della fonte (es. `"ISPRA"`, `"ISTAT"`). Valore: lista di dataset.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `slug` | string | Identificatore stabile del dataset |
| `name` | string | Nome leggibile |
| `period` | object \| null | Periodo del dataset come oggetto `{start, end}` |

## `operational_topics`

Chiave: nome del topic (da `dataciviclab.config.yml`).

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `name` | string | Nome esplicito del topic |
| `summary` | string | Descrizione sintetica del topic |
| `repos` | array | Repo rilevanti |
| `paths` | array | Path suggeriti per esplorazione |
| `next` | string | Prima azione consigliata a un agente |

## `analyses` (v3)

Lista di analisi pubblicate in `dataciviclab/analisi/`.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `slug` | string | Identificatore stabile dell'analisi (nome directory) |
| `name` | string | Titolo leggibile (da frontmatter README.md) |
| `datasets` | array | Slug dei dataset clean analizzati |
| `path` | string | Path relativo nel repo `dataciviclab` |
| `status` | string | `active` / `archived` |
| `discussion` | int \| null | Numero GitHub Discussion collegata (opzionale) |
| `issue` | int \| null | Numero GitHub Issue collegata (opzionale) |

## `analyses_by_dataset` (v3)

Reverse lookup: chiave = dataset slug, valore = lista di analysis slugs.

```json
{
  "aifa_spesa_consumo": ["aifa-spesa-consumo"],
  "bdap_entrate_stato": ["entrate-stato"]
}
```
