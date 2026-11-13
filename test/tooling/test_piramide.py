"""Gate da pirâmide: a suíte inteira precisa manter o formato saudável.

Mesmo critério do cobertura.html (qa_support/reporting/coverage_html.py):
unitário ≥ 1,5 × API e API ≥ 2 × UI. Conta casos como o behave e o pytest executam
(linhas de Exemplos contam como cenários; parametrize conta como testes).
"""
import subprocess
import sys
from pathlib import Path

from qa_support.pipeline import scenario_weight
from qa_support.reporting.coverage_html import RATIO_API_UI, RATIO_UNIT_API

from qa_support.paths import FEATURES, ROOT, UNIT, rel


def _counts():
    out = subprocess.run([sys.executable, "-m", "pytest", rel(UNIT), "--collect-only", "-q", "-p", "no:cacheprovider"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    unit = sum(1 for line in out.splitlines() if "::" in line)
    api = sum(scenario_weight(f) for f in FEATURES.glob("*/*.feature") if f.parent.name != "ui")
    ui = sum(scenario_weight(f) for f in (FEATURES / "ui").glob("*.feature"))
    return unit, api, ui


def test_piramide_saudavel():
    unit, api, ui = _counts()
    assert unit >= RATIO_UNIT_API * api, (
        f"base estreita: unitário {unit} < {RATIO_UNIT_API}× API ({api}). Mova a combinatória de validação da API "
        f"para test/unit e mantenha 1-2 exemplos representativos por regra na API.")
    assert api >= RATIO_API_UI * ui, f"topo pesado: API {api} < {RATIO_API_UI}× UI ({ui}). Leve para a API o que não exige navegador."
