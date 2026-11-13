"""Unit: os próprios contratos (JSON Schema) são válidos e estritos o suficiente."""
import pytest

from qa_support.contracts import assert_matches, validator

pytestmark = pytest.mark.trace('CONV-RN13', 'R17')

BASE = {"id": "conv_0123456789abcdef", "agent_id": "a", "owner_id": "u", "status": "open",
        "created_at": "2026-01-01T00:00:00Z", "closed_at": None, "messages": []}


@pytest.mark.parametrize("name", ["conversation", "message", "send_message_response", "error"])
def test_schema_e_valido(name):
    validator(name)


def test_payload_valido_passa():
    assert_matches("conversation", BASE)


@pytest.mark.parametrize("patch,why", [
    ({"status": "archived"}, "enum"),
    ({"messages": None}, "tipo"),
    ({"status": "closed"}, "fechada sem closed_at"),
    ({"created_at": "2026-13-01T00:00:00Z"}, "data inválida"),
    ({"created_at": "2026-01-01 00:00:00"}, "data sem T/fuso"),
    ({"extra": 1}, "campo não declarado"),
])
def test_schema_rejeita(patch, why):
    with pytest.raises(AssertionError):
        assert_matches("conversation", {**BASE, **patch})


def test_campo_obrigatorio_ausente():
    payload = dict(BASE)
    payload.pop("messages")
    with pytest.raises(AssertionError):
        assert_matches("conversation", payload)
