"""Regras de validação de entrada (puras, sem HTTP) — base da pirâmide de testes."""
from __future__ import annotations

from dataclasses import dataclass

MAX_CONTENT = 4000
AGENTS = {"agt_support": True, "agt_sales": True, "agt_retired": False}  # id -> ativo


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str


def validate_content(raw, max_len: int = MAX_CONTENT) -> tuple[str | None, ValidationError | None]:
    """content obrigatório, string, 1..max_len code points após strip() (premissa P-5)."""
    if not isinstance(raw, str):
        return None, ValidationError("VALIDATION_ERROR", "content é obrigatório e deve ser texto.")
    content = raw.strip()
    if not (1 <= len(content) <= max_len):
        return None, ValidationError("VALIDATION_ERROR", f"content deve ter entre 1 e {MAX_CONTENT} caracteres.")
    return content, None


def validate_agent(agent_id) -> ValidationError | None:
    if not isinstance(agent_id, str) or not agent_id.strip():
        return ValidationError("VALIDATION_ERROR", "agent_id é obrigatório.")
    if not AGENTS.get(agent_id):
        return ValidationError("AGENT_NOT_FOUND", "Agente inexistente ou indisponível.")
    return None
