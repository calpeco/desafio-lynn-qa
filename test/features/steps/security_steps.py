"""Steps de autenticação e isolamento entre pessoas (IDOR / enumeração)."""
from behave import then, when

from qa_support import bdd
from qa_support.http_client import ConversationsClient

ACTIONS = {
    "criar": lambda c, cid: c.request("POST", "/api/v1/conversations", json_body={"agent_id": "agt_support"}),
    "consultar": lambda c, cid: c.get_conversation(cid),
    "enviar": lambda c, cid: c.send_message(cid, "oi"),
    "encerrar": lambda c, cid: c.close_conversation(cid),
}


@when('uma requisição com autenticação "{auth:Q}" tenta "{action:Q}" na conversa de "{owner:Q}"')
def unauthenticated_attempt(context, auth, action, owner):
    header = None if auth == "nenhum" else auth   # None = cabeçalho ausente
    raw = ConversationsClient(context.base_url, None, context.exchange_log,
                              default_headers={"Authorization": header})
    raw.scenario = context.scenario.name
    try:
        bdd.remember(context, ACTIONS[action](raw, bdd.conv_id(context, owner)))
    finally:
        raw.close()


@when('"{persona:Q}" consulta a conversa de "{owner:Q}"')
def get_others_conversation(context, persona, owner):
    bdd.remember(context, bdd.client(context, persona).get_conversation(bdd.conv_id(context, owner)))


@when('"{persona:Q}" envia a mensagem "{content:Q}" na conversa de "{owner:Q}"')
def send_to_others_conversation(context, persona, content, owner):
    bdd.send(context, persona, content, owner=owner)


@when('"{persona:Q}" encerra a conversa de "{owner:Q}"')
def close_others_conversation(context, persona, owner):
    bdd.remember(context, bdd.client(context, persona).close_conversation(bdd.conv_id(context, owner)))


@when('"{persona:Q}" consulta a conversa de "{owner:Q}" e uma conversa inexistente')
def compare_foreign_and_missing(context, persona, owner):
    c = bdd.client(context, persona)
    context.pair = (c.get_conversation(bdd.conv_id(context, owner)), c.get_conversation("conv_0000000000000000"))


@when('"{persona:Q}" consulta a conversa "{raw_id:Q}"')
def get_by_raw_id(context, persona, raw_id):
    bdd.remember(context, bdd.client(context, persona).get_conversation(raw_id))


@then("as duas respostas são idênticas em status, código e mensagem")
def indistinguishable(context):
    foreign, missing = context.pair
    assert foreign.status_code == missing.status_code == 404
    fe, me = foreign.json()["error"], missing.json()["error"]
    assert (fe["code"], fe["message"]) == (me["code"], me["message"])
