"""Consolida os resultados dos shards em test/reports/: cucumber.json, report.html, cobertura.html, sec-report.html.

Entrada: test/reports/raw/ (behave-*.json, unit-results.json, evidence-*/screenshots, coverage-data-*.db)
Uso:     python test/scripts/build_reports.py --env hom [--fail-on-failures]
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # test/ (qa_support)
from qa_support.paths import ROOT, bootstrap  # noqa: E402

bootstrap()
from qa_support.paths import RAW, REPORTS, SEC, SPECS, STRATEGY_DOC  # noqa: E402
from qa_support.pipeline import plan  # noqa: E402
from qa_support.reporting.coverage_html import render_coverage  # noqa: E402
from qa_support.reporting.cucumber import merge_behave_json, scenario_status  # noqa: E402
from qa_support.reporting.report_html import render_report  # noqa: E402
from qa_support.reporting.sec_report_html import render_sec_report  # noqa: E402
from qa_support.reporting.traceability import (collect_cases, coverage_matrix, load_code_coverage, load_findings,  # noqa: E402
                                               load_risks, load_specs, risk_coverage)

ap = argparse.ArgumentParser()
ap.add_argument("--env", default=os.getenv("LYNN_ENV", "local"))
ap.add_argument("--raw", default=str(RAW))
ap.add_argument("--out", default=str(REPORTS))
ap.add_argument("--fail-on-failures", action="store_true")
ap.add_argument("--check-shards", action="store_true", help="falha se algum shard do plano não produziu resultado")
args = ap.parse_args()
raw, out = Path(args.raw), Path(args.out)
out.mkdir(parents=True, exist_ok=True)


def combine_coverage():
    """Junta os dados do coverage.py por camada (só existe quando LYNN_COVERAGE=1 no CI)."""
    if not importlib.util.find_spec("coverage"):
        return
    for layer in ("unit", "api", "ui"):
        parts = sorted(raw.glob(f"coverage-data-{layer}*.db"))
        if not parts:
            continue
        data = raw / f"coverage-combined-{layer}.db"
        subprocess.run([sys.executable, "-m", "coverage", "combine", "--keep", f"--data-file={data}", *map(str, parts)],
                       cwd=ROOT, check=False)
        subprocess.run([sys.executable, "-m", "coverage", "json", f"--data-file={data}",
                        "-o", str(raw / f"coverage-{layer}.json")], cwd=ROOT, check=False)


combine_coverage()
cucumber = merge_behave_json(sorted(raw.glob("behave-*.json")), sorted(raw.glob("evidence-*/screenshots")))
(out / "cucumber.json").write_text(json.dumps(cucumber, ensure_ascii=False, indent=1), encoding="utf-8")
unit_file = raw / "unit-results.json"
unit = json.loads(unit_file.read_text(encoding="utf-8")) if unit_file.exists() else None
sec_file = raw / "sec-results.json"
sec = json.loads(sec_file.read_text(encoding="utf-8")) if sec_file.exists() else None
findings = load_findings(SEC / "FINDINGS.md")

meta = {
    "env": args.env,
    "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "commit": os.getenv("GITHUB_SHA", "")[:8] or "local",
    "ref": os.getenv("GITHUB_REF_NAME", ""),
    "run_url": (f"{os.getenv('GITHUB_SERVER_URL')}/{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{os.getenv('GITHUB_RUN_ID')}"
                if os.getenv("GITHUB_RUN_ID") else ""),
    "base_url": os.getenv("LYNN_BASE_URL") or "aplicação embutida (mock)",
}
cases = collect_cases(cucumber, unit, sec)
specs = load_specs(SPECS)
matrix = coverage_matrix(specs, cases)
risks = risk_coverage(load_risks(STRATEGY_DOC), cases)
code_cov = load_code_coverage(raw)

(out / "report.html").write_text(render_report(cucumber, unit, meta, sec, findings), encoding="utf-8")
(out / "cobertura.html").write_text(render_coverage(cases, specs, matrix, risks, code_cov, meta, findings), encoding="utf-8")
(out / "sec-report.html").write_text(
    render_sec_report(sec, findings, SEC / "FINDINGS.md", SEC / "README.md", meta), encoding="utf-8")

failed = [c for c in cases if c.status == "failed"]
missing_shards = []
if args.check_shards:
    for shard in plan(int(os.getenv("LYNN_API_SHARDS", "4"))):
        produced = raw / {"unit": "unit-results.json", "sec": "sec-results.json"}.get(shard["layer"], f"behave-{shard['name']}.json")
        if not produced.exists() or not produced.read_text(encoding="utf-8").strip():
            missing_shards.append(shard["name"])
total_rules = len(matrix)
covered = sum(r["covered"] for r in matrix)
summary = [f"## Qualidade — ambiente `{args.env}`", "",
           "| Camada | Casos | Falhas |", "|---|---|---|"]
for layer, label in (("ui", "E2E UI"), ("api", "API"), ("unit", "Unitário"), ("sec", "Segurança")):
    lc = [c for c in cases if c.layer == layer]
    summary.append(f"| {label} | {len(lc)} | {sum(c.status == 'failed' for c in lc)} |")
summary += ["", f"**Regras de negócio cobertas:** {covered}/{total_rules} · **Falhas:** {len(failed)}",
            "", "Relatórios no artefato `qa-reports-" + args.env + "`: `report.html`, `cobertura.html`, `sec-report.html`, `cucumber.json`."]
open_findings = [f for f in findings if f["status"] != "mitigado"]
if open_findings:
    worst = ", ".join(f"{f['id']} ({f['severity']})" for f in sorted(open_findings, key=lambda f: -f["cvss"])[:3])
    summary += ["", f"**Segurança:** {len(open_findings)} achado(s) aberto(s) em test/sec/FINDINGS.md · mais graves: {worst}"]
if missing_shards:
    summary += ["", f"### ⚠ Shards sem resultado (quebraram antes de reportar): {', '.join(missing_shards)}"]
if failed:
    summary += ["", "### Falhas", *[f"- `{c.layer}` · {c.group} · {c.name}" for c in failed[:30]]]
(out / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
if os.getenv("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
        fh.write("\n".join(summary) + "\n")
print(f"cucumber.json: {sum(len(f['elements']) for f in cucumber)} cenários em {len(cucumber)} features")
print(f"report.html, cobertura.html e sec-report.html gerados em {out}  ·  regras cobertas {covered}/{total_rules}  ·  falhas {len(failed)}")
if missing_shards:
    print(f"shards sem resultado: {', '.join(missing_shards)}", file=sys.stderr)
sys.exit(1 if (args.fail_on_failures and failed) or missing_shards else 0)
