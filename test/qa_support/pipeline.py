"""Planejamento de shards e execução de um shard (local ou CI).

Shards são descobertos automaticamente: toda feature nova criada (inclusive pelo agent-qa-lynn)
entra no plano sem editar YAML. API é distribuída por peso (nº de cenários) entre N shards;
UI e unit são shards próprios.
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .paths import FEATURES, RAW, ROOT, SEC, UNIT, rel


def scenario_weight(feature: Path) -> int:
    """Cenários + linhas de Exemplos (cada linha vira um cenário)."""
    weight, in_examples = 0, False
    for line in feature.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith(("Cenário:", "Cenario:")):
            weight, in_examples = weight + 1, False
        elif s.startswith(("Exemplos:", "Cenários:")):
            in_examples = "header"
        elif s.startswith("|") and in_examples:
            weight += 0 if in_examples == "header" else 1
            in_examples = True
        elif s.startswith(("Esquema do Cenário", "Contexto:")):
            in_examples = False
    return max(weight, 1)


def plan(api_shards: int = 4, include_unit: bool = True, include_ui: bool = True, include_sec: bool = True) -> list[dict]:
    if os.getenv("LYNN_BASE_URL"):
        # Ambiente compartilhado: cenários que alteram estado global (modo do LLM, reset) colidiriam
        # entre shards concorrentes. Sem isolamento por sessão no ambiente alvo, API roda serial.
        api_shards = 1
    api_files = sorted(FEATURES.glob("*/*.feature"))
    api_files = [f for f in api_files if f.parent.name != "ui"]
    bins = [{"name": f"api-{i + 1}", "layer": "api", "paths": [], "weight": 0} for i in range(max(api_shards, 1))]
    for f in sorted(api_files, key=scenario_weight, reverse=True):  # bin packing guloso
        target = min(bins, key=lambda b: b["weight"])
        target["paths"].append(rel(f))
        target["weight"] += scenario_weight(f)
    shards = [b for b in bins if b["paths"]]
    if include_ui and (FEATURES / "ui").exists():
        ui = sorted(rel(f) for f in (FEATURES / "ui").glob("*.feature"))
        shards.append({"name": "ui", "layer": "ui", "paths": ui, "weight": sum(scenario_weight(ROOT / p) for p in ui)})
    if include_unit:
        shards.insert(0, {"name": "unit", "layer": "unit", "paths": [rel(UNIT)], "weight": 0})
    if include_sec and SEC.exists():
        shards.append({"name": "sec", "layer": "sec", "paths": [rel(SEC)], "weight": 0})
    return shards


def _coverage_prefix(shard: str) -> list[str]:
    if os.getenv("LYNN_COVERAGE") == "1" and importlib.util.find_spec("coverage"):
        # sem ponto no nome: upload-artifact ignora arquivos ocultos
        return [sys.executable, "-m", "coverage", "run", f"--data-file={RAW / f'coverage-data-{shard}.db'}",
                "--source=lynn_mock"]
    return [sys.executable]


def run_shard(shard: dict, quiet: bool = False) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    name = shard["name"]
    env = {**os.environ, "LYNN_EVIDENCE_DIR": str(RAW / f"evidence-{name}")}
    log = RAW / f"{name}.log"
    if shard["layer"] in ("unit", "sec"):
        env["LYNN_UNIT_RESULTS"] = str(RAW / "unit-results.json")
        env["LYNN_SEC_RESULTS"] = str(RAW / "sec-results.json")
        cmd = _coverage_prefix(name) + ["-m", "pytest", *shard["paths"], "-q", "-p", "no:cacheprovider",
                                        f"--junitxml={RAW / f'junit-{name}.xml'}"]
    else:
        junit = RAW / f"junit-{name}"
        shutil.rmtree(junit, ignore_errors=True)
        cmd = _coverage_prefix(name) + ["-m", "behave", *shard["paths"], "-f", "json", "-o", str(RAW / f"behave-{name}.json"),
                                        "-f", "progress", "--junit", "--junit-directory", str(junit)]
    with log.open("w", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(cmd) + "\n\n")
        fh.flush()
        proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        fh.write(proc.stdout)
    if not quiet:
        print(proc.stdout)
    return proc.returncode


def summary_line(log_text: str) -> str:
    for pattern in (r"\d+ scenarios? passed.*", r"=+ (.*(?:passed|failed).*) =+", r"^(\d+ (?:passed|failed).*)$"):
        m = re.search(pattern, log_text, re.M)
        if m:
            return (m.group(1) if m.groups() else m.group(0)).strip()
    return "?"
