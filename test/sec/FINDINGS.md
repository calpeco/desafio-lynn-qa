# Achados de segurança — LYNN "Conversa com agente"

Gerado pelo agente **qa-sec** (`.claude/agents/qa-sec.md`). O alvo é o código de `app/`, na instância
embutida local (`qa_support.embedded_server`). As referências de arquivo e linha e o SEC-001 (com
`python app` + `curl`) foram conferidos de forma independente na revisão.

Cada achado tem um teste com `@pytest.mark.xfail(strict=True)` que descreve o comportamento **seguro**
esperado. Quando a correção entrar, o teste passa a dar XPASS e, por ser estrito, **falha**. Nesse momento:
- atualize o achado (Status → mitigado);
- remova o `xfail`.

Execução: `.venv/bin/python -m pytest test/sec -q -p no:cacheprovider` → 191 passed, 33 xfailed,
0 failed, estável em 3 execuções.

## Resumo (ordenado por severidade)

| ID | Título | Severidade | CVSS | OWASP | Risco | Status |
|---|---|---|---|---|---|---|
| SEC-001 | `/__test__/*` ligado por padrão e sem autenticação | **Crítica** | 9.4 | API5 (API8, API9) | R16, R12, R01 | aberto |
| SEC-002 | Sem limite de tamanho do corpo | Média | 4.3 | API4 | R09, R11 | aberto |
| SEC-003 | Sem rate limit/quota (mensagens e autenticação) | Média | 4.3 | API4, LLM10, API2 | R11, R16 | aberto |
| SEC-006 | Header `Server` divulga versões | Baixa | 3.7 | API8 | — | aberto |
| SEC-004 | JSON profundamente aninhado → 500 | Baixa | 3.1 | API4, API8 | R09 | aberto |
| SEC-005 | Headers de segurança ausentes (UI e API) | Baixa | 3.1 | API8 | R18, R12 | aberto |
| SEC-007 | `X-Request-ID` sem validação de formato | Baixa | 3.1 | API8 | R13 | aberto |
| SEC-009 | Guardrail reconhece só o canário literal | Baixa | 3.1 | LLM07, LLM02 | R04 | aberto |
| SEC-008 | Rotas fora do contrato | Informativa | 0.0 | API9 | R17 | aberto |

---

### SEC-001 · Endpoints de controle `/__test__/*` ligados por padrão e sem autenticação
- **Severidade:** Crítica, 9.4. Vetor `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:H/A:H`. Vale para qualquer ambiente iniciado com `python app` sem `LYNN_TEST_CONTROL=0`.
- **OWASP:** API5:2023, com reflexos em API8:2023 e API9:2023 · **Risco:** R16, R12, R01
- **Onde:**
  - `app/lynn_mock/api/app.py:49`: `os.getenv("LYNN_TEST_CONTROL", "1")` deixa o controle ligado por padrão.
  - `app/lynn_mock/api/app.py:33`: `/__test__` está em `PUBLIC_PREFIXES` e não passa pela autenticação.
  - `app/lynn_mock/api/app.py:274`: `setattr(llm.settings, k, data[k])` grava o valor sem validar o tipo.
  - `app/lynn_mock/api/app.py:285-290`: `stats` e `logs` ficam públicos.
  - `app/lynn_mock/server.py:15`: `create_app()` é chamado sem desligar o controle.
- **Reprodução:**
  ```bash
  python app &                                         # nenhuma variável de ambiente
  curl -X POST localhost:8080/__test__/reset           # 200: apaga as conversas de TODAS as pessoas
  curl localhost:8080/__test__/logs                    # 200: user_id, conversation_id, idempotency_key
  curl localhost:8080/__test__/stats                   # 200: llm_calls e lista de defeitos ativos
  curl -X POST localhost:8080/__test__/llm -H 'Content-Type: application/json' -d '{"timeout_ms":"abc"}'
  # a partir daqui, todo POST .../messages de qualquer pessoa responde 500 INTERNAL_ERROR
  ```
- **Esperado × obtido:**
  - **Esperado:** o `CONTRATO_API.md` diz "somente com `LYNN_TEST_CONTROL=1`". Sem a variável, a rota deveria responder 404, ou 401 se exigir credencial. Configuração inválida deveria receber 422.
  - **Obtido:** o controle vem ligado por padrão e é acessível sem autenticação. Uma configuração inválida quebra o fluxo principal de forma persistente.
- **Impacto:**
  - **Integridade:** qualquer pessoa na rede apaga os dados de todas as pessoas.
  - **Disponibilidade:** uma única requisição derruba o serviço de forma persistente.
  - **Confidencialidade:** expõe metadados de uso e mostra quais defesas estão desligadas.
- **Recomendação:**
  - Mudar o padrão para `"0"` em `create_app` e habilitar o controle só na fixture de teste e no CI.
  - Exigir um segredo (ex.: header `X-Test-Control-Token` comparado com `hmac.compare_digest`).
  - Validar o corpo de `/__test__/llm` (`mode` num enum; `delay_ms` e `timeout_ms` inteiros ≥ 0) e responder 422 fora disso.
  - Tirar essas rotas do artefato de produção (blueprint separado).
- **Testes:** `test/sec/test_api5_funcoes_privilegiadas.py`
  - `test_controle_de_teste_nao_existe_na_configuracao_padrao`
  - `test_reset_global_exige_credencial_privilegiada`
  - `test_logs_e_stats_internos_exigem_credencial`
  - `test_configuracao_invalida_do_llm_e_rejeitada`
- **Status:** aberto

### SEC-002 · Sem limite de tamanho do corpo da requisição
- **Severidade:** Média, 4.3. Vetor `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L`.
- **OWASP:** API4:2023 · **Risco:** R09, R11
- **Onde:**
  - `app/lynn_mock/api/app.py:44`: Flask sem `MAX_CONTENT_LENGTH`.
  - `app/lynn_mock/api/app.py:98`: `_json_body` lê o corpo inteiro.
- **Reprodução:** um corpo de 2 MB (`{"agent_id":"agt_support","pad":"A"*2097152}`) em `POST /api/v1/conversations` responde **201**. No envio de mensagem com campo extra de 2 MB também: 201, com chamada ao LLM.
- **Esperado × obtido:** esperado `413` no envelope de erro padrão. Obtido `201 Created`.
- **Impacto:** memória e CPU sem teto por requisição. Poucas conexões paralelas com corpos grandes degradam o serviço para todos (agravado pelo SEC-004).
- **Recomendação:**
  - `app.config["MAX_CONTENT_LENGTH"] = 64 * 1024`.
  - Handler 413 que responda `PAYLOAD_TOO_LARGE` no envelope de erro padrão.
  - Mesmo limite no gateway.
  - Documentar o limite no contrato.
- **Teste:** `test/sec/test_api4_consumo_recursos.py::test_corpo_acima_do_limite_e_rejeitado_com_413` (criar e enviar)
- **Status:** aberto

### SEC-003 · Sem rate limit ou quota (mensagens e tentativas de autenticação)
- **Severidade:** Média, 4.3. Vetor `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L`. Com modelo pago, o impacto financeiro é direto.
- **OWASP:** API4:2023, LLM10:2025, API2:2023 · **Risco:** R11, R16
- **Onde:**
  - `app/lynn_mock/api/app.py:147`: `send_message` não tem controle por pessoa antes de chamar o LLM.
  - `app/lynn_mock/api/app.py:64-74`: o middleware não limita os 401.
- **Reprodução:**
  - 25 mensagens seguidas → 25 × `201`, com `llm_calls = 25`.
  - 25 tokens inválidos → 25 × `401`, nenhum `429`.
- **Esperado × obtido:** esperado `429` com `Retry-After` ao esgotar a cota. Obtido: nenhum limite.
- **Impacto:**
  - Custo de tokens ilimitado (*denial of wallet*).
  - Uma pessoa ocupa o pool de 32 threads do LLM.
  - Força bruta de token sem atrito.
  - Histórico e `prompt_tokens` crescem sem teto.
- **Recomendação:**
  - Rate limit por pessoa e por IP (ex.: token bucket de 10 mensagens/min).
  - Quota diária de tokens.
  - Janela de contexto truncada ou resumida (dúvidas 7 e 10 da estratégia).
  - Bloqueio progressivo após 401 repetidos.
- **Testes:** `test/sec/test_api4_consumo_recursos.py`
  - `test_rajada_de_mensagens_recebe_429_com_retry_after`
  - `test_tentativas_seguidas_de_token_invalido_sao_limitadas`
- **Status:** aberto

### SEC-004 · JSON profundamente aninhado causa 500 (RecursionError)
- **Severidade:** Baixa, 3.1. Vetor `CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:N/A:L`.
- **OWASP:** API4:2023, API8:2023 · **Risco:** R09
- **Onde:** `app/lynn_mock/domain/http_rules.py:31-32`. `parse_json_object` só captura `ValueError`, então o `RecursionError` escapa.
- **Reprodução:** um corpo `"["*50000 + "]"*50000` em `POST /api/v1/conversations` responde `500 INTERNAL_ERROR`.
- **Esperado × obtido:** esperado `400 INVALID_JSON`. Obtido `500`. O processo continua saudável (`test_servidor_continua_saudavel_apos_json_aninhado` passa).
- **Impacto:** 5xx falsos, CPU gasta em recursão e observabilidade poluída.
- **Recomendação:** capturar `RecursionError` em `parse_json_object` e devolver `BodyError(400, "INVALID_JSON", …)`. Combinar com o limite de corpo do SEC-002.
- **Teste:** `test/sec/test_api4_consumo_recursos.py::test_json_profundamente_aninhado_e_400_e_nao_500`
- **Status:** aberto

### SEC-005 · Headers de segurança ausentes (UI e API)
- **Severidade:** Baixa, 3.1. Vetor `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:N/I:L/A:N`. É defesa em profundidade: hoje o render usa `textContent` e o XSS armazenado não executa, o que o teste no Chromium confirma.
- **OWASP:** API8:2023 · **Risco:** R18, R12
- **Onde:** `app/lynn_mock/api/app.py:77`. `_after` só adiciona `X-Request-ID`.
- **Reprodução:** `curl -sI localhost:8080/` e uma resposta de conversa. Nenhuma traz `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors` nem `Referrer-Policy`. A resposta da conversa também não traz `Cache-Control: no-store`.
- **Esperado × obtido:** esperado CSP sem `'unsafe-inline'`, `nosniff`, `DENY`/`frame-ancestors 'none'`, Referrer-Policy restritiva e `no-store` nos dados de conversa. Obtido: todos ausentes.
- **Impacto:**
  - Não há segunda barreira contra um XSS futuro.
  - A página pode ser embutida em iframe (clickjacking).
  - Dados pessoais podem ficar em cache.
- **Recomendação:** em `_after`, adicionar:
  - `Content-Security-Policy: default-src 'self'; script-src 'self'; frame-ancestors 'none'`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: no-referrer`
  - `Cache-Control: no-store` em `/api/`
- **Testes:**
  - `test/sec/test_web_headers_xss.py::test_pagina_do_chat_envia_header_de_seguranca` (4 parâmetros)
  - `test/sec/test_api8_configuracao.py::test_api_envia_nosniff`
  - `test/sec/test_api8_configuracao.py::test_dado_de_conversa_nao_e_cacheavel`
- **Status:** aberto

### SEC-006 · Header `Server` divulga versões (Werkzeug/Python)
- **Severidade:** Baixa, 3.7. Vetor `CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N`.
- **OWASP:** API8:2023 · **Risco:** não mapeado. Sugestão: novo risco de hardening na matriz.
- **Onde:** `app/lynn_mock/server.py:15`. `run_simple` sobe o servidor de desenvolvimento do Werkzeug.
- **Reprodução:** `curl -sI localhost:8080/` retorna `Server: Werkzeug/3.1.9 Python/3.13.18` (confirmado na revisão).
- **Esperado × obtido:** esperado `Server` ausente ou genérico. Obtido: framework e runtime com versão.
- **Impacto:** facilita mapear CVEs e mostra que um servidor de desenvolvimento está exposto.
- **Recomendação:** gunicorn ou uwsgi atrás de um proxy que neutralize `Server`. Nunca `run_simple` fora do ambiente local.
- **Teste:** `test/sec/test_api8_configuracao.py::test_header_server_nao_divulga_versao` (em `/` e na API)
- **Status:** aberto

### SEC-007 · `X-Request-ID` do cliente aceito sem validação de formato
- **Severidade:** Baixa, 3.1. Vetor `CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:L/A:N`.
- **OWASP:** API8:2023 · **Risco:** R13
- **Onde:** `app/lynn_mock/domain/http_rules.py:53-56`. Só aplica `strip()` e corta em 128 caracteres.
- **Reprodução:** `X-Request-ID: <script>alert(1)</script>` volta como veio no header, em `error.request_id` e nos logs.
- **Esperado × obtido:** esperado aceitar só `^[A-Za-z0-9._:-]{1,128}$` e, fora disso, gerar um UUID. Obtido: qualquer valor é aceito.
- **Impacto:**
  - Permite forjar a correlação.
  - Permite injetar conteúdo em ferramentas de log que renderizem HTML.
  - Não há XSS refletido pela própria API, porque a resposta é sempre JSON (`test_x_request_id_refletido_nao_vira_html` passa).
- **Recomendação:** validar com a regex. Fora do formato, gerar um UUID novo e guardar o original truncado em `client_request_id`.
- **Teste:** `test/sec/test_api8_configuracao.py::test_x_request_id_fora_do_formato_e_substituido` (3 parâmetros)
- **Status:** aberto

### SEC-008 · Inventário: rotas fora do contrato
- **Severidade:** Informativa, 0.0.
- **OWASP:** API9:2023 · **Risco:** R17
- **Onde:** rotas registradas em `app/lynn_mock/api/app.py` que `app/CONTRATO_API.md` não documenta:
  - feedback (`:234`)
  - `GET /config.js` (`:114`)
  - `GET /__test__/stats` e `/__test__/logs` (`:285-290`)
- **Reprodução (caixa-cinza):** comparar `create_app(...).url_map.iter_rules()` com as linhas `MÉTODO /caminho` do contrato.
- **Esperado × obtido:** esperado que toda rota esteja documentada. Obtido: 4 rotas sem documentação. O feedback só aparece em `test/specs/feedback-resposta.md`.
- **Impacto:** a superfície fica fora da revisão de contrato, do gateway e de um DAST guiado por contrato.
- **Recomendação:** documentar no contrato ou gerar um OpenAPI a partir do código, e manter a verificação no CI.
- **Testes:** `test/sec/test_api9_inventario.py`
  - `test_rotas_de_producao_estao_no_contrato`
  - `test_rotas_de_controle_estao_no_contrato`
- **Status:** aberto

### SEC-009 · Guardrail de saída reconhece só o canário literal
- **Severidade:** Baixa, 3.1. Vetor `CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:L/I:N/A:N`. Tende a Média com modelo real.
- **OWASP:** LLM07:2025, LLM02:2025 · **Risco:** R04
- **Onde:** `app/lynn_mock/domain/guardrail.py:17` (`if canary and canary in text:`).
- **Reprodução (caixa-cinza):** chamar `apply_output_guardrail` com o prompt de sistema transformado. Em todas as variações abaixo o resultado é `blocked_rule = None`:
  - em base64;
  - com o canário espaçado;
  - em minúsculas;
  - sem o trecho `[canary …]`;
  - invertido.
- **Esperado × obtido:** esperado `system_prompt_leak` para qualquer variação reconhecível. Obtido: só a string exata é bloqueada.
- **Impacto:**
  - Um modelo real induzido a traduzir, codificar ou parafrasear vazaria as instruções sem disparar o filtro.
  - Pela API, com o fake LLM, o vazamento não acontece: as variações de `test_llm01_prompt_injection.py` passam. O risco é latente e aparece ao trocar o modelo.
- **Recomendação:**
  - Normalizar o texto (NFKC, casefold, remover separadores e caracteres de largura zero).
  - Procurar o canário também em base64, hex e invertido.
  - Medir a similaridade com o prompt de sistema por n-gramas.
  - Manter o prompt sem segredos.
  - Red teaming contínuo com corpus de ≥ 50 prompts.
- **Teste:** `test/sec/test_llm02_divulgacao_sensivel.py::test_guardrail_bloqueia_prompt_de_sistema_transformado` (5 parâmetros)
- **Status:** aberto
