"""Steps de reenvio, duplo clique e idempotência."""
import threading

from behave import given, then, when

from qa_support import bdd
from qa_support.contracts import assert_error


@given('que "{persona:Q}" enviou com a chave "{key:Q}" a mensagem "{content:Q}"')
def has_sent_with_key(context, persona, key, content):
    bdd.send(context, persona, content, key=key)


@when('"{persona:Q}" envia com a chave "{key:Q}" a mensagem "{content:Q}"')
def send_with_key(context, persona, key, content):
    bdd.send(context, persona, content, key=key)


@when('"{persona:Q}" envia na conversa "{name:Q}" com a chave "{key:Q}" a mensagem "{content:Q}"')
def send_named_with_key(context, persona, name, key, content):
    previous = context.last_conv
    bdd.send(context, persona, content, name=name, key=key)
    context.last_conv = previous


@when('"{persona:Q}" clica duas vezes em enviar "{content:Q}" com a chave "{key:Q}"')
def double_click(context, persona, content, key):
    """Dois POSTs disparados no mesmo instante (Barrier) com a mesma chave = duplo clique."""
    cid, c = bdd.conv_id(context, persona), bdd.client(context, persona)
    context.last_conv = (persona, bdd.DEFAULT_CONV)
    barrier, results = threading.Barrier(2), []

    def click():
        barrier.wait()
        results.append(c.send_message(cid, content, idempotency_key=key))

    threads = [threading.Thread(target=click) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    context.double = results


@then("a resposta é idêntica à da primeira tentativa")
def same_as_first(context):
    assert context.sends[-1].json() == context.sends[0].json(), "replay deve devolver os MESMOS ids"


@then("um envio foi aceito e o outro foi um replay ou recusado como em andamento")
def one_accepted(context):
    statuses = sorted(r.status_code for r in context.double)
    assert statuses in ([201, 201], [201, 409]), statuses
    for r in context.double:
        if r.status_code == 409:
            assert_error(r, 409, "IDEMPOTENCY_IN_PROGRESS")


@then("nenhum dos três envios foi um replay e todos geraram mensagens distintas")
def scoped_keys(context):
    last3 = context.sends[-3:]
    assert [r.status_code for r in last3] == [201] * 3
    assert all("idempotent-replayed" not in r.headers for r in last3)
    assert len({r.json()["user_message"]["id"] for r in last3}) == 3
