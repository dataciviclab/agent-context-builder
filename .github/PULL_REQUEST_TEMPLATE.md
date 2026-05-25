## Sintesi

Descrivi in poche righe cosa cambia e perché.

## Contesto collegato

Closes #

## Cosa cambia

- [ ] Nuovo artifact o modifica schema (session_bootstrap / triage / topic_index)
- [ ] Modifica builder (src/)
- [ ] Modifica configurazione (dataciviclab.config.yml)
- [ ] Bug fix
- [ ] CI / deploy
- [ ] Dipendenze
- [ ] Documentazione

## Impatto su artifact upstream

ACB consuma artifact da source-observatory e dataset-incubator.

- [ ] Dipendenza da nuovo artifact upstream → issue aperta nel repo produttore
- [ ] Modifica schema artifact prodotto → verificato che i consumer (MCP tools) siano allineati
- [ ] Nessun impatto su artifact

## Verifica

```bash
pytest tests/
ruff check src/
```

- [ ] `pytest tests/` passa
- [ ] `ruff check src/` passa
- [ ] Build manuale verificata: `agent-context build --config dataciviclab.config.yml --out generated/`

## Checklist PR

- [ ] Perimetro stretto: una PR = un tema o un fix
- [ ] Issue collegata o motivazione dell'assenza

## Note per chi revisiona

Rischi, limiti, punti da controllare con attenzione.
