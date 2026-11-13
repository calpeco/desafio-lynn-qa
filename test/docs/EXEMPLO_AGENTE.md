# Exemplo real: o `agent-qa-lynn` automatizando uma spec nova

Demonstração de que o projeto é reutilizável. Uma funcionalidade nova foi entregue pelo
"time de desenvolvimento", e o agente recebeu **apenas a spec em Markdown** e as próprias
instruções. Ele não teve nenhum contexto da construção do projeto.

## Entrada

- **Funcionalidade:** avaliar respostas do agente com 👍/👎 e comentário opcional. O endpoint
  `POST .../messages/{id}/feedback`, o campo `feedback` no histórico e os botões na interface já
  estavam implementados em `app/lynn_mock/`.
- **Plano gerado pelo scaffold para o agente:** [EXEMPLO_AGENTE_PLANO.md](EXEMPLO_AGENTE_PLANO.md).
- **Spec:** [`test/specs/feedback-resposta.md`](../specs/feedback-resposta.md), com 9 regras (RN01–RN09) e
  apenas **3** critérios de aceite em Gherkin. As outras regras ficaram para o agente cobrir.
- **Pedido:** *"use o agent-qa-lynn para automatizar test/specs/feedback-resposta.md"*.

## O que o agente fez (seguindo `.claude/agents/agent-qa-lynn.md`)

1. Leu `CLAUDE.md`, a spec e o [catálogo de steps](STEP_CATALOG.md).
2. Rodou `python test/scripts/qa_scaffold.py test/specs/feedback-resposta.md`. A spec passou na validação, e o
   plano apontou **13 passos reutilizáveis** e **6 a criar**.
3. Rodou `--write` e completou as features geradas, com os cenários de borda, negativos e de
   segurança que a spec não trazia em Gherkin.
4. Criou os testes unitários das regras puras (`app/lynn_mock/domain/feedback.py`), os steps e os
   métodos do Page Object.
5. Executou cada camada, rodou a feature nova 3 vezes (sem oscilação), rodou a pirâmide inteira
   em paralelo e conferiu o `cobertura.html`.
6. Testou o próprio teste: com `LYNN_FAULTS=idor`, o cenário de conversa alheia (RN05) ficou vermelho.

## Saída

| Camada | Arquivo | Casos |
|---|---|---|
| Unit | [`test/unit/test_feedback.py`](../unit/test_feedback.py) | 33 |
| API | [`test/features/api/10_avaliacao_de_respostas_do_agente.feature`](../features/api/10_avaliacao_de_respostas_do_agente.feature) | 34 |
| UI | [`test/features/ui/avaliacao_de_respostas_do_agente.feature`](../features/ui/avaliacao_de_respostas_do_agente.feature) | 3 |
| Steps | `test/features/steps/feedback_steps.py`, `test/features/steps/feedback_ui_steps.py` | 26 passos novos |
| Page Object | `test/features/pages/chat_page.py` (só métodos novos) | — |

A pirâmide da spec ficou saudável: 33 unitários, 34 de API e 3 de UI. A UI cobre só o que exige
navegador: os botões, o destaque e o agradecimento.

### Rastreabilidade entregue pelo agente

| RN | Unit | API | UI | O que cobre |
|---|---|---|---|---|
| RN01 | 5 | 1 | – | mensagem da pessoa; resposta não concluída |
| RN02 | 11 | 12 | – | ausente, nulo, vazio, caixa diferente, outro tipo, corpo que não é objeto |
| RN03 | 10 | 14 | – | 1, 500 e 501 caracteres; emoji; bordas; só espaços; tipo errado |
| RN04 | 1 | 3 | 2 | substituição; uma requisição com erro não apaga a avaliação anterior |
| RN05 | – | 5 | – | conversa alheia, mensagem alheia na própria conversa, inexistentes, 401 |
| RN06 | – | 1 | – | conversa encerrada |
| RN07 | 1 | 2 | 1 | histórico igual à resposta da API; nenhuma mensagem nova |
| RN08 | – | 2 | – | CPF fora dos logs, inclusive quando o pedido é rejeitado |
| RN09 | – | – | 3 | botões só nas respostas do agente, agradecimento, destaque, texto sem os botões |

## Consolidação posterior: pirâmide saudável

Na entrega do agente, a feature de API repetia a combinatória de validação (9 valores inválidos de
avaliação, 4 de comentário vazio e outros) que os 33 unitários dele já cobriam. Na revisão da
pirâmide do projeto, essa combinatória ficou **só no unitário**. A API manteve exemplos
representativos (34 → 20 cenários) sem perder cobertura de regra nem detecção de defeito. A regra
"combinatória no unit, 1 ou 2 exemplos por regra na API" foi incorporada às instruções do agente e
ao `CLAUDE.md`, e o gate `test/tooling/test_piramide.py` impede a regressão.

## Achados do agente, e o que foi feito com eles

| Achado do agente | Tratamento |
|---|---|
| **O log de evidências (`http_exchanges.jsonl`) gravava o comentário.** Com dados reais, isso violaria a própria RN08 | **Corrigido:** o cliente httpx mascara `comment`, CPF e cartão no log; teste em `test/tooling` |
| A RN04 (risco P1) não tinha defeito injetável | **Implementado:** `feedback_first_wins`. A feature 10 e a de UI ficam vermelhas com ele |
| O cliente httpx não tinha método de domínio para feedback | **Corrigido:** `ConversationsClient.give_feedback` |
| A spec não define qual erro vem primeiro quando há dois ao mesmo tempo, não cita autenticação e não diz o tipo do comentário | **Mantidos como dúvidas para produto.** O agente testou o comportamento atual sem inventar regra |

## Por que isso demonstra reuso

- **Entrada padronizada:** o template da spec e o scaffold transformam texto de produto em plano e esqueleto de testes.
- **Conhecimento do projeto codificado:** `CLAUDE.md`, as instruções do agente e o catálogo de steps fazem o agente seguir a pirâmide, reutilizar passos e manter a rastreabilidade sem precisar de explicação.
- **Integração sem configuração:** os shards do CI descobrem as features novas sozinhos, e o `cobertura.html` passa a mostrar a spec FDBK ao lado da CONV.
- **Senso crítico:** o agente não "passou no verde". Ele apontou lacunas da spec e um problema no próprio ferramental de evidências.
