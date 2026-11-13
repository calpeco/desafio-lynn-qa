"""API4:2023 — Unrestricted Resource Consumption (com LLM10:2025, consumo ilimitado do modelo).

Corpo grande, JSON aninhado, rajada sem rate limit e a garantia de que requisições rejeitadas não
geram custo de LLM. Payloads limitados a poucos MB e poucas dezenas de requisições.
"""
from __future__ import annotations

import pytest

from qa_support.contracts import assert_error, assert_matches
from payloads import DEEP_JSON_LEVELS, LARGE_BODY_BYTES, RATE_BURST
from sec_support import new_conversation

pytestmark = pytest.mark.owasp("API4:2023")


@pytest.mark.trace("CONV-RN04", "R09", "R11")
@pytest.mark.xfail(strict=True, reason="SEC-002: sem limite de tamanho do corpo (MAX_CONTENT_LENGTH); 2 MB aceitos com 201")
@pytest.mark.parametrize("endpoint", ["criar", "enviar"])
def test_corpo_acima_do_limite_e_rejeitado_com_413(endpoint, alice, control):
    pad = "A" * LARGE_BODY_BYTES
    if endpoint == "criar":
        r = alice.request("POST", "/api/v1/conversations", json_body={"agent_id": "agt_support", "pad": pad})
    else:
        conv = new_conversation(alice)
        r = alice.send_message(conv["id"], None, json_body={"content": "oi", "pad": pad})
    # 413 é o status semântico (RFC 9110). O contrato não define o código; exigimos o envelope padrão.
    assert r.status_code == 413, f"corpo de {LARGE_BODY_BYTES} bytes aceito com {r.status_code}"
    assert_matches("error", r.json())
    assert control.stats()["llm_calls"] == 0


@pytest.mark.trace("CONV-RN04", "R09")
@pytest.mark.xfail(strict=True, reason="SEC-004: JSON profundamente aninhado estoura a recursão do parser e vira 500")
def test_json_profundamente_aninhado_e_400_e_nao_500(alice):
    r = alice.request("POST", "/api/v1/conversations", raw_body="[" * DEEP_JSON_LEVELS + "]" * DEEP_JSON_LEVELS)
    assert_error(r, 400, "INVALID_JSON")


@pytest.mark.trace("CONV-RN04", "R09")
def test_servidor_continua_saudavel_apos_json_aninhado(alice):
    """Mesmo com o 500 de SEC-004, o processo não cai: a próxima requisição funciona (sem DoS)."""
    alice.request("POST", "/api/v1/conversations", raw_body="{\"a\":" * DEEP_JSON_LEVELS + "1" + "}" * DEEP_JSON_LEVELS)
    new_conversation(alice)


@pytest.mark.trace("CONV-RN01", "CONV-RN03", "CONV-RN04", "CONV-RN08", "R11")
@pytest.mark.parametrize("caso", ["401-sem-token", "400-json-invalido", "422-vazio", "422-acima-4000",
                                  "404-conversa-alheia", "409-encerrada", "422-tipo-errado"])
def test_requisicao_rejeitada_nao_chama_o_llm(caso, alice, bob, visitante, control):
    """Toda rejeição acontece ANTES da chamada ao modelo: atacante não gera custo com lixo."""
    conv = new_conversation(alice)
    expected = {
        "401-sem-token": (lambda: visitante.send_message(conv["id"], "oi"), 401, "UNAUTHENTICATED"),
        "400-json-invalido": (lambda: alice.request("POST", f"/api/v1/conversations/{conv['id']}/messages",
                                                    raw_body="{content:"), 400, "INVALID_JSON"),
        "422-vazio": (lambda: alice.send_message(conv["id"], "   "), 422, "VALIDATION_ERROR"),
        "422-acima-4000": (lambda: alice.send_message(conv["id"], "x" * 4001), 422, "VALIDATION_ERROR"),
        "404-conversa-alheia": (lambda: bob.send_message(conv["id"], "oi"), 404, "CONVERSATION_NOT_FOUND"),
        "409-encerrada": (lambda: (alice.close_conversation(conv["id"]), alice.send_message(conv["id"], "oi"))[1],
                          409, "CONVERSATION_CLOSED"),
        "422-tipo-errado": (lambda: alice.send_message(conv["id"], {"$gt": ""}), 422, "VALIDATION_ERROR"),
    }[caso]
    call, status, code = expected
    assert_error(call(), status, code)
    assert control.stats()["llm_calls"] == 0


@pytest.mark.owasp("LLM10:2025")
@pytest.mark.trace("CONV-RN10", "R11")
@pytest.mark.xfail(strict=True, reason="SEC-003: sem rate limit/quota por pessoa; rajada inteira vira chamadas ao LLM")
def test_rajada_de_mensagens_recebe_429_com_retry_after(alice, control):
    conv = new_conversation(alice)
    statuses = [alice.send_message(conv["id"], f"mensagem {i}") for i in range(RATE_BURST)]
    limited = [r for r in statuses if r.status_code == 429]
    assert limited, f"{RATE_BURST} mensagens seguidas, nenhuma 429; chamadas ao LLM: {control.stats()['llm_calls']}"
    assert_matches("error", limited[0].json())
    assert "Retry-After" in limited[0].headers


@pytest.mark.owasp("API2:2023")
@pytest.mark.trace("CONV-RN01", "R16")
@pytest.mark.xfail(strict=True, reason="SEC-003: sem limite de tentativas de autenticação (força bruta de token)")
def test_tentativas_seguidas_de_token_invalido_sao_limitadas(raw_http):
    codes = [raw_http.get("/api/v1/conversations/x", headers={"Authorization": f"Bearer token-{i:04d}"}).status_code
             for i in range(RATE_BURST)]
    assert 429 in codes, f"{RATE_BURST} tokens inválidos seguidos sem 429: {sorted(set(codes))}"


@pytest.mark.trace("CONV-RN12", "R13")
def test_x_request_id_gigante_e_truncado(alice):
    """Amplificação em logs/headers: o eco do X-Request-ID é limitado a 128 caracteres."""
    r = alice.get_conversation("conv_x", headers={"X-Request-ID": "r" * 8000})
    assert r.status_code == 404
    assert len(r.headers["X-Request-ID"]) == 128 and r.json()["error"]["request_id"] == r.headers["X-Request-ID"]


@pytest.mark.owasp("LLM10:2025")
@pytest.mark.trace("CONV-RN09", "R02", "R11")
def test_reenvio_com_mesma_chave_nao_gera_nova_chamada_ao_llm(alice, control):
    """Repetir a mesma requisição (ataque de replay barato) não multiplica o custo."""
    conv = new_conversation(alice)
    for _ in range(5):
        r = alice.send_message(conv["id"], "mesma mensagem", idempotency_key="sec-replay-1")
        assert r.status_code == 201
    assert control.stats()["llm_calls"] == 1
    assert len(alice.get_conversation(conv["id"]).json()["messages"]) == 2

