"""Regras que antes viviam na camada HTTP e agora são funções puras (testáveis na base da pirâmide)."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

LLM_FAIL_MSG = "Não foi possível gerar uma resposta agora. Sua mensagem foi salva; tente novamente em instantes."


def resolve_user(authorization: str | None, tokens: dict[str, str]) -> str | None:
    """Bearer token -> id da pessoa. O esquema é case-insensitive (RFC 7235); o token não."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or token != token.strip():
        return None
    return tokens.get(token)


@dataclass(frozen=True)
class BodyError:
    status: int
    code: str
    message: str


def parse_json_object(raw: str) -> tuple[dict | None, BodyError | None]:
    """Corpo precisa ser um objeto JSON. Malformado -> 400; JSON válido que não é objeto -> 422."""
    try:
        data = json.loads(raw or "null")
    except ValueError:
        return None, BodyError(400, "INVALID_JSON", "Corpo da requisição não é um JSON válido.")
    if not isinstance(data, dict):
        return None, BodyError(422, "VALIDATION_ERROR", "Corpo deve ser um objeto JSON.")
    return data, None


@dataclass(frozen=True)
class LLMFailure:
    status: int
    code: str
    message: str
    retry_after_s: int


def llm_failure_response(timed_out: bool) -> LLMFailure:
    """Premissa P-7: indisponível -> 503, timeout -> 504; sempre mensagem amigável + Retry-After."""
    return (LLMFailure(504, "LLM_TIMEOUT", LLM_FAIL_MSG, 2) if timed_out
            else LLMFailure(503, "LLM_UNAVAILABLE", LLM_FAIL_MSG, 2))


def request_id(incoming: str | None) -> str:
    """Ecoa o X-Request-ID do cliente (correlação ponta a ponta) ou gera um novo."""
    incoming = (incoming or "").strip()
    return incoming[:128] if incoming else str(uuid.uuid4())


def error_body(code: str, message: str, req_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": req_id}}
