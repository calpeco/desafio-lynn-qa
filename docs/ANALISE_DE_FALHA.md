# Análise de falha — Mensagens e respostas duplicadas (duplo clique / reenvio após falha de rede)

> Cobre a **Parte C** e o formato da **seção 7.4** do desafio. Contrato de referência:
> [`CONTRATO_API.md`](../app/CONTRATO_API.md).

## 1. Descrição

Relato: ao clicar duas vezes em "Enviar", a interface exibe duas mensagens iguais; o agente
às vezes responde uma vez, às vezes duas. Após uma falha de rede, o reenvio manual também
pode duplicar a mensagem.

Resumo técnico: o envio de mensagem (`POST /api/v1/conversations/{id}/messages`) **não é
tratado como operação idempotente** de ponta a ponta. Duas requisições logicamente iguais
viram duas mensagens persistidas e, dependendo do tempo entre elas, uma ou duas gerações no LLM.

## 2. Passos para reprodução

### 2.1 Produto (manual)
1. Autenticar, criar conversa com `agt_support`.
2. Digitar "Qual o prazo de entrega?" e clicar duas vezes rapidamente em "Enviar"
   (ou usar DevTools → Network → "Slow 3G" para alargar a janela).
3. Alternativa: com DevTools, colocar a rede "Offline" logo após o envio, voltar "Online" e
   clicar "Tentar novamente".
4. Recarregar a página e consultar `GET /conversations/{id}`.

### 2.2 No mock deste repositório (automatizado, nas duas pontas)
```bash
# servidor: comportamento correto (verde) e com o defeito injetado (o bug relatado)
behave test/features/api/07_idempotencia.feature
LYNN_FAULTS=no_idempotency behave test/features/api/07_idempotencia.feature

# cliente (UI real no Chromium): proteção ligada (verde) e desligada
behave test/features/ui/chat_ui.feature
LYNN_FAULTS=ui_double_submit behave test/features/ui/chat_ui.feature

# você também pode reproduzir à mão: abra a UI com o defeito e clique duas vezes em Enviar
LYNN_FAULTS=ui_double_submit python app   # http://127.0.0.1:8080
```
Saídas registradas em `test/evidence/fault_injection/no_idempotency.txt` e `ui_double_submit.txt`.

## 3. Resultado esperado × observado

| | Esperado | Observado (com o defeito) |
|---|---|---|
| Duplo clique (mesma `Idempotency-Key`) | 1 mensagem `user` + 1 `assistant`; 2ª resposta com `Idempotent-Replayed: true` ou `409 IDEMPOTENCY_IN_PROGRESS` | 2 mensagens `user` iguais; 1 ou 2 `assistant` |
| Reenvio após falha de rede | Mesma chave → resposta reaproveitada, histórico intacto | Nova mensagem `user` no histórico |
| Reenvio após `503/504` do LLM | Mensagem `user` existente é reprocessada, sem duplicar (**[P-8]**) | Nova mensagem `user` + mensagem `failed` órfã |
| Chamadas ao provedor LLM por mensagem lógica | 1 | 2 |

## 4. Impacto

- **UX/confiança:** histórico poluído, sensação de "agente confuso"; respostas diferentes
  para a mesma pergunta (não determinismo) parecem contradição.
- **Histórico corrompido:** viola a regra "o histórico deve preservar a ordem"; mensagens
  `assistant` podem ficar intercaladas (`user, user, assistant, assistant`).
- **Contexto do LLM:** a mensagem duplicada entra no contexto das próximas gerações,
  degradando a qualidade e aumentando tokens de prompt de forma cumulativa.
- **Custo:** até 2× tokens de completion por envio duplicado + prompt maior nas próximas.
- **Efeitos colaterais:** se o agente usa ferramentas/integrações (abrir chamado, enviar
  e-mail), a ação pode ser executada duas vezes — o impacto mais grave.
- **Métricas/billing:** contagem de mensagens, uso e quotas por cliente ficam infladas.

## 5. Severidade e prioridade

| Dimensão | Sugestão | Justificativa |
|---|---|---|
| Severidade | **Alta (S2)** | Corrompe dados persistidos (histórico) e gera custo; não há perda de dados nem brecha de segurança, por isso não é S1. Sobe para **S1** se agentes com ferramentas executarem ações duplicadas. |
| Prioridade | **P1 — corrigir antes do lançamento** | Frequência alta (duplo clique e redes móveis instáveis são comuns), visível ao usuário, mitigação de baixo custo (client) e correção estrutural bem conhecida (idempotência). |

## 6. Hipóteses de causa (em ordem de probabilidade)

| # | Hipótese | Explica "às vezes 1, às vezes 2 respostas"? |
|---|---|---|
| H1 | Frontend sem debounce/estado "enviando": botão continua habilitado | Origina as 2 requisições |
| H2 | Ausência de `Idempotency-Key` (ou chave gerada a cada clique, não por mensagem) | Servidor não consegue deduplicar |
| H3 | Retry automático do SDK/cliente HTTP/API gateway em `POST` sem chave (ex.: retry em timeout/5xx) | Duplica mesmo sem ação do usuário |
| H4 | Timeout do proxy/gateway **menor** que o tempo de geração: cliente recebe 504, reenvia, enquanto o servidor ainda processa a 1ª | Sim — a 1ª conclui no backend "em silêncio" |
| H5 | Race condition: verificação "já existe?" sem lock/unique constraint (check-then-insert) | Sim — ambas passam pela verificação |
| H6 | Fila at-least-once (ex.: geração via worker) consumida 2×, sem dedupe por id de mensagem | Sim — 2ª geração esporádica |
| H7 | Geração disparada por evento duplicado (ex.: evento "mensagem criada" emitido por 2 réplicas ou websocket reconectado) | Sim |

**Por que é intermitente:** depende do intervalo entre as requisições em relação ao ciclo
de vida da primeira.
- 2ª chega **depois** da 1ª ter concluído e o servidor deduplica parcialmente (ex.: dedupe
  só na geração, por conteúdo/turno) → 2 mensagens `user`, **1** resposta.
- 2ª chega **durante** o processamento da 1ª (janela de segundos da geração) e não há lock →
  ambas geram → **2** respostas.
- Se a resposta da 1ª se perde na rede (H4), o usuário vê falha, mas o backend concluiu;
  o reenvio produz a duplicata.

## 7. Testes para investigar

| Teste | Objetivo | Hipótese |
|---|---|---|
| 2 `POST` **simultâneos** (threads/`asyncio.gather`) com mesma chave e mesmo corpo | 1 mensagem persistida; outra resposta = replay ou `409 IDEMPOTENCY_IN_PROGRESS` | H2, H5 |
| 2 `POST` sequenciais, mesma chave/corpo | 2ª com `Idempotent-Replayed: true`, mesmo `id` | H2 |
| Mesma chave, corpo diferente | `409 IDEMPOTENCY_KEY_REUSED` | H2 |
| Chaves diferentes, mesmo corpo | 2 mensagens (comportamento legítimo; documentar) | Fronteira |
| LLM em `slow` (ex.: 5 s) + cliente com timeout de 1 s e retry | Reproduz H4; contar mensagens e chamadas ao LLM | H3, H4 |
| Toxiproxy/latência: derrubar a conexão após o servidor processar (resposta perdida) e reenviar | Reenvio não duplica | H4 |
| LLM em `error` → reenvio com mesma chave | Reprocessa sem duplicar mensagem `user` | **[P-8]** |
| Contar chamadas ao provedor LLM por `user_message.id` (spy/mock do provedor) | Deve ser exatamente 1 em sucesso | H5, H6, H7 |
| UI (Playwright): duplo clique, Enter + clique, clique durante "Slow 3G" | Botão desabilitado; 1 requisição na aba Network | H1 |
| Inspecionar config do gateway/SDK (retry policy em métodos não idempotentes) | Confirmar/descartar | H3 |
| Reentregar a mesma mensagem da fila manualmente | Worker deduplica | H6 |

## 8. Dados e logs necessários

- Por requisição: `X-Request-ID`, `Idempotency-Key`, `user_id`, `conversation_id`,
  `message_id`, hash do corpo, timestamps (recebido/início LLM/fim LLM/resposta), status HTTP.
- Gateway/LB: logs de retry, timeouts upstream (504), IP/User-Agent (identifica SDK/retry).
- Provedor LLM: nº de chamadas por `message_id`, tokens de prompt/completion, latência, `finish_reason`.
- Fila: `delivery_count`, redeliveries, ack/nack por mensagem.
- Frontend (RUM): eventos de clique no botão, requisições disparadas, erros de rede.

Consultas de exemplo:
```sql
-- Mensagens de usuário duplicadas (mesmo conteúdo, mesma conversa, < 10 s)
SELECT a.conversation_id, a.id AS first_id, b.id AS dup_id, a.content,
       EXTRACT(EPOCH FROM b.created_at - a.created_at) AS delta_s
FROM messages a JOIN messages b
  ON a.conversation_id = b.conversation_id AND a.role = 'user' AND b.role = 'user'
 AND a.content = b.content AND b.seq > a.seq
 AND b.created_at - a.created_at < INTERVAL '10 seconds';

-- Mensagens de usuário com mais de uma resposta do agente
SELECT reply_to_message_id, COUNT(*) AS respostas
FROM messages WHERE role = 'assistant'
GROUP BY reply_to_message_id HAVING COUNT(*) > 1;

-- Taxa diária de duplicação
SELECT date_trunc('day', created_at) d,
       100.0 * SUM(is_dup::int) / COUNT(*) AS duplicate_message_rate_pct
FROM user_messages_flagged GROUP BY 1 ORDER BY 1;
```

## 9. Proposta de correção e mitigação

**Cliente (mitigação rápida):**
- Desabilitar o botão/Enter enquanto a requisição está pendente (estado "enviando").
- Gerar `Idempotency-Key` (UUID v4) **por mensagem composta**, não por clique; reutilizá-la
  em todo reenvio (manual ou automático) da mesma mensagem.
- Renderização otimista com `client_message_id` para não duplicar visualmente.

**Servidor (correção estrutural):**
- Tabela de idempotência com chave única `(user_id, conversation_id, idempotency_key)`,
  hash do corpo e estado `in_progress | completed`; TTL 24 h (**[P-3]**).
  - Mesma chave + mesmo corpo + `completed` → replay da resposta (`Idempotent-Replayed: true`).
  - Mesma chave + `in_progress` → `409 IDEMPOTENCY_IN_PROGRESS` (cliente aguarda e consulta o histórico).
  - Mesma chave + corpo diferente → `409 IDEMPOTENCY_KEY_REUSED`.
- Inserção atômica (unique constraint/`INSERT ... ON CONFLICT`), não check-then-insert.
- Falha de geração (`503/504`) **não** é armazenada como resposta final: o reenvio com a
  mesma chave reaproveita a mensagem `user` existente e só refaz a geração (**[P-8]**).
- Worker de geração idempotente por `user_message_id` (no máximo 1 `assistant` por mensagem;
  unique em `reply_to_message_id`).
- Gateway/SDK: retry automático apenas para métodos idempotentes ou requisições com `Idempotency-Key`.
- Timeout do gateway ≥ timeout de geração + margem (ou migrar para 202 + polling/streaming).

**Observabilidade:**
- Métricas `duplicate_message_rate`, `llm_calls_per_user_message`, `idempotent_replay_total`,
  `idempotency_conflict_total`; alerta se `llm_calls_per_user_message > 1`.

## 10. Critérios para confirmar a resolução

1. `test/features/api/07_idempotencia.feature` verde em CI (sequencial, concorrente, corpo diferente,
   reenvio após falha do LLM) e **vermelho** com `LYNN_FAULTS=no_idempotency`
   (prova de que o teste detecta a regressão).
2. Teste de UI (`test/features/ui/chat_ui.feature`, Playwright): o duplo clique dispara exatamente
   1 requisição, e o reenvio após falha de rede ou do LLM não duplica. Fica **vermelho** com
   `LYNN_FAULTS=ui_double_submit`.
3. Em produção/canário: `duplicate_message_rate` ≈ 0 (< 0,01%) por 7 dias consecutivos.
4. `llm_calls_per_user_message == 1` (p99) e nenhuma mensagem com 2+ respostas na consulta SQL.
5. Nenhum aumento de `409 IDEMPOTENCY_KEY_REUSED` inesperado (indicaria chave reutilizada indevidamente pelo cliente).

## 11. Evidência no mock (resultado observado)

O problema foi reproduzido **nas duas pontas**, e cada uma tem um defeito injetável próprio:

| Execução | Resultado observado |
|---|---|
| `behave test/features/api/07_idempotencia.feature` | **10 cenários passam** |
| `LYNN_FAULTS=no_idempotency behave --tags=@api` | **5 cenários falham**, todos em `07_idempotencia.feature` |
| `behave test/features/ui/chat_ui.feature` | **6 cenários passam** |
| `LYNN_FAULTS=ui_double_submit behave --tags=@ui` | **3 cenários falham** (duplo clique, reenvio após falha de rede, reenvio após LLM indisponível) |

**Servidor sem idempotência** (`no_idempotency`):

| Cenário que falhou | Passo que falhou | Leitura |
|---|---|---|
| Reenvio após perda da resposta | `Idempotent-Replayed` ausente | o reenvio virou nova mensagem |
| Duplo clique simultâneo | histórico com 2 `user` + 2 `assistant` | **reproduz o relato**: 2 bolhas iguais e 2 respostas com redações diferentes (não determinismo) |
| Reenvio após falha do LLM | `failed` órfã + mensagem nova | o reenvio duplicou |
| Mesma chave, conteúdo diferente | 201 em vez de 409 | chave reutilizada sem proteção |
| Erro inesperado (500) | `failed` órfã + mensagem nova | o reenvio após o 500 duplicou |

**Cliente sem proteção** (`ui_double_submit`: botão não desabilita e cada tentativa gera chave nova), no Chromium real:

| Cenário que falhou | Observado na interface |
|---|---|
| Duplo clique em Enviar | 2 requisições, 2 mensagens do usuário e 2 respostas |
| Falha de rede depois do servidor processar | `(2, 2)` em vez de `(1, 1)`: o servidor salvou a 1ª, a resposta se perdeu e o reenvio com chave nova duplicou |
| Agente indisponível + Tentar novamente | `(2, 1)`: mensagem `failed` órfã + mensagem nova |

Os 5 cenários de API que continuam passando com `no_idempotency` são **controles negativos e
de limite**: chaves diferentes geram mensagens distintas; a chave tem escopo por pessoa e
conversa; TTL; reenvio sem chave; reenvio com a conversa já adiantada. Eles não dependem da
deduplicação, então passarem com o defeito é o esperado.

**Conclusão:** cada uma das correções (servidor e cliente) é necessária, e nenhuma basta
sozinha. A suíte detecta a ausência de qualquer uma delas.

**Limite da correção no servidor:** a deduplicação depende de o cliente enviar a
`Idempotency-Key` e de **reutilizá-la** no reenvio. Sem a chave, um reenvio cria uma nova
mensagem, e a original fica `failed`. Esse comportamento está documentado em
`test_reenvio_sem_chave_cria_nova_mensagem`. Por isso a correção no cliente (seção de
correção) é obrigatória, e não opcional.
