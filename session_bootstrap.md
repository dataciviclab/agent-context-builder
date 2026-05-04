# Session Bootstrap

**Generated**: 2026-05-04T14:03:15.444525

## 🔍 SCOUTING

**Radar**: 15 fonti — GREEN 9 · YELLOW 3 · RED 3 (probe: 2026-05-04)
  ⚠ **3 persistent RED**
  · **istat_sdmx** RED [-] — Probe exception non gestita: ReadTimeout: HTTPSConnectionPool(host='esploradati.istat.it', port=443): Read timed out. (read timeout=10) (streak 2)
  · **anac** YELLOW [403]
  · **dati_salute** RED [-] — SSL verify failed; fallback connection error (SSLError) (streak 4)
  · **lavoro_opendata** YELLOW [200] — CKAN API returned non-JSON content
  · **mur_ustat** RED [-] — Probe exception non gestita: ConnectTimeout: HTTPSConnectionPool(host='dati-ustat.mur.gov.it', port=443): Max retries exceeded with url: /api/3/action/package_list?limit=1 (Caused by ConnectTimeoutError(<HTTPSConnection(host='dati-ustat.mur.gov.it', port=443) at 0x7f258eefef90>, 'Connection to dati-ustat.mur.gov.it timed out. (connect timeout=10)')) (streak 4)
  · **opencoesione** YELLOW [403]
**Catalog Drift**: no drift signals (12 sources checked)
**Portal Scout**: unavailable

## 📥 INTAKE

**Pipeline**: 28 candidates — 28 ok
  ⚠️ **mit-incidentalita-mensile-2001-2018** — run fallito [2001](https://github.com/dataciviclab/dataset-incubator/actions/runs/25156933674)
**Dataset Catalog**: 9 clean_ready · 9 public · updated 2026-05-03

## 🔗 OPEN

> Warning: GitHub fetch error — dati incompleti
- [agent-context-builder#32](https://github.com/dataciviclab/agent-context-builder/pull/32): chore: remove orphan portal_scout code (SO no longer produces it)
- [dataset-incubator#252](https://github.com/dataciviclab/dataset-incubator/pull/252): chore(post-merge): aggiorna registry per PR #234
- [dataset-incubator#241](https://github.com/dataciviclab/dataset-incubator/pull/241): chore(post-merge): aggiorna registry per PR #240
- [dataset-incubator#200](https://github.com/dataciviclab/dataset-incubator/pull/200): chore(camera-deputati-legislature): compila entry clean catalog
- **Dependabot**: 2 bump PR(s)
**Discussions**: 20 open
  · [Domanda] Quanta parte delle entrate tributarie dipende da poche voci e quanto è diffuso?
  · [Domanda] Dove si accumulano più cause pendenti in rapporto alla popolazione?
  · [Domanda] La spesa farmaceutica regionale è proporzionale alla popolazione o ci sono regioni che spendono molto di più per abitante?
**Topics**: pipeline · governance

## 🛠 INFRA

**Repos**: 6 attivi
**Local git**: no workspace
