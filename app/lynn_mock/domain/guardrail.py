"""Guardrail de saída: impede que o prompt de sistema chegue ao usuário."""
from __future__ import annotations

from dataclasses import dataclass

REFUSAL = "Desculpe, não posso compartilhar minhas instruções internas. Posso ajudar com outra coisa?"


@dataclass(frozen=True)
class GuardrailResult:
    text: str
    finish_reason: str
    blocked_rule: str | None = None


def apply_output_guardrail(text: str, finish_reason: str, canary: str) -> GuardrailResult:
    if canary and canary in text:
        return GuardrailResult(REFUSAL, "content_filter", "system_prompt_leak")
    return GuardrailResult(text, finish_reason)
