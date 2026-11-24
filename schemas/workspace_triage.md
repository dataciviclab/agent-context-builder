# workspace_triage.json — Schema v1

Pubblicato su branch `context`. Consumato da `lab-dashboard` e agenti MCP.

## Struttura

```json
{
  "generated_at": "2026-08-28T10:00:00",
  "repos": ["dataset-incubator", "eurostat", ...],
  "prs": [{"number": 1, "title": "...", "repo": "...", "url": "...", "category": "..."}],
  "issues": [{"number": 1, "title": "...", "repo": "...", "url": "...", "category": "..."}],
  "discussions": [{"number": 1, "title": "...", "repo": "...", "category": "..."}],
  "radar": {
    "available": true,
    "generated_at": "...",
    "probe_date": "2026-08-26",
    "sources_total": 36,
    "green": 35, "yellow": 0, "red": 1,
    "persistent_red": 1,
    "sources": [{"id": "...", "status": "GREEN", "protocol": "..."}],
    "unhealthy": [{"id": "...", "status": "RED", "note": "..."}]
  },
  "source_health": {"available": true, "sources_checked": 36, "regressions": [], "alerts": []},
  "pipeline_state": {"available": true, "summary": {"total": 0, "by_status": {}}, "actionable": []},
  "registry_summary": [
    {
      "repo": "dataset-incubator",
      "available": true,
      "datasets": 92, "marts": 149, "checks": 0, "codelists": 2, "gcs": 90
    }
  ],
  "git_state": {"repo": {"available": true, "branch": "main", "dirty": false}},
  "warnings": ["..."]
}
```

## v2 (registry) — cosa cambia

- `registry_summary[]`: niente più `signals`/`signals_detail`/`entities`. La
  freschezza per dataset vive in `topic_index.datasets[].last_run`
  (~190 KB in meno nel triage, che dcl-mcp strippava comunque).
- `pipeline_state` deriva dai `checks` del registry (anomalie), non più da una
  riga `signals` per dataset.

## MCP output

Default (senza section): riepilogo compatto.
Con `section=`: solo la sezione richiesta.

Sezioni disponibili: `radar`, `prs`, `issues`, `discussions`, `registry`, `git`, `warnings`, `pipeline`, `source_health`.
