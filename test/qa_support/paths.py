"""Fonte única dos caminhos do repositório.

    app/    sistema sob teste (API mock, frontend, contratos)
    test/   tudo de teste (unit, features, ferramental, specs, scripts, evidências, relatórios)

Nenhum outro módulo monta caminho com `parents[n]`: todos importam daqui.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

APP = ROOT / "app"
CONTRACTS = APP / "contracts"

TEST = ROOT / "test"
FEATURES = TEST / "features"
STEPS = FEATURES / "steps"
PAGES = FEATURES / "pages"
UNIT = TEST / "unit"
SEC = TEST / "sec"
TOOLING = TEST / "tooling"
SPECS = TEST / "specs"
SCRIPTS = TEST / "scripts"
TEST_DOCS = TEST / "docs"
EVIDENCE = TEST / "evidence"
REPORTS = TEST / "reports"
RAW = REPORTS / "raw"

DOCS = ROOT / "docs"
STRATEGY_DOC = DOCS / "ESTRATEGIA_E_RISCOS.md"
WORKFLOWS = ROOT / ".github" / "workflows"


def bootstrap() -> None:
    """Torna importáveis `lynn_mock` (app/) e `qa_support` (test/), de qualquer ponto de entrada."""
    for p in (str(APP), str(TEST)):
        if p not in sys.path:
            sys.path.insert(0, p)


def rel(path: Path) -> str:
    """Caminho relativo à raiz, com '/' (estável entre SOs; usado em planos de shard e relatórios)."""
    return Path(path).resolve().relative_to(ROOT).as_posix()
