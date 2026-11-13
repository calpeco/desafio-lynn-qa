# Evidências

| Arquivo | Conteúdo |
|---|---|
| `latest/RESULTS.md` | A pirâmide executada: casos, falhas e tempo por camada, e o detalhe de cada caso |
| `latest/{unit,api,ui}_output.txt` | Saída de cada camada |
| `latest/{unit,api,ui}/` | JUnit XML (para CI) |
| `latest/stability.txt` | 3 execuções seguidas de API+UI (detecção de flaky) |
| `latest/screenshots/` | Um screenshot por cenário de UI (`ok__` ou `FALHOU__`) |
| `latest/http_exchanges.jsonl` | Todas as trocas HTTP da camada de API (token mascarado) |
| `EXEMPLOS_REQUISICOES.md` | Seleção legível de requisições e respostas reais |
| `fault_injection/SUMMARY.md` | Defeito injetado → cenários que falharam |

Para regenerar tudo: `./test/scripts/run_all.sh`.

Os relatórios consolidados da execução paralela ficam em `test/reports/`:
- `cucumber.json`, `report.html` e `cobertura.html` (gerados por `python test/scripts/run_parallel.py`);
- no CI, o artefato `qa-reports-<env>`.

> **Nota de transparência:** a versão destes arquivos gerada durante o desenvolvimento usou um
> executor de validação compatível com o behave, porque o ambiente não tinha acesso ao PyPI
> (ver `AI_USAGE.md`). Por isso o formato da saída de `api_output.txt`, `ui_output.txt` e
> `stability.txt` difere do *pretty formatter* oficial. A aplicação, o httpx, o Playwright e o
> Chromium eram os reais. Ao rodar `./test/scripts/run_all.sh` num `.venv` com o behave instalado,
> estes arquivos são substituídos pela saída oficial.
