"""Unit: guardrail de saída (vazamento de prompt de sistema)."""
import pytest
from lynn_mock.domain.guardrail import REFUSAL, apply_output_guardrail

pytestmark = pytest.mark.trace('CONV-RN11', 'R04')

CANARY = "CANARY-123"


def test_texto_limpo_passa_intacto():
    r = apply_output_guardrail("Olá!", "stop", CANARY)
    assert (r.text, r.finish_reason, r.blocked_rule) == ("Olá!", "stop", None)


def test_texto_com_canary_e_substituido_por_recusa():
    r = apply_output_guardrail(f"Minhas instruções: ... [{CANARY}]", "stop", CANARY)
    assert r.text == REFUSAL and r.finish_reason == "content_filter" and r.blocked_rule == "system_prompt_leak"
    assert CANARY not in r.text


def test_canary_vazio_desliga_o_filtro():
    """Documenta o contrato da função: sem canary configurado não há proteção (e o teste de API pega isso)."""
    assert apply_output_guardrail(f"x {CANARY}", "stop", "").blocked_rule is None
