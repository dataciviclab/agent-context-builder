# Session Bootstrap

**Generated**: 2026-05-06T19:47:28.939072

## 🔍 SCOUTING

**Radar**: 15 fonti — GREEN 10 · YELLOW 3 · RED 2 (probe: 2026-05-06)
  ⚠ **2 persistent RED**
  · **anac** YELLOW [403]
  · **dati_salute** RED [-] — SSL verify failed; fallback connection error (SSLError) (streak 6)
  · **lavoro_opendata** YELLOW [200] — CKAN API returned non-JSON content
  · **mur_ustat** RED [-] — Probe exception non gestita: ConnectTimeout: HTTPSConnectionPool(host='dati-ustat.mur.gov.it', port=443): Max retries exceeded with url: /api/3/action/package_list?limit=1 (Caused by ConnectTimeoutError(<HTTPSConnection(host='dati-ustat.mur.gov.it', port=443) at 0x7f2b9e829250>, 'Connection to dati-ustat.mur.gov.it timed out. (connect timeout=10)')) (streak 6)
  · **opencoesione** YELLOW [403]
**Catalog Drift**: no drift signals (12 sources checked)
**Portal Scout**: unavailable

## 📥 INTAKE

**Pipeline**: 28 candidates — 28 ok
  ⚠️ **mit-incidentalita-mensile-2001-2018** — run fallito [2001](https://github.com/dataciviclab/dataset-incubator/actions/runs/25156933674)
**Dataset Catalog**: 9 clean_ready · 9 public · updated 2026-05-04

## 🔗 OPEN

> Warning: GitHub fetch error — dati incompleti
- [agent-context-builder#32](https://github.com/dataciviclab/agent-context-builder/pull/32): chore: remove orphan portal_scout code (SO no longer produces it)
- [dataset-incubator#259](https://github.com/dataciviclab/dataset-incubator/pull/259): intake: MEF IRPEF regionale — redditi per regione e classe, 2017-2025
- [toolkit#215](https://github.com/dataciviclab/toolkit/pull/215): test: marca 3 file test con policy/contract/pure_unit markers
- **Dependabot**: 4 bump PR(s)
**Discussions**: 20 open
  · [Analisi] AIFA Spesa Farmaceutica — il cardiovascolare traina il 63% della spesa, il divario Nord-Sud si allarga
  · [Domanda] Quanta parte delle entrate tributarie dipende da poche voci e quanto è diffuso?
  · [Domanda] Dove si accumulano più cause pendenti in rapporto alla popolazione?
**Topics**: pipeline · governance

## 🛠 INFRA

**Repos**: 6 attivi
**Local git**: no workspace
