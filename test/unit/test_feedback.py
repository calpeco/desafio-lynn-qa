"""Unit: regras puras da avaliação de respostas (specs/feedback-resposta.md). Sem HTTP."""
import pytest

from lynn_mock.domain.conversations import ConversationStore
from lynn_mock.domain.feedback import MAX_COMMENT, can_receive_feedback, validate_feedback


def _conv_with_answer():
    s = ConversationStore()
    c = s.create("u_alice", "agt_support")
    u = s.append_user_message(c, "oi")
    a = s.append_assistant_message(c, u, "olá", {})
    return s, c, u, a


# ---------------------------------------------------------------- RN01
@pytest.mark.trace("FDBK-RN01", "R09")
@pytest.mark.parametrize("role,status,allowed", [
    ("assistant", "completed", True),
    ("assistant", "failed", False),     # resposta não concluída
    ("assistant", "pending", False),
    ("user", "completed", False),       # mensagem da pessoa usuária
    ("user", "failed", False),
])
def test_somente_resposta_concluida_do_agente_pode_ser_avaliada(role, status, allowed):
    assert can_receive_feedback({"role": role, "status": status}) is allowed


# ---------------------------------------------------------------- RN02
@pytest.mark.trace("FDBK-RN02", "R09")
@pytest.mark.parametrize("rating", ["positive", "negative"])
def test_avaliacoes_validas(rating):
    parsed, err = validate_feedback({"rating": rating})
    assert err is None and parsed == (rating, None)


@pytest.mark.trace("FDBK-RN02", "R09")
@pytest.mark.parametrize("body", [
    {},                                  # ausente
    {"rating": None},
    {"rating": ""},
    {"rating": "neutral"},
    {"rating": "Positive"},              # sem normalização de caixa
    {"rating": " positive "},            # sem trim no enum
    {"rating": True},
    {"rating": 1},
    {"rating": ["positive"]},
    {"rating": {"value": "positive"}},
])
def test_avaliacao_ausente_invalida_ou_de_outro_tipo(body):
    parsed, err = validate_feedback(body)
    assert parsed is None and err.code == "VALIDATION_ERROR"


# ---------------------------------------------------------------- RN03
@pytest.mark.trace("FDBK-RN03", "R09")
@pytest.mark.parametrize("comment,expected", [
    (None, None),
    ("", None),
    ("   \n\t ", None),                                  # só espaços = sem comentário
    ("  ótimo  ", "ótimo"),                              # bordas removidas
    ("a" * MAX_COMMENT, "a" * MAX_COMMENT),              # limite exato
    ("  " + "a" * MAX_COMMENT + "  ", "a" * MAX_COMMENT),  # espaços das bordas não contam
    ("🙂" * MAX_COMMENT, "🙂" * MAX_COMMENT),            # conta caracteres, não bytes
])
def test_comentario_valido(comment, expected):
    parsed, err = validate_feedback({"rating": "negative", "comment": comment})
    assert err is None and parsed == ("negative", expected)


@pytest.mark.trace("FDBK-RN03", "R09")
@pytest.mark.parametrize("comment", ["a" * (MAX_COMMENT + 1), "🙂" * (MAX_COMMENT + 1), 123, ["x"], {"t": "x"}, True])
def test_comentario_invalido(comment):
    parsed, err = validate_feedback({"rating": "positive", "comment": comment})
    assert parsed is None and err.code == "VALIDATION_ERROR"


@pytest.mark.trace("FDBK-RN03")
def test_limite_do_comentario_e_500():
    assert MAX_COMMENT == 500


# ---------------------------------------------------------------- RN04
@pytest.mark.trace("FDBK-RN04", "R02")
def test_nova_avaliacao_substitui_a_anterior_sem_criar_mensagem():
    s, c, _u, a = _conv_with_answer()
    first = s.set_feedback(a, "positive", "clara")
    second = s.set_feedback(a, "negative", None)
    assert a["feedback"] == second
    assert (second["rating"], second["comment"]) == ("negative", None)   # comentário anterior não sobra
    assert second["updated_at"] >= first["updated_at"]
    assert len(c["messages"]) == 2                                        # premissa P1


@pytest.mark.trace("FDBK-RN04", "FDBK-RN07")
def test_avaliacao_afeta_so_a_mensagem_avaliada():
    s, c, u, a = _conv_with_answer()
    s.set_feedback(a, "positive", None)
    assert u["feedback"] is None
    assert s.snapshot(c)["messages"][1]["feedback"]["rating"] == "positive"
