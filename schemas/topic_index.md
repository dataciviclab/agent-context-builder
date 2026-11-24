# topic_index.json — Schema v8

Pubblicato su branch `context`. Consumato da `data-explorer`, `lab-dashboard` e agenti MCP.

v8 allinea il catalogo al **registry v2** dei repo: `published` derivato dalle pagine
Explorer, `partitions`/`last_run` per dataset, `clean_rows` = somma delle partizioni,
`checks` a livello root. La navigazione (domains, repo cards, reverse index) è quella di v7.

## Struttura

```json
{
  "schema_version": 8,
  "generated_at": "2026-10-07T04:40:00",
  "repos": {
    "rifiuti-urbani": {
      "description": "...",
      "url": "https://github.com/dataciviclab/rifiuti-urbani",
      "role": "dati",
      "domain": "territorio-ambiente",
      "n_datasets": 16,
      "n_published": 4,
      "sources": ["ispra"]
    }
  },
  "datasets": {
    "ispra": [
      {
        "slug": "ispra_ru_base",
        "url_slug": "ispra-ru-base",
        "name": "Rifiuti Urbani",
        "description": "...",
        "source": "ISPRA",
        "source_id": "ispra",
        "period": {"start": 2006, "end": 2024},
        "published": true,
        "tags": ["ambiente"],
        "category": "ambiente",
        "registry_source": "rifiuti-urbani",
        "partitions": {"2023": 1200, "2024": 1234},
        "last_run": {"at": "2026-11-17T17:01:24Z", "year": 2024, "status": "SUCCESS"},
        "clean_rows": 2434,
        "location": {"type": "gcs", "path": "gs://...", "multi_file": true},
        "columns": [{"name": "anno", "type": "INTEGER", "role": "dimension", "semantic_type": "", "description": "..."}]
      }
    ]
  },
  "domains": [
    {
      "slug": "territorio-ambiente",
      "name": "Territorio e ambiente",
      "description": "...",
      "icon": "🌍",
      "categories": ["ambiente", "energia", "trasporti"],
      "repos": ["rifiuti-urbani"],
      "datasets": ["ispra_ru_base"],
      "dataset_count": 1
    }
  ],
  "explorer_themes": [
    {"slug": "territorio-ambiente", "name": "Territorio e ambiente", "datasets": ["ispra_ru_base"]}
  ],
  "operational_topics": {
    "pipeline": {"summary": "...", "repos": ["toolkit"], "next": "..."}
  },
  "analyses": [
    {
      "slug": "rifiuti-urbani",
      "name": "Rifiuti urbani",
      "datasets": ["ispra_ru_base"],
      "status": "published",
      "description": "...",
      "source": "ISPRA",
      "period": "2020-2024"
    }
  ],
  "analyses_by_dataset": {"ispra_ru_base": ["rifiuti-urbani"]},
  "checks": [],
  "by_repo": {"rifiuti-urbani": ["ispra_ru_base"]},
  "by_domain": {"territorio-ambiente": ["ispra_ru_base"]},
  "by_slug": {
    "ispra_ru_base": {
      "name": "Rifiuti Urbani",
      "published": true,
      "source_id": "ispra",
      "registry_source": "rifiuti-urbani",
      "domain": "territorio-ambiente",
      "category": "ambiente"
    }
  }
}
```

## Gerarchia di navigazione

```
domain (tema editoriale da data-explorer/catalog/themes.json)
  └── repo (unità ownership — registry_source)
        └── source (fonte esterna — source_id)
              └── dataset (artefatto)
                    └── analysis / signal
```

## Campi v8

| Campo | Tipo | Descrizione |
|---|---|---|
| `schema_version` | int | Sempre `8` |
| `repos.*.role` | string | `dati` \| `infra` \| `editoriale` \| `osservatorio` |
| `repos.*.domain` | string\|null | Domain primario (categoria più frequente dei suoi dataset) |
| `repos.*.n_datasets` | int | Conteggio dataset del repo |
| `repos.*.n_published` | int | Conteggio dataset con pagina Explorer (`published`) |
| `repos.*.sources` | list[string] | source_id distinti |
| `domains[]` | list | Temi editoriali con repos/datasets collegati |
| `explorer_themes[]` | list | Temi compatti per lab-dashboard Grafo (`slug`, `name`, `datasets`) |
| `analyses[]` | list | Pagine pubbliche da `data-explorer/src/dataset/*.md` |
| `by_repo` | object | slug repo → dataset slugs |
| `by_domain` | object | slug domain → dataset slugs |
| `by_slug` | object | dataset slug → card di navigazione |
| `checks[]` | list | Anomalie di struttura dai registry (`repo`, `id`, `status`, `detail`, `action`); vuoto = tutto a posto |
| `datasets.*.published` | bool | Il dataset ha una pagina Explorer (`analyses_by_dataset`), non un campo editoriale del repo |
| `datasets.*.partitions` | object | Partizione pubblicata → righe clean (assente per mart-only / non rieseguiti) |
| `datasets.*.last_run` | object | `{at, year, status}` dell'esecuzione più recente su tutte le partizioni |
| `datasets.*.clean_rows` | int | Somma delle righe clean delle partizioni |

## Backward compatibility

- `datasets` resta **raggruppato per source_id** con gli stessi campi di v7 (`registry_source`, `location`, `columns`, …) — `location` continua a essere materializzata per i consumer. `stage` non c'è più: usare `published`.
- I repo non ancora migrati a registry v2 restano letti: `last_run` e `clean_rows` arrivano dai `signals` v1.
- `repos` mantiene `description` e `url`; i campi nuovi sono aggiuntivi.
- `explorer_themes` è il formato atteso da `lab-dashboard/pages/08_Grafo.py`.

## Fonti upstream

| Sezione | Fonte |
|---|---|
| `datasets`, `repos` (base) | `registry/registry.json` di ogni repo config |
| `domains`, `explorer_themes` | `data-explorer/catalog/themes.json` |
| `analyses` | `data-explorer/src/dataset/*.md` (frontmatter YAML) |
| `role` repo | mapping statico in `navigation.py` (AGENTS.md §2) |
