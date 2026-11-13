# Injeção de falhas — a suíte detecta defeitos reais?

Cada linha liga UM defeito na aplicação (`LYNN_FAULTS=<defeito>`) e roda a camada correspondente.
Esperado: a suíte FALHA, na feature que cobre aquele risco.

Defeitos de segurança também precisam ser pegos pela suíte `test/sec` (coluna Segurança).

| Defeito | O que quebra | Camada | Feature esperada | Cenários que falharam | Features com falha | Segurança (test/sec) | Resultado |
|---|---|---|---|---|---|---|---|
| `no_idempotency` | API ignora Idempotency-Key (bug da Parte C no servidor) | @api | `07_idempotencia` | 5 | 07_idempotencia | — | ✅ detectado |
| `idor` | Não verifica o dono da conversa | @api | `04_autenticacao_isolamento` | 5 | 04_autenticacao_isolamento, 10_avaliacao_de_respostas_do_agente | ✅ 17 falham (inclui `test_api1_bola`) | ✅ detectado |
| `allow_closed` | Aceita mensagem em conversa encerrada | @api | `05_ciclo_de_vida` | 2 | 05_ciclo_de_vida | — | ✅ detectado |
| `stale_closed_check` | Checa 'encerrada' fora do lock (corrida com close) | @api | `05_ciclo_de_vida` | 1 | 05_ciclo_de_vida | — | ✅ detectado |
| `guardrail_off` | Sem filtro de saída: vaza o prompt de sistema | @api | `08_comportamento_llm` | 4 | 08_comportamento_llm | ✅ 10 falham (inclui `test_llm01_prompt_injection`) | ✅ detectado |
| `context_leak` | Contexto do LLM compartilhado entre conversas | @api | `08_comportamento_llm` | 1 | 08_comportamento_llm | ✅ 6 falham (inclui `test_llm02_divulgacao_sensivel`) | ✅ detectado |
| `silent_llm_failure` | Falha do LLM vira 201 com resposta vazia | @api | `06_falhas_do_llm` | 3 | 06_falhas_do_llm | — | ✅ detectado |
| `off_by_one_limit` | Rejeita exatamente 4000 caracteres | @api | `03_validacao_entrada` | 2 | 03_validacao_entrada | — | ✅ detectado |
| `feedback_first_wins` | Nova avaliação não substitui a anterior (proposto pelo agent-qa-lynn) | @api | `10_avaliacao_de_respostas_do_agente` | 2 | 10_avaliacao_de_respostas_do_agente | — | ✅ detectado |
| `ui_double_submit` | Frontend sem anti duplo clique e com nova chave no reenvio (bug da Parte C no cliente) | @ui | `chat_ui` | 3 | chat_ui | — | ✅ detectado |

Saída completa de cada rodada: `test/evidence/fault_injection/<defeito>.txt`.
