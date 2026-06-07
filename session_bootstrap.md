# Session Bootstrap

**Generated**: 2026-06-07T04:00:07.243201

## 🔍 SCOUTING

**Radar**: 30 fonti — GREEN 25 · YELLOW 5 · RED 0 (probe: 2026-06-06)
  · **istat_sdmx** YELLOW [-] — Timeout (ConnectTimeout)
  · **openbdap** YELLOW [-] — Retry timeout/connection: Timeout (ConnectTimeout)
  · **dati_camera** YELLOW [404]
  · **consip_open_data** YELLOW [-] — Retry timeout/connection: Timeout (ConnectTimeout)
  · **mef_irpef** YELLOW [-] — Retry timeout/connection: Timeout (ConnectTimeout)
  · **openbdap** (ckan): inventory change — azione: verificare se variazione attesa; avviare inventory-triage se nuovi dataset

## 📥 INTAKE

**Pipeline**: 38 candidates — 38 ok
  ⚠️ **mur-contribuzione-universitaria** — run fallito [0](https://github.com/dataciviclab/dataset-incubator/actions/runs/26106467223)
**Dataset Catalog**: 25 published · 25 public · updated 2026-06-06

## 📊 ANALYSES

**Attive**: 10
  · **AIFA Spesa farmaceutica convenzionata 2018-2024** · → aifa_spesa_consumo · [discussion #242](https://github.com/orgs/dataciviclab/discussions/242)
  · **Camera votazioni 2018-2025** · → camera_votazioni_sparql
  · **Flussi giustizia civile 2014-2025** · → civile_flussi
  · **Consip Consumi Convenzione 2023-2025** · → consip_consumi_convenzione
  · **Dipendenti pubblici 2010-2023** · → dipendenti_pubblici
  · **BDAP Entrate Stato 2008-2024** · → bdap_entrate_stato · [discussion #218](https://github.com/orgs/dataciviclab/discussions/218)
  · **IRPEF comunale 2019-2023** · → irpef_comunale · [discussion #88](https://github.com/orgs/dataciviclab/discussions/88)
  · **Malasanità 2022: mortalità evitabile e dotazione sanitaria regionale** · → malasanita_struttura_mortalita · [discussion #99](https://github.com/orgs/dataciviclab/discussions/99)
  · **OpenCivitas FSC 2025 RSO** · → opencivitas_fsc_2025_rso
  · **Terna mix elettrico 2023-2024** · → terna_electricity_by_source · [discussion #115](https://github.com/orgs/dataciviclab/discussions/115)

## 🗂 EXPLORER

**Pubblicati**: 18 dataset · 5 temi · [data-explorer](https://dataciviclab.github.io/data-explorer/)
  · **Territorio e ambiente**: rifiuti-urbani, capacita-rinnovabile, produzione-elettrica-fonti, mit-incidentalita
  · **Finanza pubblica**: irpef-comunale, entrate-stato, consip-consumi-convenzione, istat-gini-regionale, opencivitas-fsc-2025
  · **Sanità**: spesa-farmaceutica, bdap-lea
  · **Welfare e lavoro**: dipendenti-pubblici, pensioni-inps, istat-ipab-aree, mim-alunni-corso-eta, popolazione-istat, housing-crowding
  · **Giustizia**: flussi-giustizia-civile
  ⚠ 25 dataset published non ancora su explorer:
    · aifa_spesa_consumo
    · bdap_anagrafe_enti
    · bdap_entrate_stato
    · bdap_lea
    · bdap_spese_stato
    · ... e altri 20
  **Deploy**: ✅ success (2026-06-06)

## 🔗 OPEN

- [dataset-incubator#462](https://github.com/dataciviclab/dataset-incubator/pull/462): feat: aggiunge compose malasanita (v1/v2/v3)
- [dataset-incubator#429](https://github.com/dataciviclab/dataset-incubator/pull/429): intake: istat_nonprofit — Censimento permanente Istituzioni non profit
- [toolkit#339](https://github.com/dataciviclab/toolkit/pull/339): feat(inspect): rename PROBE command to SPARQL
- [toolkit#336](https://github.com/dataciviclab/toolkit/pull/336): feat(core): espone dateformat, timestampformat, rejects_table in clean.read
- [data-explorer#139](https://github.com/dataciviclab/data-explorer/pull/139): feat(mef-partecipazioni): partecipazioni PA per categoria — conteggio, oneri, addetti
**Discussions**: 20 open
  · [Domanda] Pensioni pubbliche DAG: come si distribuisce la spesa per regione e tipo?
  · [Domanda] BDAP LEA: quanto pesa la prevenzione nelle ASL italiane?
  · [Domanda] Pensioni PA a carico dello Stato: come si distribuiscono per regione?
**Topics**: pipeline · governance · infrastructure · analyses

## 🛠 INFRA

**Repos**: 7 attivi
**Local git**: no workspace
