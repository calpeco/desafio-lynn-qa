"""Unit: regras de validação de entrada (P-5). Rápidos, sem HTTP — base da pirâmide."""
import pytest

from lynn_mock.domain.validation import MAX_CONTENT, validate_agent, validate_content


@pytest.mark.trace("CONV-RN04", "R09")
@pytest.mark.parametrize("raw,expected", [
    ("a", "a"),
    ("a" * MAX_CONTENT, "a" * MAX_CONTENT),
    ("🙂" * MAX_CONTENT, "🙂" * MAX_CONTENT),          # code points, não bytes (4 bytes cada em UTF-8)
    ("  borda  ", "borda"),                            # strip antes de contar
    (" " + "a" * MAX_CONTENT + " ", "a" * MAX_CONTENT),  # espaços não contam para o limite
])
def test_conteudo_valido(raw, expected):
    content, err = validate_content(raw)
    assert err is None and content == expected


@pytest.mark.trace("CONV-RN04", "R09")
@pytest.mark.parametrize("raw", ["", "   \n\t", "a" * (MAX_CONTENT + 1), "🙂" * (MAX_CONTENT + 1),
                                 None, 123, ["oi"], {"x": 1}])
def test_conteudo_invalido(raw):
    content, err = validate_content(raw)
    assert content is None and err.code == "VALIDATION_ERROR"


@pytest.mark.trace("CONV-RN04")
def test_limite_configuravel_respeitado():
    assert validate_content("abc", max_len=2)[1] is not None


@pytest.mark.trace("CONV-RN02", "R09")
@pytest.mark.parametrize("agent_id,code", [
    ("agt_support", None), ("agt_sales", None),
    ("agt_retired", "AGENT_NOT_FOUND"), ("agt_x", "AGENT_NOT_FOUND"),
    ("", "VALIDATION_ERROR"), ("  ", "VALIDATION_ERROR"), (None, "VALIDATION_ERROR"), (42, "VALIDATION_ERROR"),
])
def test_validacao_de_agente(agent_id, code):
    err = validate_agent(agent_id)
    assert (err.code if err else None) == code
