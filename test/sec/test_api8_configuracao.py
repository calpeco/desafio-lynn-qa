"""API8:2023 — Security Misconfiguration (API).

Headers de segurança das respostas da API, divulgação de versão, CORS, métodos e erros sem detalhes
internos. Os headers da UI (CSP, frame) ficam em test_web_headers_xss.py.
"""
from __future__ import annotations

import re

import pytest

from qa_support.contracts import assert_error
from sec_support import new_conversation

pytestmark = pytest.mark.owasp("API8:2023")

INTERNALS = re.compile(r"Traceback|File \"|RuntimeError|RecursionError|werkzeug|flask|lynn_mock|\.py\b|bug inesperado",
                       re.IGNORECASE)


@pytest.mark.trace("R12", "R17")
@pytest.mark.xfail(strict=True, reason="SEC-005: respostas da API sem X-Content-Type-Options: nosniff")
def test_api_envia_nosniff(alice, alice_conv):
    r = alice.get_conversation(alice_conv["id"])
    assert r.headers.get("X-Content-Type-Options", "").lower() == "nosniff"


@pytest.mark.trace("CONV-RN08", "R01", "R12")
@pytest.mark.xfail(strict=True, reason="SEC-005: conversa (dado pessoal) sem Cache-Control: no-store")
def test_dado_de_conversa_nao_e_cacheavel(alice, alice_conv):
    r = alice.get_conversation(alice_conv["id"])
    assert "no-store" in r.headers.get("Cache-Control", ""), r.headers.get("Cache-Control")


@pytest.mark.xfail(strict=True, reason="SEC-006: header Server divulga Werkzeug/x.y e Python/x.y")
@pytest.mark.parametrize("path", ["/", "/api/v1/conversations/x"])
def test_header_server_nao_divulga_versao(path, raw_http):
    server = raw_http.get(path).headers.get("Server", "")
    assert not re.search(r"\d+\.\d+", server), f"Server: {server}"


@pytest.mark.trace("CONV-RN08", "R01")
@pytest.mark.parametrize("method", ["GET", "OPTIONS"])
def test_cors_nao_libera_origem_arbitraria(method, raw_http, alice_conv):
    r = raw_http.request(method, f"/api/v1/conversations/{alice_conv['id']}",
                         headers={"Origin": "https://evil.example", "Authorization": "Bearer token-alice",
                                  "Access-Control-Request-Method": "GET",
                                  "Access-Control-Request-Headers": "authorization"})
    assert "Access-Control-Allow-Origin" not in r.headers, r.headers.get("Access-Control-Allow-Origin")
    assert "Access-Control-Allow-Credentials" not in r.headers


@pytest.mark.parametrize("method", ["TRACE", "TRACK", "CONNECT"])
def test_metodos_de_diagnostico_nao_ecoam_a_requisicao(method, raw_http):
    """TRACE/TRACK refletiriam headers (inclusive Authorization) no corpo: Cross-Site Tracing."""
    r = raw_http.request(method, "/api/v1/conversations", headers={"Authorization": "Bearer token-alice"})
    assert_error(r, 405, "METHOD_NOT_ALLOWED")
    assert "token-alice" not in r.text


@pytest.mark.trace("CONV-RN07", "CONV-RN12", "R03", "R13")
@pytest.mark.parametrize("caso", ["500-bug-no-adaptador", "400-json", "404-rota", "405-metodo", "422-tipo"])
def test_erro_nao_expoe_stack_trace_nem_detalhe_interno(caso, alice, control):
    conv = new_conversation(alice)
    if caso == "500-bug-no-adaptador":
        control.llm(mode="crash")
        r, status, code = alice.send_message(conv["id"], "oi"), 500, "INTERNAL_ERROR"
    elif caso == "400-json":
        r, status, code = alice.request("POST", "/api/v1/conversations", raw_body="{'a':"), 400, "INVALID_JSON"
    elif caso == "404-rota":
        r, status, code = alice.request("GET", "/api/v1/../../etc/passwd"), 404, "NOT_FOUND"
    elif caso == "405-metodo":
        r, status, code = alice.request("DELETE", "/api/v1/conversations"), 405, "METHOD_NOT_ALLOWED"
    else:
        r, status, code = alice.send_message(conv["id"], ["lista"]), 422, "VALIDATION_ERROR"
    assert_error(r, status, code)
    assert not INTERNALS.search(r.text), f"detalhe interno no corpo: {r.text[:200]}"
    assert r.headers["Content-Type"].startswith("application/json")


@pytest.mark.trace("CONV-RN12", "R13")
def test_erro_500_registra_so_o_tipo_da_excecao_nos_logs(alice, control):
    """O log é a fonte do diagnóstico, mas sem mensagem/stack (podem conter dados)."""
    conv = new_conversation(alice)
    control.llm(mode="crash")
    r = alice.send_message(conv["id"], "oi")
    assert r.status_code == 500
    errs = [e for e in control.logs() if e["event"] == "http.unhandled_error"]
    assert errs and errs[-1]["error"] == "RuntimeError" and errs[-1]["request_id"] == r.headers["X-Request-ID"]
    assert "bug inesperado" not in str(control.logs())


@pytest.mark.trace("CONV-RN12", "R13")
@pytest.mark.xfail(strict=True, reason="SEC-007: X-Request-ID do cliente aceito sem validação de formato e ecoado")
@pytest.mark.parametrize("value", ['<script>alert(1)</script>', "a\tb", "id falso de outro serviço"])
def test_x_request_id_fora_do_formato_e_substituido(value, alice):
    r = alice.get_conversation("conv_x", headers={"X-Request-ID": value})
    echoed = r.headers["X-Request-ID"]
    assert echoed != value and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", echoed), repr(echoed)


@pytest.mark.trace("CONV-RN12", "R13")
def test_x_request_id_refletido_nao_vira_html(alice):
    """Mesmo refletido (SEC-007), o valor só aparece em JSON: não há XSS refletido pela API."""
    r = alice.get_conversation("conv_x", headers={"X-Request-ID": "<script>alert(1)</script>"})
    assert r.headers["Content-Type"] == "application/json"
