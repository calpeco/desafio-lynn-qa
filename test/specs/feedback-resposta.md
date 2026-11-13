---
id: FDBK
titulo: Avaliação de respostas do agente
area: api
status: pronta
---

# Avaliação de respostas do agente

## Contexto
A pessoa usuária avalia cada resposta do agente com 👍 (útil) ou 👎 (não útil) e,
opcionalmente, deixa um comentário. As avaliações alimentam a melhoria dos prompts e o
monitoramento de qualidade do LLM em produção. Fora de escopo: painel de análise das avaliações.

## Endpoints
- `POST /api/v1/conversations/{conversation_id}/messages/{message_id}/feedback` — registra ou substitui a avaliação.
  Corpo: `{"rating": "positive" | "negative", "comment": "texto opcional"}` → `200` com
  `{"message_id", "rating", "comment", "updated_at"}` (contrato `app/contracts/feedback_response.schema.json`).
- `GET /api/v1/conversations/{conversation_id}`: cada mensagem traz o campo `feedback` (`null` ou o objeto acima, sem `message_id`).

## Telas
| Elemento | data-testid | Observação |
|---|---|---|
| Botão 👍 na resposta do agente | `feedback-positive` | `aria-pressed="true"` quando escolhido |
| Botão 👎 na resposta do agente | `feedback-negative` | `aria-pressed="true"` quando escolhido |
| Agradecimento | `feedback-thanks` | texto "Obrigado pelo feedback!" após avaliar |
| Texto da mensagem | `message-text` | conteúdo da bolha, sem os botões |

## Regras de negócio
- **RN01** — Somente respostas do agente concluídas podem ser avaliadas; avaliar mensagem da pessoa usuária retorna 422 `FEEDBACK_NOT_ALLOWED`. [camadas: unit, api] [riscos: R09]
- **RN02** — A avaliação é obrigatória e aceita apenas `positive` ou `negative`; outro valor, ausente ou de outro tipo retorna 422 `VALIDATION_ERROR`. [camadas: unit, api] [riscos: R09]
- **RN03** — O comentário é opcional, com até 500 caracteres após remover espaços das bordas; comentário só com espaços equivale a sem comentário (`null`). [camadas: unit, api] [riscos: R09]
- **RN04** — Cada resposta tem no máximo uma avaliação: avaliar de novo substitui a anterior. [camadas: unit, api, ui] [riscos: R02]
- **RN05** — Somente a dona da conversa pode avaliar; conversa alheia ou inexistente retorna 404 `CONVERSATION_NOT_FOUND`, e mensagem inexistente retorna 404 `MESSAGE_NOT_FOUND`. [camadas: api] [riscos: R01]
- **RN06** — É possível avaliar respostas de uma conversa já encerrada. [camadas: api]
- **RN07** — A avaliação aparece no histórico da conversa, no campo `feedback` da mensagem avaliada. [camadas: api] [riscos: R17]
- **RN08** — O texto do comentário nunca é registrado nos logs (pode conter dados pessoais). [camadas: api] [riscos: R12]
- **RN09** — Na interface, cada resposta do agente mostra 👍/👎; ao avaliar, aparece "Obrigado pelo feedback!" e o botão escolhido fica destacado. [camadas: ui]

## Critérios de aceite
```gherkin
@RN07 @smoke
Cenário: Avaliar positivamente uma resposta do agente
  Dado que a API de conversas está disponível
  E que "Alice" tem uma conversa aberta
  E que "Alice" enviou a mensagem "Qual o horário de atendimento?"
  Quando "Alice" avalia a última resposta do agente como "positive" com o comentário "Resposta clara"
  Então a resposta tem status 200
  E a resposta segue o contrato "feedback_response"
  E a última resposta do agente no histórico tem avaliação "positive" com o comentário "Resposta clara"
```

```gherkin
@RN05 @security
Cenário: Outra pessoa não avalia resposta em conversa alheia
  Dado que a API de conversas está disponível
  E que "Alice" tem uma conversa aberta
  E que "Alice" enviou a mensagem "oi"
  Quando "Bob" avalia a última resposta do agente na conversa de "Alice" como "negative"
  Então a resposta tem status 404 e código de erro "CONVERSATION_NOT_FOUND"
```

```gherkin
@RN09 @ui
Cenário: Avaliar uma resposta pela interface
  Dado que a API de conversas está disponível
  E que "Alice" entrou no chat pela interface
  Quando inicia na interface uma nova conversa com o "Agente de suporte"
  E envia na interface a mensagem "Qual o horário de atendimento?"
  E avalia na interface a última resposta do agente com 👍
  Então a interface agradece a avaliação
  E o botão 👍 da última resposta fica destacado
```

## Dados de teste
Personas `Alice` e `Bob`. Comentário: limites de 500 e 501 caracteres, comentário só com espaços,
comentário com dado pessoal (ex.: CPF) para a RN08.

## Premissas e dúvidas
- **P1** — Avaliar não muda o histórico além do campo `feedback` (não cria mensagem nova).
- **D1** — A pessoa pode **remover** a avaliação? Fora de escopo nesta versão (não há endpoint).
