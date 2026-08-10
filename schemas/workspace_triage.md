# workspace_triage.json — Schema v1

Artifact machine-readable generato da ACB e pubblicato sul branch `context`.
Contiene stato incrociato di PR, issue, discussion, git e segnali operativi.

---

## Struttura

```json
{
  "generated_at": "2026-04-20T10:00:00",
  "workspace_root": "/path/to/workspace",
  "repos": ["dataset-incubator", "dataciviclab"],
  "open_prs": 3,
  "prs": [
    { "number": 149, "title": "feat: push archive GCS", "repo": "dataset-incubator", "url": "..." }
  ],
  "open_issues": 5,
  "issues": [
    { "number": 116, "title": "radar daily action", "repo": "source-observatory", "url": "..." }
  ],
  "open_discussions": 2,
  "discussions": [
    { "number": 214, "title": "ISTAT povertà", "repo": "dataciviclab", "url": "...", "category": "Proposte" }
  ],
  "github_fetch_errors": {},
  "git_state": {
    "dataset-incubator": {
      "available": true,
      "reason": null,
      "dirty": false,
      "current_branch": "main",
      "branches_ahead": [],
      "untracked_files": []
    }
  },
  "warnings": ["dataset-incubator: branch feat/xyz ahead of main"],
  "radar": { "generated_at": "...", "green": 20, "yellow": 2, "red": 0, "unhealthy": [] },
  "source_health": { "captured_at": "...", "alerts": [] },
  "pipeline_state": { "generated_at": "...", "actionable": [] },
  "registry_summary": [
    {
      "repo": "dataset-incubator",
      "available": true,
      "source_repo": "dataciviclab/dataset-incubator",
      "updated_at": "2026-08-08",
      "datasets": 114,
      "marts": 197,
      "signals": 117,
      "codelists": 0,
      "entities": 19,
      "gcs": 114,
      "reason": ""
    }
  ]
}
```

---

## Campi radice

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `generated_at` | ISO 8601 | Timestamp di generazione |
| `workspace_root` | string \| null | Path workspace locale, null in shared mode |
| `repos` | array | Lista repo monitorati |
| `open_prs` | int \| null | Conteggio PR aperte; null se errore fetch |
| `prs` | array | PR aperte (number, title, repo, url) |
| `open_issues` | int \| null | Conteggio issue aperte; null se errore fetch |
| `issues` | array | Issue aperte (number, title, repo, url) |
| `open_discussions` | int \| null | Conteggio discussion; null se no token |
| `discussions` | array | Discussion aperte (number, title, repo, url, category) |
| `github_fetch_errors` | object | Errori per repo/risorsa; vuoto se tutto ok |
| `git_state` | object | Stato git per repo (vedi sotto) |
| `warnings` | array | Warning testuali su branch dirty/ahead |
| `radar` | object \| null | Health fonti da `radar_summary.json` |
| `source_health` | object \| null | Segnali drift/inventory da `catalog_signals.json` |
| `pipeline_state` | object \| null | Stato candidati dai signals del registry DI |
| `registry_summary` | array | Orientamento per-repo dei registry.json dei repo configurati |

## `git_state[repo]`

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `available` | bool | Repo presente e valido localmente |
| `reason` | string \| null | Motivo se `available: false` (`path_not_found`, `not_git_repo`, `local_disabled`) |
| `dirty` | bool \| null | File modificati non committati |
| `current_branch` | string \| null | Branch corrente |
| `branches_ahead` | array | Branch locali ahead di main |
| `untracked_files` | array | File non tracciati |

## `registry_summary[]`

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `repo` | string | Nome repo (sotto l'org) |
| `available` | bool | Il repo ha un `registry.json` parsabile |
| `source_repo` | string | `source_repo` dichiarato nel registry |
| `updated_at` | string | Freschezza del registry (data) |
| `datasets` / `marts` / `signals` | int | Conteggio entries per sezione |
| `codelists` / `entities` | int | Conteggio entries (dict keyed-by-name) |
| `gcs` | int | Dataset con `location.type: gcs` (parquet queryabile = pubblicato) |
| `reason` | string | Motivo se `available: false` (`registry_not_found`, `invalid_json`) |

**Pubblicazione**: essendo nel registry con location GCS, un dataset è di
fatto pubblicato (parquet queryabile). Il campo `stage` del registry NON è
esposto: è un default del builder (`incubating`) che solo dataset-incubator
promuove — non riflette la pubblicazione reale e non deve essere usato come
segnale.

Un repo del config senza `registry.json` (non ancora migrato) è riportato
con `available: false` e NON sporca `warnings`/`github_fetch_errors`
(il 404 è stato normale, non un errore).

## Valori null

I campi `open_prs`, `open_issues`, `open_discussions` sono `null` in caso di errore fetch.
Le sezioni `radar`, `source_health`, `pipeline_state` sono `null` se
l'artifact upstream non è disponibile o non è stato ancora prodotto.
