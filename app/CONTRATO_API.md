# Contrato da API "Conversa com agente" (definido para o desafio)

> O enunciado descreve apenas os endpoints e as regras de negócio. Este documento fixa o
> contrato que a suíte valida. Tudo marcado com **[P-n]** é uma premissa minha e está
> listado também no README e no documento de estratégia.

Base: `/api/v1`. Corpo sempre JSON (`Content-Type: application/json`).

## Autenticação

- `Authorization: Bearer <token>`. Tokens fictícios no mock: `token-alice` (user `u_alice`),
  `token-bob` (user `u_bob`). **[P-1]** Ausente/ inválido → `401 UNAUTHENTICATED`.

## Cabeçalhos transversais

| Cabeçalho | Direção | Regra |
|---|---|---|
| `X-Request-ID` | req/resp | Se enviado, é ecoado; senão o servidor gera um UUID. **[P-2]** |
| `Idempotency-Key` | req | Opcional em `POST .../messages`. Mesma chave + mesmo corpo → mesma resposta, sem nova mensagem. Mesma chave + corpo diferente → `409 IDEMPOTENCY_KEY_REUSED`. Requisição concorrente com chave em processamento → `409 IDEMPOTENCY_IN_PROGRESS`. Escopo: (usuário, conversa, chave). TTL 24h. **[P-3]** |
| `Idempotent-Replayed: true` | resp | Presente quando a resposta é reaproveitada. |

## Envelope de erro (todas as respostas 4xx/5xx)

```json
{ "error": { "code": "CONVERSATION_CLOSED", "message": "texto para o usuário", "request_id": "..." } }
```

## Endpoints

### `POST /conversations` → `201`
Req: `{ "agent_id": "agt_support" }`. Agentes válidos no mock: `agt_support`, `agt_sales`.
`agt_retired` existe mas está desativado.
- `agent_id` ausente/não-string → `422 VALIDATION_ERROR`
- agente inexistente ou desativado → `422 AGENT_NOT_FOUND` **[P-4]**

Resp: objeto `Conversation` (ver abaixo) com `status: "open"` e `messages: []`.

### `POST /conversations/{id}/messages` → `201`
Req: `{ "content": "texto" }`.
- `content` obrigatório, string, 1..4000 caracteres **após** `strip()`; contagem por
  code points Unicode. Somente espaços → inválido. **[P-5]**
- Conversa encerrada → `409 CONVERSATION_CLOSED`
- Conversa inexistente **ou de outra pessoa** → `404 CONVERSATION_NOT_FOUND`
  (não 403, para não permitir enumeração de IDs). **[P-6]**

Resp `201`: `{ "user_message": Message, "assistant_message": Message }`.

Falha do provedor de LLM: a mensagem do usuário **é persistida** com `status: "failed"`
e a resposta é **[P-7]**:
- `503 LLM_UNAVAILABLE` (provedor fora/erro) ou `504 LLM_TIMEOUT` (excedeu o timeout de geração, padrão 10 s);
- `message` em linguagem natural para o usuário ("Não foi possível gerar uma resposta agora...");
- header `Retry-After`.
Reenvio após falha com a mesma `Idempotency-Key` reprocessa a geração **sem duplicar**
a mensagem do usuário (a falha não é "cacheada" como resposta final). Se a conversa já
avançou (há mensagens depois da que falhou), a resposta não é inserida "no passado": o
reenvio vira um novo turno ao final e a original permanece `failed`. Sem `Idempotency-Key`
o servidor não deduplica (limite conhecido). **[P-8]**

Ordem das checagens: autenticação → JSON → existência/dono (404) → encerrada (409) →
validação (422) → idempotência. Consequência: replay de uma chave após o encerramento
retorna `409`, não a resposta armazenada (decisão consciente: o estado atual prevalece).
O status "encerrada" é revalidado dentro do lock da conversa, para cobrir a corrida com
`close`; uma mensagem cuja geração já começou antes do `close` é concluída. Erros
inesperados retornam `500 INTERNAL_ERROR` no envelope padrão e liberam a chave. **[P-11]**

Processamento síncrono, até alguns segundos. **[P-9]** (Streaming/202 assíncrono fica como
pergunta aberta para produto/engenharia.)

### `GET /conversations/{id}` → `200`
Retorna `Conversation` com histórico ordenado por `seq` crescente (1, 2, 3 ...).

### `POST /conversations/{id}/close` → `200`
Encerra. Encerrar de novo é idempotente (`200`, mesmo estado). **[P-10]**

## Modelos

`Conversation`
```json
{ "id": "conv_...", "agent_id": "agt_support", "owner_id": "u_alice",
  "status": "open|closed", "created_at": "ISO-8601", "closed_at": null,
  "messages": [Message] }
```

`Message`
```json
{ "id": "msg_...", "seq": 1, "role": "user|assistant", "content": "...",
  "status": "completed|failed", "created_at": "ISO-8601",
  "metadata": { "model": "fake-llm-1", "latency_ms": 12, "prompt_tokens": 10,
                "completion_tokens": 20, "finish_reason": "stop" } }
```
`metadata` é obrigatório em mensagens `assistant` (custo/observabilidade) e `null` em `user`.

Schemas formais (JSON Schema draft 2020-12) em [`app/contracts/`](contracts).

## Frontend mínimo

`GET /` serve um chat (HTML/JS puro, `app/lynn_mock/web/static/`) usado pelos testes E2E. Ele
implementa a mitigação de cliente da Parte C: botão desabilitado durante o envio e uma
`Idempotency-Key` por mensagem, reutilizada no "Tentar novamente". Os seletores são
estáveis, via `data-testid`.

## Controle de teste (somente com `LYNN_TEST_CONTROL=1`)

`POST /__test__/llm` `{ "mode": "ok|error|timeout|slow|crash", "delay_ms": 0, "timeout_ms": 10000 }` — altera o
comportamento do LLM simulado. `POST /__test__/config` `{ "idempotency_ttl_s": 0 }` altera o TTL. `POST /__test__/reset` limpa o estado **e restaura a configuração padrão**. Nunca existiria em
produção; em ambiente real o equivalente seria um stub do provedor (WireMock/toxiproxy).

## Falhas injetáveis (`LYNN_FAULTS`, separadas por vírgula)

Usadas para provar que a suíte detecta defeitos reais ("testar os testes"):

| Flag | Defeito simulado | Feature que deve falhar |
|---|---|---|
| `no_idempotency` | Ignora `Idempotency-Key` (bug da Parte C) | `07_idempotencia.feature` |
| `idor` | Não verifica dono da conversa | `04_autenticacao_isolamento.feature` |
| `allow_closed` | Aceita mensagem em conversa encerrada | `05_ciclo_de_vida.feature` |
| `guardrail_off` | Sem filtro de saída: vaza prompt de sistema | `08_comportamento_llm.feature` |
| `context_leak` | Contexto do LLM compartilhado entre conversas | `08_comportamento_llm.feature` |
| `silent_llm_failure` | Falha do LLM vira 201 com resposta vazia | `06_falhas_do_llm.feature` |
| `off_by_one_limit` | Rejeita exatamente 4000 caracteres | `03_validacao_entrada.feature` |
| `stale_closed_check` | Checa "encerrada" só antes do lock da conversa (corrida com close) | `05_ciclo_de_vida.feature` |
| `feedback_first_wins` | Nova avaliação não substitui a anterior (RN04 da spec FDBK) | `10_avaliacao_de_respostas_do_agente.feature` |
| `ui_double_submit` | **Frontend**: botão não desabilita durante o envio e cada tentativa gera chave nova | `test/features/ui/chat_ui.feature` |
