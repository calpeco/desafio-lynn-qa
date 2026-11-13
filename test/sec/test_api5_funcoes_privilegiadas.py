"""API5:2023 — Broken Function Level Authorization.

Funções privilegiadas: os endpoints de controle /__test__/* (reset global, troca do modo do LLM,
leitura de logs) e métodos HTTP que não deveriam existir nos recursos.
"""
from __future__ import annotations

import httpx
import pytest

from lynn_mock.api.app import create_app
from qa_support.contracts import assert_error
from sec_support import new_conversation

pytestmark = pytest.mark.owasp("API5:2023")

CONTROL_ENDPOINTS = [
    ("POST", "/__test__/reset", {}),
    ("POST", "/__test__/llm", {"mode": "ok"}),
    ("POST", "/__test__/config", {}),
    ("GET", "/__test__/stats", None),
    ("GET", "/__test__/logs", None),
]


@pytest.fixture
def default_app_client(monkeypatch):
    """Aplicação montada como em `python app` (server.py): sem LYNN_TEST_CONTROL definido.
    In-process via WSGITransport do httpx: nenhuma porta nova, nenhum tráfego externo."""
    monkeypatch.delenv("LYNN_TEST_CONTROL", raising=False)
    monkeypatch.delenv("LYNN_FAULTS", raising=False)
    with httpx.Client(transport=httpx.WSGITransport(app=create_app()), base_url="http://lynn.local") as c:
        yield c


@pytest.mark.trace("R16", "R12")
@pytest.mark.xfail(strict=True, reason="SEC-001: /__test__/* habilitado por padrão (LYNN_TEST_CONTROL default '1')")
@pytest.mark.parametrize("method,path,body", CONTROL_ENDPOINTS, ids=[p for _, p, _ in CONTROL_ENDPOINTS])
def test_controle_de_teste_nao_existe_na_configuracao_padrao(method, path, body, default_app_client):
    """O contrato diz 'somente com LYNN_TEST_CONTROL=1'. Sem a variável, a rota não pode existir."""
    r = default_app_client.request(method, path, json=body)
    # 401 (exige credencial, middleware roda antes do roteamento) ou 404: os dois provam ausência de acesso.
    assert r.status_code in (401, 404), f"{method} {path} respondeu {r.status_code} sem LYNN_TEST_CONTROL"


@pytest.mark.trace("CONV-RN08", "R01", "R16")
@pytest.mark.xfail(strict=True, reason="SEC-001: /__test__/reset sem autenticação apaga os dados de todas as pessoas")
@pytest.mark.parametrize("persona", ["Visitante", "Bob"])
def test_reset_global_exige_credencial_privilegiada(persona, client_factory, alice):
    conv = new_conversation(alice)
    attacker = client_factory(persona)
    r = attacker.request("POST", "/__test__/reset", json_body={})
    assert r.status_code in (401, 403, 404), f"{persona} executou reset global: {r.status_code}"
    assert alice.get_conversation(conv["id"]).status_code == 200, "conversa da Alice foi apagada"


@pytest.mark.trace("CONV-RN12", "R12", "R16")
@pytest.mark.xfail(strict=True, reason="SEC-001: /__test__/logs e /stats legíveis sem autenticação")
@pytest.mark.parametrize("path", ["/__test__/logs", "/__test__/stats"])
def test_logs_e_stats_internos_exigem_credencial(path, raw_http, alice_conv):
    r = raw_http.get(path)
    assert r.status_code in (401, 403, 404), f"{path} aberto ao anônimo; trecho: {r.text[:160]}"
    assert "u_alice" not in r.text and alice_conv["id"] not in r.text


@pytest.mark.trace("CONV-RN07", "R03", "R15")
@pytest.mark.xfail(strict=True, reason="SEC-001: /__test__/llm aceita tipos inválidos e derruba todo envio com 500")
def test_configuracao_invalida_do_llm_e_rejeitada(raw_http, alice):
    r = raw_http.post("/__test__/llm", json={"timeout_ms": "abc"})
    assert r.status_code == 422, f"configuração inválida aceita com {r.status_code}"
    conv = new_conversation(alice)
    assert alice.send_message(conv["id"], "oi").status_code == 201


@pytest.mark.trace("CONV-RN08", "R01")
@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("suffix", ["", "/messages", "/close"])
def test_metodos_nao_publicados_retornam_405_sem_efeito(method, suffix, alice, alice_conv):
    before = alice.get_conversation(alice_conv["id"]).json()
    r = alice.request(method, f"/api/v1/conversations/{alice_conv['id']}{suffix}", json_body={"status": "closed"})
    assert_error(r, 405, "METHOD_NOT_ALLOWED")
    assert alice.get_conversation(alice_conv["id"]).json() == before


@pytest.mark.trace("CONV-RN08", "R01")
@pytest.mark.parametrize("override", ["DELETE", "PUT"])
def test_method_override_nao_e_honrado(override, alice, alice_conv):
    """X-HTTP-Method-Override não pode transformar um POST em DELETE/PUT por trás de um proxy."""
    r = alice.request("POST", f"/api/v1/conversations/{alice_conv['id']}", json_body={},
                      headers={"X-HTTP-Method-Override": override, "X-Method-Override": override})
    assert_error(r, 405, "METHOD_NOT_ALLOWED")
    assert alice.get_conversation(alice_conv["id"]).status_code == 200
