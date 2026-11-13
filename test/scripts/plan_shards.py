"""Imprime o plano de shards. Com --github-output, publica a matrix para o GitHub Actions.

  python test/scripts/plan_shards.py                 # tabela legível
  python test/scripts/plan_shards.py --api-shards 3  # muda o paralelismo da API
  python test/scripts/plan_shards.py --github-output # escreve matrix=... em $GITHUB_OUTPUT
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # test/ (qa_support)
from qa_support.pipeline import plan  # noqa: E402
from qa_support.faults import FAULTS, SEC_EXPECT  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--api-shards", type=int, default=int(os.getenv("LYNN_API_SHARDS", "4")))
ap.add_argument("--github-output", action="store_true")
args = ap.parse_args()
shards = plan(args.api_shards)
matrix = {"include": [{"name": s["name"], "layer": s["layer"]} for s in shards]}
if args.github_output:
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write(f"matrix={json.dumps(matrix)}\n")
        # a suíte de segurança inclui um teste no Chromium: defeitos com SEC_EXPECT também precisam do navegador
        faults = [{"fault": name, "browser": tag == "@ui" or name in SEC_EXPECT} for name, (_, tag, _) in FAULTS.items()]
        fh.write(f"faults={json.dumps({'include': faults})}\n")
for s in shards:
    print(f"{s['name']:8} {s['layer']:5} peso={s['weight']:<4} {' '.join(s['paths'])}")
