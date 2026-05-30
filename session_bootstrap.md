# Session Bootstrap

**Generated**: 2026-05-30T08:29:00.604548

## 🔍 SCOUTING

**Radar**: 27 fonti — GREEN 24 · YELLOW 2 · RED 1 (probe: 2026-05-30)
  ⚠ **1 persistent RED**
  · **istat_sdmx** YELLOW [-] — Timeout (ReadTimeout)
  · **dati_salute** RED [-] — SSL verify failed; fallback connection error (SSLError) (streak 14)
  · **opencoesione** YELLOW [403]
**Catalog Drift**: no drift signals (22 sources checked)

## 📥 INTAKE

**Pipeline**: 33 candidates — 33 ok
  ⚠️ **mur-contribuzione-universitaria** — run fallito [0](https://github.com/dataciviclab/dataset-incubator/actions/runs/26106467223)
**Dataset Catalog**: 15 published · 15 public · updated 2026-05-29

## 📊 ANALYSES

**Attive**: 5
  · **IRPEF comunale 2019-2023** · → irpef_comunale · [discussion #88](https://github.com/orgs/dataciviclab/discussions/88)
  · **Flussi giustizia civile 2014-2025** · → civile_flussi
  · **"Malasanità 2022: mortalità evitabile e dotazione sanitaria regionale"** · → malasanita_struttura_mortalita · [discussion #99](https://github.com/orgs/dataciviclab/discussions/99)
  · **Terna mix elettrico 2023-2024** · → terna_electricity_by_source · [discussion #115](https://github.com/orgs/dataciviclab/discussions/115)
  · **Dipendenti pubblici 2010-2023** · → dipendenti_pubblici

## 🗂 EXPLORER

**Pubblicati**: 13 dataset · 5 temi · [data-explorer](https://dataciviclab.github.io/data-explorer/)
  · **Territorio e ambiente**: rifiuti-urbani, capacita-rinnovabile, produzione-elettrica-fonti
  · **Finanza pubblica**: irpef-comunale, entrate-stato, consip-consumi-convenzione, istat-gini-regionale
  · **Sanità**: spesa-farmaceutica, bdap-lea
  · **Welfare e lavoro**: dipendenti-pubblici, pensioni-inps, istat-ipab-aree
  · **Giustizia**: flussi-giustizia-civile
  ⚠ 15 dataset published non ancora su explorer:
    · aifa_spesa_consumo
    · bdap_entrate_stato
    · bdap_lea
    · civile_flussi
    · consip_consumi_convenzione
    · ... e altri 10
  **Deploy**: ✅ success (2026-05-29)

## 🔗 OPEN

- [toolkit#308](https://github.com/dataciviclab/toolkit/pull/308): feat: routing SPARQL in probe_url_routed + scaffold + fix _format_args
- [data-explorer#124](https://github.com/dataciviclab/data-explorer/pull/124): feat(opencivitas-fsc-2025): aggiungi dataset explorer — Fondo Solidarietà Comunale
- [source-observatory#302](https://github.com/dataciviclab/source-observatory/pull/302): feat: dataset grouping, enrich refactor con dispatch per protocollo, dead code removal
**Discussions**: 20 open
  · [Domanda] ASIA ISTAT — Quante imprese e addetti ci sono nel mio comune?
  · [Proposte] MCP adapters and source-check patterns for public data — cross-country comparison (FR/IT)
  · [Datasets] INPS ReI — evoluzione spesa e platea beneficiari 2018-2019
**Topics**: pipeline · governance · infrastructure · analyses

## 🛠 INFRA

**Repos**: 7 attivi
**Local git**: no workspace
