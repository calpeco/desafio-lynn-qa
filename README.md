# LYNN — Teste prático QA Sênior: "Conversa com agente"

Estratégia de qualidade e **base reutilizável de automação de testes** para a funcionalidade
**Conversa com agente**, organizada como **pirâmide de testes**:
- **BDD (Cucumber/Gherkin via behave)** na API e na UI.
- Execução **paralela no GitHub Actions** nos ambientes **dev** e **hom**.
- Relatórios **`cucumber.json`**, **`report.html`** e **`cobertura.html`**, este com o gráfico da pirâmide e a cobertura de regras e riscos.
- O **`agent-qa-lynn`** gera automação nova a partir de uma spec em Markdown.

```
                 ┌────────────────┐
                 │   E2E de UI    │    9 cenários  behave + Playwright + Page Objects  → test/features/ui/
                 ├────────────────┤
                 │ API / contrato │  84 cenários   behave + httpx + JSON Schema        → test/features/api/
                 ├────────────────┤
                 │    Unitário    │ 138 testes     pytest (<1 s, sem rede)             → test/unit/
                 └────────────────┘
```

O sistema sob teste é uma **API mock com LLM simulado e um frontend mínimo de chat** que seguem um
contrato definido por mim ([app/CONTRATO_API.md](app/CONTRATO_API.md)). Para provar que os testes
**detectam defeitos de verdade**, a aplicação aceita **10 defeitos injetáveis** (9 na API e 1 no
frontend), e a suíte detecta todos.

| Entregável (enunciado) | Onde está |
|---|---|
| 7.1 README | este arquivo |
| 7.2 / Parte A — Estratégia e riscos | [docs/ESTRATEGIA_E_RISCOS.md](docs/ESTRATEGIA_E_RISCOS.md) |
| Contrato e premissas | [app/CONTRATO_API.md](app/CONTRATO_API.md) · [app/contracts/](app/contracts) |
| 7.3 / Parte B — Testes | [test/unit](test/unit) · [test/features/](test/features) · aplicação em [app/lynn_mock/](app/lynn_mock) |
| 7.4 / Parte C — Análise de falha | [docs/ANALISE_DE_FALHA.md](docs/ANALISE_DE_FALHA.md) |
| Parte D — Plano de execução | [seção abaixo](#parte-d--plano-de-execução) |
| 7.5 — Uso de IA | [AI_USAGE.md](AI_USAGE.md) |
| 7.6 — Evidências | [test/evidence/](test/evidence) · `test/reports/` (gerado a cada execução) |
| Reuso: agente e specs | [`.claude/agents/agent-qa-lynn.md`](.claude/agents/agent-qa-lynn.md) · [CLAUDE.md](CLAUDE.md) · [test/specs/](test/specs) |
| Segurança (OWASP) | agente [`.claude/agents/qa-sec.md`](.claude/agents/qa-sec.md) · suíte [test/sec/](test/sec) · achados [FINDINGS.md](test/sec/FINDINGS.md) |
| CI | [`.github/workflows/`](.github/workflows) (`dev.yml`, `hom.yml`, `_qa-pipeline.yml`) |

---

## Instalação (.venv)

Requisitos: **Python 3.11+**. Não usa serviços pagos, credenciais reais nem rede externa
(só a instalação de pacotes e do Chromium).

```bash
./setup.sh                      # cria .venv, instala requirements (app + test) e o Chromium do Playwright
source .venv/bin/activate
```

<details><summary>Manual / Windows</summary>

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium     # Linux/CI sem libs do navegador: --with-deps chromium
```
</details>

## Execução

Os testes sobem a aplicação sozinhos (servidor embutido em porta aleatória). Não é preciso
iniciar nada antes.

```bash
python test/scripts/run_parallel.py    # TUDO em paralelo (mesmo plano do CI) + test/reports/: cucumber.json, report.html, cobertura.html, sec-report.html
python test/scripts/plan_shards.py     # mostra como as features são distribuídas entre os shards

pytest                            # base: testes unitários (<1 s)
behave --tags=@api                # meio: API/contrato/integração
behave --tags=@ui                 # topo: E2E no Chromium
behave --tags=@smoke              # caminho crítico (API + UI)
behave --tags=@CONV-RN09          # tudo o que cobre uma regra de negócio · ou um risco: --tags=@R02
behave --tags=@security           # por tipo: @idempotency @llm @resilience @contract @validation @observability
HEADED=1 SLOW_MO=300 behave --tags=@ui           # ver o navegador executando

python -m pytest test/sec        # segurança: OWASP API Top 10 + LLM Top 10 (achados conhecidos aparecem como xfail)
python -m pytest test/tooling    # testa o próprio ferramental (workflows, catálogo de steps, relatórios)
python test/scripts/fault_injection.py # liga cada defeito e verifica que a suíte o detecta
./test/scripts/run_all.sh         # evidências versionadas (test/evidence/): camadas, estabilidade e injeção de falhas
make parallel | make unit | make api | make ui | make faults | make tooling   # atalhos
```

**Aplicação standalone** (para explorar com o navegador, curl ou Postman):

```bash
python app        # UI em http://127.0.0.1:8080 · API em /api/v1
LYNN_BASE_URL=http://127.0.0.1:8080 behave --tags=@api   # a mesma suíte contra um servidor externo
LYNN_FAULTS=ui_double_submit python app  # reproduza à mão o bug da Parte C na UI
```

Variáveis (todas opcionais): [.env.example](.env.example). Para apontar a uma API real, use
`LYNN_BASE_URL` e os tokens `LYNN_TOKEN_*`. O ambiente alvo precisa expor um controle de teste
equivalente a `/__test__/*` (reset e stub do LLM).

## Arquitetura da automação

```
.
├── app/                              SISTEMA SOB TESTE (tudo que é da API)
│   ├── lynn_mock/
│   │   ├── domain/                   regras puras: validação, idempotência, guardrail, conversas, feedback, regras HTTP
│   │   ├── llm/fake_llm.py           LLM simulado
│   │   ├── api/app.py                camada HTTP (Flask) + injeção de defeitos (LYNN_FAULTS)
│   │   ├── web/static/               frontend mínimo (HTML/JS puro)
│   │   └── server.py                 servidor standalone (python app)
│   ├── contracts/                    JSON Schema das respostas (contrato publicado da API)
│   ├── CONTRATO_API.md               contrato, premissas P-1..P-11, defeitos injetáveis
│   └── requirements.txt              dependências só da aplicação
│
├── test/                             TUDO QUE É DE TESTE
│   ├── unit/                         BASE da pirâmide (pytest) · @pytest.mark.trace("ID-RNxx", "Rxx")
│   ├── features/                     MEIO e TOPO (behave / Gherkin pt-BR)
│   │   ├── api/NN_*.feature          um arquivo por assunto/risco; tags @ID-RNxx e @Rxx
│   │   ├── ui/*.feature              E2E no navegador
│   │   ├── steps/                    step definitions (só orquestram)
│   │   ├── pages/                    Page Objects (seletores data-testid SÓ aqui)
│   │   └── environment.py            hooks: sobe a app, isola cenários, navegador só para @ui
│   ├── sec/                          SEGURANÇA (pytest, transversal): OWASP API Top 10 2023 + LLM Top 10 2025,
│   │                                 FINDINGS.md (SEC-001..009), gerada pelo agente qa-sec
│   ├── tooling/                      testes do ferramental: workflows, catálogo, relatórios, gate da pirâmide
│   ├── qa_support/                   biblioteca de QA: paths (fonte única de caminhos), cliente httpx, contratos,
│   │                                 controle de teste, índice de steps, shards, defeitos, reporting/
│   ├── specs/                        especificações em Markdown (entrada do agent-qa-lynn)
│   ├── scripts/                      qa_scaffold · step_catalog · plan_shards · run_shard · run_parallel ·
│   │                                 build_reports · fault_injection · run_all.sh
│   ├── docs/                         STEP_CATALOG.md (gerado) · EXEMPLO_AGENTE.md
│   ├── evidence/                     evidências versionadas (execução, estabilidade, injeção de defeitos)
│   ├── reports/                      cucumber.json · report.html · cobertura.html (gerados)
│   └── requirements.txt              dependências de teste (inclui as da app)
│
├── docs/                             ESTRATEGIA_E_RISCOS.md · ANALISE_DE_FALHA.md (entregáveis do desafio)
├── .github/workflows/                _qa-pipeline.yml (reutilizável) · dev.yml · hom.yml
├── .claude/agents/                  agent-qa-lynn.md (automação a partir de specs) · qa-sec.md (testes de segurança)
├── CLAUDE.md · README.md · AI_USAGE.md
├── pytest.ini · behave.ini           rodam da raiz (pythonpath = app test; paths = test/features)
├── requirements.txt · setup.sh · Makefile · .env.example
```

**Fronteira app × test:** `test/` importa `lynn_mock` só para subir a aplicação embutida e para os
unitários do domínio. `app/` nunca importa nada de `test/`. Os caminhos ficam centralizados em
`test/qa_support/paths.py`. Os pontos de entrada só localizam a pasta `test/` para importá-lo, e essa fronteira é verificada por `test/tooling/test_estrutura.py`.

Decisões de design:
- **Steps falam a língua do negócio; detalhes ficam abaixo deles.** HTTP fica no `http_client`, seletores nos Page Objects, e um step tem no máximo uma ou duas linhas de orquestração.
- **Tipo `{x:Q}`** (texto entre aspas, sem aspas internas), registrado no `environment.py`. Ele impede que um placeholder "engula" o resto da frase e torna os padrões não ambíguos. O behave recusa passos ambíguos ao carregar.
- **Cada cenário é independente:** o `before_scenario` faz o reset completo do estado e da configuração, e o navegador abre um contexto novo por cenário.
- **Espera determinística na UI:** o `BasePage.wait_until_settled()` acompanha as requisições em voo pelos eventos do Playwright, sem `sleep` e sem ganchos no código da aplicação. Uma janela de silêncio pega um segundo envio duplicado.
- **Persona e golden set no Gherkin:** `"Alice"`, `"Bob"` e `"Visitante"`; o golden set de LLM é uma tabela de Exemplos que produto consegue revisar.

### O que é simulado

| Simulado | Como |
|---|---|
| Autenticação | Tokens fictícios `token-alice` → `u_alice`, `token-bob` → `u_bob` |
| Agentes | `agt_support`, `agt_sales` (ativos), `agt_retired` (desativado) |
| Modelo de linguagem | [app/lynn_mock/llm/fake_llm.py](app/lynn_mock/llm/fake_llm.py): redação aleatória com fatos fixos; usa o histórico como contexto; recusa inventar preço; obedece a prompt injection de forma "ingênua" (quem bloqueia é o guardrail da aplicação, que é o que se testa); *canary token* no prompt de sistema |
| Falhas do provedor | `POST /__test__/llm {"mode": "error\|timeout\|slow\|crash"}`. O timeout é imposto pela aplicação |
| Falha de rede na UI | `page.route` do Playwright: a requisição chega ao servidor, mas a resposta é abortada |
| Persistência | Memória, com reset completo a cada cenário |
| Defeitos (`LYNN_FAULTS`) | API: `no_idempotency`, `idor`, `allow_closed`, `stale_closed_check`, `guardrail_off`, `context_leak`, `silent_llm_failure`, `off_by_one_limit`, `feedback_first_wins` · UI: `ui_double_submit` |

## Criar automação nova com o `agent-qa-lynn`

O projeto é uma **base reutilizável**. Para automatizar uma funcionalidade nova:

1. **Escreva a spec** em `test/specs/<nome>.md` a partir de [`test/specs/_TEMPLATE.md`](test/specs/_TEMPLATE.md). Ela precisa de:
   - **front matter**: `id`, `titulo`, `area`, `status: pronta`;
   - **regras** `RNxx` com `[camadas: unit, api, ui]` e `[riscos: Rxx]`;
   - **critérios de aceite** em Gherkin (opcionais);
   - a tabela de **telas** com `data-testid`.
2. **Peça ao agente**. No Claude Code, dentro do repositório, use *"use o agent-qa-lynn para automatizar test/specs/<nome>.md"*. A definição dele fica em [`.claude/agents/agent-qa-lynn.md`](.claude/agents/agent-qa-lynn.md), e as convenções que ele segue (e que qualquer pessoa deve seguir) em [CLAUDE.md](CLAUDE.md).
3. **O agente**:
   - valida a spec e monta o plano por camada (`test/scripts/qa_scaffold.py`);
   - gera as features com rastreabilidade (`@<ID>-RNxx`, `@Rxx`);
   - **reutiliza** passos do [catálogo](test/docs/STEP_CATALOG.md) e só cria os que faltam;
   - escreve os unitários, os steps e os Page Objects;
   - executa tudo e verifica a cobertura;
   - devolve um relatório com rastreabilidade, resultados e achados.
4. **Sem o agente**, o mesmo fluxo funciona à mão: `python test/scripts/qa_scaffold.py test/specs/<nome>.md` mostra o plano (passos a reutilizar ou criar, `data-testid` sem Page Object, o que já está automatizado), e `--write` gera as features.

**Exemplo real neste repositório:**
- O time de desenvolvimento entregou a funcionalidade "Avaliação de respostas do agente" (👍/👎).
- A spec está em [`test/specs/feedback-resposta.md`](test/specs/feedback-resposta.md).
- O agent-qa-lynn gerou, sem contexto prévio:
  - [`test/unit/test_feedback.py`](test/unit/test_feedback.py);
  - [`test/features/api/10_avaliacao_de_respostas_do_agente.feature`](test/features/api/10_avaliacao_de_respostas_do_agente.feature);
  - [`test/features/ui/avaliacao_de_respostas_do_agente.feature`](test/features/ui/avaliacao_de_respostas_do_agente.feature);
  - os steps e os métodos novos do Page Object.
- O resultado está em [test/docs/EXEMPLO_AGENTE.md](test/docs/EXEMPLO_AGENTE.md).

## Testes de segurança com o `qa-sec`

O agente [`qa-sec`](.claude/agents/qa-sec.md) é um engenheiro de AppSec com mentalidade de QA. Ele:
- modela as ameaças;
- revisa o código de `app/`;
- transforma as ameaças em **testes automatizados** em [`test/sec/`](test/sec), um arquivo por categoria OWASP.

No Claude Code: *"use o qa-sec para criar/atualizar os testes de segurança"*.

| | |
|---|---|
| **Escopo** | OWASP API Security Top 10 2023 (API1, 2, 3, 4, 5, 8, 9, 10; API6 e API7 justificados como N/A), OWASP Top 10 para LLM 2025 (LLM01, 02, 05, 07, 10) e headers/XSS na UI (Chromium) |
| **Execução** | `python -m pytest test/sec` → **191 seguros, 33 vulnerabilidades conhecidas (xfail estrito), 0 falhas**, estável em 3 execuções |
| **Relatório** | `test/reports/sec-report.html`, gerado junto com os outros relatórios (`run_parallel.py` / `build_reports.py`) e publicado no artefato do CI |
| **Achados** | [FINDINGS.md](test/sec/FINDINGS.md): **9** (1 crítico, 2 médios, 5 baixos, 1 informativo), com CVSS 3.1, arquivo:linha, reprodução e recomendação |
| **Teste do teste** | Com `LYNN_FAULTS=idor`, `guardrail_off` e `context_leak`, a suíte de segurança fica vermelha. Isso é verificado pela injeção de defeitos (coluna "Segurança") |
| **Limites** | Somente a instância local ou um ambiente de teste da equipe; payloads mínimos e não destrutivos; o agente não altera `app/` |

**Achado mais grave, SEC-001 (Crítica, 9.4):** os endpoints de controle de teste (`/__test__/*`) vêm ligados por
padrão e não exigem autenticação. Com `python app`, uma requisição anônima apaga as conversas de todas as pessoas, e
isso foi reproduzido manualmente na revisão. A correção recomendada está no FINDINGS.

**Como um achado vira regressão:** o teste descreve o comportamento **seguro** e leva `xfail(strict=True)`.
- Hoje a pipeline mostra o risco ("⚠ vulnerabilidade conhecida") sem ficar vermelha.
- Quando a correção entrar, o teste passa a dar XPASS e **quebra**, obrigando a atualizar o achado e remover o `xfail`.

**Fora da pirâmide:** a segurança é uma dimensão transversal. Ela tem shard próprio (`sec`) no CI, uma coluna "Segurança" na
matriz de rastreabilidade e um card OWASP com os achados no `cobertura.html`, e também aparece no `report.html`.
Ela não entra na contagem nem no gate da pirâmide.

## Execução paralela, CI e relatórios

**Shards.** O [`test/qa_support/pipeline.py`](test/qa_support/pipeline.py) descobre as features e distribui as de API entre N shards, balanceando pelo número de cenários. UI e unit são shards próprios. Uma feature nova entra no plano **sem editar YAML**. Cada shard sobe a sua instância da aplicação, então não há estado compartilhado. Contra um ambiente real (`LYNN_BASE_URL`), a API roda serial, porque o estado global do ambiente colidiria entre shards.

**GitHub Actions.** O [`_qa-pipeline.yml`](.github/workflows/_qa-pipeline.yml) é reutilizável e tem estes jobs:

```
tooling ─┐
plan ────┼─► test (matrix paralela: unit · api-1..N · ui · sec) ──► report ──► artefato qa-reports-<env>
         └─► fault-injection (matrix paralela, opcional)
```

| Workflow | Quando roda | Particularidades |
|---|---|---|
| [`dev.yml`](.github/workflows/dev.yml) | push em `develop`/`feature/**`, PR para `develop`, manual | cancela a execução anterior da mesma branch; sem injeção de defeitos (feedback rápido) |
| [`hom.yml`](.github/workflows/hom.yml) | push em `hom`/`release/**`, **todo dia útil 03:17 (Brasília)**, manual | não cancela execuções; **com injeção de defeitos** (teste dos testes) |

**Configuração no GitHub** (Settings → Environments → `dev` e `hom`):
- **Variable** `LYNN_BASE_URL`: URL do ambiente. Se ficar vazia, cada job sobe a aplicação mock.
- **Secrets** `LYNN_TOKEN_ALICE` e `LYNN_TOKEN_BOB`: tokens das personas de teste.
- A cobertura de código é coletada com `coverage.py` em todos os shards e combinada por camada.
- Para QA, prefira environments **sem revisores obrigatórios** e sem regra de *deployment branches*. Os jobs `plan` e cada shard de `test` referenciam o environment, então cada um viraria uma aprovação, e a execução noturna roda na branch padrão.

**Relatórios** (artefato `qa-reports-<env>`, ou `test/reports/` localmente):

| Arquivo | Conteúdo |
|---|---|
| `cucumber.json` | Formato Cucumber padrão (entendido por Jenkins, Xray, Allure, ReportPortal). Junta todos os shards e anexa os screenshots de UI como *embeddings*. Convertido da saída nativa do behave (`-f json`) por [`test/qa_support/reporting/cucumber.py`](test/qa_support/reporting/cucumber.py) |
| `report.html` | Execução: taxa de aprovação, resultado por feature, filtros (status, camada, tag), passos com erro e tempo, screenshots, unitários com rastreabilidade. Arquivo único, abre offline, com tema claro e escuro |
| `cobertura.html` | **Gráfico da pirâmide** (largura proporcional ao número de casos, com a forma ideal tracejada), a distribuição % por camada e o veredito pelo critério unitário ≥ 1,5× API e API ≥ 2× UI. Traz também a cobertura de regras por camada, a matriz de rastreabilidade RN × camada, a cobertura de riscos e a cobertura de código por camada |
| `sec-report.html` | **Relatório de segurança**: risco atual (pior achado aberto), achados por severidade (CVSS 3.1), cobertura das 20 categorias OWASP (API Top 10 2023 + LLM Top 10 2025, com N/A justificado), ficha de cada achado (onde, reprodução, impacto, recomendação) ligada aos testes que o reproduzem, modelo de ameaças STRIDE e todos os testes com filtros |
| `summary.md` | Resumo publicado no *job summary* do GitHub Actions |

O exit code do job `report` falha se houver qualquer caso vermelho. Os artefatos são publicados mesmo assim.

## Como interpretar os resultados

- Cada comando termina com **exit code 0 em sucesso e ≠ 0 em falha**. O behave lista os *Failing scenarios* e o passo exato que falhou; as violações de contrato listam todos os campos inválidos.
- **`test/reports/report.html`**: comece por aqui. Use o filtro "Falhas" e a busca por tag (`@CONV-RN09`, `@R02`).
- **`test/reports/cobertura.html`**: confira se a pirâmide está saudável e se há regra com ⚠ "sugerida, sem teste".
- [test/evidence/fault_injection/SUMMARY.md](test/evidence/fault_injection/SUMMARY.md): para cada defeito, quais cenários ficaram vermelhos.
- [test/evidence/EXEMPLOS_REQUISICOES.md](test/evidence/EXEMPLOS_REQUISICOES.md): requisições e respostas reais dos cenários-chave.

> As evidências versionadas foram geradas num ambiente sem acesso ao PyPI, com um executor compatível com o behave (detalhes em [test/evidence/README.md](test/evidence/README.md) e no AI_USAGE). Rodar `python test/scripts/run_parallel.py` ou o CI gera tudo com o behave oficial.

## Estratégia (resumo)

Detalhes, matriz de 18 riscos e Go/No-Go em [docs/ESTRATEGIA_E_RISCOS.md](docs/ESTRATEGIA_E_RISCOS.md).

1. **Risco antes de cobertura, na camada mais baixa que pega o risco.** A atomicidade da idempotência é testada no unitário (50 threads); a corrida HTTP, na API; o duplo clique real, na UI.
   **A combinatória fica no unitário e a API tem exemplos representativos.** A pirâmide saudável (unitário ≥ 1,5× API e API ≥ 2× UI) é um gate de CI, em `test/tooling/test_piramide.py`.
2. **O LLM fica isolado atrás de um fake controlável.** A plataforma é testada de forma determinística; a qualidade do modelo real é avaliada à parte (golden set + LLM-as-judge + monitoramento).
3. **Asserções sobre invariantes, nunca sobre texto exato.** A mesma entrada é repetida N vezes e verificam-se propriedades.
4. **Testar os testes.** Cada risco P1 tem um cenário que fica vermelho com o defeito correspondente ligado.

| Feature | Risco | Cenários |
|---|---|---|
| `01_fluxo_principal` | Fluxo principal e uso de contexto | 2 |
| `02_contrato` | Quebra de contrato | 4 |
| `03_validacao_entrada` | Exemplos representativos de validação na integração HTTP (4000/4001, emoji, tipo, JSON malformado, agente); a combinatória completa está no unit | 10 |
| `04_autenticacao_isolamento` | 401 em cada endpoint (variações de token no unit), IDOR, enumeração, IDs maliciosos | 11 |
| `05_ciclo_de_vida` | Conversa encerrada (inclusive corrida com o close), ordem do histórico | 5 |
| `06_falhas_do_llm` | LLM indisponível, timeout, lento, recuperação | 6 |
| `07_idempotencia` | Reenvio, duplo clique concorrente, falha + reenvio, escopo, TTL, erro inesperado | 10 |
| `08_comportamento_llm` | Não determinismo, golden set, prompt injection, vazamento de contexto, custo | 11 |
| `09_observabilidade` | Correlação, logs estruturados, PII fora dos logs | 5 |
| `10_avaliacao_de_respostas_do_agente` | Spec FDBK, gerada pelo agent-qa-lynn: validação (representativa), permissão, substituição, logs, contrato | 20 |
| `ui/chat_ui` | Duplo clique, falha de rede + reenvio, erro visível, encerrada, XSS | 6 |
| `ui/avaliacao_de_respostas_do_agente` | 👍/👎 na interface, agradecimento, destaque, troca de avaliação (gerada pelo agente) | 3 |

### Riscos prioritários (top 6 de 16)

| ID | Risco | I×P | Prior. | Coberto por |
|---|---|---|---|---|
| R02 | Duplicidade em duplo clique ou reenvio | 20 | P1 | unit (check-and-set) + `07_idempotencia` + `ui/chat_ui` |
| R04 | Prompt injection / vazamento do system prompt | 20 | P1 | unit (guardrail) + `08_comportamento_llm` |
| R03 | Falha do LLM silenciosa | 16 | P1 | `06_falhas_do_llm` + UI (erro visível) |
| R06 | Alucinação | 16 | P1 | golden set (harness); medição real exige modelo real |
| R01 | IDOR: conversa alheia | 15 | P1 | `04_autenticacao_isolamento` |
| R05 | Vazamento de contexto entre conversas | 10 | P2 | `08_comportamento_llm` |

## Premissas e decisões

Lista completa em [CONTRATO_API.md](app/CONTRATO_API.md).

| # | Premissa | Por quê |
|---|---|---|
| P-1 | Bearer token; 401 com envelope de erro | Padrão de mercado |
| P-3 | `Idempotency-Key` com escopo (usuário, conversa, chave) e TTL de 24h; outro corpo → 409 | Resolve a Parte C no servidor |
| P-5 | 1..4000 **code points** após `strip()` | Ambiguidade bytes × caracteres; testado com emoji |
| P-6 | Conversa alheia → **404** | Evita enumeração de IDs |
| P-7 | Falha do LLM → 503/504 com mensagem amigável e `Retry-After`; a mensagem fica salva como `failed` | "Informar o usuário" sem perder o que ele digitou |
| P-8 | Reenvio após falha com a mesma chave não duplica; se a conversa já avançou, vira um novo turno | A ordem do histórico é preservada |
| P-9 | Resposta síncrona (timeout 10 s) | Streaming fica como dúvida para produto |
| P-10 | Encerrar duas vezes é idempotente | Retry seguro |
| P-11 | "Encerrada" é revalidada dentro do lock; erro inesperado → 500 padronizado e chave liberada | Corridas e chaves travadas |

**Por que a Opção 1 (aplicação mock) + contrato.** Não há API pública da LYNN, e uma API
genérica não exercita as regras pedidas. Com o mock eu controlo o LLM e a rede, então a suíte
é determinística e reprodutível offline. O frontend mínimo viabiliza testar a Parte C onde ela
nasce, no navegador. A suíte de API é independente do mock: com `LYNN_BASE_URL` ela roda
contra qualquer implementação do mesmo contrato.

## Limitações conhecidas

- **O mock não é o produto.** A suíte prova o contrato que *eu* defini. Contra a API real, as divergências são achados a discutir.
- **A qualidade do modelo real não é medida.** O fake prova o *harness*. Alucinação, tom e toxicidade reais exigem modelo, um golden set maior e LLM-as-judge.
- **Prompt injection:** o fake só "obedece" aos ataques que reconhece. Com modelo real, os ataques devem vir de um corpus de red teaming.
- **Sem carga/performance real.** A concorrência vai até 8 requisições simultâneas na API e 50 threads no unitário.
- **A UI é mínima** e serve só para viabilizar o E2E. Não há testes de acessibilidade nem de responsividade.
- **Sem `Idempotency-Key` o servidor não deduplica.** Isso está documentado em cenário; a correção depende do cliente, e o E2E cobre esse lado.
- **O GitHub Actions não foi executado neste ambiente** (sem acesso ao GitHub a partir dele). Os workflows foram validados estruturalmente (`test/tooling/test_workflows.py`: jobs, matrix dinâmica, scripts referenciados, artefatos) e os scripts que eles chamam foram executados localmente. A primeira execução real deve ser acompanhada.
- **A cobertura de código (`coverage.py`)** é coletada só no CI; aqui o pacote não estava disponível. O `cobertura.html` mostra a seção quando os dados existem.
- **Contra um ambiente compartilhado** (dev/hom reais), a API roda em um único shard, porque não há isolamento de estado por sessão de teste. O próximo passo é um cabeçalho de sessão no controle de teste.
- **Corridas entre réplicas não são representadas.** O lock é por processo; em produção isso exige unique constraint no banco.
- `/__test__` não existe em produção; em staging, o equivalente seria um stub do provedor (WireMock/toxiproxy).

## Parte D — Plano de execução

**Distribuição do tempo (~7h, com as duas refatorações):**

| Atividade | Tempo |
|---|---|
| Leitura, riscos, premissas e contrato | 0h45 |
| Aplicação mock (domínio, LLM simulado, defeitos) + frontend mínimo | 1h15 |
| Base: testes unitários | 0h30 |
| Meio: features de API + steps (behave/httpx) | 1h15 |
| Topo: E2E com Playwright + Page Objects | 0h45 |
| Base reutilizável: specs, scaffold, agente, CI dev/hom, relatórios | 1h30 |
| Estratégia, análise de falha, evidências, README, revisão | 1h00 |

**O que fiz primeiro e por quê.** Primeiro, **contrato e premissas**: sem decidir 403 × 404,
o comportamento após falha do LLM e a idempotência, não há o que testar. Depois, o mock com
**LLM controlável**, porque sem controlar a falha do LLM metade dos riscos P1 não é testável.
Os testes vieram em ordem de risco. Por último, a injeção de defeitos, para validar a própria suíte.

**Refatoração para a pirâmide.** A primeira versão tinha 101 testes de API em pytest. Extraí as
regras para `app/lynn_mock/domain` e passei a testá-las no unitário. Os cenários de API viraram
Gherkin. Acrescentei o frontend e o E2E, porque a Parte C é um bug de interface e só o
navegador prova a correção do lado do cliente. Antes de migrar, rodei a suíte antiga contra a
aplicação refatorada: ela pegou uma regressão (seção 7.5).

**Base reutilizável (3ª iteração).** Specs em Markdown viraram a entrada da automação, com
rastreabilidade de regra e risco em todos os testes. Entraram também o scaffold, o catálogo de
steps, o `agent-qa-lynn`, os shards dinâmicos e os workflows dev e hom. Os relatórios
`cucumber.json`, `report.html` e `cobertura.html` mostram a pirâmide. Quando o `cobertura.html`
apontou que a pirâmide estava irregular (havia mais cenários de API que unitários), extraí as regras
HTTP para o domínio e reforcei a base. O agente foi provado numa funcionalidade nova
([test/docs/EXEMPLO_AGENTE.md](test/docs/EXEMPLO_AGENTE.md)).

**Organização em `app/` × `test/` (4ª iteração).** Tudo o que é da API foi para `app/` e tudo o que é de teste para `test/`. A fronteira e a fonte única de caminhos (`test/qa_support/paths.py`) são verificadas por teste. Os comandos continuam rodando da raiz.

**O que simplifiquei ou deixei de fazer.** Persistência real; OpenAPI (usei JSON Schema);
carga (k6/Locust); rate limit (não especificado, virou dúvida); avaliação com modelo real;
publicação dos relatórios no GitHub Pages (hoje ficam como artefato).

**Segunda iteração:**
1. Rodar a suíte contra staging e triar as divergências de contrato.
2. Eval de LLM com modelo real: golden set de 100+ casos, LLM-as-judge calibrado e gate no CI a cada mudança de prompt ou modelo.
3. Red teaming automatizado (garak/promptfoo), incluindo injection indireta via documentos de contexto.
4. Carga com reenvios (k6) medindo `duplicate_message_rate` e p95.
5. Schemathesis (fuzzing de contrato), Pact frontend↔API e acessibilidade (axe) na UI.
6. Publicar `report.html` e `cobertura.html` no GitHub Pages por ambiente, com histórico de tendência.
7. Isolamento por sessão no controle de teste, para paralelizar a API também contra ambientes compartilhados.
8. Gate de qualidade no PR: falhar quando uma regra da spec perder cobertura ou a pirâmide inverter.

## Uso de IA

Usei o **Claude** (Anthropic) com agentes e subagentes para planejamento, código, documentação
e revisão independente. Tudo foi validado por execução. Detalhes, prompts, os erros encontrados
nas sugestões e as correções estão em [AI_USAGE.md](AI_USAGE.md).
