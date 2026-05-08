# Session Bootstrap

**Generated**: 2026-05-08T13:50:17.648348

## 🔍 SCOUTING

**Radar**: 16 fonti — GREEN 9 · YELLOW 3 · RED 4 (probe: 2026-05-08)
  ⚠ **2 persistent RED**
  · **istat_sdmx** RED [-] — Probe exception non gestita: ReadTimeout: HTTPSConnectionPool(host='esploradati.istat.it', port=443): Read timed out. (read timeout=10)
  · **anac** YELLOW [403]
  · **dati_salute** RED [-] — SSL verify failed; fallback connection error (SSLError) (streak 8)
  · **dati_camera** RED [503]
  · **lavoro_opendata** YELLOW [200] — CKAN API returned non-JSON content
  · **mur_ustat** RED [-] — Probe exception non gestita: ConnectTimeout: HTTPSConnectionPool(host='dati-ustat.mur.gov.it', port=443): Max retries exceeded with url: /api/3/action/package_list?limit=1 (Caused by ConnectTimeoutError(<HTTPSConnection(host='dati-ustat.mur.gov.it', port=443) at 0x7fa7de546840>, 'Connection to dati-ustat.mur.gov.it timed out. (connect timeout=10)')) (streak 8)
  · **opencoesione** YELLOW [403]
**Catalog Drift**: no drift signals (12 sources checked)
**Portal Scout**: unavailable

## 📥 INTAKE

**Pipeline**: 29 candidates — 29 ok
  ⚠️ **camera-deputati-legislature** — run fallito [2024](https://github.com/dataciviclab/dataset-incubator/actions/runs/25509412527)
  ⚠️ **mur-contribuzione-universitaria** — run fallito [2024](https://github.com/dataciviclab/dataset-incubator/actions/runs/25509412527)
  ⚠️ **pensioni-pa-dag** — run fallito [2024](https://github.com/dataciviclab/dataset-incubator/actions/runs/25509412527)
**Dataset Catalog**: 9 clean_ready · 9 public · updated 2026-05-04

## 🔗 OPEN

> Warning: GitHub fetch error — dati incompleti
- [agent-context-builder#32](https://github.com/dataciviclab/agent-context-builder/pull/32): chore: remove orphan portal_scout code (SO no longer produces it)
- [dataset-incubator#259](https://github.com/dataciviclab/dataset-incubator/pull/259): intake: MEF IRPEF regionale — redditi per regione e classe, 2017-2025
- **Dependabot**: 4 bump PR(s)
**Discussions**: 20 open
  · [Analisi] AIFA Spesa Farmaceutica — il cardiovascolare traina il 63% della spesa, il divario Nord-Sud si allarga
  · [Domanda] Quanta parte delle entrate tributarie dipende da poche voci e quanto è diffuso?
  · [Domanda] Dove si accumulano più cause pendenti in rapporto alla popolazione?
**Topics**: pipeline · governance

## 🛠 INFRA

**Repos**: 6 attivi
**Local git**: no workspace
