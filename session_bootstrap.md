# Session Bootstrap

**Generated**: 2026-04-29T13:59:16.662976

## Repos

- **agent-context-builder**: Genera contesto operativo compatto per gli agenti di DataCivicLab a partire da GitHub e, opzionalmente, da checkout locali dei repo Lab.
- **dataset-incubator**: dataset-incubator è il repo dove il Lab fa intake, verifica e incubazione leggera dei filoni dataset prima della promozione verso dataciviclab o una repo progetto dedicata.
- **dataciviclab**: dataciviclab è l’hub pubblico dell’ecosistema, pensato per spiegare chi siamo, cosa facciamo e come orientarsi tra le repo.
- **toolkit**: Toolkit è il motore tecnico di DataCivicLab per eseguire pipeline dati riproducibili da dataset.yml, da RAW a CLEAN e MART, con validazione, tracking e output leggibili dai notebook.
- **data-explorer**: Frontend pubblico dati civici - Evidence.dev + DuckDB + GCS
- **source-observatory**: Piccolo intelligence layer per fonti pubbliche: radar, catalog-watch, monitoraggio risorse e workflow di source-check.

## Open PRs

- [dataset-incubator#200](https://github.com/dataciviclab/dataset-incubator/pull/200): chore(camera-deputati-legislature): compila entry clean catalog
- [dataset-incubator#199](https://github.com/dataciviclab/dataset-incubator/pull/199): chore: aggiungi support dataset bdap-anagrafe-enti
- [source-observatory#159](https://github.com/dataciviclab/source-observatory/pull/159): docs: audit fix — stale semantics, catalog_signals structure
- **Dependabot**: 4 bump PR(s) - [#29](https://github.com/dataciviclab/agent-context-builder/pull/29), [#63](https://github.com/dataciviclab/data-explorer/pull/63) ...

## Open Discussions

- [dataciviclab#240](https://github.com/orgs/dataciviclab/discussions/240) [Domanda]: Dove si accumulano più cause pendenti in rapporto alla popolazione?
- [dataciviclab#239](https://github.com/orgs/dataciviclab/discussions/239) [Domanda]: Quanta parte delle entrate tributarie dipende da poche voci e quanto è diffuso?
- [dataciviclab#238](https://github.com/orgs/dataciviclab/discussions/238) [Domanda]: La spesa farmaceutica regionale è proporzionale alla popolazione o ci sono regioni che spendono molto di più per abitante?
- [dataciviclab#237](https://github.com/orgs/dataciviclab/discussions/237) [Datasets]: BDAP MOP — soggetti titolari di Opere Pubbliche, per CUP e codice fiscale (2026)
- [dataciviclab#236](https://github.com/orgs/dataciviclab/discussions/236) [Datasets]: CONSIP MEPA — acquisti e appalti stipulati della PA, per provincia (2023-2025)
- [dataciviclab#234](https://github.com/orgs/dataciviclab/discussions/234) [Datasets]: BDAP Anagrafe Enti — copertura open data dei portali PA
- [dataciviclab#210](https://github.com/orgs/dataciviclab/discussions/210) [Domanda]: La geografia del calo iscrizioni nelle scuole primarie (2015-2024)
- [dataciviclab#228](https://github.com/orgs/dataciviclab/discussions/228) [Datasets]: Consip partecipazioni — geografia delle imprese nelle gare pubbliche (2023-2025)
- [dataciviclab#227](https://github.com/orgs/dataciviclab/discussions/227) [Datasets]: MUR DSU Regionale — posti alloggio e borse per regione e ateneo (2024-2025)
- [dataciviclab#175](https://github.com/orgs/dataciviclab/discussions/175) [Annunci]: Nuove categorie, stesso obiettivo: rendere piu' chiaro il passaggio da fonte a lettura pubblica

## Local State

*No local git repos found*

## Topics

- pipeline
- governance

## Radar Status

Fonti: 14 — GREEN 8 · YELLOW 3 · RED 3 (probe: 2026-04-29)

- **istat_sdmx** (sdmx): RED [HTTP -]
- **anac** (ckan): YELLOW [HTTP 403]
- **dati_salute** (html): RED [HTTP -]
- **lavoro_opendata** (ckan): YELLOW [HTTP 200]
- **mur_ustat** (ckan): RED [HTTP -]
- **opencoesione** (rest): YELLOW [HTTP 403]

## Catalog Drift

*No catalog drift signals* (as of 2026-04-27T06:09:57+00:00, 10 sources checked)

## Pipeline State

- **istat-ciclo-acqua-prelievo-distribuzione** [error]: anni: ? — fonte: ? — mart: no — ⚠ no dataset.yml and no sources/ directory
  - azione: correggere la struttura del candidato
  *(as of 2026-04-28 — 1 error, 26 ok)*

## Dataset Catalog

*5 clean_ready dataset(s), 5 public* (updated 2026-04-28)
- **bdap_entrate_stato** (public): BDAP Entrate Stato - Serie Storica [2008-2024]
- **ispra_ru_base** (public): ISPRA - Rifiuti Urbani (dati base) [2020-2024]
- **ispra_ru_costi_kg** (public): ISPRA - Costi gestione rifiuti (EUR/kg) [2020-2024]
- **ispra_ru_costi_procapite** (public): ISPRA - Costi gestione rifiuti (EUR/abitante) [2020-2024]
- **mur_contribuzione_universitaria** (public): MUR - Gettito della contribuzione universitaria [2017-2024]

## Portal Scout

Portali rilevati: 51 — nuovi candidati: 37 — strutturati confermati: 6

**Nuovi candidati strutturati:**
- `dati-coll.dfp.gov.it` — CKAN
- `dati.comune.mt.it` — CKAN
- `dati.toscana.it` — CKAN
- `dati.mit.gov.it` — CKAN
- `indicepa.gov.it` — CKAN
- `opendata-ercolano.cultura.gov.it` — CKAN
