# Session Bootstrap

**Generated**: 2026-04-21T07:52:21.997615

## Repos

- **agent-context-builder**: Genera contesto operativo compatto per gli agenti di DataCivicLab a partire da GitHub e, opzionalmente, da checkout locali dei repo Lab.
- **dataset-incubator**: dataset-incubator è il repo dove il Lab fa intake, verifica e incubazione leggera dei filoni dataset prima della promozione verso dataciviclab o una repo progetto dedicata.
- **dataciviclab**: dataciviclab è l’hub pubblico dell’ecosistema, pensato per spiegare chi siamo, cosa facciamo e come orientarsi tra le repo.
- **toolkit**: Toolkit è il motore tecnico di DataCivicLab per eseguire pipeline dati riproducibili da dataset.yml, da RAW a CLEAN e MART, con validazione, tracking e output leggibili dai notebook.
- **data-explorer**: Frontend pubblico dati civici - Evidence.dev + DuckDB + GCS
- **source-observatory**: Piccolo intelligence layer per fonti pubbliche: radar, catalog-watch, monitoraggio risorse e workflow di source-check.

## Open PRs

- [agent-context-builder#25](https://github.com/dataciviclab/agent-context-builder/pull/25): chore: allinea ACB al boundary drift/inventory di SO #117
- [source-observatory#126](https://github.com/dataciviclab/source-observatory/pull/126): refactor: catalog_signals drift/inventory only + CATALOG_WATCH_REPORT auto-generato (SO #117)
- **Dependabot**: 3 bump PR(s) - [#152](https://github.com/dataciviclab/dataset-incubator/pull/152), [#60](https://github.com/dataciviclab/data-explorer/pull/60) ...

## Open Discussions

- [dataset-incubator#77](https://github.com/dataciviclab/dataset-incubator/discussions/77) [Datasets]: [Dataset] Pensioni della PA per tipo e territorio – MEF DAG 2017-2026
- [dataset-incubator#75](https://github.com/dataciviclab/dataset-incubator/discussions/75) [Datasets]: [Dataset] Fondo di Solidarieta Comunale 2025 - OpenCivitas/Sogei (comuni RSO)
- [dataciviclab#214](https://github.com/orgs/dataciviclab/discussions/214) [Datasets]: ISTAT povertà assoluta e relativa: incidenze, intensità e soglie (2014-2024)
- [dataciviclab#211](https://github.com/orgs/dataciviclab/discussions/211) [Datasets]: MUR contribuzione universitaria: tasse, esoneri e diritto allo studio per ateneo (2009-2024)
- [dataciviclab#210](https://github.com/orgs/dataciviclab/discussions/210) [Domande]: La geografia del calo iscrizioni nelle scuole primarie (2015-2024)
- [dataciviclab#218](https://github.com/orgs/dataciviclab/discussions/218) [Analisi]: [Analisi] Entrate dello Stato 2008-2024: nelle crisi cresce il peso dei prestiti?
- [dataciviclab#224](https://github.com/orgs/dataciviclab/discussions/224) [Metodo]: Come funziona il flusso tra repo Lab — e cosa manca?
- [dataciviclab#223](https://github.com/orgs/dataciviclab/discussions/223) [Datasets]: INPS ReI — evoluzione spesa e platea beneficiari 2018-2019
- [dataciviclab#182](https://github.com/orgs/dataciviclab/discussions/182) [Datasets]: ISTAT Terzo Settore: istituzioni non-profit per comune (2011, 2015, 2017, 2020)
- [dataciviclab#165](https://github.com/orgs/dataciviclab/discussions/165) [Datasets]: [Dataset] Partecipazioni pubbliche dichiarate – MEF 2023

## Local State

*No local git repos found*

## Topics

- pipeline
- governance

## Radar Status

Fonti: 13 — GREEN 6 · YELLOW 7 · RED 0 (probe: 2026-04-20)

- **istat_sdmx** (sdmx): YELLOW [HTTP -]
- **anac** (ckan): YELLOW [HTTP 403]
- **openbdap** (ckan): YELLOW [HTTP -]
- **dati_salute** (html): YELLOW [HTTP -]
- **consip_open_data** (ckan): YELLOW [HTTP -]
- **mur_ustat** (ckan): YELLOW [HTTP -]
- **opencoesione** (rest): YELLOW [HTTP 403]

## Source Health

- **mur_ustat** (ckan): regressione
  - azione: valutare declassamento a radar-only se persiste
- **istat_sdmx** (sdmx): recovery
- **openbdap** (ckan): recovery
- **consip_open_data** (ckan): recovery
  *(captured 2026-04-20T05:49:12+00:00, 9 sources checked)*

## Pipeline State

*16 candidates, tutti ok*
  *(as of 2026-04-16 — 16 ok)*

## Dataset Catalog

*7 clean_ready dataset(s), 7 public* (updated 2026-04-14)
- **bdap_entrate_stato** (public): BDAP Entrate Stato - Serie Storica [2008-2024]
- **civile_flussi_2014_2024** (public): Giustizia Civile - Flussi 2014-2024 [2014-2024]
- **dipendenti_pubblici** (public): Dipendenti Pubblici - Occupazione e Turnover [2010-2023]
- **ispra_consumo_suolo** (public): ISPRA - Consumo di Suolo 2024 [2024]
- **ispra_ru_base** (public): ISPRA - Rifiuti Urbani (dati base) [2020-2024]
- **ispra_ru_costi_kg** (public): ISPRA - Costi gestione rifiuti (EUR/kg) [2020-2024]
- **ispra_ru_costi_procapite** (public): ISPRA - Costi gestione rifiuti (EUR/abitante) [2020-2024]

## Portal Scout

Portali rilevati: 47 — nuovi candidati: 33 — strutturati confermati: 4

**Nuovi candidati strutturati:**
- `dati-coll.dfp.gov.it` — CKAN
- `indicepa.gov.it` — CKAN
- `dati.mit.gov.it` — CKAN
- `opendata-ercolano.cultura.gov.it` — CKAN
