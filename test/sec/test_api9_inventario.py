"""API9:2023 — Improper Inventory Management.

Caixa-cinza: toda rota registrada no Flask precisa estar no contrato (app/CONTRATO_API.md);
versões/caminhos antigos não podem responder; o frontend não vaza a configuração do servidor.
"""
from __future__ import annotations

import re

import pytest

from lynn_mock.api.app import create_app
from qa_support.paths import APP

pytestmark = pytest.mark.owasp("API9:2023")

CONTRACT = (APP / "CONTRATO_API.md").read_text(encoding="utf-8")


def _undocumented(app) -> list[str]:
    missing = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        path = rule.rule.removeprefix("/api/v1")
        pattern = re.escape(path)
        pattern = re.sub(r"<[^>]+>", r"\\{[^}]+\\}", pattern.replace(r"\<", "<").replace(r"\>", ">"))
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            if not re.search(rf"`{method} {pattern}`", CONTRACT) and not re.search(rf"`{method} {pattern} ", CONTRACT):
                missing.append(f"{method} {rule.rule}")
    return missing


@pytest.mark.trace("CONV-RN13", "FDBK-RN07", "R17")
@pytest.mark.xfail(strict=True, reason="SEC-008: rotas de produção fora do contrato (feedback, /config.js)")
def test_rotas_de_producao_estao_no_contrato():
    assert _undocumented(create_app(faults=set(), test_control=False)) == []


@pytest.mark.trace("R16")
@pytest.mark.xfail(strict=True, reason="SEC-008: /__test__/stats e /__test__/logs não documentados")
def test_rotas_de_controle_estao_no_contrato():
    prod = set(_undocumented(create_app(faults=set(), test_control=False)))
    extra = [r for r in _undocumented(create_app(faults=set(), test_control=True)) if r not in prod]
    assert extra == []


@pytest.mark.trace("CONV-RN08", "R01")
@pytest.mark.parametrize("path", ["/api/v0/conversations", "/api/v2/conversations", "/api/conversations",
                                  "/api/v1/conversations/", "/api/v1/conversations.json", "/api/v1/debug",
                                  "/api/v1/swagger.json", "/console", "/.env"])
def test_versoes_e_caminhos_sombra_nao_respondem(path, alice):
    r = alice.request("GET", path)
    assert r.status_code in (404, 405), f"{path} respondeu {r.status_code}"
    assert r.json()["error"]["code"] in ("NOT_FOUND", "METHOD_NOT_ALLOWED")
    assert "token-" not in r.text and "LYNN_" not in r.text


@pytest.mark.trace("R16")
def test_config_js_nao_expoe_defeitos_de_servidor(raw_http):
    """/config.js é público: só pode carregar defeitos de UI (ui_*), nunca a lista de LYNN_FAULTS
    de servidor (que diria ao atacante qual proteção está desligada)."""
    body = raw_http.get("/config.js").text
    for fault in ("idor", "guardrail_off", "context_leak", "allow_closed", "no_idempotency"):
        assert fault not in body
