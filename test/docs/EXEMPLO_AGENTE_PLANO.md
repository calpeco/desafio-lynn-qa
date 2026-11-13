# Plano de automação — FDBK · Avaliação de respostas do agente

Spec: `test/specs/feedback-resposta.md`

## Validação da spec

- ✅ estrutura válida

## Regras × camadas da pirâmide

| Regra | Camadas sugeridas | Riscos | Critério na spec | Já automatizado (tags) |
|---|---|---|---|---|
| RN01 — Somente respostas do agente concluídas podem ser avaliadas; avaliar mensagem da pessoa usuária retorna 422 `FEEDBACK_NOT_ALLOWED`. | unit, api | R09 | não | unit:0 ⚠ · api:0 ⚠ · ui:0 |
| RN02 — A avaliação é obrigatória e aceita apenas `positive` ou `negative`; outro valor, ausente ou de outro tipo retorna 422 `VALIDATION_ERROR`. | unit, api | R09 | não | unit:0 ⚠ · api:0 ⚠ · ui:0 |
| RN03 — O comentário é opcional, com até 500 caracteres após remover espaços das bordas; comentário só com espaços equivale a sem comentário (`null`). | unit, api | R09 | não | unit:0 ⚠ · api:0 ⚠ · ui:0 |
| RN04 — Cada resposta tem no máximo uma avaliação: avaliar de novo substitui a anterior. | unit, api, ui | R02 | não | unit:0 ⚠ · api:0 ⚠ · ui:0 ⚠ |
| RN05 — Somente a dona da conversa pode avaliar; conversa alheia ou inexistente retorna 404 `CONVERSATION_NOT_FOUND`, e mensagem inexistente retorna 404 `MESSAGE_NOT_FOUND`. | api | R01 | sim | unit:0 · api:0 ⚠ · ui:0 |
| RN06 — É possível avaliar respostas de uma conversa já encerrada. | api | — | não | unit:0 · api:0 ⚠ · ui:0 |
| RN07 — A avaliação aparece no histórico da conversa, no campo `feedback` da mensagem avaliada. | api | R17 | sim | unit:0 · api:0 ⚠ · ui:0 |
| RN08 — O texto do comentário nunca é registrado nos logs (pode conter dados pessoais). | api | R12 | não | unit:0 · api:0 ⚠ · ui:0 |
| RN09 — Na interface, cada resposta do agente mostra 👍/👎; ao avaliar, aparece "Obrigado pelo feedback!" e o botão escolhido fica destacado. | ui | — | sim | unit:0 · api:0 · ui:0 ⚠ |

⚠ = camada sugerida na spec ainda sem nenhum caso com a tag da regra.


## Trabalho por camada

- **unit** (RN01, RN02, RN03, RN04): regra pura em app/lynn_mock/domain → teste em test/unit com @pytest.mark.trace
- **api** (RN01, RN02, RN03, RN04, RN05, RN06, RN07, RN08): cenário em test/features/api com steps httpx (reutilize o catálogo)
- **ui** (RN04, RN09): cenário em test/features/ui; seletores data-testid só em test/features/pages

## Passos a CRIAR (6)

- `when` → padrão sugerido: `"{v1:Q}" avalia a última resposta do agente como "{v2:Q}" com o comentário "{v3:Q}"`  
  usado em: Quando "Alice" avalia a última resposta do agente como "positive" com o comentário "Resposta clara"
- `then` → padrão sugerido: `a última resposta do agente no histórico tem avaliação "{v1:Q}" com o comentário "{v2:Q}"`  
  usado em: E a última resposta do agente no histórico tem avaliação "positive" com o comentário "Resposta clara"
- `when` → padrão sugerido: `"{v1:Q}" avalia a última resposta do agente na conversa de "{v2:Q}" como "{v3:Q}"`  
  usado em: Quando "Bob" avalia a última resposta do agente na conversa de "Alice" como "negative"
- `when` → padrão sugerido: `avalia na interface a última resposta do agente com 👍`  
  usado em: E avalia na interface a última resposta do agente com 👍
- `then` → padrão sugerido: `a interface agradece a avaliação`  
  usado em: Então a interface agradece a avaliação
- `then` → padrão sugerido: `o botão 👍 da última resposta fica destacado`  
  usado em: E o botão 👍 da última resposta fica destacado

## Passos REUTILIZADOS (13)

- `Dado que a API de conversas está disponível` → `api_available` (test/features/steps/common_steps.py)
- `E a resposta segue o contrato "feedback_response"` → `follows_contract` (test/features/steps/common_steps.py)
- `E envia na interface a mensagem "Qual o horário de atendimento?"` → `send_ui` (test/features/steps/ui_steps.py)
- `E que "Alice" entrou no chat pela interface` → `logged_in` (test/features/steps/ui_steps.py)
- `E que "Alice" enviou a mensagem "Qual o horário de atendimento?"` → `has_sent` (test/features/steps/conversation_steps.py)
- `E que "Alice" enviou a mensagem "oi"` → `has_sent` (test/features/steps/conversation_steps.py)
- `E que "Alice" tem uma conversa aberta` → `has_open_conversation` (test/features/steps/conversation_steps.py)
- `Então a resposta tem status 200` → `status_is` (test/features/steps/common_steps.py)
- `Então a resposta tem status 404 e código de erro "CONVERSATION_NOT_FOUND"` → `error_is` (test/features/steps/common_steps.py)
- `Quando inicia na interface uma nova conversa com o "Agente de suporte"` → `start_conversation` (test/features/steps/ui_steps.py)

## data-testid sem Page Object

- `feedback-negative`
- `feedback-positive`
- `feedback-thanks`
- `message-text`

## Arquivos gerados

- `test/features/api/10_avaliacao_de_respostas_do_agente.feature`
- `test/features/ui/avaliacao_de_respostas_do_agente.feature`
