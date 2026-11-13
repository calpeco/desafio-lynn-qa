#!/usr/bin/env bash
# Executa a pirâmide inteira e gera as evidências em test/evidence/:
#   1. unit (pytest)  2. API (behave @api)  3. UI (behave @ui)  4. resumo  5. estabilidade  6. injeção de falhas
set -uo pipefail
cd "$(dirname "$0")/../.."  # raiz do repositório
PY="${PYTHON:-.venv/bin/python}"
OUT=test/evidence/latest
RUNS="${STABILITY_RUNS:-3}"
rm -rf "$OUT" && mkdir -p "$OUT"
export LYNN_EVIDENCE_DIR="$OUT"

echo "== 1/6 Base: testes unitários (pytest) =="
"$PY" -m pytest -v -p no:cacheprovider --junitxml="$OUT/unit/junit.xml" 2>&1 | tee "$OUT/unit_output.txt"
unit_rc=${PIPESTATUS[0]}

echo "== 2/6 Meio: API / contrato / integração (behave @api) =="
"$PY" -m behave --tags=@api --junit --junit-directory "$OUT/api" 2>&1 | tee "$OUT/api_output.txt"
api_rc=${PIPESTATUS[0]}
cp "$OUT/http_exchanges.jsonl" "$OUT/http_exchanges_api.jsonl" 2>/dev/null || true

echo "== 3/6 Topo: E2E de UI (behave @ui + Playwright) =="
"$PY" -m behave --tags=@ui --junit --junit-directory "$OUT/ui" 2>&1 | tee "$OUT/ui_output.txt"
ui_rc=${PIPESTATUS[0]}
mv "$OUT/http_exchanges_api.jsonl" "$OUT/http_exchanges.jsonl" 2>/dev/null || true

echo "== 4/6 Resumo da pirâmide =="
"$PY" test/scripts/summarize_results.py "$OUT"
"$PY" test/scripts/curate_examples.py "$OUT/http_exchanges.jsonl" test/evidence/EXEMPLOS_REQUISICOES.md

echo "== 5/6 Estabilidade: ${RUNS} execuções de API+UI (detecta flaky) =="
: > "$OUT/stability.txt"
for i in $(seq 1 "$RUNS"); do
  line=$(LYNN_EVIDENCE_DIR=/tmp/lynn-stab "$PY" -m behave -f progress 2>&1 | grep -E "scenarios? passed" | head -1)
  echo "execução $i: $line" | tee -a "$OUT/stability.txt"
done

echo "== 6/6 Injeção de falhas: a suíte detecta defeitos reais? =="
"$PY" test/scripts/fault_injection.py
fault_rc=$?

echo
if [[ $unit_rc -eq 0 && $api_rc -eq 0 && $ui_rc -eq 0 && $fault_rc -eq 0 ]]; then
  echo "RESULTADO GERAL: SUCESSO"; exit 0
fi
echo "RESULTADO GERAL: FALHA (unit=$unit_rc api=$api_rc ui=$ui_rc fault_injection=$fault_rc)"; exit 1
