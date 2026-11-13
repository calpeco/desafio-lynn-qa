"""Ferramental de relatório: conversão behave → Cucumber JSON, rastreabilidade e plano de shards."""
import json
from pathlib import Path

from qa_support.pipeline import plan, scenario_weight
from qa_support.reporting.coverage_html import render_coverage
from qa_support.reporting.cucumber import merge_behave_json, scenario_status
from qa_support.reporting.report_html import render_report
from qa_support.reporting.traceability import TestCase as Case, collect_cases, coverage_matrix, load_risks, load_specs, parse_spec

from qa_support.paths import FEATURES, SPECS, STRATEGY_DOC, rel

BEHAVE = [{
    "keyword": "Funcionalidade", "name": "Demo", "tags": ["api"], "location": "features/api/demo.feature:3",
    "status": "failed", "elements": [
        {"type": "background", "name": "", "location": "features/api/demo.feature:5", "steps": []},
        {"type": "scenario", "keyword": "Cenário", "name": "Passa", "tags": ["CONV-RN01", "R16"],
         "location": "features/api/demo.feature:8", "status": "passed",
         "steps": [{"keyword": "Dado", "name": "x", "location": "features/api/demo.feature:9",
                    "result": {"status": "passed", "duration": 0.5},
                    "table": {"headings": ["a"], "rows": [["1"]]}}]},
        {"type": "scenario", "keyword": "Cenário", "name": "Falha", "tags": ["CONV-RN04"],
         "location": "features/api/demo.feature:12", "status": "failed",
         "steps": [{"keyword": "Quando", "name": "y", "location": "features/api/demo.feature:13",
                    "result": {"status": "failed", "duration": 0.1, "error_message": ["linha 1", "linha 2"]}},
                   {"keyword": "Então", "name": "z", "location": "features/api/demo.feature:14"}]},
    ]}]


def _write(tmp_path, data, name="behave-api-1.json"):
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_conversao_para_cucumber_json(tmp_path):
    cuke = merge_behave_json([_write(tmp_path, BEHAVE)])
    f = cuke[0]
    assert (f["uri"], f["line"], f["tags"][0]["name"]) == ("features/api/demo.feature", 3, "@api")
    assert [e["name"] for e in f["elements"]] == ["Passa", "Falha"]           # background descartado
    ok, bad = f["elements"]
    assert ok["steps"][0]["result"] == {"status": "passed", "duration": 500_000_000}  # ns
    assert ok["steps"][0]["rows"] == [{"cells": ["a"]}, {"cells": ["1"]}]
    assert bad["steps"][0]["result"]["error_message"] == "linha 1\nlinha 2"
    assert bad["steps"][1]["result"]["status"] == "skipped"                   # passo não executado
    assert (scenario_status(ok), scenario_status(bad)) == ("passed", "failed")


def test_shards_sao_mesclados_por_feature(tmp_path):
    a = _write(tmp_path, BEHAVE, "behave-api-1.json")
    b = _write(tmp_path, BEHAVE, "behave-api-2.json")
    cuke = merge_behave_json([a, b])
    assert len(cuke) == 1 and len(cuke[0]["elements"]) == 4


def test_screenshot_vira_embedding(tmp_path):
    shots = tmp_path / "screenshots"
    shots.mkdir()
    (shots / "ok__Passa.png").write_bytes(b"\x89PNG fake")
    cuke = merge_behave_json([_write(tmp_path, BEHAVE)], [shots])
    emb = cuke[0]["elements"][0]["steps"][-1]["embeddings"][0]
    assert emb["mime_type"] == "image/png" and emb["data"]


def test_parse_spec_e_matriz(tmp_path):
    spec = tmp_path / "x.md"
    spec.write_text("---\nid: ABC\ntitulo: T\n---\n- **RN01** — Regra um. [camadas: unit, api] [riscos: R01]\n"
                    "- **RN02** — Regra dois.\n", encoding="utf-8")
    s = parse_spec(spec)
    assert [(r.tag, r.layers, r.risks) for r in s.rules] == [("ABC-RN01", ["unit", "api"], ["R01"]), ("ABC-RN02", [], [])]
    cases = [Case("api", "t", "g", "passed", ["ABC-RN01"], 0.1)]
    m = coverage_matrix([s], cases)
    assert m[0]["covered"] and m[0]["missing_suggested"] == ["unit"]
    assert not m[1]["covered"]


def test_specs_e_riscos_reais_sao_lidos():
    specs = load_specs(SPECS)
    assert any(s.id == "CONV" and len(s.rules) >= 10 for s in specs)
    risks = load_risks(STRATEGY_DOC)
    assert {"R01", "R02", "R18"} <= set(risks) and risks["R02"]["priority"] == "P1"


def test_relatorios_html_renderizam(tmp_path):
    cuke = merge_behave_json([_write(tmp_path, BEHAVE)])
    unit = {"tests": [{"id": "t", "file": "test/unit/test_x.py", "name": "test_x", "status": "passed",
                       "duration_s": 0.01, "tags": ["CONV-RN04"], "error": None}]}
    meta = {"env": "dev"}
    html = render_report(cuke, unit, meta)
    assert "Relatório de execução" in html and "Falha" in html and "linha 2" in html
    cases = collect_cases(cuke, unit)
    specs = load_specs(SPECS)
    cov = render_coverage(cases, specs, coverage_matrix(specs, cases),
                          [], {"unit": {"percent": 91.0, "covered": 91, "statements": 100}}, meta)
    assert "Pirâmide de testes" in cov and "91%" in cov and "<svg" in cov


def test_plano_de_shards_cobre_todas_as_features_uma_vez():
    shards = plan(api_shards=3)
    paths = [p for s in shards if s["layer"] in ("api", "ui") for p in s["paths"]]
    features = sorted(rel(p) for p in FEATURES.glob("*/*.feature"))
    assert sorted(paths) == features and len(paths) == len(set(paths))


def test_peso_conta_cenarios_e_linhas_de_exemplos(tmp_path):
    f = tmp_path / "x.feature"
    f.write_text("# language: pt\nFuncionalidade: X\n  Contexto:\n    Dado que algo\n"
                 "  Cenário: um\n    Dado que a\n  Cenário: dois\n    Dado que b\n"
                 "  Esquema do Cenário: três\n    Dado que <v>\n    Exemplos:\n      | v |\n      | 1 |\n      | 2 |\n      | 3 |\n",
                 encoding="utf-8")
    assert scenario_weight(f) == 5


def test_ambiente_compartilhado_forca_api_serial(monkeypatch):
    monkeypatch.setenv("LYNN_BASE_URL", "https://hom.exemplo")
    assert sum(1 for s in plan(api_shards=4) if s["layer"] == "api") == 1


def test_log_de_evidencias_mascara_dados_pessoais():
    """Achado do agent-qa-lynn: o log de trocas HTTP gravava o comentário (RN08 da spec FDBK)."""
    from qa_support.http_client import _mask_response, redact

    assert redact('{"rating": "positive", "comment": "ligue 123.456.789-00"}') == '{"rating": "positive", "comment": "***"}'
    assert "4111" not in redact('{"content": "cartão 4111 1111 1111 1111"}')
    assert _mask_response({"comment": "texto", "rating": "negative"}) == {"comment": "***", "rating": "negative"}
    assert _mask_response({"comment": None}) == {"comment": None}


def test_achados_de_seguranca_sao_lidos_do_findings():
    from qa_support.paths import SEC
    from qa_support.reporting.traceability import load_findings

    findings = load_findings(SEC / "FINDINGS.md")
    assert {f["id"] for f in findings} >= {"SEC-001", "SEC-009"}
    crit = next(f for f in findings if f["id"] == "SEC-001")
    assert crit["severity"] == "Crítica" and crit["cvss"] == 9.4


def test_seguranca_e_transversal_e_nao_entra_na_piramide(tmp_path):
    from qa_support.reporting.traceability import LAYERS

    sec = {"tests": [{"id": "s", "file": "test/sec/test_api1_bola.py", "name": "t", "status": "xfailed",
                      "duration_s": 0.1, "tags": ["API1:2023", "CONV-RN08", "R01"], "error": "SEC-001"}]}
    cases = collect_cases([], None, sec)
    assert cases[0].layer == "sec" and "sec" not in LAYERS
    html = render_coverage(cases, load_specs(SPECS), coverage_matrix(load_specs(SPECS), cases), [], {}, {"env": "x"},
                           [{"id": "SEC-001", "title": "x", "severity": "Crítica", "cvss": 9.4, "owasp": "API5",
                             "risk": "R16", "status": "aberto"}])
    assert "API1:2023" in html and "SEC-001" in html and "Segurança" in html


def test_plano_tem_shard_de_seguranca():
    assert any(s["name"] == "sec" and s["paths"] == ["test/sec"] for s in plan())


def test_sec_report_cruza_resultados_achados_e_owasp(tmp_path):
    from qa_support.paths import SEC
    from qa_support.reporting.sec_report_html import md_to_html, parse_finding_sections, parse_owasp_map, render_sec_report
    from qa_support.reporting.traceability import load_findings

    sections = parse_finding_sections(SEC / "FINDINGS.md")
    assert "SEC-001" in sections and "Reprodução" in sections["SEC-001"]["body_md"]
    na = parse_owasp_map(SEC / "README.md")
    assert {"API6", "API7", "LLM06"} <= set(na) and {"LLM03", "LLM04", "LLM08", "LLM09"} <= set(na)
    assert "<pre>" in md_to_html("- a\n  ```bash\n  curl x\n  ```") and "<code>x</code>" in md_to_html("`x`")
    sec = {"tests": [
        {"id": "test/sec/test_api5_x.py::t", "file": "test/sec/test_api5_x.py", "name": "t", "status": "xfailed",
         "duration_s": 0.1, "tags": ["API5:2023", "R16"], "error": "SEC-001: controle exposto"},
        {"id": "test/sec/test_api1_x.py::u", "file": "test/sec/test_api1_x.py", "name": "u", "status": "passed",
         "duration_s": 0.1, "tags": ["API1:2023"], "error": None}]}
    html = render_sec_report(sec, load_findings(SEC / "FINDINGS.md"), SEC / "FINDINGS.md", SEC / "README.md", {"env": "hom"})
    assert "Relatório de segurança" in html and "Crítica" in html
    assert "reproduzido nesta execução por 1 teste(s)" in html          # ligação teste ↔ achado pelo reason do xfail
    assert "não aplicável" in html and "LLM10" in html and "API10" in html  # matriz OWASP completa (20 categorias)
