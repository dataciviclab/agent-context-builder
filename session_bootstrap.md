# Session Bootstrap

**Generated**: 2026-04-19T11:32:13.214068

## Repos

- agent-context-builder
- dataset-incubator
- dataciviclab
- toolkit
- data-explorer
- source-observatory

## Open PRs

- [agent-context-builder#22](https://github.com/dataciviclab/agent-context-builder/pull/22): feat: consuma discovered_portals_summary.json (portal scout)
- [dataset-incubator#149](https://github.com/dataciviclab/dataset-incubator/pull/149): feat: workflow post-merge per run locale e push GCS candidati
- [dataset-incubator#146](https://github.com/dataciviclab/dataset-incubator/pull/146): Aggiunge scaffold candidate da template
- [dataset-incubator#137](https://github.com/dataciviclab/dataset-incubator/pull/137): Feat/istat delitti 2024
- [source-observatory#119](https://github.com/dataciviclab/source-observatory/pull/119): feat: portal-scout — discovery, scout strutturale e workflow agente
- **Dependabot**: 1 bump PR(s) - [#52](https://github.com/dataciviclab/data-explorer/pull/52)

## Open Discussions

- [dataset-incubator#77](https://github.com/dataciviclab/dataset-incubator/discussions/77) [Datasets]: [Dataset] Pensioni della PA per tipo e territorio – MEF DAG 2017-2026
- [dataset-incubator#75](https://github.com/dataciviclab/dataset-incubator/discussions/75) [Datasets]: [Dataset] Fondo di Solidarieta Comunale 2025 - OpenCivitas/Sogei (comuni RSO)
- [dataciviclab#224](https://github.com/orgs/dataciviclab/discussions/224) [Metodo]: Come funziona il flusso tra repo Lab — e cosa manca?
- [dataciviclab#223](https://github.com/orgs/dataciviclab/discussions/223) [Datasets]: INPS ReI — evoluzione spesa e platea beneficiari 2018-2019
- [dataciviclab#182](https://github.com/orgs/dataciviclab/discussions/182) [Datasets]: ISTAT Terzo Settore: istituzioni non-profit per comune (2011, 2015, 2017, 2020)
- [dataciviclab#165](https://github.com/orgs/dataciviclab/discussions/165) [Datasets]: [Dataset] Partecipazioni pubbliche dichiarate – MEF 2023
- [dataciviclab#149](https://github.com/orgs/dataciviclab/discussions/149) [Datasets]: ISTAT Ciclo dell'acqua - prelievo vs distribuzione, perdite idriche per distretto
- [dataciviclab#218](https://github.com/orgs/dataciviclab/discussions/218) [Analisi]: [Analisi] Entrate dello Stato 2008-2024: nelle crisi cresce il peso dei prestiti?
- [dataciviclab#217](https://github.com/orgs/dataciviclab/discussions/217) [Datasets]: RdC INPS - Nuclei con disabili: distribuzione provinciale dei beneficiari (2019-2020)
- [dataciviclab#216](https://github.com/orgs/dataciviclab/discussions/216) [Datasets]: ANF INPS - Assegni al nucleo familiare, beneficiari e importi (2016-2020)

## Local State

*No local git repos found*

## Topics

- agent-context-builder
- toolkit
- datasets
- analytics

## Radar Status

Fonti: 13 — GREEN 9 · YELLOW 3 · RED 1 (probe: 2026-04-19)

- **anac** (ckan): YELLOW [HTTP 403]
- **dati_salute** (html): RED [HTTP -]
- **mur_ustat** (ckan): YELLOW [HTTP -]
- **opencoesione** (rest): YELLOW [HTTP 403]

## Source Health

- **istat_sdmx** (sdmx): regressione — Errore: SDMX fetch failed after 3 attempts for istat_sdmx on https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1: tentativo 1: ConnectTimeout (https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1), tentativo 2: ConnectTimeout (https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1), tentativo 3: ConnectTimeout (https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1)
  - azione: monitorare nei prossimi run
- **openbdap** (ckan): regressione — Errore: HTTPSConnectionPool(host='bdap-opendata.rgs.mef.gov.it', port=443): Max retries exceeded with url: /SpodCkanApi/api/3/action/package_list (Caused by ConnectTimeoutError(<HTTPSConnection(host='bdap-opendata.rgs.mef.gov.it', port=443) at 0x7f658ce00d10>, 'Connection to bdap-opendata.rgs.mef.gov.it timed out. (connect timeout=60)'))
  - azione: monitorare nei prossimi run
- **consip_open_data** (ckan): regressione — Errore: HTTPSConnectionPool(host='dati.consip.it', port=443): Max retries exceeded with url: /api/3/action/package_list (Caused by ConnectTimeoutError(<HTTPSConnection(host='dati.consip.it', port=443) at 0x7f658cd450d0>, 'Connection to dati.consip.it timed out. (connect timeout=60)'))
  - azione: monitorare nei prossimi run
- **mur_ustat** (ckan): regressione — Errore persistente: HTTPSConnectionPool(host='dati-ustat.mur.gov.it', port=443): Max retries exceeded with url: /api/3/action/package_list (Caused by ConnectTimeoutError(<HTTPSConnection(host='dati-ustat.mur.gov.it', port=443) at 0x7f658cd48470>, 'Connection to dati-ustat.mur.gov.it timed out. (connect timeout=60)')) (messaggio cambiato rispetto al run precedente)
  - azione: valutare declassamento a radar-only se persiste
  *(captured 2026-04-18T10:39:20+00:00, 9 sources checked)*

## Pipeline State

*16 candidates, tutti ok*
  *(as of 2026-04-16 — 16 ok)*

## Dataset Catalog

*7 clean_ready dataset(s), 7 public* (updated 2026-04-14)
- **bdap_entrate_stato** (clean_ready, public): BDAP Entrate Stato - Serie Storica [2008-2024] - 2 metric, 9 dimension columns - `gs://dataciviclab-clean/bdap_entrate_stato/2024/bdap_entrate_stato_2024_clean.parquet`
- **civile_flussi_2014_2024** (clean_ready, public): Giustizia Civile - Flussi 2014-2024 [2014-2024] - 3 metric, 7 dimension columns - `gs://dataciviclab-clean/civile_flussi_2014_2024/2024/civile_flussi_2014_2024_2024_clean.parquet`
- **dipendenti_pubblici** (clean_ready, public): Dipendenti Pubblici - Occupazione e Turnover [2010-2023] - 14 metric, 13 dimension columns - `gs://dataciviclab-clean/dipendenti_pubblici/*/dipendenti_pubblici_*_clean.parquet`
- **ispra_consumo_suolo** (clean_ready, public): ISPRA - Consumo di Suolo 2024 [2024] - 3 metric, 4 dimension columns - `gs://dataciviclab-clean/ispra_consumo_suolo/2024/ispra_consumo_suolo_2024_clean.parquet`
- **ispra_ru_base** (clean_ready, public): ISPRA - Rifiuti Urbani (dati base) [2020-2024] - 3 metric, 6 dimension columns - `gs://dataciviclab-clean/ispra_ru_base/*/ispra_ru_base_*_clean.parquet`
- **ispra_ru_costi_kg** (clean_ready, public): ISPRA - Costi gestione rifiuti (EUR/kg) [2020-2024] - 6 metric, 5 dimension columns - `gs://dataciviclab-clean/ispra_ru_costi_kg/*/ispra_ru_costi_kg_*_clean.parquet`
- **ispra_ru_costi_procapite** (clean_ready, public): ISPRA - Costi gestione rifiuti (EUR/abitante) [2020-2024] - 9 metric, 5 dimension columns - `gs://dataciviclab-clean/ispra_ru_costi_procapite/*/ispra_ru_costi_procapite_*_clean.parquet`
