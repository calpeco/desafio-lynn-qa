# Convenções do projeto LYNN QA

Este repositório é uma **base reutilizável de automação de testes** organizada como pirâmide.
Toda automação nova (feita por pessoas ou pelo agente `agent-qa-lynn`) segue estas regras.

## Estrutura

Duas pastas de primeiro nível, com fronteira rígida:
- **`app/`**: o sistema sob teste e tudo que é da API (código, frontend, contratos, documento do contrato).
- **`test/`**: tudo que é de teste (unit, features, steps, pages, ferramental, specs, scripts, evidências, relatórios).

`app/` nunca importa de `test/`. Arquivo de teste nunca vai para `app/`. Comandos rodam da **raiz**
(`pytest.ini` usa `pythonpath = app test`; `behave.ini` usa `paths = test/features`). Os caminhos ficam em
`test/qa_support/paths.py`. A fronteira é verificada por `test/tooling/test_estrutura.py`.

| Pasta | Conteúdo | Regra |
|---|---|---|
| `test/specs/*.md` | Especificações de funcionalidades (entrada da automação) | Formato de `test/specs/_TEMPLATE.md`; IDs `RNxx` estáveis |
| `test/unit/` | **Base**: pytest sobre `app/lynn_mock/domain` | Sem rede/servidor; `@pytest.mark.trace("ID-RNxx", "Rxx")` em todo teste |
| `test/features/api/` | **Meio**: Gherkin pt-BR + behave + httpx | Arquivo `NN_assunto.feature`; tags `@api` + `@ID-RNxx` + `@Rxx` |
| `test/features/ui/` | **Topo**: Gherkin + Playwright | Só o que precisa de navegador; tags `@ui` + rastreabilidade |
| `test/features/steps/` | Step definitions | Só orquestram; nada de HTTP cru nem seletor |
| `test/features/pages/` | Page Objects | **Único** lugar com seletores (`data-testid`) |
| `test/sec/` | **Segurança** (transversal, fora da pirâmide): pytest por categoria OWASP | `@pytest.mark.owasp(...)` em todo teste; achado = `xfail(strict=True, reason="SEC-NNN")` + `FINDINGS.md`. Criado e mantido pelo agente `qa-sec` |
| `test/qa_support/` | Cliente httpx, contratos, controle de teste, relatórios | Reutilizável entre projetos |
| `app/contracts/` | JSON Schema das respostas | Toda resposta de API validada |
| `app/lynn_mock/` | Sistema sob teste (mock) | Testes **não** alteram comportamento para passar |

## Regras de automação

1. **Camada mais baixa que pega o risco.** Regra pura → unit. HTTP, estado, concorrência, contrato → API. Só o que exige navegador → UI.
   - **Combinatória fica no unit.** Limites, tipos, formatos e variações de token vão para `test/unit` com `parametrize`. A API mantém só **1 ou 2 exemplos representativos por regra**, que provam a integração (código HTTP, envelope de erro, persistência). Não replique na API uma tabela que o unit já cobre.
   - **Pirâmide saudável é requisito:** unitário ≥ 1,5× API e API ≥ 2× UI. O CI reprova se quebrar (`test/tooling/test_piramide.py`); o veredito também aparece no `cobertura.html`.
2. **Reutilize passos.** Consulte `test/docs/STEP_CATALOG.md` antes de criar. Passo novo: placeholder `{x:Q}` para texto entre aspas e `{n:d}` para inteiro. Padrões não podem ser ambíguos.
3. **Rastreabilidade obrigatória.** Todo cenário e todo teste unitário carrega pelo menos uma tag `@ID-RNxx` da spec e os riscos `@Rxx` da matriz (`docs/ESTRATEGIA_E_RISCOS.md`).
4. **LLM é não determinístico.** Nunca compare texto exato de resposta do agente; verifique invariantes e repita N vezes.
5. **Cenários independentes.** Cada cenário cria seus dados (personas `Alice`, `Bob`, `Visitante`). Nada de depender da ordem.
6. **Sem `sleep` para esperar resultado.** Na UI use `wait_until_settled()`/`expect`; na API use a resposta. `sleep` só para ordenar eventos de propósito, com comentário.
7. **Teste o teste.** Para regra P1, prove que o teste falha com o defeito (`LYNN_FAULTS`, ver `test/qa_support/faults.py`).
8. **Sem segredos.** Tokens vêm de variáveis de ambiente (`.env.example`); nada real no repositório.

## Comandos

```bash
./setup.sh && source .venv/bin/activate              # .venv + dependências + Chromium
python app                                           # sobe a API + UI em http://127.0.0.1:8080
python test/scripts/qa_scaffold.py test/specs/<spec>.md        # valida a spec e planeja (--write gera features)
python test/scripts/step_catalog.py                       # atualiza test/docs/STEP_CATALOG.md
pytest                                               # unit
behave --tags=@api | behave --tags=@ui               # BDD por camada
python test/scripts/run_parallel.py                       # tudo em paralelo + test/reports/{cucumber.json,report.html,cobertura.html,sec-report.html}
python -m pytest test/sec                           # segurança (OWASP); xfail = vulnerabilidade conhecida
python -m pytest test/tooling                       # valida workflows, catálogo e relatórios
python test/scripts/fault_injection.py                    # a suíte detecta os defeitos?
```

## Definição de pronto de uma automação

- Spec válida no scaffold (sem ❌) e todas as regras com caso nas camadas sugeridas (`cobertura.html` sem ⚠).
- `pytest`, `behave` e `pytest test/tooling` verdes; catálogo de steps regenerado.
- Nenhuma asserção fraca (`is not None`, `>= 0`, `in (200, 201, 404)` sem motivo escrito).
- Achados (bug no sistema, ambiguidade na spec) relatados, não contornados.
