# Registro do uso de Inteligência Artificial

## Ferramentas

| Ferramenta | Finalidade |
|---|---|
| **Claude (Anthropic), modelo Claude Opus 5.5**, no app Claude com execução de código em ambiente isolado | Agente principal: leitura do enunciado, definição do contrato, implementação do mock e da suíte, execução dos testes e geração das evidências |
| **agent-qa-lynn** (v3) | Subagente definido neste repositório (`.claude/agents/agent-qa-lynn.md`). Foi executado sem contexto prévio sobre uma spec nova para provar o reuso (`test/docs/EXEMPLO_AGENTE.md`) |
| **Subagentes do Claude** (2 em paralelo + 1 revisor) | Rascunho do documento de estratégia e riscos; rascunho da análise de falha (Parte C); revisão independente da entrega contra o enunciado |
| **Skills do Claude** | Leitura do PDF do enunciado. Na 1ª iteração, a skill de QA Playwright/Cucumber foi descartada porque não havia frontend. Na 2ª iteração (pedido explícito de pirâmide + BDD), o padrão dela orientou a estrutura: features, step definitions e Page Objects, adaptados para Python (behave) |

Nenhuma credencial real, dado pessoal ou informação proprietária foi usada. Tokens e usuários
são fictícios. O PDF do enunciado foi fornecido à ferramenta como entrada.

## Iterações

1. **v1:** 101 testes de API em pytest, mock em Flask, documentação, revisão por subagente independente.
2. **v2 (refatoração a pedido):** pirâmide de testes com `.venv`, Python, Cucumber/BDD (behave), cliente httpx, frontend mínimo e E2E com Playwright + Cucumber + Page Objects + step definitions.
3. **v3 (base reutilizável):**
   - o `agent-qa-lynn` cria automação a partir de specs em Markdown (template, scaffold, catálogo de steps e `CLAUDE.md`);
   - GitHub Actions `dev.yml`/`hom.yml` com execução paralela (matrix dinâmica);
   - `cucumber.json`, `report.html` e `cobertura.html` com a pirâmide e a rastreabilidade por regra e risco.
4. **v4 (organização):** pasta `app/` com tudo que é da API (código, frontend, contratos, documento do contrato) e pasta `test/` com tudo que é de teste. A fronteira e a centralização dos caminhos são verificadas por teste.
5. **v5 (segurança):** o agente `qa-sec` (`.claude/agents/qa-sec.md`) foi criado e executado. Ele gerou a suíte `test/sec` (224 testes OWASP) e o `FINDINGS.md` com 9 vulnerabilidades. A suíte foi integrada a shards, CI, relatórios e injeção de defeitos.

## Etapas em que a IA foi usada

| Etapa | Uso da IA | Parte gerada/influenciada |
|---|---|---|
| Planejamento | Extração dos requisitos do PDF; proposta de premissas e do contrato | `app/CONTRATO_API.md` (gerado pelo agente principal) |
| Código | Geração do mock (`mock_api/`), dos schemas (`app/contracts/`), da suíte (`tests/`) e dos scripts (`test/scripts/`) | Gerado por IA, executado e corrigido iterativamente |
| Documentação | Subagentes redigiram `ESTRATEGIA_E_RISCOS.md` e `ANALISE_DE_FALHA.md` **em paralelo**, a partir do contrato; o agente principal escreveu README e este arquivo | Rascunhos gerados por IA, depois ajustados (ver abaixo) |
| Revisão | Subagente revisor, sem contexto da produção, comparou a entrega item a item com o enunciado | Lista de lacunas, tratadas antes da entrega |
| Verificação | Execução real: suíte completa, 5 rodadas de estabilidade, 7 rodadas com defeitos injetados | `test/evidence/` (saídas reais, não escritas à mão) |

## Exemplos resumidos de prompts

- Pedido da 3ª iteração: *"Torne esse projeto reutilizável, onde através do agent-qa-lynn posso criar automação de teste, seguindo a estrutura do projeto, lendo um arquivo markdown, e refatora o projeto para rodar no GitHub Actions nos ambientes dev.yml e hom.yml com execução em paralelo, e gere cucumber.json, report.html e cobertura.html com o gráfico da pirâmide."*
- Ao agent-qa-lynn: *"Você é o agent-qa-lynn; siga `.claude/agents/agent-qa-lynn.md`. Tarefa: automatizar `test/specs/feedback-resposta.md`. Não altere `app/lynn_mock/`, os contratos nem a spec; relate achados."*
- Pedido da 2ª iteração: *"Refatora o projeto e use pirâmide de teste, usar .venv, python, cucumber, bdd, httpclient, e se tiver frontend usar playwright com cucumber, page object e step definitions."*

- Ao agente principal: *"Resolva esse desafio da melhor forma possível utilizando agentes e skills"* (com o PDF anexado).
- Ao subagente de estratégia: *"Escreva docs/ESTRATEGIA_E_RISCOS.md (pt-BR) coerente com app/CONTRATO_API.md: matriz de riscos R01..R16 com impacto × probabilidade, justificativa e mapeamento para o arquivo de teste; níveis de teste; cenários de LLM; critérios de entrada/saída e Go/No-Go mensurável; dúvidas ligadas às premissas [P-n]. 2 a 4 páginas, sem enchimento."*
- Ao subagente da Parte C: *"Escreva docs/ANALISE_DE_FALHA.md no formato da seção 7.4: hipóteses ordenadas (sem debounce, sem idempotency key, retry de gateway, timeout do proxy menor que o tempo de geração, race condition, fila at-least-once); explique a intermitência; testes de investigação, logs e consultas, correção cliente/servidor, critérios de aceite, severidade × prioridade."*
- Ao revisor: *"Compare o repositório com cada item das seções 5, 6 e 7 do enunciado e aponte o que falta, o que está inconsistente e o que não roda."*

## Como os resultados foram verificados

1. **Tudo foi executado.** Nenhuma afirmação sobre resultado foi aceita sem rodar o comando correspondente. Os números do README (62 unit + 86 API + 6 UI, 9/9 defeitos detectados, contagem por feature) vêm da execução.
2. **Os testes foram testados.** Cada defeito injetado (`LYNN_FAULTS`) precisa deixar vermelho o arquivo que cobre aquele risco ([test/evidence/fault_injection/SUMMARY.md](test/evidence/fault_injection/SUMMARY.md)). Um teste que passa com o defeito ligado não está testando nada.
3. **Os schemas foram testados.** Há testes que garantem que o contrato **rejeita** payloads inválidos (status fora do enum, campo ausente, data inválida).
4. **Estabilidade:** 5 execuções seguidas, sem teste flaky (`test/evidence/latest/stability.txt`).
5. **Revisão cruzada:** os documentos dos subagentes foram conferidos contra o código final.

## Erros e respostas inadequadas da IA, e o que foi corrigido

| # | Problema na saída da IA | Como foi detectado | Correção |
|---|---|---|---|
| 1 | O teste esperava **404** para o ID `../conversations`, mas o cliente HTTP normaliza a URL e a requisição vira `GET /conversations`, que responde **405** | Falha na primeira execução | Asserção ajustada para "nunca 5xx, sempre o envelope de erro", com a explicação no docstring |
| 2 | Os schemas declaravam `format: date-time`, mas o `jsonschema` **ignora esse formato em silêncio** sem o pacote opcional `rfc3339-validator`: o contrato parecia validar datas e não validava | Revisão do código + checagem das dependências instaladas | Checker de `date-time` explícito e teste negativo com datas inválidas |
| 3 | O subagente de estratégia marcou alucinação (R06) e PII em logs (R12) como "não automatizados" e atribuiu o orçamento de latência ao arquivo errado. Ele escreveu antes da suíte existir | Comparação do documento com os testes implementados | Coluna "Cobertura" corrigida; limiares do Go/No-Go marcados como **proposta**, não como requisito |
| 4 | O subagente da Parte C descreveu o resultado "observado" sem ter executado nada | Revisão: a afirmação não tinha evidência | Seção substituída pelo resultado real (4 falhas, 2 controles negativos passando) com trechos da saída |
| 5 | O script de injeção de falhas não extraía o resumo do pytest no modo `-q` (a coluna aparecia como "?") | Inspeção do `SUMMARY.md` gerado | Regex corrigida |
| 6 | O README dizia 27 testes de validação; são 24 | Contagem via `pytest --collect-only` | Número corrigido |
| 7 | **Bug de concorrência no mock gerado pela IA:** o status "encerrada" era checado antes do lock da conversa. Uma mensagem que esperava na fila era aceita depois do `close` | **Subagente revisor**, que reproduziu a corrida com um script | Revalidação dentro do lock + teste de corrida + defeito injetável `stale_closed_check`, para provar que o teste pega o bug |
| 8 | O reenvio após falha, com a conversa já adiantada, gravava a resposta "no passado" (assistant seq 4 respondendo ao seq 1) | Subagente revisor | Regra explícita (P-8): novo turno ao final, original fica `failed`; teste dedicado |
| 9 | Exceção inesperada deixava a `Idempotency-Key` em `in_progress` para sempre; o TTL de 24h era declarado mas nunca aplicado | Subagente revisor | `500 INTERNAL_ERROR` padronizado, chave liberada, TTL aplicado; testes `crash` e TTL |
| 10 | **Teste de timeout circular:** o próprio fake se cortava no timeout, então o teste não provava que a *aplicação* corta | Subagente revisor | Timeout passou a ser imposto pela aplicação (future com timeout); o fake agora só demora |
| 11 | Asserção condicional (`if any(...)`) no teste de guardrail, que nunca falharia | Autorrevisão e revisor | Asserção incondicional: toda tentativa é bloqueada e registrada em log |
| 12 | Qualquer execução local de `pytest` sobrescrevia a evidência versionada | Subagente revisor | Execução local grava em `.artifacts/`; só o `run_all.sh` atualiza `test/evidence/` |
| 13 | O documento de estratégia ainda dizia "200" para a falha silenciosa (o código retorna 201) e era contraditório sobre R06 | Subagente revisor | Texto corrigido |

**Lição registrada:** a revisão por um agente *sem o contexto da produção* encontrou 4 bugs
reais de concorrência e robustez que passaram por 96 testes verdes e pela autorrevisão. Verde
não é prova de correção; foi o que motivou o 8º defeito injetável.

## 2ª iteração: problemas encontrados e corrigidos

| # | Problema | Como foi detectado | Correção |
|---|---|---|---|
| 14 | **Regressão na refatoração:** ao extrair a idempotência para `app/lynn_mock/domain`, o handler de erro inesperado passou a apagar o `user_message_id`, e o reenvio após um 500 duplicava | **Teste de paridade**: a suíte v1 (101 testes) rodou contra a aplicação refatorada antes da migração | `fail()` preserva o id; teste unitário de regressão (`test_fail_sem_id_nao_apaga_id_registrado`) |
| 15 | **Teste E2E de duplo clique que não testava nada:** passava mesmo com a proteção desligada | Injeção do defeito `ui_double_submit` | O `dblclick()` do Playwright errava o 2º clique porque o indicador "digitando" desloca o botão. Troquei por dois cliques reais, o 2º com `force=True`; agora fica vermelho sem a proteção |
| 16 | **Bug real no frontend gerado pela IA:** o CSS `.error{display:flex}` anulava o atributo `hidden`, e o banner de erro nunca sumia | Cenário E2E "não exibe erro" falhando | Regra `[hidden]{display:none!important}` |
| 17 | **Vazamento de estado entre cenários:** o `/__test__/reset` não restaurava o TTL alterado pelo cenário de TTL. Os cenários de UI executados depois herdavam TTL 0 e a deduplicação "falhava" | Só aparecia rodando API+UI juntos (cada camada isolada passava) | O reset restaura toda a configuração padrão |
| 18 | `wait_for_load_state("networkidle")` não espera `fetch` disparado depois da navegação; as asserções liam a tela antes da resposta | Cenários de reenvio falhando de forma intermitente | Espera real por requisições em voo (eventos do Playwright), com janela de silêncio |
| 19 | Arquivos estáticos com 404 (pasta errada no Flask) e `id` ausente num elemento do HTML | Primeira execução da UI (erro de JS capturado no console do navegador) | Corrigidos |
| 20 | 1 passo sem definição (latência) | O runner reportou *undefined step* | Passo criado |
| 21 | **Quebraria no behave real:** o navegador era criado no `before_scenario`; o behave descarta atributos criados no cenário, então o 2º cenário de UI reiniciava o Playwright e dava erro | **Subagente revisor**, por conhecimento do behave; o executor de validação não imitava as camadas de contexto | Navegador num `SimpleNamespace` criado no `before_all`. O executor passou a imitar as camadas, o bug foi reproduzido e a correção foi validada |
| 22 | No behave 1.2.7+/1.3, uma exceção que não é `AssertionError` termina com status `error`; o screenshot sairia marcado como "ok" | Subagente revisor | Helper `_failed()` que aceita `failed` e `error` |
| 23 | `behave` sem limite de versão e `parse` (importado diretamente) ausente do `requirements.txt` | Subagente revisor | `behave>=1.2.6,<1.4` e `parse` declarados |
| 24 | Descrições de feature começando com `Regra:`: no behave 1.3 (com suporte a *Rule*) seriam interpretadas como bloco de regra | Autorrevisão durante a revisão | Reescritas como "Regra de negócio —" |
| 25 | Seletor em step de UI (contra a regra do Page Object), asserção fraca de crescimento de tokens, `join` sem checagem | Subagente revisor | Locators movidos para `ChatPage`, crescimento estrito, `join` verificado |

**Limitação do ambiente de desenvolvimento:** o ambiente onde a IA trabalhou **não tinha acesso
ao PyPI**, então o `behave` não pôde ser instalado ali. Os cenários e os steps foram validados
com um executor mínimo compatível, escrito só para isso e **não incluído no repositório**. Ele
suporta Gherkin em pt, Esquema/Exemplos, Contexto, tabelas, tags, hooks, tipos do `parse` e a
mesma regra de detecção de passos ambíguos do behave. O `httpx`, o Playwright e o Chromium
eram os reais. **Antes de entregar, é preciso rodar `./scripts/run_all.sh` num `.venv` com o behave
real**, para regenerar `test/evidence/` com a saída oficial.

## 3ª iteração: problemas encontrados e corrigidos

| # | Problema | Como foi detectado | Correção |
|---|---|---|---|
| 26 | **A pirâmide estava irregular:** 86 cenários de API contra 62 unitários | O próprio `cobertura.html` recém-criado ("Formato irregular") | Regras que viviam na camada HTTP (autenticação, parsing do corpo, mapeamento de falha do LLM, request id) foram extraídas para `app/lynn_mock/domain/http_rules.py` e testadas na base. O esquema de autenticação passou a ser case-insensitive (RFC 7235) |
| 27 | Os IDs de risco R14 e R15 foram usados para XSS e contrato, mas na matriz eles significam outra coisa | Revisão das tags contra a matriz | Riscos R17 (contrato) e R18 (XSS) acrescentados à matriz e tags corrigidas |
| 28 | O executor de validação só lia o 1º caminho quando recebia várias features | O `cucumber.json` saiu com 70 de 92 cenários | Corrigido (só afeta o ambiente local; o behave real aceita vários caminhos) |
| 29 | O workflow referenciava `test/scripts/step_catalog.py` antes de ele existir | `test/tooling/test_workflows.py` (scripts referenciados existem) | Script criado. O teste continua protegendo o CI |
| 30 | **O log de evidências gravava o comentário e dados pessoais em texto puro** | **agent-qa-lynn**, ao automatizar a RN08 da spec de feedback | Mascaramento de `comment`, CPF e cartão no log do cliente httpx + teste |
| 31 | A RN04 de feedback (risco P1) não tinha defeito injetável | agent-qa-lynn (proposta no relatório) | Defeito `feedback_first_wins` implementado; detectado por 3 cenários |
| 32 | O ambiente de nuvem reiniciou durante a execução do agente | Notificação do ambiente | Os arquivos e o executor de validação sobreviveram; o agente concluiu normalmente |

| 33 | **Pirâmide pouco saudável:** 131 unitários contra 120 de API. A API repetia a combinatória de validação que o unitário já cobria (limites, tipos, variações de token, valores de avaliação) | Pedido da pessoa + leitura do `cobertura.html` | Combinatória mantida só no unitário, com 1 ou 2 exemplos representativos por regra na API (120 → 84). Regras, riscos e os 10 defeitos continuam cobertos |
| 34 | Ataques de prompt injection na feature dependiam do detector do dublê; um ataque não reconhecido passaria sem testar nada | Limitação já documentada na estratégia | Unitário lê os ataques da tabela da feature e exige que o dublê reconheça cada um, com controles benignos |
| 35 | Nada impedia a pirâmide de voltar a inchar (inclusive pelo agente) | Análise da causa raiz | Gate `test/tooling/test_piramide.py` (unitário ≥ 1,5× API e API ≥ 2× UI) + regra no agente e no `CLAUDE.md`; passos sem uso também reprovam |
| 36 | Indicadores "Qualquer camada" e "Camadas sugeridas atendidas" poluíam o `cobertura.html` | Pedido da pessoa | Removidos; no lugar entra a distribuição % da pirâmide |

### 4ª iteração (estrutura `app/` × `test/`)

| # | Ponto | Como foi tratado |
|---|---|---|
| 37 | Mais de 20 módulos calculavam caminhos com `parents[n]`; mover pastas quebraria em silêncio | Fonte única `test/qa_support/paths.py`; scripts, hooks e testes passaram a importar dali. `test/tooling/test_estrutura.py` impede a volta do padrão |
| 38 | `test` é também o nome de um pacote da biblioteca padrão do Python | A pasta `test/` **não** virou pacote: `app/` e `test/` entram no `sys.path` (`pytest.ini: pythonpath`, `bootstrap()` nos pontos de entrada), e os imports continuam `lynn_mock` e `qa_support` |
| 39 | O behave real lê `paths` do `behave.ini`; o executor de validação local não lia | Executor ajustado para ler (só no ambiente local); `behave.ini` com `paths = test/features` |
| 40 | Links relativos em Markdown quebraram com a mudança de pasta (10 links) | Verificador automático de links; corrigidos todos (0 quebrados) |
| 41 | Dependências misturadas | `app/requirements.txt` (aplicação) e `test/requirements.txt` (testes, inclui a app); o da raiz agrega os dois |

### 5ª iteração (segurança com o `qa-sec`)

| # | Ponto | Como foi tratado |
|---|---|---|
| 42 | O nome pedido, `qa_sec`, não segue o padrão do Claude Code (o `name` de um subagente aceita só minúsculas e hífens) | Consulta à documentação oficial; arquivo e nome no padrão: `.claude/agents/qa-sec.md`, `name: qa-sec`, conforme autorizado pela pessoa |
| 43 | O agente não conseguiu gravar o `FINDINGS.md` (escrita bloqueada no ambiente dele) | O conteúdo foi pedido ao agente, **conferido na fonte** (as linhas citadas batem com o código) e gravado. O SEC-001 foi reproduzido de forma independente com `python app` + `curl` |
| 44 | Achados de segurança derrubariam a pipeline ou seriam ignorados | `xfail(strict=True)`: aparecem como "⚠ vulnerabilidade conhecida" e quebram quando forem corrigidos |
| 45 | A suíte de segurança precisava provar que pega defeitos | `fault_injection.py` exige que `idor`, `guardrail_off` e `context_leak` também derrubem `test/sec` |
| 46 | Segurança inflaria a pirâmide | Tratada como camada transversal (`CROSS_LAYERS`), com coluna e card próprios no relatório e fora do gate da pirâmide |
| 47 | Faltava uma visão de segurança para AppSec e gestão | `test/reports/sec-report.html`: cruza `sec-results.json`, `FINDINGS.md` e o mapa OWASP do README. Cada achado é ligado aos testes que o reproduzem pelo `reason` do xfail, e as 20 categorias OWASP aparecem com N/A justificado. Coberto por teste de ferramental e publicado no CI |

**Limitações desta iteração:**
- **O GitHub Actions não pôde ser executado** a partir do ambiente de desenvolvimento. Os workflows foram validados estruturalmente por testes, e os scripts que eles chamam foram executados localmente.
- **O `coverage.py` não estava disponível localmente.** A cobertura de código por camada só aparece no CI.

## Decisões tomadas fora da sugestão inicial

- Usar **injeção de defeitos** (teste de mutação manual) como evidência de que a suíte é eficaz, e não apenas que ela passa.
- Fazer o modelo fake **obedecer** a prompt injection, para que o teste valide o *guardrail da aplicação* e não um modelo que nunca falha.
- Responder **404** em vez de 403 para conversa alheia, e testar que "alheia" e "inexistente" são indistinguíveis.
- **v1:** não usar BDD nem Playwright, porque não havia UI. **v2:** BDD na API e na UI (especificação legível por produto, golden set como tabela de Exemplos), mas a base continua em pytest puro, porque Gherkin não agrega nada a teste de função.
- Criar um frontend mínimo para que a Parte C (bug de interface) fosse testada onde nasce, no navegador, com um defeito injetável próprio (`ui_double_submit`).
- Rodar a suíte antiga contra a aplicação refatorada **antes** de migrar os testes (teste de paridade).
- **v3:**
  - `cucumber.json` por **conversão** da saída nativa do behave, em vez de depender de um formatter de terceiros;
  - "cobertura" em duas dimensões: **rastreabilidade de regras e riscos por camada**, verificável em qualquer lugar, e **cobertura de código**, no CI;
  - shards descobertos automaticamente, para que uma feature nova (inclusive criada pelo agente) entre no CI sem editar YAML;
  - um `_qa-pipeline.yml` reutilizável para dev e hom, sem duplicar YAML;
  - provar o agente numa funcionalidade nova, com o time de dev entregando código e o QA (agente) recebendo só a spec.

## Responsabilidade

A IA acelerou a produção. As decisões de escopo, as premissas, a priorização de riscos e a
aceitação de cada artefato passaram por revisão e por execução. Consigo explicar e defender cada
teste, a escolha do mock e os trade-offs registrados no README.
