#!/usr/bin/env bash
# Cria o .venv, instala as dependências e o Chromium do Playwright.
set -euo pipefail
cd "$(dirname "$0")"  # raiz do repositório
PY="${PYTHON:-python3}"
"$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
# Em Linux/CI sem as libs do navegador, use: .venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python -m playwright install chromium
echo "Pronto. Ative com: source .venv/bin/activate"
