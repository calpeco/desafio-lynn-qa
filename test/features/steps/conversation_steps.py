"""Steps de conversa: criar, enviar, consultar, encerrar, histórico e ordem."""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from behave import given, then, when

from qa_support import bdd
from qa_support.contracts import assert_error


# ---------------------------------------------------------------- pré-condições
@given('que "{owner:Q}" tem uma conversa aberta')
def has_open_conversation(context, owner):
    bdd.create_conversation(context, owner)


@given('que "{owner:Q}" tem uma conversa aberta chamada "{name:Q}"')
def has_named_conversation(context, owner, name):
    previous = context.last_conv
    bdd.create_conversation(context, owner, name)
    context.last_conv = previous or (owner, name)  # conversa nomeada não vira a "atual"


@given('que "{persona:Q}" enviou a mensagem "{content:Q}"')
def has_sent(context, persona, content):
    bdd.send(context, persona, content)


@given('que "{persona:Q}" encerrou a conversa')
def has_closed(context, persona):
    r = bdd.remember(context, bdd.client(context, persona).close_conversation(bdd.conv_id(context, persona)))
    assert r.status_code == 200, r.text
    context.closed_at = r.json()["closed_at"]


# ---------------------------------------------------------------- ações
@when('"{persona:Q}" cria uma conversa com o agente "{agent:Q}"')
def create_with_agent(context, persona, agent):
    r = bdd.remember(context, bdd.client(context, persona).create_conversation(agent))
    if r.status_code == 201:
        context.convs[(persona, bdd.DEFAULT_CONV)] = r.json()["id"]
        context.last_conv = (persona, bdd.DEFAULT_CONV)


@when('"{persona:Q}" cria uma conversa com o corpo {body}')
def create_with_body(context, persona, body):
    bdd.remember(context, bdd.client(context, persona).request("POST", "/api/v1/conversations", raw_body=body))


@when('"{persona:Q}" envia a mensagem "{content:Q}"')
def send_message(context, persona, content):
    bdd.send(context, persona, content)


@when('"{persona:Q}" envia uma mensagem com {size:d} caracteres "{char:Q}"')
def send_sized(context, persona, size, char):
    bdd.send(context, persona, char * size)


@when('"{persona:Q}" envia o corpo {body}')
def send_raw_body(context, persona, body):
    bdd.send(context, persona, None, json_body=json.loads(body))


@when('"{persona:Q}" envia o JSON malformado {raw}')
def send_malformed(context, persona, raw):
    cid = bdd.conv_id(context, persona)
    bdd.remember(context, bdd.client(context, persona).request(
        "POST", f"/api/v1/conversations/{cid}/messages", raw_body=raw))


@when('"{persona:Q}" consulta a conversa')
def get_conversation(context, persona):
    bdd.remember(context, bdd.client(context, persona).get_conversation(bdd.conv_id(context, persona)))


@when('"{persona:Q}" encerra a conversa')
def close_conversation(context, persona):
    bdd.remember(context, bdd.client(context, persona).close_conversation(bdd.conv_id(context, persona)))


@when('"{persona:Q}" chama "{method:Q}" em "{path:Q}"')
def raw_call(context, persona, method, path):
    bdd.remember(context, bdd.client(context, persona).request(method, path))


@when('"{persona:Q}" envia {n:d} mensagens em sequência')
def send_sequence(context, persona, n):
    context.sent_texts = [f"mensagem número {i} com algum conteúdo" for i in range(1, n + 1)]
    for text in context.sent_texts:
        assert bdd.send(context, persona, text).status_code == 201


@when('"{persona:Q}" envia {n:d} mensagens simultâneas')
def send_concurrently(context, persona, n):
    texts = [f"concorrente {i}" for i in range(n)]
    cid, c = bdd.conv_id(context, persona), bdd.client(context, persona)
    context.last_conv = (persona, bdd.DEFAULT_CONV)
    with ThreadPoolExecutor(max_workers=n) as pool:
        context.concurrent = list(pool.map(lambda t: c.send_message(cid, t), texts))
    context.sent_texts = texts


@when('"{persona:Q}" envia em segundo plano a mensagem "{content:Q}"')
def send_in_background(context, persona, content):
    cid, c = bdd.conv_id(context, persona), bdd.client(context, persona)
    result = {}
    t = threading.Thread(target=lambda: result.setdefault("r", c.send_message(cid, content)))
    t.start()
    context.background[content] = (t, result)
    # Ordem A → B → close. 150 ms é folgado diante do atraso de 600 ms do LLM no cenário;
    # se o ambiente for muito lento, a falha aparece como asserção clara (não como flake silencioso).
    time.sleep(0.15)


# ---------------------------------------------------------------- verificações
@then('a conversa está aberta, sem mensagens e pertence a "{owner_id:Q}"')
def conv_open_empty(context, owner_id):
    body = context.response.json()
    assert (body["status"], body["messages"], body["owner_id"]) == ("open", [], owner_id), body


@then("a conversa está encerrada")
def conv_closed(context):
    body = context.response.json()
    assert body["status"] == "closed" and body["closed_at"], body


@then('a conversa de "{owner:Q}" continua aberta')
def conv_still_open(context, owner):
    r = bdd.client(context, owner).get_conversation(bdd.conv_id(context, owner))
    assert r.json()["status"] == "open"


@then("a data de encerramento não mudou")
def closed_at_unchanged(context):
    assert context.response.json()["closed_at"] == context.closed_at


@then("a resposta do agente referencia a mensagem enviada")
def assistant_replies_to_user(context):
    body = context.response.json()
    assert body["assistant_message"]["reply_to"] == body["user_message"]["id"]


@then("a resposta do agente informa tokens de prompt e de resposta maiores que zero")
def has_token_metadata(context):
    meta = context.response.json()["assistant_message"]["metadata"]
    assert meta["prompt_tokens"] > 0 and meta["completion_tokens"] > 0 and meta["latency_ms"] >= 0, meta


@then("a mensagem do usuário não tem metadados")
def user_has_no_metadata(context):
    assert context.response.json()["user_message"]["metadata"] is None


@then('o agente respondeu contendo "{text:Q}"')
def assistant_contains(context, text):
    content = context.response.json()["assistant_message"]["content"]
    assert text in content, content


@then("o conteúdo armazenado é igual ao enviado sem espaços nas bordas")
def stored_equals_sent(context):
    sent = json.loads(context.response.request.content)["content"]
    assert context.response.json()["user_message"]["content"] == sent.strip()


@then('o conteúdo armazenado é "{text:Q}"')
def stored_is(context, text):
    assert context.response.json()["user_message"]["content"] == text


@then("nada foi persistido na conversa")
def nothing_persisted(context):
    assert bdd.messages(context) == []


@then('o histórico de "{owner:Q}" tem {n:d} mensagens')
def history_count(context, owner, n):
    msgs = bdd.messages(context, owner)
    assert len(msgs) == n, [(m["role"], m["content"][:30]) for m in msgs]


@then("o histórico contém, em ordem:")
def history_matches_table(context):
    msgs = bdd.messages(context)
    got = [(m["role"], m["content"], m["status"]) for m in msgs]
    expected = [(r["papel"], r["conteúdo"], r["status"]) for r in context.table]
    assert len(got) == len(expected), f"esperado {len(expected)} mensagens, obtido {len(got)}: {got}"
    for (role, content, status), (e_role, e_content, e_status) in zip(got, expected):
        assert role == e_role and status == e_status and (e_content == "*" or content == e_content), \
            f"\n  esperado: {expected}\n  obtido:   {got}"


@then("o histórico tem seq contíguo de 1 a {n:d}")
def seq_contiguous(context, n):
    assert [m["seq"] for m in bdd.messages(context)] == list(range(1, n + 1))


@then("cada resposta do agente vem logo após a sua pergunta")
def replies_adjacent(context):
    msgs = bdd.messages(context)
    by_id = {m["id"]: m for m in msgs}
    for m in msgs:
        if m["role"] == "assistant":
            assert by_id[m["reply_to"]]["seq"] == m["seq"] - 1, f"resposta fora de ordem: seq {m['seq']}"


@then("as mensagens do usuário estão na ordem em que foram enviadas")
def user_messages_in_order(context):
    msgs = bdd.messages(context)
    assert [m["content"] for m in msgs if m["role"] == "user"] == context.sent_texts
    assert [m["created_at"] for m in msgs] == sorted(m["created_at"] for m in msgs)


@then("todos os envios simultâneos tiveram status 201")
def all_concurrent_ok(context):
    assert [r.status_code for r in context.concurrent] == [201] * len(context.concurrent)
    users = sorted(m["content"] for m in bdd.messages(context) if m["role"] == "user")
    assert users == sorted(context.sent_texts)


def _background_result(context, content):
    thread, result = context.background[content]
    thread.join(timeout=15)
    assert not thread.is_alive() and "r" in result, f"envio em segundo plano de {content!r} não terminou"
    return result["r"]


@then('o envio em segundo plano de "{content:Q}" terminou com status {status:d}')
def background_status(context, content, status):
    assert _background_result(context, content).status_code == status


@then('o envio em segundo plano de "{content:Q}" terminou com status {status:d} e código de erro "{code:Q}"')
def background_error(context, content, status, code):
    assert_error(_background_result(context, content), status, code)


@then('as mensagens do usuário no histórico são apenas "{content:Q}"')
def only_user_messages(context, content):
    users = [m["content"] for m in bdd.messages(context) if m["role"] == "user"]
    assert users == [content], f"mensagem aceita após o encerramento: {users}"
