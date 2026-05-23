# Session Bootstrap

**Generated**: 2026-05-23T19:11:45.043718

## 🔍 SCOUTING

**Radar**: 23 fonti — GREEN 17 · YELLOW 5 · RED 1 (probe: 2026-05-23)
  ⚠ **1 persistent RED**
  · **istat_sdmx** YELLOW [-] — Timeout (ReadTimeout)
  · **anac** YELLOW [403]
  · **dati_salute** RED [-] — SSL verify failed; fallback connection error (SSLError) (streak 14)
  · **lavoro_opendata** YELLOW [200] — CKAN API returned non-JSON content
  · **mur_ustat** YELLOW [-] — Retry timeout/connection: Timeout (ConnectTimeout)
  · **opencoesione** YELLOW [403]
**Catalog Drift**: no drift signals (15 sources checked)

## 📥 INTAKE

**Pipeline**: 32 candidates — 32 ok
  ⚠️ **camera-deputati-legislature** — run fallito [2024](https://github.com/dataciviclab/dataset-incubator/actions/runs/25509412527)
  ⚠️ **mur-contribuzione-universitaria** — run fallito [0](https://github.com/dataciviclab/dataset-incubator/actions/runs/26106467223)
**Dataset Catalog**: 11 published · 11 public · updated 2026-05-19

## 🗂 EXPLORER

**Pubblicati**: 8 dataset · 5 temi · [data-explorer](https://dataciviclab.github.io/data-explorer/)
  · **Territorio e ambiente**: rifiuti-urbani, capacita-rinnovabile
  · **Finanza pubblica**: irpef-comunale, entrate-stato
  · **Sanità**: spesa-farmaceutica
  · **Welfare e lavoro**: dipendenti-pubblici, pensioni-inps
  · **Giustizia**: flussi-giustizia-civile
  ⚠ 11 dataset published non ancora su explorer:
    · aifa_spesa_consumo
    · bdap_lea
    · civile_flussi
    · consip_consumi_convenzione
    · dipendenti_pubblici
    · ... e altri 6
  **Deploy**: ✅ success (2026-05-22)

## 🔗 OPEN

- [dataset-incubator#380](https://github.com/dataciviclab/dataset-incubator/pull/380): allinea flusso intake: go intake, scout --scaffold, new-analysis
- [dataset-incubator#360](https://github.com/dataciviclab/dataset-incubator/pull/360): chore: aggiunta directory figures per candidate MIT
- [data-explorer#105](https://github.com/dataciviclab/data-explorer/pull/105): feat(consip-consumi-convenzione): aggiungi dataset explorer e catalogo
- [data-explorer#104](https://github.com/dataciviclab/data-explorer/pull/104): feat(bdap-lea): aggiungi dataset explorer e catalogo
**Discussions**: 20 open
  · [Datasets] Giustizia Amministrativa — Quanto durano i ricorsi al CdS?
  · [Datasets] Corte Costituzionale — Come decide la Consulta?
  · [Datasets] Consip — Chi vince le gare pubbliche?
**Topics**: pipeline · governance · infrastructure

## 🛠 INFRA

**Repos**: 7 attivi
**Local git**: no workspace
