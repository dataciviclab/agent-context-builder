# topic_index.json — Schema v5

Pubblicato su branch `context`. Consumato da `lab-dashboard` e agenti MCP.

## Struttura

```json
{
  "schema_version": 5,
  "generated_at": "2026-08-28T10:00:00",
  "repos": {
    "dataset-incubator": {"description": "...", "url": "https://..."}
  },
  "datasets": {
    "ISPRA": [
      {
        "slug": "ispra_ru_base",
        "name": "Rifiuti Urbani",
        "description": "Raccolta differenziata...",
        "source_id": "ispra",
        "period": {"start": 2006, "end": 2024},
        "stage": "published",
        "tags": ["ambiente"],
        "category": "ambiente",
        "location": {
          "type": "gcs",
          "path": "gs://dataciviclab-clean/ispra_ru_base/2024/...",
          "multi_file": true
        },
        "columns": [
          {"name": "anno", "type": "INTEGER", "role": "dimension", "description": "Anno"}
        ]
      }
    ]
  },
  "explorer_themes": [
    {"slug": "territorio-ambiente", "name": "Territorio e ambiente", "datasets": ["..."]}
  ],
  "analyses": [
    {"slug": "cinque-per-mille", "name": "5x1000", "datasets": ["ade_cinque_per_mille"], "status": "active"}
  ],
  "analyses_by_dataset": {"ade_cinque_per_mille": ["cinque-per-mille"]},
  "operational_topics": {"pipeline": {"summary": "...", "repos": [...]}}
}
```

## Campi dataset (v5)

| Campo | Tipo | Descrizione |
|---|---|---|
| `slug` | string | Identificativo unico |
| `name` | string | Nome leggibile |
| `description` | string | Descrizione del dataset |
| `source_id` | string | ID fonte (es. `ispra`, `anac`) |
| `period` | object | `{start, end}` anni coperti |
| `stage` | string | `published` o `incubating` |
| `tags` | list[string] | Tag categorici |
| `category` | string | Categoria principale |
| `location` | object | `{type, path, multi_file}` — path GCS |
| `columns` | list[object] | Schema colonne: `{name, type, role, description}` |
