# Session Bootstrap

**Generated**: 2026-05-03T13:11:42.598194

## 🔍 SCOUTING

**Radar**: 14 fonti — GREEN 9 · YELLOW 3 · RED 2 (probe: 2026-05-03)
  ⚠ **2 persistent RED**
  · **anac** YELLOW [403]
  · **dati_salute** RED [-] — SSL verify failed; fallback connection error (SSLError) (streak 2)
  · **lavoro_opendata** YELLOW [200] — CKAN API returned non-JSON content
  · **mur_ustat** RED [-] — Probe exception non gestita: ConnectTimeout: HTTPSConnectionPool(host='dati-ustat.mur.gov.it', port=443): Max retries exceeded with url: /api/3/action/package_list?limit=1 (Caused by ConnectTimeoutError(<HTTPSConnection(host='dati-ustat.mur.gov.it', port=443) at 0x7f66b6271070>, 'Connection to dati-ustat.mur.gov.it timed out. (connect timeout=10)')) (streak 2)
  · **opencoesione** YELLOW [403]
**Catalog Drift**: no drift signals (12 sources checked)
**Portal Scout**: unavailable

## 📥 INTAKE

**Pipeline**: 28 candidates — 28 ok
  ⚠️ **mit-incidentalita-mensile-2001-2018** — run fallito [2001](https://github.com/dataciviclab/dataset-incubator/actions/runs/25156933674)
**Dataset Catalog**: 9 clean_ready · 9 public · updated 2026-05-03

## 🔗 OPEN

> Warning: GitHub fetch error — dati incompleti
- [dataset-incubator#241](https://github.com/dataciviclab/dataset-incubator/pull/241): chore(post-merge): aggiorna registry per PR #240
- [dataset-incubator#234](https://github.com/dataciviclab/dataset-incubator/pull/234): refactor(ispra-ru-costi-kg): sostituisce path hardcoded cross-fonte con support dichiarativo
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
