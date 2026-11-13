"""Roda a pirâmide inteira EM PARALELO localmente (mesmo plano do CI) e gera os relatórios.

  python test/scripts/run_parallel.py             # todos os shards, paralelismo = nº de CPUs
  python test/scripts/run_parallel.py -j 3 --api-shards 2
  python test/scripts/run_parallel.py --env dev   # rótulo do ambiente nos relatórios

Cada shard sobe a SUA instância da aplicação (porta aleatória): não há estado compartilhado.
Saída: test/reports/cucumber.json, test/reports/report.html, test/reports/cobertura.html.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # test/ (qa_support)
from qa_support.paths import ROOT, bootstrap  # noqa: E402

bootstrap()
from qa_support.pipeline import RAW, plan, run_shard, summary_line  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 4)
ap.add_argument("--api-shards", type=int, default=int(os.getenv("LYNN_API_SHARDS", "4")))
ap.add_argument("--env", default=os.getenv("LYNN_ENV", "local"))
args = ap.parse_args()

shutil.rmtree(RAW, ignore_errors=True)
shards = plan(args.api_shards)
print(f"{len(shards)} shards, até {args.jobs} em paralelo:")
t0 = time.monotonic()


def go(shard):
    start = time.monotonic()
    rc = run_shard(shard, quiet=True)
    line = summary_line((RAW / f"{shard['name']}.log").read_text(encoding="utf-8"))
    print(f"  {'✔' if rc == 0 else '✘'} {shard['name']:7} {time.monotonic() - start:5.1f}s  {line}", flush=True)
    return rc


with ThreadPoolExecutor(max_workers=args.jobs) as pool:
    codes = list(pool.map(go, shards))
print(f"tempo total (paralelo): {time.monotonic() - t0:.1f}s")
rc = subprocess.call([sys.executable, str(Path(__file__).resolve().parent / "build_reports.py"), "--env", args.env], cwd=ROOT)
sys.exit(1 if any(codes) or rc else 0)
