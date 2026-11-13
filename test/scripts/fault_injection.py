"""A suíte DETECTA defeitos reais? (teste de mutação manual)

Liga um defeito por vez na aplicação (LYNN_FAULTS), roda a camada que deveria pegá-lo e
verifica que a feature esperada ficou vermelha. Lê os relatórios JUnit do behave.
Saídas: test/evidence/fault_injection/<defeito>.txt e SUMMARY.md. Exit 1 se algum passar despercebido.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qa_support.paths import EVIDENCE, ROOT  # noqa: E402
from qa_support.faults import FAULTS, SEC_EXPECT  # noqa: E402
OUT = EVIDENCE / "fault_injection"
PY = os.getenv("PYTHON", sys.executable)

def failed_scenarios(junit_dir: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for xml in junit_dir.glob("*.xml"):
        root = ET.parse(xml).getroot()
        for case in root.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                result.setdefault(xml.stem, []).append(case.get("name"))
    return result


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="roda um único defeito (usado pela matrix do CI)")
    args = ap.parse_args()
    selected = {args.only: FAULTS[args.only]} if args.only else FAULTS
    if OUT.exists() and not args.only:
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    rows, undetected = [], []
    for fault, (desc, tag, expected) in selected.items():
        junit = Path(tempfile.mkdtemp(prefix=f"lynn_{fault}_"))
        env = {**os.environ, "LYNN_FAULTS": fault, "LYNN_EVIDENCE_DIR": str(junit / "evidence")}
        proc = subprocess.run([PY, "-m", "behave", f"--tags={tag}", "-f", "progress",
                               "--junit", "--junit-directory", str(junit)],
                              cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
        (OUT / f"{fault}.txt").write_text(f"$ LYNN_FAULTS={fault} behave --tags={tag}\n\n{proc.stdout}{proc.stderr}",
                                          encoding="utf-8")
        failed = failed_scenarios(junit)
        total = sum(len(v) for v in failed.values())
        detected = any(expected in f for f in failed)
        sec_cell = "—"
        if fault in SEC_EXPECT:  # a suíte de segurança (test/sec) também precisa pegar este defeito
            sec_json = junit / "sec-results.json"
            sec_proc = subprocess.run([PY, "-m", "pytest", "test/sec", "-q", "-p", "no:cacheprovider"], cwd=ROOT,
                                      env={**env, "LYNN_SEC_RESULTS": str(sec_json)},
                                      capture_output=True, text=True, timeout=900)
            with (OUT / f"{fault}.txt").open("a", encoding="utf-8") as fh:
                fh.write(f"\n\n$ LYNN_FAULTS={fault} pytest test/sec\n\n{sec_proc.stdout[-6000:]}")
            sec_failed = [t for t in json.loads(sec_json.read_text(encoding="utf-8"))["tests"] if t["status"] == "failed"]
            sec_ok = any(SEC_EXPECT[fault] in t["file"] for t in sec_failed)
            detected = detected and sec_ok
            sec_cell = f"{'✅' if sec_ok else '❌'} {len(sec_failed)} falham (inclui `{SEC_EXPECT[fault]}`)"
        undetected += [] if detected else [fault]
        files = ", ".join(sorted(k.replace("TESTS-", "") for k in failed)) or "—"
        rows.append(f"| `{fault}` | {desc} | {tag} | `{expected}` | {total} | {files} | {sec_cell} | "
                    f"{'✅ detectado' if detected else '❌ NÃO detectado'} |")
        print(f"{fault:20} {tag:5} {'DETECTADO' if detected else 'NAO DETECTADO':14} {total:3} cenários falharam"
              + (f" · segurança: {sec_cell}" if sec_cell != "—" else ""))

    md = ["# Injeção de falhas — a suíte detecta defeitos reais?", "",
          "Cada linha liga UM defeito na aplicação (`LYNN_FAULTS=<defeito>`) e roda a camada correspondente.",
          "Esperado: a suíte FALHA, na feature que cobre aquele risco.", "",
          "Defeitos de segurança também precisam ser pegos pela suíte `test/sec` (coluna Segurança).", "",
          "| Defeito | O que quebra | Camada | Feature esperada | Cenários que falharam | Features com falha | Segurança (test/sec) | Resultado |",
          "|---|---|---|---|---|---|---|---|", *rows, "",
          "Saída completa de cada rodada: `test/evidence/fault_injection/<defeito>.txt`."]
    (OUT / (f"SUMMARY-{args.only}.md" if args.only else "SUMMARY.md")).write_text("\n".join(md) + "\n", encoding="utf-8")
    return 1 if undetected else 0


if __name__ == "__main__":
    sys.exit(main())
