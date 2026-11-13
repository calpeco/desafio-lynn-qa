"""Gera test/docs/STEP_CATALOG.md: todos os passos disponíveis, para REUTILIZAR antes de criar.

  python test/scripts/step_catalog.py           # regenera o catálogo
  python test/scripts/step_catalog.py --check   # falha se estiver desatualizado (usado no CI)
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # test/ (qa_support)
from qa_support.paths import ROOT, bootstrap  # noqa: E402

bootstrap()
from qa_support.steps_index import load_steps  # noqa: E402

PREFIX = {"given": "Dado", "when": "Quando", "then": "Então", "step": "Dado/Quando/Então"}
steps = load_steps()
by_file = defaultdict(list)
for s in steps:
    by_file[s.file].append(s)
lines = ["# Catálogo de steps", "",
         "> Gerado por `python test/scripts/step_catalog.py`. **Não edite à mão.** Antes de criar um passo novo,",
         "> procure aqui. Tipos de placeholder: `{x:Q}` texto entre aspas · `{n:d}` inteiro · `{x}` resto da linha.",
         "> Passos `Dado` começam com `que` no texto (ex.: `Dado que \"Alice\" tem uma conversa aberta`).", "",
         f"Total: **{len(steps)} passos** em {len(by_file)} arquivos.", ""]
for file, items in sorted(by_file.items()):
    lines += [f"## `{file}`", "", "| Tipo | Padrão | Função |", "|---|---|---|"]
    for s in items:
        pattern = s.pattern.replace("|", "\\|")
        doc = f" — {s.doc}" if s.doc else ""
        lines.append(f"| {PREFIX[s.kind]} | `{pattern}` | `{s.func}` (L{s.line}){doc} |")
    lines.append("")
content = "\n".join(lines)
from qa_support.paths import TEST_DOCS  # noqa: E402

target = TEST_DOCS / "STEP_CATALOG.md"
if "--check" in sys.argv:
    sys.exit(0 if target.exists() and target.read_text(encoding="utf-8") == content else 1)
target.write_text(content, encoding="utf-8")
print(f"{target.relative_to(ROOT)}: {len(steps)} passos")
