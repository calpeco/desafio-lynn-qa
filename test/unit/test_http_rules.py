"""Unit: regras extraídas da camada HTTP (autenticação, corpo, falha do LLM, correlação)."""
import pytest

from lynn_mock.domain.http_rules import (error_body, llm_failure_response, parse_json_object, request_id,
                                         resolve_user)
from qa_support.contracts import assert_matches

TOKENS = {"token-alice": "u_alice", "token-bob": "u_bob"}


@pytest.mark.trace("CONV-RN01", "R16")
@pytest.mark.parametrize("header,user", [
    ("Bearer token-alice", "u_alice"),
    ("Bearer token-bob", "u_bob"),
    ("bearer token-alice", "u_alice"),      # esquema é case-insensitive (RFC 7235)
    ("BEARER token-alice", "u_alice"),
    (None, None),
    ("", None),
    ("Bearer", None),
    ("Bearer ", None),
    ("Bearer  token-alice", None),          # espaço extra não é normalizado em silêncio
    ("Bearer token-alice ", None),
    ("Bearer TOKEN-ALICE", None),            # o token é case-sensitive
    ("token-alice", None),
    ("Basic dXNlcjpwYXNz", None),
    ("Bearer token-invalido", None),
])
def test_resolve_user(header, user):
    assert resolve_user(header, TOKENS) == user


@pytest.mark.trace("CONV-RN04", "R09")
@pytest.mark.parametrize("raw,status,code", [
    ('{"content": "x"}', None, None),
    ("{}", None, None),
    ("", 422, "VALIDATION_ERROR"),           # corpo vazio = null = não é objeto
    ("null", 422, "VALIDATION_ERROR"),
    ('["content"]', 422, "VALIDATION_ERROR"),
    ("123", 422, "VALIDATION_ERROR"),
    ("{content: 'x'}", 400, "INVALID_JSON"),
    ('{"content": "x"', 400, "INVALID_JSON"),
    ("not json", 400, "INVALID_JSON"),
])
def test_parse_json_object(raw, status, code):
    data, err = parse_json_object(raw)
    if status is None:
        assert err is None and isinstance(data, dict)
    else:
        assert data is None and (err.status, err.code) == (status, code)


@pytest.mark.trace("CONV-RN07", "R03")
@pytest.mark.parametrize("timed_out,status,code", [(True, 504, "LLM_TIMEOUT"), (False, 503, "LLM_UNAVAILABLE")])
def test_falha_do_llm_vira_erro_claro_com_retry_after(timed_out, status, code):
    f = llm_failure_response(timed_out)
    assert (f.status, f.code) == (status, code)
    assert f.retry_after_s > 0
    assert "não foi possível gerar uma resposta" in f.message.lower()


@pytest.mark.trace("CONV-RN12", "R13")
@pytest.mark.parametrize("incoming,echoed", [("qa-123", True), ("  qa-456  ", True), ("", False), (None, False), ("   ", False)])
def test_request_id_ecoa_ou_gera(incoming, echoed):
    rid = request_id(incoming)
    assert rid
    assert (rid == incoming.strip()) if echoed else len(rid) == 36


@pytest.mark.trace("CONV-RN12", "R13")
def test_request_id_tem_tamanho_limitado():
    assert len(request_id("x" * 10_000)) == 128   # evita log injection / headers gigantes


@pytest.mark.trace("CONV-RN13", "R17")
@pytest.mark.parametrize("code", ["UNAUTHENTICATED", "CONVERSATION_CLOSED", "LLM_TIMEOUT", "INTERNAL_ERROR"])
def test_envelope_de_erro_segue_o_contrato(code):
    assert_matches("error", error_body(code, "mensagem", "req-1"))
