---
name: lab-check
description: Check rapido delle novità e dello stato del Lab tramite MCP dataciviclab-context.
license: MIT
metadata:
  version: "0.2"
  owner: "DataCivicLab"
  tags: [context, triage, check, mcp]
---

# Workflow: lab-check

Obiettivo: orientarsi rapidamente su PR, issue, discussion, topic e blocchi operativi via MCP.

## Quando usarlo

- Inizio sessione senza quadro chiaro.
- Controllo warning, PR, issue o discussion per una macro-area.
- Triage tematico prima di aprire file o repo specifici.
- **Non usare** per task tecnici isolati, build dati o editing di codice.

## Profilo operativo

- **Shared-mode MCP**: percorso primario di questo workflow.
- **Local-mode git**: se hai il workspace locale, usa anche stato git reale e report locali.

Precondizione: server MCP `dataciviclab-context` accessibile.

## Passi canonici

1. **session_bootstrap**: prima chiamata. Leggi repo attivi, PR, issue, discussion e warning.
2. **topic_index**: usalo se la sessione è tematica e serve capire dove guardare.
3. **workspace_triage**: usalo se il problema riguarda stato incrociato di repo o issue.
4. **refresh_context**: solo se i dati sono palesemente obsoleti dopo merge/push. Attendere la CI.

## Stop rules ed errori

- Fermati se i tool MCP falliscono o restituiscono JSON non leggibile.
- Non usare `refresh_context` a ogni sessione: e' eccezione, non default.
- Non scrivere commenti o aprire issue solo da triage: valida l'attualità.
- Ricorda il lag fisiologico tra GitHub/CI e stato git locale.

## Output minimo

Il workflow è completo quando hai uno di questi esiti:

- artifact identificato: PR, issue, discussion o topic;
- nessuna novità critica: puoi continuare il task già noto;
- contesto bloccato: serve refresh o debug MCP.

## Stati finali
- `checked`: Orientamento completato, pronto al lavoro.
- `waiting-for-refresh`: Rebuild CI in corso.
- `blocked-on-context`: Errore tecnico dei tool context.

## Riferimenti
- README `agent-context-builder`
- MCP `dataciviclab-context`
