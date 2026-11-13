# Specs: entrada da automação

Cada arquivo `*.md` aqui descreve **uma funcionalidade** no formato de [`_TEMPLATE.md`](_TEMPLATE.md).
A spec é lida por três consumidores:

| Consumidor | Usa |
|---|---|
| `test/scripts/qa_scaffold.py` (e o `agent-qa-lynn`) | front matter, regras `RNxx`, critérios de aceite em Gherkin, tabela de telas |
| `test/reports/cobertura.html` | regras e `[camadas: ...]` para montar a matriz de rastreabilidade |
| Pessoas (produto, dev, QA) | contexto, premissas e dúvidas |

Regras de ouro:
- **IDs estáveis.** Nunca renumere uma `RNxx`: as tags `@<ID>-RNxx` dos testes dependem delas. Regra removida vira "(removida)", e o número não é reaproveitado.
- **Uma regra verificável por linha.** "Rápido" não é verificável; "responde em até 10 s" é.
- **Camadas sugeridas** seguem a pirâmide: regra pura → `unit`; HTTP, estado e permissão → `api`; só o que exige navegador → `ui`.
- **`status: pronta`** só quando produto e QA concordam. O agente recusa specs em `rascunho`.

| Spec | ID | Regras |
|---|---|---|
| [conversa-com-agente.md](conversa-com-agente.md) | CONV | 13 |
| [feedback-resposta.md](feedback-resposta.md) | FDBK | 9 |
