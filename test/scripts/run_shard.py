"""Executa UM shard do plano (é o que cada job da matrix do GitHub Actions chama).

  python test/scripts/run_shard.py --shard api-2
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # test/ (qa_support)
from qa_support.pipeline import plan, run_shard  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--shard", required=True)
ap.add_argument("--api-shards", type=int, default=int(os.getenv("LYNN_API_SHARDS", "4")))
args = ap.parse_args()
shard = next((s for s in plan(args.api_shards) if s["name"] == args.shard), None)
if shard is None:
    sys.exit(f"shard desconhecido: {args.shard}. Veja: python test/scripts/plan_shards.py")
sys.exit(run_shard(shard))
