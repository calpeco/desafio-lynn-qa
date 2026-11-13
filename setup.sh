#!/usr/bin/env bash
# Cria o .venv, instala as dependências (app + test) e o Chromium do Playwright.
#
# Funciona em: Linux, macOS e Windows via Git Bash / MSYS2 / Cygwin / WSL.
# No Windows sem bash (PowerShell ou cmd), use setup.ps1 ou setup.cmd: fazem a mesma coisa.
#
# Uso: ./setup.sh [opções]
#   --with-deps            instala também as libs de sistema do Chromium (Linux; pede sudo)
#   --skip-browser         não baixa o Chromium (só testes unitários, API e segurança)
#   --recreate             apaga e recria o .venv
#   --system-site-packages o .venv enxerga os pacotes do Python do sistema (ambiente sem rede)
#   -h, --help             mostra esta ajuda
# Variável opcional: PYTHON=/caminho/do/python (força o interpretador)
set -euo pipefail

cd "$(dirname "$0")"  # raiz do repositório
MIN_MAJOR=3 MIN_MINOR=11
VENV=.venv

WITH_DEPS=0 SKIP_BROWSER=0 RECREATE=0 VENV_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --with-deps) WITH_DEPS=1 ;;
    --skip-browser) SKIP_BROWSER=1 ;;
    --recreate) RECREATE=1 ;;
    --system-site-packages) VENV_ARGS+=(--system-site-packages) ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opção desconhecida: $arg (use --help)" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------- sistema
case "$(uname -s 2>/dev/null || echo unknown)" in
  Linux*)   if grep -qi microsoft /proc/version 2>/dev/null; then OS=wsl; else OS=linux; fi ;;
  Darwin*)  OS=macos ;;
  MINGW*|MSYS*|CYGWIN*) OS=windows ;;
  *)        OS=unknown ;;
esac

# ---------------------------------------------------------------- Python
# Um candidato vale se existir, executar de verdade (o "python" falso da Microsoft Store
# só abre a loja) e for 3.11+.
version_ok() {
  "$@" -c "import sys; sys.exit(0 if sys.version_info[:2] >= ($MIN_MAJOR, $MIN_MINOR) else 1)" >/dev/null 2>&1
}
PY=()
if [[ -n "${PYTHON:-}" ]]; then
  PY=("$PYTHON")
  version_ok "${PY[@]}" || { echo "PYTHON=$PYTHON não é Python $MIN_MAJOR.$MIN_MINOR+." >&2; exit 1; }
else
  candidates=("python3" "python")
  [[ $OS == windows ]] && candidates=("py -3" "python" "python3")
  for c in "${candidates[@]}"; do
    read -r -a cmd <<<"$c"
    command -v "${cmd[0]}" >/dev/null 2>&1 && version_ok "${cmd[@]}" && { PY=("${cmd[@]}"); break; }
  done
fi
if [[ ${#PY[@]} -eq 0 ]]; then
  echo "Python $MIN_MAJOR.$MIN_MINOR+ não encontrado. Instale em https://www.python.org/downloads/" >&2
  echo "ou indique o caminho: PYTHON=/caminho/python ./setup.sh" >&2
  exit 1
fi
echo "Sistema: $OS · Python: $("${PY[@]}" -c 'import sys; print(sys.version.split()[0], sys.executable)')"

# ---------------------------------------------------------------- .venv
# Windows (Git Bash) cria .venv/Scripts/python.exe; os demais, .venv/bin/python.
venv_python() {
  if [[ -x $VENV/Scripts/python.exe ]]; then echo "$VENV/Scripts/python.exe"
  elif [[ -x $VENV/bin/python ]]; then echo "$VENV/bin/python"
  fi
}
if [[ $RECREATE -eq 1 && -d $VENV ]]; then echo "Removendo $VENV"; rm -rf "$VENV"; fi
# Um .venv copiado de outro sistema (ex.: criado no Windows e usado no WSL) não funciona: recria.
if [[ -d $VENV ]] && { [[ -z "$(venv_python)" ]] || ! "$(venv_python)" -c "" >/dev/null 2>&1; }; then
  echo "$VENV existente é de outro sistema ou está quebrado: recriando"; rm -rf "$VENV"
fi
if [[ ! -d $VENV ]]; then
  echo "Criando $VENV"
  "${PY[@]}" -m venv ${VENV_ARGS[@]+"${VENV_ARGS[@]}"} "$VENV"
fi
VPY="$(venv_python)"
[[ -n $VPY ]] || { echo "Falha ao criar $VENV (no Debian/Ubuntu: sudo apt install python3-venv)" >&2; exit 1; }

# ---------------------------------------------------------------- dependências
"$VPY" -m pip install --upgrade pip || echo "Aviso: não foi possível atualizar o pip; seguindo com a versão atual."
"$VPY" -m pip install -r requirements.txt

if [[ $SKIP_BROWSER -eq 1 ]]; then
  echo "Chromium não instalado (--skip-browser): os cenários @ui não vão rodar."
elif [[ $WITH_DEPS -eq 1 && ( $OS == linux || $OS == wsl ) ]]; then
  "$VPY" -m playwright install --with-deps chromium
else
  "$VPY" -m playwright install chromium
  [[ $OS == linux || $OS == wsl ]] && echo "Se o Chromium reclamar de bibliotecas ausentes: ./setup.sh --with-deps"
fi

# ---------------------------------------------------------------- próximo passo
echo
echo "Pronto. Ative o ambiente com:"
case "$OS" in
  windows) echo "  source .venv/Scripts/activate      (Git Bash)"
           echo "  .venv\\Scripts\\Activate.ps1         (PowerShell)  ·  .venv\\Scripts\\activate.bat (cmd)" ;;
  *)       echo "  source .venv/bin/activate" ;;
esac
echo "Depois: pytest  ·  behave --tags=@api  ·  python test/scripts/run_parallel.py"
