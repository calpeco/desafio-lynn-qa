"""Rastreabilidade: specs (regras) + matriz de riscos + resultados por camada da pirâmide."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..paths import rel
from .cucumber import scenario_status

LAYERS = ("ui", "api", "unit")  # pirâmide: topo → base
CROSS_LAYERS = ("sec",)          # dimensões transversais (fora da contagem da pirâmide)
ALL_LAYERS = LAYERS + CROSS_LAYERS
LAYER_LABEL = {"ui": "E2E de UI", "api": "API / contrato / integração", "unit": "Unitário", "sec": "Segurança"}


@dataclass
class Rule:
    spec: str
    rid: str            # ex.: RN04
    text: str
    layers: list[str]
    risks: list[str]

    @property
    def tag(self) -> str:
        return f"{self.spec}-{self.rid}"


@dataclass
class Spec:
    id: str
    title: str
    path: str
    status: str
    rules: list[Rule] = field(default_factory=list)


_FRONT = re.compile(r"^---\s*\n(.*?)\n---", re.S)
_RULE = re.compile(r"^\s*-\s*\*\*(RN\d+)\*\*\s*[—-]\s*(.+?)\s*$", re.M)


def _front_matter(text: str) -> dict:
    m = _FRONT.match(text)
    meta = {}
    for line in (m.group(1).splitlines() if m else []):
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.split("#", 1)[0].strip()
    return meta


def parse_spec(path: Path) -> Spec:
    text = path.read_text(encoding="utf-8")
    meta = _front_matter(text)
    spec = Spec(meta.get("id", path.stem.upper()), meta.get("titulo", path.stem), str(path), meta.get("status", ""))
    for rid, body in _RULE.findall(text):
        layers = re.search(r"\[camadas:\s*([^\]]+)\]", body)
        risks = re.search(r"\[riscos:\s*([^\]]+)\]", body)
        clean = re.sub(r"\s*\[(camadas|riscos):[^\]]*\]", "", body).strip()
        spec.rules.append(Rule(spec.id, rid, clean,
                               [x.strip() for x in layers.group(1).split(",")] if layers else [],
                               [x.strip() for x in risks.group(1).split(",")] if risks else []))
    return spec


def load_specs(specs_dir: Path) -> list[Spec]:
    specs = [parse_spec(p) for p in sorted(specs_dir.glob("*.md")) if not p.name.startswith(("_", "README"))]
    for spec in specs:  # caminho relativo ao repositório (o relatório não deve expor a máquina)
        spec.path = rel(Path(spec.path))
    return specs


def load_risks(strategy_md: Path) -> dict[str, dict]:
    """Lê a matriz de riscos (linhas '| R01 | descrição | I | P | score | prioridade | ...')."""
    risks = {}
    for line in strategy_md.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and re.fullmatch(r"R\d+", cells[0]):
            risks[cells[0]] = {"id": cells[0], "text": cells[1], "score": cells[4],
                               "priority": re.sub(r"\*", "", cells[5])}
    return risks


@dataclass
class TestCase:
    layer: str
    name: str
    group: str
    status: str
    tags: list[str]
    duration_s: float


def collect_cases(cucumber: list[dict], unit_results: dict | None, sec_results: dict | None = None) -> list[TestCase]:
    cases = []
    for feature in cucumber:
        layer = "ui" if "/ui/" in feature["uri"] or any(t["name"] == "@ui" for t in feature["tags"]) else "api"
        for el in feature["elements"]:
            tags = [t["name"].lstrip("@") for t in feature["tags"] + el["tags"]]
            dur = sum(s["result"].get("duration", 0) for s in el["steps"]) / 1e9
            cases.append(TestCase(layer, el["name"], Path(feature["uri"]).stem, scenario_status(el), tags, dur))
    for layer, results in (("unit", unit_results), ("sec", sec_results)):
        for t in (results or {}).get("tests", []):
            cases.append(TestCase(layer, t["name"], Path(t["file"]).stem, t["status"], t.get("tags", []), t["duration_s"]))
    return cases


def coverage_matrix(specs: list[Spec], cases: list[TestCase]) -> list[dict]:
    """Uma linha por regra: casos por camada, status agregado e se a cobertura sugerida foi atendida."""
    rows = []
    for spec in specs:
        for rule in spec.rules:
            per_layer = {}
            for layer in ALL_LAYERS:
                hits = [c for c in cases if c.layer == layer and rule.tag in c.tags]
                failed = sum(c.status == "failed" for c in hits)
                per_layer[layer] = {"count": len(hits), "failed": failed,
                                    "status": "none" if not hits else ("failed" if failed else "passed")}
            covered_layers = [l for l in ALL_LAYERS if per_layer[l]["count"]]
            missing = [l for l in rule.layers if per_layer.get(l, {}).get("count", 0) == 0]
            rows.append({"spec": spec.id, "rule": rule, "per_layer": per_layer, "covered": bool(covered_layers),
                         "missing_suggested": missing,
                         "failing": any(per_layer[l]["failed"] for l in ALL_LAYERS)})
    return rows


def risk_coverage(risks: dict[str, dict], cases: list[TestCase]) -> list[dict]:
    rows = []
    for rid, risk in risks.items():
        per_layer = {l: sum(1 for c in cases if c.layer == l and rid in c.tags) for l in ALL_LAYERS}
        failed = sum(1 for c in cases if rid in c.tags and c.status == "failed")
        rows.append({**risk, "per_layer": per_layer, "total": sum(per_layer.values()), "failed": failed})
    return rows


def load_code_coverage(raw_dir: Path) -> dict[str, dict]:
    """coverage.py JSON por camada (coverage-unit.json, coverage-api.json, coverage-ui.json), se existir."""
    out = {}
    for layer in LAYERS:
        f = raw_dir / f"coverage-{layer}.json"
        if f.exists():
            totals = json.loads(f.read_text(encoding="utf-8")).get("totals", {})
            out[layer] = {"percent": round(float(totals.get("percent_covered", 0)), 1),
                          "covered": totals.get("covered_lines", 0), "statements": totals.get("num_statements", 0)}
    return out


_FINDING_ROW = re.compile(r"^\|\s*(SEC-\d+)\s*\|\s*(.+?)\s*\|\s*\**([^|*]+?)\**\s*\|\s*([\d.]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\w+)\s*\|", re.M)


def load_findings(findings_md: Path) -> list[dict]:
    """Tabela-resumo de test/sec/FINDINGS.md: id, título, severidade, CVSS, OWASP, risco, status."""
    if not findings_md.exists():
        return []
    rows = _FINDING_ROW.findall(findings_md.read_text(encoding="utf-8"))
    return [{"id": i, "title": t, "severity": sev.strip(), "cvss": float(c), "owasp": o, "risk": r, "status": st}
            for i, t, sev, c, o, r, st in rows]
