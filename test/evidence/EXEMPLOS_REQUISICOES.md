# Exemplos de requisições e respostas (extraídos da execução real)

Gerado por `test/scripts/curate_examples.py` a partir de `test/evidence/latest/http_exchanges.jsonl` (log de todas as chamadas da camada de API; token mascarado).

## Fluxo feliz completo
Cenário: *Criar, conversar, consultar o histórico e encerrar*

```http
POST /api/v1/conversations
X-Request-ID: qa-b3cbadff-4e7e-4ced-b0bc-bb9f7691371b
Authorization: Bearer ***

{"agent_id": "agt_support"}

→ 201  (8 ms)  {"x-request-id": "qa-b3cbadff-4e7e-4ced-b0bc-bb9f7691371b"}
{
  "id": "conv_41b11c188af44fdb",
  "agent_id": "agt_support",
  "owner_id": "u_alice",
  "status": "open",
  "created_at": "2026-11-13T12:15:37.745Z",
  "closed_at": null,
  "messages": []
}
```

```http
POST /api/v1/conversations/conv_41b11c188af44fdb/messages
X-Request-ID: qa-85ac30ff-19a0-42b5-afd8-db5bc76906f6
Authorization: Bearer ***

{"content": "Qual o horário de atendimento?"}

→ 201  (3 ms)  {"x-request-id": "qa-85ac30ff-19a0-42b5-afd8-db5bc76906f6"}
{
  "user_message": {
    "id": "msg_f95f02483f5246a1",
    "seq": 1,
    "role": "user",
    "content": "Qual o horário de atendimento?",
    "status": "completed",
    "created_at": "2026-11-13T12:15:37.761Z",
    "reply_to": null,
    "metadata": null,
    "feedback": null
  },
  "assistant_message": {
    "id": "msg_93debd8cd9154f6c",
    "seq": 2,
    "role": "assistant",
    "content": "Entendi. O suporte está disponível em dias úteis, das 8h às 18h.",
    "status": "completed",
    "created_at": "2026-11-13T12:15:37.761Z",
    "reply_to": "msg_f95f02483f5246a1",
    "metadata": {
      "model": "fake-llm-1",
      "latency_ms": 0,
      "prompt_tokens": 25,
      "completion_tokens": 12,
      "finish_reason": "stop"
    },
    "feedback": null
  }
}
```

```http
GET /api/v1/conversations/conv_41b11c188af44fdb
X-Request-ID: qa-0b9ebea1-7a90-4df2-b888-c8fb684cd997
Authorization: Bearer ***

→ 200  (2 ms)  {"x-request-id": "qa-0b9ebea1-7a90-4df2-b888-c8fb684cd997"}
{
  "id": "conv_41b11c188af44fdb",
  "agent_id": "agt_support",
  "owner_id": "u_alice",
  "status": "open",
  "created_at": "2026-11-13T12:15:37.745Z",
  "closed_at": null,
  "messages": [
    {
      "id": "msg_f95f02483f5246a1",
      "seq": 1,
      "role": "user",
      "content": "Qual o horário de atendimento?",
      "status": "completed",
      "created_at": "2026-11-13T12:15:37.761Z",
      "reply_to": null,
      "metadata": null,
      "feedback": null
    },
    {
      "id": "msg_93debd8cd9154f6c",
      "seq": 2,
      "role": "assistant",
      "content": "Entendi. O suporte está disponível em dias úteis, das 8h às 18h.",
      "status": "completed",
      "created_at": "2026-11-13T12:15:37.761Z",
      "reply_to": "msg_f95f02483f5246a1",
      "metadata": {
        "model": "fake-llm-1",
        "latency_ms": 0,
        "prompt_tokens": 25,
        "completion_tokens": 12,
        "finish_reason": "stop"
      },
      "feedback": null
    }
  ]
}
```

```http
GET /api/v1/conversations/conv_41b11c188af44fdb
X-Request-ID: qa-923bd6cf-cfe4-4eca-b06e-fe215d785dac
Authorization: Bearer ***

→ 200  (1 ms)  {"x-request-id": "qa-923bd6cf-cfe4-4eca-b06e-fe215d785dac"}
{
  "id": "conv_41b11c188af44fdb",
  "agent_id": "agt_support",
  "owner_id": "u_alice",
  "status": "open",
  "created_at": "2026-11-13T12:15:37.745Z",
  "closed_at": null,
  "messages": [
    {
      "id": "msg_f95f02483f5246a1",
      "seq": 1,
      "role": "user",
      "content": "Qual o horário de atendimento?",
      "status": "completed",
      "created_at": "2026-11-13T12:15:37.761Z",
      "reply_to": null,
      "metadata": null,
      "feedback": null
    },
    {
      "id": "msg_93debd8cd9154f6c",
      "seq": 2,
      "role": "assistant",
      "content": "Entendi. O suporte está disponível em dias úteis, das 8h às 18h.",
      "status": "completed",
      "created_at": "2026-11-13T12:15:37.761Z",
      "reply_to": "msg_f95f02483f5246a1",
      "metadata": {
        "model": "fake-llm-1",
        "latency_ms": 0,
        "prompt_tokens": 25,
        "completion_tokens": 12,
        "finish_reason": "stop"
      },
      "feedback": null
    }
  ]
}
```

```http
POST /api/v1/conversations/conv_41b11c188af44fdb/close
X-Request-ID: qa-86ca38c3-19e1-4726-b9a9-2210ce497469
Authorization: Bearer ***

→ 200  (2 ms)  {"x-request-id": "qa-86ca38c3-19e1-4726-b9a9-2210ce497469"}
{
  "id": "conv_41b11c188af44fdb",
  "agent_id": "agt_support",
  "owner_id": "u_alice",
  "status": "closed",
  "created_at": "2026-11-13T12:15:37.745Z",
  "closed_at": "2026-11-13T12:15:37.776Z",
  "messages": [
    {
      "id": "msg_f95f02483f5246a1",
      "seq": 1,
      "role": "user",
      "content": "Qual o horário de atendimento?",
      "status": "completed",
      "created_at": "2026-11-13T12:15:37.761Z",
      "reply_to": null,
      "metadata": null,
      "feedback": null
    },
    {
      "id": "msg_93debd8cd9154f6c",
      "seq": 2,
      "role": "assistant",
      "content": "Entendi. O suporte está disponível em dias úteis, das 8h às 18h.",
      "status": "completed",
      "created_at": "2026-11-13T12:15:37.761Z",
      "reply_to": "msg_f95f02483f5246a1",
      "metadata": {
        "model": "fake-llm-1",
        "latency_ms": 0,
        "prompt_tokens": 25,
        "completion_tokens": 12,
        "finish_reason": "stop"
      },
      "feedback": null
    }
  ]
}
```

```http
GET /api/v1/conversations/conv_41b11c188af44fdb
X-Request-ID: qa-14a943d4-e436-418a-9c5f-95ea3bf2abe7
Authorization: Bearer ***

→ 200  (2 ms)  {"x-request-id": "qa-14a943d4-e436-418a-9c5f-95ea3bf2abe7"}
{
  "id": "conv_41b11c188af44fdb",
  "agent_id": "agt_support",
  "owner_id": "u_alice",
  "status": "closed",
  "created_at": "2026-11-13T12:15:37.745Z",
  "closed_at": "2026-11-13T12:15:37.776Z",
  "messages": [
    {
      "id": "msg_f95f02483f5246a1",
      "seq": 1,
      "role": "user",
      "content": "Qual o horário de atendimento?",
      "status": "completed",
      "created_at": "2026-11-13T12:15:37.761Z",
      "reply_to": null,
      "metadata": null,
      "feedback": null
    },
    {
      "id": "msg_93debd8cd9154f6c",
      "seq": 2,
      "role": "assistant",
      "content": "Entendi. O suporte está disponível em dias úteis, das 8h às 18h.",
      "status": "completed",
      "created_at": "2026-11-13T12:15:37.761Z",
      "reply_to": "msg_f95f02483f5246a1",
      "metadata": {
        "model": "fake-llm-1",
        "latency_ms": 0,
        "prompt_tokens": 25,
        "completion_tokens": 12,
        "finish_reason": "stop"
      },
      "feedback": null
    }
  ]
}
```

## Entrada inválida (4001 caracteres)
Cenário: *4001 caracteres é rejeitado*

```http
POST /api/v1/conversations/conv_b09eccde95e347d7/messages
X-Request-ID: qa-06d1ce01-8fb0-4c34-af33-9cd86993785a
Authorization: Bearer ***

{"content": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa…

→ 422  (1 ms)  {"x-request-id": "qa-06d1ce01-8fb0-4c34-af33-9cd86993785a"}
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "content deve ter entre 1 e 4000 caracteres.",
    "request_id": "qa-06d1ce01-8fb0-4c34-af33-9cd86993785a"
  }
}
```

## Mensagem em conversa encerrada
Cenário: *Mensagem em conversa encerrada é recusada*

```http
POST /api/v1/conversations/conv_e6804b27bad14e71/messages
X-Request-ID: qa-deb8ff65-1723-4f4e-9b95-aa651f7b725a
Authorization: Bearer ***

{"content": "depois de encerrar"}

→ 409  (2 ms)  {"x-request-id": "qa-deb8ff65-1723-4f4e-9b95-aa651f7b725a"}
{
  "error": {
    "code": "CONVERSATION_CLOSED",
    "message": "Esta conversa foi encerrada. Inicie uma nova conversa.",
    "request_id": "qa-deb8ff65-1723-4f4e-9b95-aa651f7b725a"
  }
}
```

## Acesso à conversa de outra pessoa
Cenário: *Outra pessoa não lê conversa alheia*

```http
GET /api/v1/conversations/conv_865dae7833e24b54
X-Request-ID: qa-5b727f8a-ba3e-4fbd-8953-9c0191391764
Authorization: Bearer ***

→ 404  (1 ms)  {"x-request-id": "qa-5b727f8a-ba3e-4fbd-8953-9c0191391764"}
{
  "error": {
    "code": "CONVERSATION_NOT_FOUND",
    "message": "Conversa não encontrada.",
    "request_id": "qa-5b727f8a-ba3e-4fbd-8953-9c0191391764"
  }
}
```

## LLM indisponível
Cenário: *Usuário é informado quando não há resposta (indisponível)*

```http
POST /api/v1/conversations/conv_0c92fa324544454f/messages
X-Request-ID: qa-7842177c-ebf3-4d43-85a7-ad961119a47f
Authorization: Bearer ***

{"content": "Olá, preciso de ajuda"}

→ 503  (1 ms)  {"retry-after": "2", "x-request-id": "qa-7842177c-ebf3-4d43-85a7-ad961119a47f"}
{
  "error": {
    "code": "LLM_UNAVAILABLE",
    "message": "Não foi possível gerar uma resposta agora. Sua mensagem foi salva; tente novamente em instantes.",
    "request_id": "qa-7842177c-ebf3-4d43-85a7-ad961119a47f"
  }
}
```

## Reenvio com a mesma Idempotency-Key (replay)
Cenário: *Reenvio após perda da resposta*

```http
POST /api/v1/conversations
X-Request-ID: qa-adbf5f30-d378-4c53-942d-118eb68db208
Authorization: Bearer ***

{"agent_id": "agt_support"}

→ 201  (2 ms)  {"x-request-id": "qa-adbf5f30-d378-4c53-942d-118eb68db208"}
{
  "id": "conv_9c0b9f9b2a0e4278",
  "agent_id": "agt_support",
  "owner_id": "u_alice",
  "status": "open",
  "created_at": "2026-11-13T12:15:41.248Z",
  "closed_at": null,
  "messages": []
}
```

```http
POST /api/v1/conversations/conv_9c0b9f9b2a0e4278/messages
X-Request-ID: qa-fa354c72-4711-4f19-9752-9a3e107865fd
Authorization: Bearer ***
Idempotency-Key: k1

{"content": "Qual o horário?"}

→ 201  (2 ms)  {"x-request-id": "qa-fa354c72-4711-4f19-9752-9a3e107865fd"}
{
  "user_message": {
    "id": "msg_995f0a49f100404f",
    "seq": 1,
    "role": "user",
    "content": "Qual o horário?",
    "status": "completed",
    "created_at": "2026-11-13T12:15:41.251Z",
    "reply_to": null,
    "metadata": null,
    "feedback": null
  },
  "assistant_message": {
    "id": "msg_a672ff9745cd421a",
    "seq": 2,
    "role": "assistant",
    "content": "Entendi. Atendemos de segunda a sexta-feira, entre 8h e 18h. Qualquer dúvida, é só chamar.",
    "status": "completed",
    "created_at": "2026-11-13T12:15:41.251Z",
    "reply_to": "msg_995f0a49f100404f",
    "metadata": {
      "model": "fake-llm-1",
      "latency_ms": 0,
      "prompt_tokens": 23,
      "completion_tokens": 15,
      "finish_reason": "stop"
    },
    "feedback": null
  }
}
```

```http
POST /api/v1/conversations/conv_9c0b9f9b2a0e4278/messages
X-Request-ID: qa-5d52f04e-924f-4693-90ee-8e13ed2ac7da
Authorization: Bearer ***
Idempotency-Key: k1

{"content": "Qual o horário?"}

→ 201  (1 ms)  {"idempotent-replayed": "true", "x-request-id": "qa-5d52f04e-924f-4693-90ee-8e13ed2ac7da"}
{
  "user_message": {
    "id": "msg_995f0a49f100404f",
    "seq": 1,
    "role": "user",
    "content": "Qual o horário?",
    "status": "completed",
    "created_at": "2026-11-13T12:15:41.251Z",
    "reply_to": null,
    "metadata": null,
    "feedback": null
  },
  "assistant_message": {
    "id": "msg_a672ff9745cd421a",
    "seq": 2,
    "role": "assistant",
    "content": "Entendi. Atendemos de segunda a sexta-feira, entre 8h e 18h. Qualquer dúvida, é só chamar.",
    "status": "completed",
    "created_at": "2026-11-13T12:15:41.251Z",
    "reply_to": "msg_995f0a49f100404f",
    "metadata": {
      "model": "fake-llm-1",
      "latency_ms": 0,
      "prompt_tokens": 23,
      "completion_tokens": 15,
      "finish_reason": "stop"
    },
    "feedback": null
  }
}
```

```http
GET /api/v1/conversations/conv_9c0b9f9b2a0e4278
X-Request-ID: qa-48b9c302-047c-4e77-b3d2-5e902cf6da9f
Authorization: Bearer ***

→ 200  (1 ms)  {"x-request-id": "qa-48b9c302-047c-4e77-b3d2-5e902cf6da9f"}
{
  "id": "conv_9c0b9f9b2a0e4278",
  "agent_id": "agt_support",
  "owner_id": "u_alice",
  "status": "open",
  "created_at": "2026-11-13T12:15:41.248Z",
  "closed_at": null,
  "messages": [
    {
      "id": "msg_995f0a49f100404f",
      "seq": 1,
      "role": "user",
      "content": "Qual o horário?",
      "status": "completed",
      "created_at": "2026-11-13T12:15:41.251Z",
      "reply_to": null,
      "metadata": null,
      "feedback": null
    },
    {
      "id": "msg_a672ff9745cd421a",
      "seq": 2,
      "role": "assistant",
      "content": "Entendi. Atendemos de segunda a sexta-feira, entre 8h e 18h. Qualquer dúvida, é só chamar.",
      "status": "completed",
      "created_at": "2026-11-13T12:15:41.251Z",
      "reply_to": "msg_995f0a49f100404f",
      "metadata": {
        "model": "fake-llm-1",
        "latency_ms": 0,
        "prompt_tokens": 23,
        "completion_tokens": 15,
        "finish_reason": "stop"
      },
      "feedback": null
    }
  ]
}
```

## Prompt injection bloqueado pelo guardrail
Cenário: *Prompt injection não vaza o prompt de sistema (direto)*

```http
POST /api/v1/conversations
X-Request-ID: qa-633c64ee-e4c6-4e72-be23-b7166de92b34
Authorization: Bearer ***

{"agent_id": "agt_support"}

→ 201  (2 ms)  {"x-request-id": "qa-633c64ee-e4c6-4e72-be23-b7166de92b34"}
{
  "id": "conv_37acf89094814e1a",
  "agent_id": "agt_support",
  "owner_id": "u_alice",
  "status": "open",
  "created_at": "2026-11-13T12:15:42.385Z",
  "closed_at": null,
  "messages": []
}
```
