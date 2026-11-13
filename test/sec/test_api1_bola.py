"""API1:2023 — Broken Object Level Authorization (BOLA/IDOR).

Cobre TODOS os endpoints com ID no caminho, inclusive feedback em mensagem de OUTRA conversa.
Aprofunda o 04_autenticacao_isolamento.feature: feedback, mensagem cruzada entre conversas,
indistinguibilidade em todos os endpoints, adulteração do ID, escopo da Idempotency-Key e
efeitos colaterais (estado, chamadas ao LLM). Deve falhar com LYNN_FAULTS=idor.
"""
from __future__ import annotations

import uuid

import pytest

from qa_support.contracts import assert_error
from sec_support import new_conversation, send_ok

pytestmark = pytest.mark.owasp("API1:2023")

# Operações por objeto: (nome, função(client, conv_id, msg_id) -> resposta)
OPERATIONS = {
    "consultar": lambda c, cid, mid: c.get_conversation(cid),
    "encerrar": lambda c, cid, mid: c.close_conversation(cid),
    "enviar": lambda c, cid, mid: c.send_message(cid, "Bob tentando escrever"),
    "avaliar": lambda c, cid, mid: c.give_feedback(cid, mid, {"rating": "negative", "comment": "bob"}),
}


def _alice_state(alice, conv_id):
    r = alice.get_conversation(conv_id)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.trace("CONV-RN08", "FDBK-RN05", "R01")
@pytest.mark.parametrize("op", OPERATIONS)
def test_outra_pessoa_nao_opera_conversa_alheia(op, alice, bob, alice_conv, control):
    before = _alice_state(alice, alice_conv["id"])
    calls_before = control.stats()["llm_calls"]

    r = OPERATIONS[op](bob, alice_conv["id"], alice_conv["assistant_msg"])

    assert_error(r, 404, "CONVERSATION_NOT_FOUND")
    for leaked in ("u_alice", "Mensagem privada da Alice", alice_conv["assistant_msg"]):
        assert leaked not in r.text, f"resposta a Bob expõe {leaked!r}"
    after = _alice_state(alice, alice_conv["id"])
    assert after == before, "a tentativa de Bob alterou a conversa da Alice"
    assert control.stats()["llm_calls"] == calls_before, "tentativa negada não pode gerar custo de LLM"


@pytest.mark.trace("FDBK-RN05", "R01")
def test_feedback_cruzado_conversa_propria_com_mensagem_alheia(alice, bob, alice_conv):
    """Bob usa a PRÓPRIA conversa no caminho e o ID da mensagem da Alice: o par (conversa, mensagem)
    precisa ser validado, não só a conversa."""
    bob_conv = new_conversation(bob)
    r = bob.give_feedback(bob_conv["id"], alice_conv["assistant_msg"], {"rating": "negative"})
    assert_error(r, 404, "MESSAGE_NOT_FOUND")
    msg = next(m for m in _alice_state(alice, alice_conv["id"])["messages"] if m["id"] == alice_conv["assistant_msg"])
    assert msg["feedback"] is None, "feedback de Bob gravado em mensagem da Alice"


@pytest.mark.trace("FDBK-RN05", "R01")
def test_feedback_em_mensagem_de_outra_conversa_da_mesma_pessoa(alice, alice_conv):
    """Mesmo sendo dona das duas conversas, a mensagem precisa pertencer à conversa do caminho."""
    outra = new_conversation(alice)
    r = alice.give_feedback(outra["id"], alice_conv["assistant_msg"], {"rating": "positive"})
    assert_error(r, 404, "MESSAGE_NOT_FOUND")


@pytest.mark.trace("CONV-RN08", "FDBK-RN05", "R01")
@pytest.mark.parametrize("op", OPERATIONS)
def test_conversa_alheia_e_inexistente_sao_indistinguiveis(op, bob, alice_conv):
    """Sem oráculo de enumeração em NENHUM endpoint (P-6): mesmo status, código, mensagem e headers."""
    fake = "conv_" + uuid.uuid4().hex[:16]
    alheia = OPERATIONS[op](bob, alice_conv["id"], alice_conv["assistant_msg"])
    inexistente = OPERATIONS[op](bob, fake, "msg_" + uuid.uuid4().hex[:16])
    a, b = alheia.json()["error"], inexistente.json()["error"]
    assert (alheia.status_code, a["code"], a["message"]) == (inexistente.status_code, b["code"], b["message"])
    ignore = {"date", "x-request-id", "content-length"}
    assert ({k for k in alheia.headers if k not in ignore} == {k for k in inexistente.headers if k not in ignore})


@pytest.mark.trace("CONV-RN08", "R01")
@pytest.mark.parametrize("variant", ["upper", "trailing-slash", "espaco", "ponto-e-virgula", "query-owner", "encoded-slash"])
def test_id_adulterado_nao_contorna_dono(variant, bob, alice_conv):
    cid = alice_conv["id"]
    path = {
        "upper": cid.upper(),
        "trailing-slash": cid + "/",
        "espaco": cid + "%20",
        "ponto-e-virgula": cid + ";owner=u_bob",
        "query-owner": cid + "?owner_id=u_bob&user=u_alice",
        "encoded-slash": "..%2f" + cid,
    }[variant]
    r = bob.request("GET", f"/api/v1/conversations/{path}")
    # 404 em ambos os códigos é aceitável e intencional: NOT_FOUND (rota não casa) e
    # CONVERSATION_NOT_FOUND (rota casa, dono não) significam "nada aqui"; o que importa é não vazar.
    assert r.status_code == 404, r.text
    assert r.json()["error"]["code"] in {"NOT_FOUND", "CONVERSATION_NOT_FOUND"}
    assert "Mensagem privada da Alice" not in r.text and "u_alice" not in r.text


@pytest.mark.trace("CONV-RN08", "CONV-RN09", "R01", "R02")
def test_idempotency_key_alheia_nao_reproduz_resposta_de_outra_pessoa(alice, bob):
    """Escopo (usuário, conversa, chave): a chave da Alice não pode virar oráculo nem replay para Bob."""
    key = f"sec-{uuid.uuid4()}"
    alice_conv = new_conversation(alice)
    r1 = alice.send_message(alice_conv["id"], "Segredo de idempotência da Alice", idempotency_key=key)
    assert r1.status_code == 201

    # 1) Bob reenvia o MESMO corpo e chave na conversa da Alice: nada de replay.
    r2 = bob.send_message(alice_conv["id"], "Segredo de idempotência da Alice", idempotency_key=key)
    assert_error(r2, 404, "CONVERSATION_NOT_FOUND")
    assert "Idempotent-Replayed" not in r2.headers
    # 2) Bob usa a mesma chave na PRÓPRIA conversa com outro corpo: não pode receber 409 KEY_REUSED
    #    (revelaria que a chave existe) nem a resposta da Alice.
    bob_conv = new_conversation(bob)
    r3 = bob.send_message(bob_conv["id"], "conteúdo do Bob", idempotency_key=key)
    assert r3.status_code == 201, r3.text
    assert "Idempotent-Replayed" not in r3.headers
    assert "Segredo de idempotência da Alice" not in r3.text


@pytest.mark.trace("CONV-RN08", "CONV-RN12", "R01", "R13")
def test_tentativa_de_bola_fica_rastreavel_sem_expor_conteudo(bob, alice_conv, control):
    """Detecção: o acesso negado vira log de acesso com o ator e o status, sem o conteúdo da vítima."""
    r = bob.get_conversation(alice_conv["id"])
    assert r.status_code == 404
    access = [e for e in control.logs() if e.get("event") == "http.access"
              and e.get("request_id") == r.headers["X-Request-ID"]]
    assert len(access) == 1, access
    assert access[0]["user_id"] == "u_bob" and access[0]["status"] == 404
    assert "Mensagem privada da Alice" not in str(control.logs())
