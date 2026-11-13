"""API3:2023 — Broken Object Property Level Authorization (mass assignment e exposição excessiva).

O cliente não pode escolher dono, status, papel, id, datas, metadados do modelo nem feedback de
outra mensagem; e as respostas não podem carregar dados além do contrato.
"""
from __future__ import annotations

import pytest

from qa_support.contracts import assert_error, assert_matches
from payloads import MASS_ASSIGN_CONVERSATION, MASS_ASSIGN_FEEDBACK, MASS_ASSIGN_MESSAGE
from sec_support import new_conversation

pytestmark = pytest.mark.owasp("API3:2023")


@pytest.mark.trace("CONV-RN08", "CONV-RN13", "R01", "R17")
def test_criar_conversa_ignora_campos_de_servidor(alice, bob):
    r = alice.request("POST", "/api/v1/conversations", json_body={"agent_id": "agt_support", **MASS_ASSIGN_CONVERSATION})
    assert r.status_code == 201, r.text
    conv = r.json()
    assert_matches("conversation", conv)
    assert conv["owner_id"] == "u_alice", "owner_id veio do corpo (mass assignment)"
    assert conv["status"] == "open" and conv["closed_at"] is None
    assert conv["id"] != MASS_ASSIGN_CONVERSATION["id"] and conv["id"].startswith("conv_")
    assert conv["created_at"] != MASS_ASSIGN_CONVERSATION["created_at"]
    assert conv["messages"] == [], "mensagens forjadas foram injetadas no histórico"
    assert "role" not in conv
    # e Bob, o "dono" pretendido, continua sem acesso
    assert_error(bob.get_conversation(conv["id"]), 404, "CONVERSATION_NOT_FOUND")


@pytest.mark.trace("CONV-RN05", "CONV-RN13", "R10", "R17")
def test_enviar_mensagem_ignora_papel_status_seq_e_metadados(alice):
    conv = new_conversation(alice)
    r = alice.send_message(conv["id"], None, json_body={"content": "Olá", **MASS_ASSIGN_MESSAGE})
    assert r.status_code == 201, r.text
    body = r.json()
    assert_matches("send_message_response", body)
    user, assistant = body["user_message"], body["assistant_message"]
    assert user["role"] == "user", "cliente escolheu o papel da própria mensagem"
    assert user["status"] == "completed" and user["seq"] == 1 and user["id"] != MASS_ASSIGN_MESSAGE["id"]
    assert user["metadata"] is None and user["feedback"] is None and user["reply_to"] is None
    assert assistant["reply_to"] == user["id"]
    assert assistant["metadata"]["model"] != MASS_ASSIGN_MESSAGE["metadata"]["model"]
    history = alice.get_conversation(conv["id"]).json()["messages"]
    assert [m["role"] for m in history] == ["user", "assistant"], "mensagem de 'assistant' forjada pelo cliente"


@pytest.mark.trace("FDBK-RN07", "FDBK-RN05", "R17", "R01")
def test_feedback_ignora_message_id_e_updated_at_do_corpo(alice, alice_conv):
    r = alice.give_feedback(alice_conv["id"], alice_conv["assistant_msg"], {"rating": "positive", **MASS_ASSIGN_FEEDBACK})
    assert r.status_code == 200, r.text
    fb = r.json()
    assert_matches("feedback_response", fb)
    assert fb["message_id"] == alice_conv["assistant_msg"], "message_id do corpo sobrepôs o do caminho"
    assert fb["updated_at"] != MASS_ASSIGN_FEEDBACK["updated_at"]
    assert set(fb) == {"message_id", "rating", "comment", "updated_at"}


@pytest.mark.trace("CONV-RN03", "R08")
def test_encerrar_ignora_corpo_que_tenta_reabrir_ou_trocar_dono(alice, bob):
    conv = new_conversation(alice)
    r = alice.request("POST", f"/api/v1/conversations/{conv['id']}/close",
                      json_body={"status": "open", "owner_id": "u_bob", "closed_at": None})
    assert r.status_code == 200 and r.json()["status"] == "closed" and r.json()["owner_id"] == "u_alice"
    assert_error(bob.get_conversation(conv["id"]), 404, "CONVERSATION_NOT_FOUND")


@pytest.mark.trace("CONV-RN08", "CONV-RN13", "R01", "R17")
def test_resposta_de_erro_contem_apenas_o_envelope(bob, alice_conv):
    """Exposição excessiva: erro não carrega o objeto, dono, ids nem detalhes internos."""
    r = bob.get_conversation(alice_conv["id"])
    assert set(r.json()) == {"error"} and set(r.json()["error"]) == {"code", "message", "request_id"}


@pytest.mark.trace("CONV-RN13", "R17")
def test_conversa_nao_expoe_campos_internos(alice, alice_conv):
    """O snapshot devolve só os campos do contrato (nenhum campo interno, lock ou contexto do LLM)."""
    conv = alice.get_conversation(alice_conv["id"]).json()
    assert_matches("conversation", conv)
    assert set(conv) == {"id", "agent_id", "owner_id", "status", "created_at", "closed_at", "messages"}
    for m in conv["messages"]:
        assert set(m) == {"id", "seq", "role", "content", "status", "created_at", "reply_to", "metadata", "feedback"}
        if m["metadata"]:
            assert set(m["metadata"]) == {"model", "latency_ms", "prompt_tokens", "completion_tokens", "finish_reason"}
