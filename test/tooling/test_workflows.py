"""Valida a estrutura dos workflows do GitHub Actions (não há actionlint/rede no ambiente local)."""
import re
from pathlib import Path

import pytest
import yaml

from qa_support.paths import ROOT, TEST
from qa_support.paths import WORKFLOWS as WF


def load(name):
    data = yaml.safe_load((WF / name).read_text(encoding="utf-8"))
    data["on"] = data.pop(True, data.get("on"))  # YAML 1.1 lê a chave `on` como booleano
    return data


@pytest.mark.parametrize("name,env", [("dev.yml", "dev"), ("hom.yml", "hom")])
def test_ambiente_chama_o_pipeline_reutilizavel(name, env):
    wf = load(name)
    job = wf["jobs"]["qa"]
    assert job["uses"] == "./.github/workflows/_qa-pipeline.yml"
    assert job["with"]["environment"] == env
    assert job["secrets"] == "inherit"
    assert wf["permissions"] == {"contents": "read"}
    assert "workflow_dispatch" in wf["on"]


def test_hom_roda_injecao_de_defeitos_e_dev_nao():
    assert load("dev.yml")["jobs"]["qa"]["with"]["run_fault_injection"] is False
    assert "run_fault_injection" in str(load("hom.yml")["jobs"]["qa"]["with"]["run_fault_injection"])
    assert load("dev.yml")["concurrency"]["cancel-in-progress"] is True
    assert load("hom.yml")["concurrency"]["cancel-in-progress"] is False


def test_pipeline_paralelo_com_matrix_dinamica():
    wf = load("_qa-pipeline.yml")
    jobs = wf["jobs"]
    assert set(jobs) == {"tooling", "plan", "test", "report", "fault-injection"}
    assert jobs["test"]["needs"] == "plan"
    assert jobs["test"]["strategy"]["matrix"] == "${{ fromJSON(needs.plan.outputs.matrix) }}"
    assert jobs["test"]["strategy"]["fail-fast"] is False
    assert jobs["report"]["needs"] == ["plan", "test"] and "!cancelled()" in jobs["report"]["if"]
    assert "workflow_call" in wf["on"] and wf["on"]["workflow_call"]["inputs"]["environment"]["required"]


def test_scripts_referenciados_existem():
    text = "\n".join(p.read_text(encoding="utf-8") for p in WF.glob("*.yml"))
    for script in set(re.findall(r"python (test/scripts/[\w./-]+\.py)", text)):
        assert (ROOT / script).exists(), script


def test_relatorios_publicados():
    steps = load("_qa-pipeline.yml")["jobs"]["report"]["steps"]
    upload = next(s for s in steps if s.get("with", {}).get("name", "").startswith("qa-reports-"))
    for f in ("cucumber.json", "report.html", "cobertura.html"):
        assert f"reports/{f}" in upload["with"]["path"]
    assert upload["if"] == "always()"


def test_artefatos_de_shard_nao_dependem_de_arquivo_oculto():
    """upload-artifact v4 ignora arquivos ocultos: dados de cobertura não podem começar com ponto."""
    src = (TEST / "qa_support" / "pipeline.py").read_text(encoding="utf-8")
    assert "coverage-data-" in src and "/.coverage" not in src


def test_artefato_de_defeito_publica_so_os_arquivos_do_proprio_defeito():
    steps = load("_qa-pipeline.yml")["jobs"]["fault-injection"]["steps"]
    upload = next(s for s in steps if "upload-artifact" in s.get("uses", ""))
    assert "${{ matrix.fault }}.txt" in upload["with"]["path"] and "SUMMARY-${{ matrix.fault }}" in upload["with"]["path"]


def test_relatorio_reprova_shard_sem_resultado():
    report = load("_qa-pipeline.yml")["jobs"]["report"]["steps"]
    assert any("--check-shards" in s.get("run", "") for s in report)
