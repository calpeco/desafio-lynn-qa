# Suíte de segurança (`test/sec`)

Testes automatizados de segurança (OWASP API Security Top 10 2023, OWASP Top 10 para LLM 2025 e
headers/XSS da UI) contra o sistema de `app/`. Fora da contagem da pirâmide. Achados: SEC-001 a SEC-009
(o `reason` de cada `xfail` traz o ID e o resumo; detalhes em [FINDINGS.md](FINDINGS.md)).

## Como executar

```bash
.venv/bin/python -m pytest test/sec -q -p no:cacheprovider          # instância embutida (padrão)
LYNN_BASE_URL=http://host-de-teste .venv/bin/python -m pytest test/sec   # SÓ ambiente de teste da equipe
LYNN_FAULTS=idor .venv/bin/python -m pytest test/sec -q                  # prova de detecção (deve falhar)
```

- `passed`: controle presente. `xfailed`: **achado conhecido** (SEC-NNN no `reason`), com o teste descrevendo
  o comportamento seguro. `XPASS` (strict) = falha: a correção entrou e o achado precisa ser atualizado.
- Relatório: `test/reports/sec-report.html` (`python test/scripts/run_parallel.py` ou `build_reports.py`): risco atual, severidades, matriz OWASP completa, fichas dos achados ligadas aos testes.
- Resultado JSON: `test/reports/raw/sec-results.json` (ou `LYNN_SEC_RESULTS`), com `"layer": "sec"` e tags owasp + trace.
- Cada teste é independente: `/__test__/reset` antes de cada um (fixture `autouse`).
- XSS usa Chromium headless (Playwright) com todas as requisições fora da instância local abortadas.

## Modelo de ameaças (STRIDE leve)

| Elemento | Conteúdo |
|---|---|
| **Ativos** | conversas e mensagens (PII livre), comentários de feedback, prompt de sistema (canário `LYNN-SYS-CANARY`), logs estruturados, tokens bearer, orçamento de tokens do LLM |
| **Atores** | anônimo; pessoa autenticada (Alice); outra pessoa autenticada (Bob); conteúdo do LLM (não confiável); quem alcança a porta de `/__test__` |
| **Fronteiras** | navegador ↔ API (bearer, JSON); API ↔ LLM (contexto montado pela app, guardrail na saída); API ↔ logs (`log_buffer` exposto em `/__test__/logs`) |
| **Superfície** | `POST /api/v1/conversations`, `GET /…/{id}`, `POST /…/{id}/close`, `POST /…/{id}/messages`, `POST /…/{id}/messages/{mid}/feedback` (não documentado), `GET /`, `/config.js`, `/static/*`, `/__test__/{reset,llm,config,stats,logs}` (públicos) |

| STRIDE | Ameaça principal | Onde testamos |
|---|---|---|
| Spoofing | token adulterado, identidade em header/query/cookie | `test_api2_autenticacao.py` |
| Tampering | mass assignment, método/override, reset global anônimo | `test_api3_*`, `test_api5_*` |
| Repudiation | `X-Request-ID` forjável, acesso negado sem rastro | `test_api8_*`, `test_api1_*` (log da tentativa) |
| Info disclosure | BOLA, contexto entre conversas, prompt de sistema, PII em logs, versão | `test_api1_*`, `test_llm01_*`, `test_llm02_*`, `test_api8_*` |
| DoS | corpo grande, JSON aninhado, rajada, provedor lento, config inválida | `test_api4_*`, `test_api10_*`, `test_api5_*` |
| Elevation | endpoints de controle sem auth | `test_api5_*` |

## Mapa OWASP → arquivos

| Categoria | Arquivo | Observação |
|---|---|---|
| API1 BOLA | `test_api1_bola.py` | todos os endpoints com ID, feedback cruzado, enumeração, ID adulterado, escopo da Idempotency-Key |
| API2 Autenticação | `test_api2_autenticacao.py` (+ força bruta em `test_api4_*`, storage do token em `test_web_*`) | 13 variações × 5 endpoints |
| API3 Propriedades | `test_api3_propriedades.py` | mass assignment em criar/enviar/feedback/encerrar; exposição excessiva |
| API4 Recursos | `test_api4_consumo_recursos.py` | 2 MB, JSON aninhado, rajada, custo de LLM em rejeições |
| API5 Funções | `test_api5_funcoes_privilegiadas.py` | `/__test__/*`, métodos, override |
| API6 Fluxos sensíveis | N/A | não há fluxo de negócio monetizável (compra, cadastro, cupom); o abuso relevante (spam de mensagens) está em API4/LLM10 |
| API7 SSRF | N/A | nenhuma entrada vira URL buscada pelo servidor; o LLM é in-process |
| API8 Configuração | `test_api8_configuracao.py`, `test_web_headers_xss.py` | headers, versão, CORS, TRACE, erros sem stack |
| API9 Inventário | `test_api9_inventario.py` | rotas registradas × contrato; versões sombra |
| API10 Consumo inseguro | `test_api10_consumo_inseguro.py` | provedor LLM como API de terceiros |
| LLM01 Prompt injection | `test_llm01_prompt_injection.py` | 14 variações (codificação, idioma, role-play), indireta via histórico e feedback |
| LLM02 Divulgação | `test_llm02_divulgacao_sensivel.py` | contexto entre pessoas/conversas, canal lateral de tokens, PII em 7 caminhos de log |
| LLM05 Saída imprópria | `test_web_headers_xss.py`, `test_api10_*` | saída do LLM renderizada só como texto/JSON |
| LLM07 Vazamento do prompt | `test_llm01_*`, `test_llm02_*` (guardrail caixa-cinza) | |
| LLM10 Consumo ilimitado | `test_api4_*` | rajada, replay idempotente |
| LLM03/04/08/09 | N/A | sem cadeia de suprimento de modelo, treino/fine-tuning, RAG/embeddings nem conteúdo factual crítico (alucinação é coberta pelo golden set em `08_comportamento_llm.feature`) |
| LLM06 Agência excessiva | N/A | o agente não tem ferramentas nem ações; só gera texto |

## Rastreabilidade

`@pytest.mark.owasp(...)` em todo teste e `@pytest.mark.trace("CONV-RNxx"|"FDBK-RNxx", "Rxx")` ligando a
`test/specs/*.md` e à matriz `docs/ESTRATEGIA_E_RISCOS.md` (R01, R02, R04, R05, R09, R11, R12, R13, R16, R17, R18).

## Prova de detecção (`LYNN_FAULTS`)

| Defeito | Falham (exemplos) |
|---|---|
| `idor` | 18 testes: `test_api1_bola.py` (todas as operações, enumeração, ID adulterado, idempotência), API3, rejeição sem LLM |
| `guardrail_off` | 11 testes: as 7 injeções que o modelo obedece, repetição, indireta via histórico, persistência filtrada |
| `context_leak` | 6 testes: segredo entre pessoas (3 frases), entre conversas, dois segredos, canal lateral de tokens |

## Limites conhecidos

- Fake LLM: injeções que ele não entende não provam robustez de um modelo real (ver SEC-009 e red teaming).
- Sem DAST/fuzzing amplo, sem testes de TLS (servidor local HTTP), sem carga real.
