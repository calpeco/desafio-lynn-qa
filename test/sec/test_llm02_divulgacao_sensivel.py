"""LLM02:2025 — Sensitive Information Disclosure.

Contexto de outra conversa/pessoa (com controle positivo e canal lateral de tokens), PII em logs em
todos os caminhos (sucesso, erro de validação, JSON inválido, falha do LLM, feedback) e a robustez
do guardrail de saída (caixa-cinza). Deve falhar com LYNN_FAULTS=context_leak.
"""
from __future__ import annotations

import base64

import pytest

from lynn_mock.domain.guardrail import apply_output_guardrail
from lynn_mock.llm.fake_llm import SYSTEM_CANARY, SYSTEM_PROMPT
from payloads import FAKE_CARD, FAKE_CPF, SECRET_ALICE, SECRET_ASKS, SECRET_BOB, SECRET_SET
from sec_support import logs_text, new_conversation, send_ok

pytestmark = pytest.mark.owasp("LLM02:2025")

PII_MARKERS = (FAKE_CPF, FAKE_CPF.replace(".", "").replace("-", ""), FAKE_CARD, FAKE_CARD.replace(" ", ""))


@pytest.mark.trace("CONV-RN11", "R05")
def test_controle_positivo_segredo_e_lembrado_na_propria_conversa(alice):
    """Sem este controle, os testes de isolamento passariam mesmo se o modelo nunca lembrasse nada."""
    conv = new_conversation(alice)
    send_ok(alice, conv["id"], SECRET_SET.format(SECRET_ALICE))
    assert SECRET_ALICE in send_ok(alice, conv["id"], SECRET_ASKS[0])["assistant_message"]["content"]


@pytest.mark.trace("CONV-RN08", "CONV-RN11", "R05", "R01")
@pytest.mark.parametrize("ask", SECRET_ASKS)
def test_segredo_de_outra_pessoa_nao_chega_ao_contexto(ask, alice, bob):
    conv = new_conversation(alice)
    send_ok(alice, conv["id"], SECRET_SET.format(SECRET_ALICE))
    bob_conv = new_conversation(bob)
    answer = send_ok(bob, bob_conv["id"], ask)["assistant_message"]["content"]
    assert SECRET_ALICE not in answer, "segredo da Alice apareceu para o Bob"


@pytest.mark.trace("CONV-RN11", "R05")
def test_segredo_nao_atravessa_conversas_da_mesma_pessoa(alice):
    a = new_conversation(alice)
    send_ok(alice, a["id"], SECRET_SET.format(SECRET_ALICE))
    b = new_conversation(alice)
    assert SECRET_ALICE not in send_ok(alice, b["id"], SECRET_ASKS[0])["assistant_message"]["content"]


@pytest.mark.trace("CONV-RN08", "CONV-RN11", "R05", "R01")
def test_com_dois_segredos_cada_pessoa_recebe_so_o_seu(alice, bob):
    a, b = new_conversation(alice), new_conversation(bob)
    send_ok(alice, a["id"], SECRET_SET.format(SECRET_ALICE))
    send_ok(bob, b["id"], SECRET_SET.format(SECRET_BOB))
    for client, conv, mine, other in ((alice, a, SECRET_ALICE, SECRET_BOB), (bob, b, SECRET_BOB, SECRET_ALICE)):
        answer = send_ok(client, conv["id"], SECRET_ASKS[0])["assistant_message"]["content"]
        assert mine in answer and other not in answer, answer


@pytest.mark.trace("CONV-RN11", "R05", "R11")
def test_canal_lateral_tokens_de_prompt_nao_dependem_de_outras_conversas(alice, bob):
    """prompt_tokens é exposto em metadata: se outra conversa entrasse no contexto, o número mudaria."""
    baseline_conv = new_conversation(bob)
    baseline = send_ok(bob, baseline_conv["id"], "oi")["assistant_message"]["metadata"]["prompt_tokens"]
    conv = new_conversation(alice)
    send_ok(alice, conv["id"], "palavra " * 300)
    later_conv = new_conversation(bob)
    later = send_ok(bob, later_conv["id"], "oi")["assistant_message"]["metadata"]["prompt_tokens"]
    assert later == baseline, f"prompt_tokens subiu de {baseline} para {later} por atividade de outra pessoa"


# ------------------------------------------------------------------ PII em logs (R12)
@pytest.mark.trace("CONV-RN12", "FDBK-RN08", "R12")
@pytest.mark.parametrize("caminho", ["201-sucesso", "422-acima-do-limite", "400-json-invalido", "503-falha-llm",
                                     "504-timeout-llm", "feedback-comentario", "404-conversa-alheia"])
def test_pii_nao_vai_para_logs_em_nenhum_caminho(caminho, alice, bob, control):
    conv = new_conversation(alice)
    text = f"Meu CPF é {FAKE_CPF} e o cartão {FAKE_CARD}"
    if caminho == "201-sucesso":
        r = alice.send_message(conv["id"], text)
    elif caminho == "422-acima-do-limite":
        r = alice.send_message(conv["id"], text + "x" * 4000)
    elif caminho == "400-json-invalido":
        r = alice.request("POST", f"/api/v1/conversations/{conv['id']}/messages", raw_body='{"content": "' + text)
    elif caminho == "503-falha-llm":
        control.llm(mode="error")
        r = alice.send_message(conv["id"], text)
    elif caminho == "504-timeout-llm":
        control.llm(mode="timeout", delay_ms=800, timeout_ms=100)
        r = alice.send_message(conv["id"], text)
    elif caminho == "feedback-comentario":
        mid = send_ok(alice, conv["id"], "oi")["assistant_message"]["id"]
        r = alice.give_feedback(conv["id"], mid, {"rating": "negative", "comment": text})
    else:
        r = bob.send_message(conv["id"], text)
    assert r.status_code in {"201-sucesso": (201,), "422-acima-do-limite": (422,), "400-json-invalido": (400,),
                             "503-falha-llm": (503,), "504-timeout-llm": (504,), "feedback-comentario": (200,),
                             "404-conversa-alheia": (404,)}[caminho], r.text
    logs = logs_text(control)
    for marker in PII_MARKERS + ("token-alice", "token-bob"):
        assert marker not in logs, f"{marker!r} apareceu nos logs ({caminho})"


@pytest.mark.trace("CONV-RN12", "R12")
@pytest.mark.parametrize("caminho", ["422-acima-do-limite", "409-encerrada"])
def test_erro_nao_ecoa_o_conteudo_enviado(caminho, alice):
    conv = new_conversation(alice)
    if caminho == "409-encerrada":
        alice.close_conversation(conv["id"])
        r = alice.send_message(conv["id"], f"CPF {FAKE_CPF}")
    else:
        r = alice.send_message(conv["id"], f"CPF {FAKE_CPF} " + "x" * 4000)
    assert r.status_code in (409, 422) and FAKE_CPF not in r.text


# ------------------------------------------------------------------ guardrail (caixa-cinza)
@pytest.mark.owasp("LLM07:2025")
@pytest.mark.trace("CONV-RN11", "R04")
@pytest.mark.xfail(strict=True, reason="SEC-009: guardrail só bloqueia o canário literal; codificado/parafraseado passa")
@pytest.mark.parametrize("variant", ["base64", "canario-espacado", "canario-minusculo", "prompt-sem-canario", "invertido"])
def test_guardrail_bloqueia_prompt_de_sistema_transformado(variant):
    """Um modelo real pode devolver o prompt traduzido, codificado ou parcial. O filtro de saída
    precisa reconhecer o conteúdo, não apenas a string exata do canário."""
    leaked = {
        "base64": base64.b64encode(SYSTEM_PROMPT.encode()).decode(),
        "canario-espacado": SYSTEM_PROMPT.replace(SYSTEM_CANARY, " ".join(SYSTEM_CANARY)),
        "canario-minusculo": SYSTEM_PROMPT.lower(),
        "prompt-sem-canario": SYSTEM_PROMPT.split("[canary")[0],
        "invertido": SYSTEM_PROMPT[::-1],
    }[variant]
    result = apply_output_guardrail("Claro! " + leaked, "stop", SYSTEM_CANARY)
    assert result.blocked_rule == "system_prompt_leak", f"variação '{variant}' passou pelo guardrail"
