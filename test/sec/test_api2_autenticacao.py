"""API2:2023 — Broken Authentication.

Aprofunda o 04_autenticacao_isolamento.feature (4 variações) com: comparação exata do token
(prefixo, sufixo, caixa, espaços), credencial fora do header (query, cookie, X-Api-Key), todos os
endpoints, rotas desconhecidas sem oráculo e ausência de efeito colateral (LLM, estado).
"""
from __future__ import annotations

import pytest

from qa_support.contracts import assert_error
from payloads import AUTH_BYPASS
from sec_support import new_conversation

pytestmark = pytest.mark.owasp("API2:2023")

# (método, caminho) de todos os endpoints de negócio; {c}/{m} são preenchidos com IDs reais da Alice.
ENDPOINTS = [
    ("POST", "/api/v1/conversations", {"agent_id": "agt_support"}),
    ("GET", "/api/v1/conversations/{c}", None),
    ("POST", "/api/v1/conversations/{c}/close", None),
    ("POST", "/api/v1/conversations/{c}/messages", {"content": "oi"}),
    ("POST", "/api/v1/conversations/{c}/messages/{m}/feedback", {"rating": "positive"}),
]


def _call(raw_http, method, path, body, conv, headers=None, params=None):
    url = path.format(c=conv["id"], m=conv["assistant_msg"])
    return raw_http.request(method, url, json=body, headers=headers or {}, params=params)


@pytest.mark.trace("CONV-RN01", "R16")
@pytest.mark.parametrize("variant,authorization", AUTH_BYPASS, ids=[a[0] for a in AUTH_BYPASS])
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: f"{e[0]} {e[1]}")
def test_credencial_invalida_e_negada_em_todo_endpoint(endpoint, variant, authorization, raw_http, alice,
                                                     alice_conv, control):
    method, path, body = endpoint
    before = alice.get_conversation(alice_conv["id"]).json()
    calls = control.stats()["llm_calls"]
    headers = {"Authorization": authorization} if authorization is not None else {}

    r = _call(raw_http, method, path, body, alice_conv, headers)

    assert_error(r, 401, "UNAUTHENTICATED")
    assert control.stats()["llm_calls"] == calls, "requisição não autenticada chegou ao LLM"
    assert alice.get_conversation(alice_conv["id"]).json() == before, "requisição não autenticada mudou estado"


@pytest.mark.trace("CONV-RN01", "R16")
@pytest.mark.parametrize("where", ["query-access_token", "query-token", "cookie", "x-api-key", "x-user-id"])
def test_token_fora_do_header_authorization_nao_autentica(where, raw_http, alice_conv):
    """O token só vale no header Authorization: em query vaza em logs/proxies; cookie abriria CSRF."""
    headers, params = {}, None
    if where == "query-access_token":
        params = {"access_token": "token-alice"}
    elif where == "query-token":
        params = {"token": "token-alice"}
    elif where == "cookie":
        headers = {"Cookie": "token=token-alice; Authorization=Bearer%20token-alice"}
    elif where == "x-api-key":
        headers = {"X-Api-Key": "token-alice"}
    else:
        headers = {"X-User-Id": "u_alice"}  # identidade declarada pelo cliente
    r = raw_http.get(f"/api/v1/conversations/{alice_conv['id']}", headers=headers, params=params)
    assert_error(r, 401, "UNAUTHENTICATED")
    assert "Mensagem privada da Alice" not in r.text


@pytest.mark.trace("CONV-RN01", "R16")
def test_header_x_user_id_nao_troca_a_identidade_autenticada(bob, alice_conv):
    """Um header de identidade não pode sobrepor o dono do token (confused deputy)."""
    r = bob.get_conversation(alice_conv["id"], headers={"X-User-Id": "u_alice", "X-Forwarded-User": "u_alice"})
    assert_error(r, 404, "CONVERSATION_NOT_FOUND")


@pytest.mark.trace("CONV-RN01", "R16")
@pytest.mark.parametrize("path", ["/api/v1/admin", "/api/v2/conversations", "/api/v1/users", "/api/v1/conversations/x/export"])
def test_rota_desconhecida_sem_token_e_igual_a_rota_real_sem_token(path, raw_http):
    """Sem credencial, rota inexistente responde igual à existente: o anônimo não mapeia a API."""
    real = raw_http.get("/api/v1/conversations/conv_qualquer")
    unknown = raw_http.get(path)
    assert_error(unknown, 401, "UNAUTHENTICATED")
    assert unknown.json()["error"]["message"] == real.json()["error"]["message"]


@pytest.mark.trace("CONV-RN01", "R16")
def test_token_ausente_e_token_errado_tem_a_mesma_mensagem(raw_http):
    """Mensagem única: não diz se o token existe, expirou ou está quase certo."""
    a = raw_http.get("/api/v1/conversations/x")
    b = raw_http.get("/api/v1/conversations/x", headers={"Authorization": "Bearer token-alicf"})
    assert a.json()["error"]["message"] == b.json()["error"]["message"]


@pytest.mark.trace("CONV-RN01", "R16")
def test_controle_positivo_esquema_case_insensitive_autentica(client_factory):
    """Controle positivo (RFC 7235: esquema case-insensitive). Prova que os 401 acima não são acidente
    do teste: com o token certo, mesmo com 'bearer' minúsculo, a API autentica."""
    c = client_factory(token=None, default_headers={"Authorization": "bearer token-alice"})
    conv = new_conversation(c)
    assert conv["owner_id"] == "u_alice"
