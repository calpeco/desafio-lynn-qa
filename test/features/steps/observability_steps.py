"""Steps de observabilidade: correlação por request id, logs estruturados e PII."""
from behave import then, when

from qa_support import bdd


@when('"{persona:Q}" envia a mensagem "{content:Q}" com o identificador de requisição "{rid:Q}"')
def send_with_request_id(context, persona, content, rid):
    bdd.send(context, persona, content, headers={"X-Request-ID": rid})


@when('"{persona:Q}" consulta a conversa "{raw_id:Q}" sem identificador de requisição')
def get_without_request_id(context, persona, raw_id):
    bdd.remember(context, bdd.client(context, persona).get_conversation(raw_id, headers={"X-Request-ID": ""}))


@then('os logs da requisição "{rid:Q}" contêm os eventos "{raw:Q}"')
def logs_have_events(context, rid, raw):
    events = [l["event"] for l in context.control.logs() if l.get("request_id") == rid]
    for e in bdd.terms(raw):
        assert e in events, f"evento {e!r} ausente: {events}"


@then('o evento de log "{event:Q}" contém os campos "{raw:Q}"')
def log_has_fields(context, event, raw):
    entry = next((l for l in context.control.logs() if l["event"] == event), None)
    assert entry, f"evento {event!r} não encontrado"
    for f in bdd.terms(raw):
        assert f in entry, f"log sem {f!r} (necessário para SLO/custo): {entry}"


@then('o evento de log "{event:Q}" da requisição "{rid:Q}" tem "{field:Q}" igual a "{value:Q}"')
def log_field_equals(context, event, rid, field, value):
    entries = [l for l in context.control.logs() if l["event"] == event and l.get("request_id") == rid]
    assert entries and str(entries[0].get(field)) == value, entries


@then('os logs não contêm "{raw:Q}"')
def logs_do_not_contain(context, raw):
    dump = str(context.control.logs())
    for t in bdd.terms(raw):
        assert t not in dump, f"{t!r} encontrado nos logs (PII/credencial)"
