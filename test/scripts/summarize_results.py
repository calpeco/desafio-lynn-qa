"""Gera test/evidence/latest/RESULTS.md: a pirâmide executada (unit → API → UI) a partir dos JUnit."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else "test/evidence/latest")


def collect(directory: Path):
    rows, total, failed, secs = [], 0, 0, 0.0
    for xml in sorted(directory.glob("*.xml")):
        for case in ET.parse(xml).getroot().iter("testcase"):
            bad = case.find("failure") is not None or case.find("error") is not None
            t = float(case.get("time", 0) or 0)
            total, failed, secs = total + 1, failed + bad, secs + t
            group = xml.stem.replace("TESTS-", "") if xml.stem.startswith("TESTS-") else case.get("classname", "")
            rows.append((("❌" if bad else "✅"), group.split(".")[-1], case.get("name"), t))
    return rows, total, failed, secs


layers = [("Topo — E2E UI (behave + Playwright)", out / "ui"),
          ("Meio — API/contrato/integração (behave + httpx)", out / "api"),
          ("Base — unitários (pytest)", out / "unit")]
md = ["# Resultado da execução — pirâmide de testes", "",
      "| Camada | Casos | Falhas | Tempo |", "|---|---|---|---|"]
details, all_ok = [], True
for name, d in layers:
    rows, total, failed, secs = collect(d)
    all_ok &= failed == 0 and total > 0
    md.append(f"| {name} | {total} | {failed} | {secs:.1f}s |")
    details += ["", f"<details><summary>{name}: {total} casos</summary>", "",
                "| | Grupo | Caso | Tempo |", "|---|---|---|---|"]
    details += [f"| {r[0]} | `{r[1]}` | {r[2]} | {r[3]:.2f}s |" for r in rows] + ["", "</details>"]
md += ["", f"**Status geral: {'✅ SUCESSO' if all_ok else '❌ FALHA'}**"] + details
(out / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(f"escrito {out / 'RESULTS.md'}")
