"""Validação de contrato via JSON Schema (draft 2020-12) a partir de contracts/."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from datetime import datetime

from referencing import Registry, Resource

# O jsonschema só valida "date-time" se o pacote opcional rfc3339-validator estiver
# instalado; sem ele a checagem é ignorada em silêncio. Registramos um checker explícito
# para o contrato não depender de dependência opcional.
_FORMATS = FormatChecker()


@_FORMATS.checks("date-time", raises=ValueError)
def _is_datetime(value) -> bool:
    if not isinstance(value, str):
        return True
    if "T" not in value or not (value.endswith("Z") or value[-6] in "+-"):
        raise ValueError("date-time deve ser ISO-8601 com fuso (ex.: 2026-01-01T00:00:00Z)")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return True

from .paths import CONTRACTS as CONTRACTS_DIR  # noqa: E402  (contratos pertencem à API: app/contracts)


@lru_cache
def _registry() -> Registry:
    resources = []
    for f in CONTRACTS_DIR.glob("*.schema.json"):
        schema = json.loads(f.read_text(encoding="utf-8"))
        resources.append((f.name, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


@lru_cache
def validator(name: str) -> Draft202012Validator:
    schema = json.loads((CONTRACTS_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry(), format_checker=_FORMATS)


def assert_matches(name: str, payload) -> None:
    """Falha com TODAS as violações de contrato, não só a primeira (diagnóstico mais rápido)."""
    errors = sorted(validator(name).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(f"  - {'/'.join(map(str, e.path)) or '<raiz>'}: {e.message}" for e in errors)
        raise AssertionError(f"Resposta viola o contrato '{name}':\n{details}")


def assert_error(resp, status: int, code: str) -> dict:
    """Erro esperado: status, envelope padronizado, código e request_id rastreável."""
    assert resp.status_code == status, f"esperado {status}, obtido {resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert_matches("error", body)
    assert body["error"]["code"] == code, body
    assert body["error"]["request_id"] == resp.headers.get("X-Request-ID"), "request_id do corpo != header"
    return body
