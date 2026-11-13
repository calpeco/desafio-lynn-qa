"""Steps de avaliação (feedback) de respostas do agente — specs/feedback-resposta.md (FDBK).

HTTP fica no cliente (`ConversationsClient.give_feedback`); `_rate` só registra a resposta no contexto.
"""
from behave import given, then, when

from qa_support import bdd
from qa_support.contracts import assert_matches
from qa_support.http_client import ConversationsClient

MISSING_MSG = "msg_0000000000000000"
MISSING_CONV = "conv_0000000000000000"


def _rate(context, persona, conv, message_id, *, body=None, raw_body=None, http=None):
    c = http or bdd.client(context, persona)
    return bdd.remember(context, c.give_feedback(conv, message_id, body=body, raw_body=raw_body))


def _last(context, owner, role):
    msgs = bdd.messages(context, owner)
    found = [m for m in msgs if m["role"] == role]
    assert found, f"pré-condição: nenhuma mensagem {role!r} no histórico de {owner!r}: {msgs}"
    return found[-1]


def _rate_last_answer(context, persona, owner, body=None, raw_body=None):
    msg = _last(context, owner, "assistant")
    context.rated_message_id = msg["id"]
    return _rate(context, persona, bdd.conv_id(context, owner), msg["id"], body=body, raw_body=raw_body)


def _history(context, owner=None):
    owner = owner or context.last_conv[0]
    r = bdd.client(context, owner).get_conversation(bdd.conv_id(context, owner))
    assert r.status_code == 200, r.text
    assert_matches("conversation", r.json())          # campo `feedback` validado pelo contrato
    return r.json()["messages"]


def _last_answer_feedback(context):
    answers = [m for m in _history(context) if m["role"] == "assistant"]
    assert answers, "nenhuma resposta do agente no histórico"
    return answers[-1]["feedback"]


# ---------------------------------------------------------------- pré-condições
@given('que "{persona:Q}" avaliou a última resposta do agente como "{rating:Q}" com o comentário "{comment:Q}"')
def has_rated(context, persona, rating, comment):
    r = _rate_last_answer(context, persona, persona, {"rating": rating, "comment": comment})
    assert r.status_code == 200, f"pré-condição falhou: {r.status_code} {r.text}"


# ---------------------------------------------------------------- ações
@when('"{persona:Q}" avalia a última resposta do agente como "{rating:Q}"')
def rate_last(context, persona, rating):
    _rate_last_answer(context, persona, persona, {"rating": rating})


@when('"{persona:Q}" avalia a última resposta do agente como "{rating:Q}" com o comentário "{comment:Q}"')
def rate_last_with_comment(context, persona, rating, comment):
    _rate_last_answer(context, persona, persona, {"rating": rating, "comment": comment})


@when('"{persona:Q}" avalia a última resposta do agente como "{rating:Q}" com um comentário de {n:d} caracteres "{char:Q}"')
def rate_last_sized(context, persona, rating, n, char):
    context.sent_comment = char * n
    _rate_last_answer(context, persona, persona, {"rating": rating, "comment": char * n})


@when('"{persona:Q}" avalia a última resposta do agente com o corpo {body}')
def rate_last_raw(context, persona, body):
    _rate_last_answer(context, persona, persona, raw_body=body)


@when('"{persona:Q}" avalia a última resposta do agente na conversa de "{owner:Q}" como "{rating:Q}"')
def rate_others(context, persona, owner, rating):
    _rate_last_answer(context, persona, owner, {"rating": rating})


@when('"{persona:Q}" avalia, na própria conversa, a última resposta do agente da conversa de "{owner:Q}"')
def rate_foreign_message_in_own_conv(context, persona, owner):
    foreign = _last(context, owner, "assistant")
    _rate(context, persona, bdd.conv_id(context, persona), foreign["id"], body={"rating": "positive"})


@when('"{persona:Q}" avalia a última mensagem do usuário como "{rating:Q}"')
def rate_user_message(context, persona, rating):
    msg = _last(context, persona, "user")
    _rate(context, persona, bdd.conv_id(context, persona), msg["id"], body={"rating": rating})


@when('"{persona:Q}" avalia uma mensagem inexistente da própria conversa')
def rate_missing_message(context, persona):
    _rate(context, persona, bdd.conv_id(context, persona), MISSING_MSG, body={"rating": "positive"})


@when('"{persona:Q}" avalia uma mensagem de uma conversa inexistente')
def rate_in_missing_conversation(context, persona):
    _rate(context, persona, MISSING_CONV, MISSING_MSG, body={"rating": "positive"})


@when('uma requisição sem autenticação avalia a última resposta do agente de "{owner:Q}"')
def rate_unauthenticated(context, owner):
    msg = _last(context, owner, "assistant")
    raw = ConversationsClient(context.base_url, None, context.exchange_log)
    raw.scenario = context.scenario.name
    try:
        _rate(context, None, bdd.conv_id(context, owner), msg["id"], body={"rating": "positive"}, http=raw)
    finally:
        raw.close()


# ---------------------------------------------------------------- verificações
@then('a resposta registra a avaliação "{rating:Q}" sem comentário')
def response_has_no_comment(context, rating):
    body = context.response.json()
    assert_matches("feedback_response", body)
    assert (body["message_id"], body["rating"], body["comment"]) == (context.rated_message_id, rating, None), body


@then("a resposta registra o comentário enviado sem os espaços das bordas")
def response_comment_trimmed(context):
    body = context.response.json()
    assert_matches("feedback_response", body)
    assert body["comment"] == context.sent_comment, (len(body["comment"] or ""), len(context.sent_comment))


@then('a última resposta do agente no histórico tem avaliação "{rating:Q}" com o comentário "{comment:Q}"')
def history_has(context, rating, comment):
    fb = _last_answer_feedback(context)
    assert fb is not None and (fb["rating"], fb["comment"]) == (rating, comment), fb


@then('a última resposta do agente no histórico tem avaliação "{rating:Q}" sem comentário')
def history_has_no_comment(context, rating):
    fb = _last_answer_feedback(context)
    assert fb is not None and (fb["rating"], fb["comment"]) == (rating, None), fb


@then('a última resposta do agente na conversa de "{owner:Q}" não tem avaliação')
def history_without_feedback(context, owner):
    context.last_conv = (owner, bdd.DEFAULT_CONV)
    assert _last_answer_feedback(context) is None


@then("a avaliação no histórico é a mesma devolvida pela API")
def history_equals_response(context):
    body = context.response.json()
    fb = _last_answer_feedback(context)
    assert fb == {k: body[k] for k in ("rating", "comment", "updated_at")}, (fb, body)


@then("as mensagens do usuário no histórico não têm avaliação")
def user_messages_without_feedback(context):
    users = [m for m in _history(context) if m["role"] == "user"]
    assert users and all(m["feedback"] is None for m in users), users
