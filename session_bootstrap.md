# Session Bootstrap

**Generated**: 2026-04-22T16:58:12.222006

## Repos

- **agent-context-builder**: Genera contesto operativo compatto per gli agenti di DataCivicLab a partire da GitHub e, opzionalmente, da checkout locali dei repo Lab.
- **dataset-incubator**: dataset-incubator è il repo dove il Lab fa intake, verifica e incubazione leggera dei filoni dataset prima della promozione verso dataciviclab o una repo progetto dedicata.
- **dataciviclab**: dataciviclab è l’hub pubblico dell’ecosistema, pensato per spiegare chi siamo, cosa facciamo e come orientarsi tra le repo.
- **toolkit**: Toolkit è il motore tecnico di DataCivicLab per eseguire pipeline dati riproducibili da dataset.yml, da RAW a CLEAN e MART, con validazione, tracking e output leggibili dai notebook.
- **data-explorer**: Frontend pubblico dati civici - Evidence.dev + DuckDB + GCS
- **source-observatory**: Piccolo intelligence layer per fonti pubbliche: radar, catalog-watch, monitoraggio risorse e workflow di source-check.

## Open PRs

- [dataset-incubator#153](https://github.com/dataciviclab/dataset-incubator/pull/153): feat(intake): MUR contribuzione universitaria — gettito per ateneo (2017-2024)
- [toolkit#147](https://github.com/dataciviclab/toolkit/pull/147): feat(ckan): supporta la selezione della resource per nome
- **Dependabot**: 3 bump PR(s) - [#152](https://github.com/dataciviclab/dataset-incubator/pull/152), [#60](https://github.com/dataciviclab/data-explorer/pull/60) ...

## Open Discussions

- [dataciviclab#228](https://github.com/orgs/dataciviclab/discussions/228) [Datasets]: Consip partecipazioni — geografia delle imprese nelle gare pubbliche (2023-2025)
- [dataciviclab#227](https://github.com/orgs/dataciviclab/discussions/227) [Datasets]: MUR DSU Regionale — posti alloggio e borse per regione e ateneo (2024-2025)
- [dataciviclab#175](https://github.com/orgs/dataciviclab/discussions/175) [Annunci]: Nuove categorie, stesso obiettivo: rendere piu' chiaro il passaggio da fonte a lettura pubblica
- [dataciviclab#214](https://github.com/orgs/dataciviclab/discussions/214) [Datasets]: ISTAT povertà assoluta e relativa: incidenze, intensità e soglie (2014-2024)
- [dataciviclab#211](https://github.com/orgs/dataciviclab/discussions/211) [Datasets]: MUR contribuzione universitaria: tasse, esoneri e diritto allo studio per ateneo (2009-2024)
- [dataciviclab#210](https://github.com/orgs/dataciviclab/discussions/210) [Domande]: La geografia del calo iscrizioni nelle scuole primarie (2015-2024)
- [dataciviclab#218](https://github.com/orgs/dataciviclab/discussions/218) [Analisi]: [Analisi] Entrate dello Stato 2008-2024: nelle crisi cresce il peso dei prestiti?
- [dataciviclab#224](https://github.com/orgs/dataciviclab/discussions/224) [Metodo]: Come funziona il flusso tra repo Lab — e cosa manca?
- [dataciviclab#223](https://github.com/orgs/dataciviclab/discussions/223) [Datasets]: INPS ReI — evoluzione spesa e platea beneficiari 2018-2019
- [dataciviclab#182](https://github.com/orgs/dataciviclab/discussions/182) [Datasets]: ISTAT Terzo Settore: istituzioni non-profit per comune (2011, 2015, 2017, 2020)

## Local State

*No local git repos found*

## Topics

- pipeline
- governance

## Radar Status

Fonti: 13 — GREEN 5 · YELLOW 8 · RED 0 (probe: 2026-04-22)

- **istat_sdmx** (sdmx): YELLOW [HTTP -]
- **anac** (ckan): YELLOW [HTTP 403]
- **openbdap** (ckan): YELLOW [HTTP -]
- **dati_salute** (html): YELLOW [HTTP -]
- **consip_open_data** (ckan): YELLOW [HTTP -]
- **lavoro_opendata** (ckan): YELLOW [HTTP 200]
- **mur_ustat** (ckan): YELLOW [HTTP -]
- **opencoesione** (rest): YELLOW [HTTP 403]

## Catalog Drift

- **openbdap** (ckan): inventory change
  - azione: verificare se variazione attesa; avviare catalog-inventory-scout se nuovi dataset
  *(captured 2026-04-21T10:18:46+00:00, 9 sources checked)*

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
