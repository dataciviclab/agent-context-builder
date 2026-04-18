# Session Bootstrap

**Generated**: 2026-04-18T14:27:52.150839

## Repos

- agent-context-builder
- dataset-incubator
- dataciviclab
- toolkit
- data-explorer
- source-observatory

## Open PRs

- [agent-context-builder#20](https://github.com/dataciviclab/agent-context-builder/pull/20): Consuma il clean catalog di dataset-incubator
- [agent-context-builder#19](https://github.com/dataciviclab/agent-context-builder/pull/19): Consume Source Observatory inventory summary
- [agent-context-builder#16](https://github.com/dataciviclab/agent-context-builder/pull/16): test(acb): audit suite — rimozione test banali
- [dataset-incubator#146](https://github.com/dataciviclab/dataset-incubator/pull/146): Aggiunge scaffold candidate da template
- [dataset-incubator#137](https://github.com/dataciviclab/dataset-incubator/pull/137): Feat/istat delitti 2024
- [source-observatory#113](https://github.com/dataciviclab/source-observatory/pull/113): test(so): audit suite — rimozione test banali
- **Dependabot**: 9 bump PR(s) - [#136](https://github.com/dataciviclab/toolkit/pull/136), [#55](https://github.com/dataciviclab/data-explorer/pull/55) ...

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
