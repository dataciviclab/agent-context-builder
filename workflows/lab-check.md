---
name: lab-check
description: Skill invocabile come /lab-check per controllare le novità e lo stato del DataCivicLab tramite il server MCP dataciviclab-context.
license: MIT
metadata:
  version: "0.2"
  owner: "DataCivicLab"
  tags: [context, triage, check, mcp]
---

# Workflow: lab-check

Workflow canonico di `agent-context-builder`.
Versione: 0.2 - 2026-04-16

## Obiettivo di fase

Fornire agli agenti e ai contributor umani una procedura rapida per leggere lo stato strutturato del Lab (novità, blocchi, PR aperte, issue rilevanti) usando i tool MCP del builder di contesto.

Questo workflow serve a:

- orientarsi rapidamente nel Lab e nei task aperti
- individuare i repository o le discussion che richiedono attenzione prima di lavorare
- fare il punto e definire le priorità della sessione

Non serve a:

- estrarre repository o dataset per l'elaborazione diretta dal workspace (è puramente per contesto)
- sostituire skill operative di PR e file editing
- ispezionare il contenuto dettagliato del codice di una determinata applicazione

## Profilo operativo coperto

Questo workflow copre il profilo **shared-mode via MCP** (`dataciviclab-context`).

Il Lab ha due profili operativi distinti:

- **Shared-mode (MCP)** — Claude Code e agenti che leggono il contesto via server MCP. Questo è il profilo che questo workflow descrive.
- **Local-mode** — Codex o agenti con accesso diretto al git workspace locale. In questo caso il check dello stato parte dal git state reale, non dai tool MCP.

Se stai lavorando in local-mode, questo workflow non è il tuo percorso primario.

## Quando usarlo

Usalo quando hai già:

- iniziato una nuova sessione e non hai chiaro il contesto generale
- devi controllare se ci sono issue aperte, discussion o warning per una macro-area del Lab
- l'MCP server `dataciviclab-context` attivo e vuoi un quadro aggiornato

Non usarlo quando:

- sei già inquadrato su un task operativo piccolo in un singolo repo (es. fix di uno script in `toolkit`)
- devi compilare layer puliti o mart (usa le skill specifiche o tool in `toolkit`)

## Preconditions minime

- Server MCP `dataciviclab-context` avviato e accessibile all'agente.
- Intento esplorativo / di status check ben definito.

Nel dubbio:
- se sai già su che problema lavorare, salta questo check e vai dritto al file/issue.

## Stop rules

Fermati e non forzare il workflow quando:

- l'agente o il server non riescono a ottenere i json o le dipendenze per rispondere ai tool
- il `session_bootstrap` restituisce un contesto obsoleto per motivi tecnici

## Passi canonici

### 1. Avvio sessione di base

Usa il tool `mcp__dataciviclab-context__session_bootstrap`.
- **Cosa fare:** Chiamare il tool via MCP.
- **Cosa controllare:** Leggere l'elenco dei repo attivi, le PR aperte, le discussion recenti e lo stato locale rilevante. 
- **Cosa evitare:** Ignorare blocchi di stato chiari segnalati nell'output.

### 2. Ispezione dei Topic e Triage

In base all'obiettivo operativo ci sono due percorsi:

- Se la sessione è tematica (es. "scouting su appalti" o topic affine):
  Usa `mcp__dataciviclab-context__topic_index` per capire dove guardare e valutare le path specifiche pertinenti in giro per il lab.
- Se si deve gestire lo stato incrociato di un repository:
  Usa `mcp__dataciviclab-context__workspace_triage` per ottenere le informazioni su git status, issue e le discussioni aggregate.

## Azioni opzionali e Troubleshooting

Se il contesto restituito è palesemente obsoleto rispetto a merge o push appena effettuati, puoi invocare `mcp__dataciviclab-context__refresh_context` per triggerare una rebuild della CI.
Attenzione: questo step impiegherà ~1 minuto prima di produrre un output aggiornato e **non** deve essere eseguito di default ogni volta, ma solo come eccezione.

## Errori tipici

- Entrare in una catena esplorativa lunga senza aver prima richiesto il `session_bootstrap`.
- Confondere triage su issue con la scrittura di commenti diretti sulle issue prima di validarne l'attualità.
- Ignorare la cache di GitHub in cui pesca il contesto; ricordati che può laggare rispetto allo stato git locale ultimissimo.

## Output minimo atteso

L'esito del workflow è considerato completo se l'agente o il contributor ha ottenuto un quadro chiaro sullo stato del Lab e sa cosa fare (o non fare) nella sessione.

Gli esiti validi sono tutti questi:

- Ha identificato un artifact (PR, issue, discussion) su cui concentrarsi.
- Ha constatato che non ci sono novità critiche e può proseguire sul task già in corso.
- Ha deciso di non fare nulla ora e ha una motivazione chiara.

Non è richiesta una classificazione formale dell'artifact né la selezione obbligatoria di un "prossimo passo".

## Definition of done

- Il report dello stato Lab è stato interpretato correttamente.
- Il focus della sessione è stato sbloccato o ristretto al passo immediatamente successivo da farsi nel workspace di interesse.

## Stati finali ammessi

- `checked` (l'orientamento è completato)
- `waiting-for-refresh` (trigger di aggiornamento fatto, serve attendere la CI)
- `blocked-on-context` (tool fallisce)

## Dove orientarsi

- README del repo `/agent-context-builder`
- [dataciviclab-context MCP] per il backend esecutivo legato all'esposizione
